"""API-agnostic LLM wrapper with streaming and prompt caching."""

import os
import sys
from typing import Generator


class LLMClient:
    def __init__(self, provider: str = "anthropic"):
        self.provider = provider
        self._client = None

    @property
    def client(self):
        if self._client is not None:
            return self._client

        if self.provider == "anthropic":
            try:
                import anthropic
            except ImportError:
                print("ERROR: pip install anthropic")
                sys.exit(1)
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("ERROR: ANTHROPIC_API_KEY not set")
                sys.exit(1)
            self._client = anthropic.Anthropic()
        elif self.provider == "openai":
            try:
                import openai
            except ImportError:
                print("ERROR: pip install openai")
                sys.exit(1)
            if not os.environ.get("OPENAI_API_KEY"):
                print("ERROR: OPENAI_API_KEY not set")
                sys.exit(1)
            self._client = openai.OpenAI()
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        return self._client

    def chat_stream(self, system: str, messages: list[dict],
                    model: str | None = None) -> Generator[str, None, str]:
        """Stream chat responses. Yields text chunks, returns full response."""
        if self.provider == "anthropic":
            return self._anthropic_stream(system, messages, model or "claude-opus-4-6")
        elif self.provider == "openai":
            return self._openai_stream(system, messages, model or "gpt-4o")

    def _anthropic_stream(self, system: str, messages: list[dict],
                          model: str) -> Generator[str, None, str]:
        import anthropic
        full_text = ""
        try:
            with self.client.messages.stream(
                model=model,
                max_tokens=4096,
                system=system,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    full_text += text
                    yield text
        except anthropic.RateLimitError as e:
            retry_after = e.response.headers.get("retry-after", "60")
            print(f"\nRate limit hit. Retry after {retry_after}s.")
            raise
        except anthropic.AuthenticationError:
            print("\nANTHROPIC_API_KEY invalid.")
            sys.exit(1)
        return full_text

    def _openai_stream(self, system: str, messages: list[dict],
                       model: str) -> Generator[str, None, str]:
        full_text = ""
        oai_messages = [{"role": "system", "content": system}] + messages
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
        return full_text

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
            print(f"\nRate limit hit. Retry after {retry_after}s.")
            raise
        except anthropic.AuthenticationError:
            print("\nANTHROPIC_API_KEY invalid.")
            sys.exit(1)

    def _openai_extract(self, system: str, user_prompt: str, model: str) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content
