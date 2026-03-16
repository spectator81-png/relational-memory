"""Signal extraction from conversations using LLM-as-Judge."""

import json
import logging
from pathlib import Path

from .llm import LLMClient
from .storage import secure_write_json
from .vector import DIMENSIONS

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "signal_extraction.md"

# Stuck detection: warn if a dimension varies less than this over N sessions
STUCK_VARIANCE_THRESHOLD = 0.02
STUCK_SESSION_COUNT = 3


def _load_prompt() -> str:
    """Load the signal extraction prompt, stripping the markdown header."""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    # Remove the title line (v1 or v2), keep everything from the role description
    for header in ("# Signal Extraction Prompt v2\n\n", "# Signal Extraction Prompt v1\n\n"):
        if header in text:
            text = text.split(header, 1)[-1]
            break
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


def validate_signals(raw_signals: dict) -> dict:
    """Validate and normalize extracted signals.

    - Ensures all 7 dimensions are present
    - Coerces values to float
    - Clamps to [0.0, 1.0]
    - Handles both v1 format (value+signal) and v2 format (evidence+value+signal)

    Returns normalized signals dict.
    Raises ValueError if too many dimensions are missing or malformed.
    """
    validated = {}
    missing = []
    coerced = []

    for dim in DIMENSIONS:
        if dim not in raw_signals:
            missing.append(dim)
            continue

        entry = raw_signals[dim]

        # Handle case where LLM returns just a number instead of a dict
        if isinstance(entry, (int, float)):
            entry = {"value": entry, "signal": "(no signal provided)"}
            coerced.append(dim)

        if not isinstance(entry, dict):
            missing.append(dim)
            logger.warning("Signal '%s': expected dict, got %s", dim, type(entry).__name__)
            continue

        # Extract and validate the value
        raw_value = entry.get("value")
        if raw_value is None:
            missing.append(dim)
            logger.warning("Signal '%s': no 'value' key in response", dim)
            continue

        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            missing.append(dim)
            logger.warning("Signal '%s': could not convert '%s' to float", dim, raw_value)
            continue

        # Clamp to valid range
        if value < 0.0 or value > 1.0:
            logger.warning("Signal '%s': value %.3f out of range, clamping to [0.0, 1.0]", dim, value)
            value = max(0.0, min(1.0, value))

        validated[dim] = {
            "value": value,
            "signal": entry.get("signal", "(no signal provided)"),
        }

        # Preserve evidence field from v2 format
        if "evidence" in entry:
            validated[dim]["evidence"] = entry["evidence"]

        # Preserve resilience type sub-score
        if dim == "resilience" and "type" in entry:
            rtype = str(entry["type"]).strip().lower()
            if rtype in ("relationship", "dependency", "untested"):
                validated[dim]["type"] = rtype
            else:
                logger.warning("Resilience type '%s' not recognized, defaulting to 'untested'", rtype)
                validated[dim]["type"] = "untested"

    # Log warnings
    if missing:
        logger.warning("Missing or invalid dimensions: %s", ", ".join(missing))
    if coerced:
        logger.warning("Coerced bare numbers to dicts: %s", ", ".join(coerced))

    # Fail hard if too many dimensions are broken
    if len(missing) > 2:
        raise ValueError(
            f"Signal extraction failed: {len(missing)}/7 dimensions missing or invalid "
            f"({', '.join(missing)}). Raw response may be malformed."
        )

    # Preserve explicit_corrections from v2 format
    corrections = raw_signals.get("explicit_corrections", [])
    if isinstance(corrections, list) and corrections:
        # Validate each correction entry
        valid_corrections = []
        for corr in corrections:
            if isinstance(corr, dict) and "dimension" in corr:
                valid_corrections.append({
                    "dimension": str(corr.get("dimension", "")),
                    "direction": str(corr.get("direction", "")),
                    "quote": str(corr.get("quote", "")),
                })
        if valid_corrections:
            validated["_explicit_corrections"] = valid_corrections
            logger.info(
                "Explicit corrections detected: %s",
                ", ".join(f"{c['dimension']} ({c['direction']})" for c in valid_corrections),
            )

    return validated


