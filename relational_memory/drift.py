"""Drift detection — monitors when the relationship vector shifts too far.

The "breaking point" concept: If the vector drifts so far from the AI's
established identity that it would no longer feel authentic, the system
should communicate this transparently rather than silently adapting.

This is NOT about preventing change — relationships evolve. It's about
detecting when adaptation would cross into inauthenticity.
"""

import logging
from pathlib import Path

from .vector import RelationalVector, DIMENSIONS

logger = logging.getLogger(__name__)

# How far a single dimension can drift from its baseline before triggering
DRIFT_THRESHOLD = 0.25

# Minimum sessions before drift detection activates
# (need enough data to establish a meaningful baseline)
MIN_SESSIONS_FOR_DRIFT = 5


def compute_baseline(signal_log: list[dict]) -> dict[str, float] | None:
    """Compute baseline values from signal history (average over all sessions).

    Returns dict of dimension -> average value, or None if not enough data.
    """
    if len(signal_log) < MIN_SESSIONS_FOR_DRIFT:
        return None

    sums = {d: 0.0 for d in DIMENSIONS}
    counts = {d: 0 for d in DIMENSIONS}

    for entry in signal_log:
        signals = entry.get("signals", {})
        for dim in DIMENSIONS:
            sig = signals.get(dim, {})
            if isinstance(sig, dict) and "value" in sig:
                sums[dim] += sig["value"]
                counts[dim] += 1

    baseline = {}
    for dim in DIMENSIONS:
        if counts[dim] > 0:
            baseline[dim] = sums[dim] / counts[dim]

    return baseline if len(baseline) == len(DIMENSIONS) else None


def detect_drift(
    vector: RelationalVector,
    signal_log: list[dict],
    threshold: float = DRIFT_THRESHOLD,
) -> list[dict]:
    """Detect dimensions where the current vector has drifted far from baseline.

    Returns list of drift alerts:
    [{"dimension": "formality", "baseline": 0.3, "current": 0.6, "drift": 0.3, "direction": "higher"}]
    """
    baseline = compute_baseline(signal_log)
    if baseline is None:
        return []

    alerts = []
    for dim in DIMENSIONS:
        if dim not in baseline:
            continue

        current = vector.values[dim]
        base = baseline[dim]
        drift = current - base

        if abs(drift) >= threshold:
            alerts.append({
                "dimension": dim,
                "baseline": round(base, 3),
                "current": round(current, 3),
                "drift": round(drift, 3),
                "direction": "higher" if drift > 0 else "lower",
            })
            logger.warning(
                "Drift detected: %s has shifted %.2f from baseline %.2f to %.2f",
                dim, drift, base, current,
            )

    return alerts


def format_drift_warning(alerts: list[dict]) -> str:
    """Format drift alerts into a human-readable warning for the system prompt.

    This text gets injected into the context so the AI can address it transparently.
    """
    if not alerts:
        return ""

    lines = [
        "DRIFT WARNING: The following dimensions have shifted significantly "
        "from the established baseline of this relationship:"
    ]
    for alert in alerts:
        dim = alert["dimension"]
        direction = alert["direction"]
        drift = abs(alert["drift"])
        lines.append(
            f"- {dim}: shifted {direction} by {drift:.2f} "
            f"(baseline {alert['baseline']:.2f} -> current {alert['current']:.2f})"
        )
    lines.append(
        "If this shift feels inauthentic or forced, consider addressing it "
        "transparently: 'I notice our dynamic has been shifting — is this intentional?'"
    )
    return "\n".join(lines)
