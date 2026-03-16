"""API-agnostic LLM wrapper with streaming and prompt caching.

Supported providers:
  - anthropic: Claude (default)
  - openai: GPT-4o / GPT-4o-mini
  - google: Gemini 2.0 Flash / Pro
  - local: Any OpenAI-compatible API (Ollama, llama.cpp, vLLM, LM Studio)
"""

import os
from typing import Generator


class LLMConfigError(Exception):
    """Raised when LLM provider is misconfigured (missing package or API key)."""


class LLMAuthError(Exception):
    """Raised when API authentication fails."""


PROVIDERS = ("anthropic", "openai", "google", "local")


class LLMClient:
    def __init__(self, provider: str = "anthropic"):
        if provider not in PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Supported: {', '.join(PROVIDERS)}"
            )
        self.provider = provider
        self._client = None

    @property
    def client(self):
        if self._client is not None:
            return self._client

        if self.provider == "anthropic":
            self._client = self._init_anthropic()
        elif self.provider == "openai":
            self._client = self._init_openai()
        elif self.provider == "google":
            self._client = self._init_google()
        elif self.provider == "local":
            self._client = self._init_local()

        return self._client

    # --- Initialization ---

    def _init_anthropic(self):
        try:
            import anthropic
        except ImportError:
            raise LLMConfigError(
                "Anthropic package not installed. Run: pip install anthropic"
            )
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMConfigError(
                "ANTHROPIC_API_KEY environment variable not set"
            )
        return anthropic.Anthropic()

    def _init_openai(self):
        try:
            import openai
        except ImportError:
            raise LLMConfigError(
                "OpenAI package not installed. Run: pip install openai"
            )
        if not os.environ.get("OPENAI_API_KEY"):
            raise LLMConfigError(
                "OPENAI_API_KEY environment variable not set"
            )
        return openai.OpenAI()

    def _init_google(self):
        try:
            from google import genai
        except ImportError:
            raise LLMConfigError(
                "Google GenAI package not installed. Run: pip install google-genai"
            )
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise LLMConfigError(
                "GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set"
            )
        return genai.Client(api_key=api_key)

    def _init_local(self):
        """Initialize OpenAI-compatible client for local models (Ollama, llama.cpp, vLLM)."""
        try:
            import openai
        except ImportError:
            raise LLMConfigError(
                "OpenAI package not installed (needed for local provider). Run: pip install openai"
            )
        base_url = os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/v1")
        return openai.OpenAI(
            base_url=base_url,
            api_key=os.environ.get("LOCAL_LLM_KEY", "not-needed"),
        )

    # --- Chat streaming ---

    def chat_stream(self, system: str, messages: list[dict],
                    model: str | None = None) -> Generator[str, None, str]:
        """Stream chat responses. Yields text chunks, returns full response."""
        if self.provider == "anthropic":
            return self._anthropic_stream(system, messages, model or "claude-opus-4-6")
        elif self.provider == "openai":
            return self._openai_stream(system, messages, model or "gpt-4o")
        elif self.provider == "google":
            return self._google_stream(system, messages, model or "gemini-2.0-flash")
        elif self.provider == "local":
            local_model = model or os.environ.get("LOCAL_LLM_MODEL", "llama3.2")
            return self._openai_stream(system, messages, local_model)

    def _anthropic_stream(self, system: str, messages: list[dict],
                          model: str) -> Generator[str, None, str]:
        import anthropic
        full_text = ""
        try:
            with self.client.messages.stream(
                model=model,
                max_tokens=4096,
                system=[{
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    full_text += text
                    yield text
        except anthropic.RateLimitError as e:
            retry_after = e.response.headers.get("retry-after", "60")
            raise RuntimeError(
                f"Rate limit hit. Retry after {retry_after}s."
            ) from e
        except anthropic.AuthenticationError as e:
            raise LLMAuthError("ANTHROPIC_API_KEY is invalid.") from e
        return full_text

    def _openai_stream(self, system: str, messages: list[dict],
                       model: str) -> Generator[str, None, str]:
        import openai
        full_text = ""
        oai_messages = [{"role": "system", "content": system}] + messages
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=oai_messages,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_text += delta.content
                    yield delta.content
        except openai.RateLimitError as e:
            raise RuntimeError(f"Rate limit hit: {e}") from e
        except openai.AuthenticationError as e:
            raise LLMAuthError(f"API key is invalid: {e}") from e
        except openai.APIConnectionError as e:
            raise RuntimeError(f"Connection failed: {e}") from e
        return full_text

    def _google_stream(self, system: str, messages: list[dict],
                       model: str) -> Generator[str, None, str]:
        from google.genai import types

        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ("user", "human") else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg.get("content", ""))],
            ))

        full_text = ""
        try:
            response = self.client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=4096,
                ),
            )
            for chunk in response:
                if chunk.text:
                    full_text += chunk.text
                    yield chunk.text
        except Exception as e:
            err_str = str(e).lower()
            if "quota" in err_str or "rate" in err_str or "429" in err_str:
                raise RuntimeError(f"Rate limit hit: {e}") from e
            elif "api key" in err_str or "401" in err_str or "403" in err_str:
                raise LLMAuthError(f"Google API key is invalid: {e}") from e
            raise
        return full_text

    # --- Non-streaming extraction ---

    def extract(self, system: str, user_prompt: str,
                model: str | None = None) -> str:
        """Non-streaming call for signal extraction / condensation (cheap model).
        Uses prompt caching on the system block for Anthropic."""
        if self.provider == "anthropic":
            return self._anthropic_extract(system, user_prompt,
                                           model or "claude-haiku-4-5-20251001")
        elif self.provider == "openai":
            return self._openai_extract(system, user_prompt,
                                        model or "gpt-4o-mini")
        elif self.provider == "google":
            return self._google_extract(system, user_prompt,
                                        model or "gemini-2.0-flash")
        elif self.provider == "local":
            local_model = model or os.environ.get("LOCAL_LLM_EXTRACT_MODEL",
                                                  os.environ.get("LOCAL_LLM_MODEL", "llama3.2"))
            return self._openai_extract(system, user_prompt, local_model)

    def _anthropic_extract(self, system: str, user_prompt: str, model: str) -> str:
        import anthropic
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        except anthropic.RateLimitError as e:
            retry_after = e.response.headers.get("retry-after", "60")
            raise RuntimeError(
                f"Rate limit hit. Retry after {retry_after}s."
            ) from e
        except anthropic.AuthenticationError as e:
            raise LLMAuthError("ANTHROPIC_API_KEY is invalid.") from e

    def _openai_extract(self, system: str, user_prompt: str, model: str) -> str:
        import openai
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content
        except openai.RateLimitError as e:
            raise RuntimeError(f"Rate limit hit: {e}") from e
        except openai.AuthenticationError as e:
            raise LLMAuthError(f"API key is invalid: {e}") from e
        except openai.APIConnectionError as e:
            raise RuntimeError(f"Connection failed: {e}") from e

    def _google_extract(self, system: str, user_prompt: str, model: str) -> str:
        from google.genai import types

        try:
            response = self.client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=1024,
                ),
            )
            return response.text
        except Exception as e:
            err_str = str(e).lower()
            if "quota" in err_str or "rate" in err_str or "429" in err_str:
                raise RuntimeError(f"Rate limit hit: {e}") from e
            elif "api key" in err_str or "401" in err_str or "403" in err_str:
                raise LLMAuthError(f"Google API key is invalid: {e}") from e
            raise
