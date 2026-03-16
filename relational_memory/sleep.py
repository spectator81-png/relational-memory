"""Sleep-time condensation agent — periodically distills signals into layers."""

import json
import logging
from pathlib import Path

from .layers import LayerStore
from .llm import LLMClient
from .signals import load_signal_log, _parse_llm_json
from .storage import secure_write_json
from .vector import RelationalVector

logger = logging.getLogger(__name__)

CONDENSATION_INTERVAL = 5  # Every 5 sessions
PROMPT_PATH = Path(__file__).parent / "prompts" / "condensation.md"
MAX_SIGNAL_LOG_ENTRIES = 20  # Keep only last 20 sessions in log


def should_condense(session_count: int) -> bool:
    return session_count > 0 and session_count % CONDENSATION_INTERVAL == 0


def condense(signal_log_path: Path, layers: LayerStore,
             vector: RelationalVector, llm: LLMClient):
    """Run the sleep-time condensation agent.

    Reads the signal log, sends it + current layers to the LLM,
    writes updated layers, and trims the signal log.
    Creates a timestamped version backup before overwriting.
    """
    signal_log = load_signal_log(signal_log_path)
    if not signal_log:
        logger.info("Empty signal log — skipping condensation")
        return

    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    # Format the signal log for the prompt
    log_text = json.dumps(signal_log, indent=2, ensure_ascii=False)

    # Format current vector
    vector_text = ", ".join(f"{k}={v:.2f}" for k, v in vector.values.items())

    # Fill the prompt
    prompt = prompt_template.format(
        signal_log=log_text,
        current_base_tone=layers.read_base_tone() or "(empty — first condensation)",
        current_patterns=layers.read_patterns() or "(empty — first condensation)",
        current_anchors=layers.read_anchors() or "(empty — first condensation)",
        current_vector=vector_text,
    )

    # Split: everything before "## Data to analyze" is system, rest is user
    if "## Data to analyze" in prompt:
        system_part = prompt.split("## Data to analyze")[0].rstrip()
        user_part = "## Data to analyze" + prompt.split("## Data to analyze")[1]
    else:
        system_part = prompt
        user_part = ""

    # Reinforce task instruction at the end of user prompt
    user_part += (
        "\n\n## Task\n\n"
        "Analyze the data above. Return ONLY the JSON object with base_tone, patterns, anchors. "
        "Do NOT explain your analysis. Output valid JSON only, nothing else."
    )

    # Versioned backup before overwriting (replaces simple .bak)
    version_id = layers.save_version(label="pre-condensation")
    if version_id:
        print(f"  [Sleep-Time] Version gesichert: {version_id}")

    print("\n  [Sleep-Time] Running condensation...")
    raw = llm.extract(system=system_part, user_prompt=user_part)

    # Parse response
    try:
        result = _parse_llm_json(raw)
    except ValueError as e:
        logger.error("Sleep-time condensation returned invalid JSON: %s", e)
        # Restore from version backup
        if version_id:
            try:
                restored = layers.restore_version(version_id)
                print(f"  [Sleep-Time] FEHLER: {restored} Layer(s) aus Version {version_id} wiederhergestellt")
            except FileNotFoundError:
                print("  [Sleep-Time] FEHLER: Konnte Layers nicht wiederherstellen")
        raise

    # Write updated layers
    if "base_tone" in result and result["base_tone"]:
        layers.write_base_tone(result["base_tone"])
        print("  [Sleep-Time] Base tone updated")

    if "patterns" in result and result["patterns"]:
        layers.write_patterns(result["patterns"])
        print("  [Sleep-Time] Patterns updated")

    if "anchors" in result and result["anchors"]:
        layers.write_anchors(result["anchors"])
        print("  [Sleep-Time] Anchors updated")

    # Trim signal log (keep last N entries)
    if len(signal_log) > MAX_SIGNAL_LOG_ENTRIES:
        signal_log = signal_log[-MAX_SIGNAL_LOG_ENTRIES:]
        secure_write_json(signal_log_path, signal_log)
        print(f"  [Sleep-Time] Signal log trimmed to {MAX_SIGNAL_LOG_ENTRIES} entries")

    print("  [Sleep-Time] Condensation complete.\n")
