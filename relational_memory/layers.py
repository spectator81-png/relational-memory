"""3-layer relational memory store (base_tone, patterns, anchors)."""

from pathlib import Path


class LayerStore:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _read(self, name: str) -> str:
        path = self.base_path / f"{name}.md"
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return ""

    def _write(self, name: str, content: str):
        path = self.base_path / f"{name}.md"
        path.write_text(content.strip() + "\n", encoding="utf-8")

    def read_base_tone(self) -> str:
        return self._read("base_tone")

    def read_patterns(self) -> str:
        return self._read("patterns")

    def read_anchors(self) -> str:
        return self._read("anchors")

    def write_base_tone(self, content: str):
        self._write("base_tone", content)

    def write_patterns(self, content: str):
        self._write("patterns", content)

    def write_anchors(self, content: str):
        self._write("anchors", content)

    def is_initialized(self) -> bool:
        return any(
            (self.base_path / f"{name}.md").exists()
            for name in ("base_tone", "patterns", "anchors")
        )
