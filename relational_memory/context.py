"""Assemble relational context for system prompt injection."""

from pathlib import Path

from .drift import detect_drift, format_drift_warning
from .layers import LayerStore
from .signals import load_signal_log
from .vector import RelationalVector

TEMPLATE_PATH = Path(__file__).parent / "prompts" / "context_template.md"


def assemble_context(
    vector: RelationalVector,
    layers: LayerStore,
    signal_log_path: Path | None = None,
) -> str:
    """Build the relational system prompt block (~300-600 tokens).

    Args:
        vector: Current relationship vector.
        layers: Layer store with base_tone, patterns, anchors.
        signal_log_path: Optional path to signal log for drift detection.
    """
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    # Layer content (empty string if not yet initialized)
    base_tone = layers.read_base_tone() or "(Not yet formed — too few sessions)"
    patterns = layers.read_patterns() or "(No patterns detected yet)"
    anchors = layers.read_anchors() or "(No anchor moments yet)"

    # Resilience guidance
    resilience = vector.values.get("resilience", 0.5)
    if resilience > 0.7:
        resilience_guidance = (
            "This relationship handles directness well. Push back when you disagree. "
            "Be honest even when it's uncomfortable — the relationship can take it."
        )
    elif resilience < 0.3:
        resilience_guidance = (
            "This relationship is still forming. Be gentle with disagreements. "
            "Frame challenges as questions, not statements. Build trust first."
        )
    else:
        resilience_guidance = (
            "Balance directness with tact. You can disagree, but frame it constructively."
        )

    # Drift detection (if signal log available)
    drift_warning = ""
    if signal_log_path and signal_log_path.exists():
        signal_log = load_signal_log(signal_log_path)
        drift_alerts = detect_drift(vector, signal_log)
        if drift_alerts:
            drift_warning = "\n\n" + format_drift_warning(drift_alerts)

    # Fill template
    result = template.format(
        base_tone=base_tone,
        patterns=patterns,
        anchors=anchors,
        formality=f"{vector.values['formality']:.2f}",
        warmth=f"{vector.values['warmth']:.2f}",
        humor=f"{vector.values['humor']:.2f}",
        depth=f"{vector.values['depth']:.2f}",
        trust=f"{vector.values['trust']:.2f}",
        energy=f"{vector.values['energy']:.2f}",
        resilience=f"{resilience:.2f}",
        resilience_guidance=resilience_guidance,
        session_count=vector.session_count,
    )

    # Append drift warning after the template (not inside it, to avoid format issues)
    if drift_warning:
        result += drift_warning

    return result.strip()
