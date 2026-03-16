"""Message truncation with sliding window for context management.

Prevents unbounded message list growth that would hit context limits.
Strategy: Keep the most recent N messages in full, summarize older ones.
"""

import logging

logger = logging.getLogger(__name__)

# Default window sizes
FULL_WINDOW = 20       # Keep last N messages in full
SUMMARY_MAX_CHARS = 500  # Max length for the summary of older messages


def truncate_messages(
    messages: list[dict],
    full_window: int = FULL_WINDOW,
) -> list[dict]:
    """Apply sliding window truncation to a message list.

    If len(messages) <= full_window, returns messages unchanged.
    Otherwise, replaces older messages with a summary message.

    Returns a new list (does not modify the original).
    """
    if len(messages) <= full_window:
        return list(messages)

    # Split into old (to summarize) and recent (to keep)
    old_messages = messages[:-full_window]
    recent_messages = messages[-full_window:]

    # Build summary of old messages
    summary_parts = []
    turn_count = 0
    for msg in old_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, list):
            # Handle structured content blocks
            texts = []
            for block in content:
                if isinstance(block, str):
                    texts.append(block)
                elif isinstance(block, dict) and "text" in block:
                    texts.append(block["text"])
            content = " ".join(texts)

        # Truncate individual messages in summary
        if len(content) > 100:
            content = content[:97] + "..."
        summary_parts.append(f"[{role}]: {content}")
        turn_count += 1

    summary_text = "\n".join(summary_parts)

    # Truncate overall summary if too long
    if len(summary_text) > SUMMARY_MAX_CHARS:
        summary_text = summary_text[:SUMMARY_MAX_CHARS - 3] + "..."

    # Create summary message
    summary_msg = {
        "role": "user",
        "content": (
            f"[Earlier in this conversation ({turn_count} messages summarized):\n"
            f"{summary_text}\n"
            f"...end of summary. The conversation continues below.]"
        ),
    }

    logger.info(
        "Truncated %d messages to summary + %d recent messages",
        len(old_messages), len(recent_messages),
    )

    return [summary_msg] + list(recent_messages)
