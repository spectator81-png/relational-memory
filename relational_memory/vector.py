"""7D Relational Vector with EMA update."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .storage import secure_write_json

logger = logging.getLogger(__name__)

DIMENSIONS = ["formality", "warmth", "humor", "depth", "trust", "energy", "resilience"]
DEFAULT_VECTOR = {d: 0.5 for d in DIMENSIONS}
ALPHA_NORMAL = 0.9
ALPHA_CORRECTION = 0.5  # Fast learning when user explicitly corrects


class RelationalVector:
    def __init__(self, values: dict[str, float] | None = None, session_count: int = 0,
                 last_updated: str | None = None):
        self.values = dict(values) if values else dict(DEFAULT_VECTOR)
        self.session_count = session_count
        self.last_updated = last_updated or datetime.now(timezone.utc).isoformat()

    def update(self, signals: dict[str, dict], alpha_override: float | None = None):
        """Update vector with extracted signals via EMA.

        signals: {"formality": {"value": 0.3, "signal": "..."}, ...}
                 May contain "_explicit_corrections" key with list of corrections.
        alpha_override: force a specific alpha for ALL dimensions.
                        If None, uses ALPHA_NORMAL (0.9) for normal updates
                        and ALPHA_CORRECTION (0.5) for explicitly corrected dimensions.

        Returns the number of dimensions actually updated.
        """
        # Determine which dimensions have explicit corrections
        corrections = signals.get("_explicit_corrections", [])
        corrected_dims = set()
        if isinstance(corrections, list):
            for corr in corrections:
                dim = corr.get("dimension", "")
                if dim in DIMENSIONS:
                    corrected_dims.add(dim)

        updated_dims = []
        skipped_dims = []

        for dim in DIMENSIONS:
            if dim not in signals:
                skipped_dims.append(dim)
                continue
            signal_value = signals[dim]["value"]

            # Choose alpha: explicit override > correction-based > normal
            if alpha_override is not None:
                alpha = alpha_override
            elif dim in corrected_dims:
                alpha = ALPHA_CORRECTION
                logger.info(
                    "Dimension '%s' explicitly corrected — using fast alpha (%.1f)",
                    dim, ALPHA_CORRECTION,
                )
            else:
                alpha = ALPHA_NORMAL

            self.values[dim] = alpha * self.values[dim] + (1 - alpha) * signal_value
            updated_dims.append(dim)

        # Log skipped dimensions explicitly — don't let them disappear silently
        if skipped_dims:
            logger.warning(
                "Vector update: %d/%d dimensions skipped (missing from signals): %s",
                len(skipped_dims), len(DIMENSIONS), ", ".join(skipped_dims),
            )

        # Only increment session count if we actually updated something meaningful
        if len(updated_dims) >= 5:  # At least 5 of 7 dimensions must be present
            self.session_count += 1
            self.last_updated = datetime.now(timezone.utc).isoformat()
        else:
            logger.warning(
                "Vector update: only %d/%d dimensions updated — session count NOT incremented. "
                "This session's signals may be unreliable.",
                len(updated_dims), len(DIMENSIONS),
            )

        return len(updated_dims)

    def to_dict(self) -> dict:
        return {
            "values": self.values,
            "session_count": self.session_count,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RelationalVector":
        return cls(
            values=data.get("values", DEFAULT_VECTOR),
            session_count=data.get("session_count", 0),
            last_updated=data.get("last_updated"),
        )

    def save(self, path: Path):
        secure_write_json(path, self.to_dict())

    @classmethod
    def load(cls, path: Path) -> "RelationalVector":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Corrupted vector file %s: %s — starting fresh", path, e)
            return cls()
