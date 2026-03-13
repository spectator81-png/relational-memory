"""Signal extraction from conversations using LLM-as-Judge."""

import json
from pathlib import Path

from .llm import LLMClient
from .vector import DIMENSIONS

PROMPT_PATH = Path(__file__).parent / "prompts" / "signal_extraction.md"


def _load_prompt() -> str:
    """Load the signal extraction prompt, stripping the markdown header."""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    # Remove the title line, keep everything from the role description
    if "# Signal Extraction Prompt v1\n\n" in text:
        text = text.split("# Signal Extraction Prompt v1\n\n", 1)[-1]
    # Remove the placeholder at the end — we'll append the conversation separately
    if "## Conversation to analyze" in text:
        text = text.rsplit("## Conversation to analyze", 1)[0].rstrip()
    return text


def format_conversation(messages: list[dict]) -> str:
    """Format chat messages into a readable transcript for the LLM judge.

    Accepts messages in the standard format: [{"role": "user"|"assistant", "content": "..."}]
    """
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and "text" in block:
                    parts.append(block["text"])
            content = "\n".join(parts)

        if not content or not content.strip():
            continue

        label = "Human" if role in ("human", "user") else "Assistant"
        lines.append(f"[{label}]\n{content.strip()}\n")

    return "\n".join(lines)


def extract_signals(messages: list[dict], llm: LLMClient) -> dict:
    """Extract 7 relational signals from a conversation.

    Returns: {"formality": {"value": 0.3, "signal": "..."}, ...}
    """
    prompt = _load_prompt()
    transcript = format_conversation(messages)

    # Truncate if too long (keep recent context)
    max_chars = 80_000
    if len(transcript) > max_chars:
        transcript = "...[truncated]...\n\n" + transcript[-max_chars:]

    user_prompt = (
        f"## Conversation to analyze\n\n{transcript}\n\n"
        "## Task\n\n"
        "Analyze the conversation above. Return ONLY the JSON object with 7 dimensions. "
        "Do NOT continue the conversation. Do NOT respond to the human. "
        "Output valid JSON only, nothing else."
    )
    raw = llm.extract(system=prompt, user_prompt=user_prompt)

    # Parse JSON from response (handle markdown code fences)
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    return json.loads(text)


def save_signal_log(signals: dict, log_path: Path):
    """Append signals to the session signal log."""
    from datetime import datetime, timezone

    log_path.parent.mkdir(parents=True, exist_ok=True)

    entries = []
    if log_path.exists():
        entries = json.loads(log_path.read_text(encoding="utf-8"))

    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
    })

    log_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")


def load_signal_log(log_path: Path) -> list[dict]:
    """Load the signal log."""
    if not log_path.exists():
        return []
    return json.loads(log_path.read_text(encoding="utf-8"))
