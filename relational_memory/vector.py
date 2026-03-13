"""7D Relational Vector with EMA update."""

import json
from datetime import datetime, timezone
from pathlib import Path

DIMENSIONS = ["formality", "warmth", "humor", "depth", "trust", "energy", "resilience"]
DEFAULT_VECTOR = {d: 0.5 for d in DIMENSIONS}
ALPHA_NORMAL = 0.9


class RelationalVector:
    def __init__(self, values: dict[str, float] | None = None, session_count: int = 0,
                 last_updated: str | None = None):
        self.values = dict(values) if values else dict(DEFAULT_VECTOR)
        self.session_count = session_count
        self.last_updated = last_updated or datetime.now(timezone.utc).isoformat()

    def update(self, signals: dict[str, dict], alpha_override: float | None = None):
        """Update vector with extracted signals via EMA.

        signals: {"formality": {"value": 0.3, "signal": "..."}, ...}
        alpha_override: force a specific alpha (e.g. for explicit corrections in v2)
        """
        for dim in DIMENSIONS:
            if dim not in signals:
                continue
            signal_value = signals[dim]["value"]
            alpha = alpha_override if alpha_override is not None else ALPHA_NORMAL
            self.values[dim] = alpha * self.values[dim] + (1 - alpha) * signal_value

        self.session_count += 1
        self.last_updated = datetime.now(timezone.utc).isoformat()

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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "RelationalVector":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)