def check_stuck_dimensions(signals: dict, log_path: Path) -> list[str]:
    """Check if any dimension has been stuck (low variance) over recent sessions.

    Returns list of dimension names that appear stuck.
    """
    if not log_path.exists():
        return []

    log = load_signal_log(log_path)
    if len(log) < STUCK_SESSION_COUNT:
        return []

    recent = log[-STUCK_SESSION_COUNT:]
    stuck = []

    for dim in DIMENSIONS:
        values = []
        for entry in recent:
            sig = entry.get("signals", {}).get(dim, {})
            if isinstance(sig, dict) and "value" in sig:
                values.append(sig["value"])

        if len(values) < STUCK_SESSION_COUNT:
            continue

        variance = max(values) - min(values)
        if variance < STUCK_VARIANCE_THRESHOLD:
            stuck.append(dim)
            logger.warning(
                "Dimension '%s' appears stuck: last %d values = %s (variance %.3f < %.3f)",
                dim, STUCK_SESSION_COUNT, [f"{v:.2f}" for v in values],
                variance, STUCK_VARIANCE_THRESHOLD,
            )

    return stuck


def _parse_llm_json(raw: str) -> dict:
    """Parse JSON from LLM response, handling code fences and surrounding text."""
    text = raw.strip()

    # Remove markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    # Extract JSON object from surrounding text
    if "{" in text:
        start = text.index("{")
        # Find the matching closing brace (handle nested objects)
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    text = text[start:i + 1]
                    break

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Provide context for debugging
        preview = text[:200] + "..." if len(text) > 200 else text
        raise ValueError(
            f"LLM returned invalid JSON: {e}\nResponse preview: {preview}"
        ) from e


def extract_signals(messages: list[dict], llm: LLMClient) -> dict:
    """Extract 7 relational signals from a conversation.

    Returns validated dict: {"formality": {"value": 0.3, "signal": "...", "evidence": "..."}, ...}
    Raises ValueError if signal extraction fails validation or conversation is empty.
    """
    if not messages:
        raise ValueError("Cannot extract signals from empty conversation.")

    # Filter to messages with actual content
    valid = [m for m in messages if m.get("content")]
    if not valid:
        raise ValueError("No messages with content to analyze.")

    if len(valid) == 1:
        logger.warning("Single-message session — signal extraction may be limited")

    prompt = _load_prompt()
    transcript = format_conversation(valid)

    if not transcript.strip():
        raise ValueError("Conversation produced empty transcript after formatting.")

    # Truncate if too long (keep recent context)
    max_chars = 80_000
    if len(transcript) > max_chars:
        logger.info(
            "Transcript truncated: %d → %d chars (keeping recent context)",
            len(transcript), max_chars,
        )
        transcript = "...[truncated]...\n\n" + transcript[-max_chars:]

    user_prompt = (
        f"## Conversation to analyze\n\n{transcript}\n\n"
        "## Task\n\n"
        "Analyze the conversation above. Return ONLY the JSON object with all 7 dimensions. "
        "Each dimension MUST include 'evidence', 'value', and 'signal' fields. "
        "Do NOT continue the conversation. Do NOT respond to the human. "
        "Output valid JSON only, nothing else."
    )
    raw = llm.extract(system=prompt, user_prompt=user_prompt)
    raw_signals = _parse_llm_json(raw)

    # Validate and normalize
    return validate_signals(raw_signals)


def save_signal_log(signals: dict, log_path: Path):
    """Append signals to the session signal log."""
    from datetime import datetime, timezone

    entries = []
    if log_path.exists():
        try:
            entries = json.loads(log_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            logger.warning("Corrupted signal log %s: %s — starting fresh", log_path, e)
            entries = []

    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
    })

    secure_write_json(log_path, entries)


def load_signal_log(log_path: Path) -> list[dict]:
    """Load the signal log."""
    if not log_path.exists():
        return []
    try:
        data = json.loads(log_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError as e:
        logger.warning("Corrupted signal log %s: %s", log_path, e)
        return []
