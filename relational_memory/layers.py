"""3-layer relational memory store (base_tone, patterns, anchors).

v2.1: Timestamped versioning — every write creates a version snapshot.
Versions are stored in layers/versions/ and pruned to MAX_VERSIONS.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from .storage import secure_mkdir, secure_write_text

logger = logging.getLogger(__name__)

LAYER_NAMES = ("base_tone", "patterns", "anchors")
MAX_VERSIONS = 10


class LayerStore:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        secure_mkdir(base_path)
        self._versions_path = base_path / "versions"

    def _read(self, name: str) -> str:
        path = self.base_path / f"{name}.md"
        if path.exists():
            try:
                return path.read_text(encoding="utf-8").strip()
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("Could not read layer %s: %s", path, e)
                return ""
        return ""

    def _write(self, name: str, content: str):
        secure_write_text(
            self.base_path / f"{name}.md",
            content.strip() + "\n",
        )

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
            for name in LAYER_NAMES
        )

    # --- Versioning ---

    def save_version(self, label: str = "") -> str | None:
        """Snapshot all current layers into versions/ with a timestamp.

        Returns the version ID (timestamp string) or None if no layers exist.
        """
        if not self.is_initialized():
            return None

        secure_mkdir(self._versions_path)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        version_id = f"{ts}_{label}" if label else ts

        saved = 0
        for name in LAYER_NAMES:
            content = self._read(name)
            if content:
                secure_write_text(
                    self._versions_path / f"{name}_{version_id}.md",
                    content + "\n",
                )
                saved += 1

        if saved:
            logger.info("Layer version saved: %s (%d layers)", version_id, saved)
            self._prune_versions()
            return version_id
        return None

    def list_versions(self) -> list[str]:
        """List available version IDs, newest first."""
        if not self._versions_path.exists():
            return []

        # Extract unique version IDs from filenames
        # Format: base_tone_2026-03-16T14-30-00.md
        version_ids = set()
        for f in self._versions_path.glob("*.md"):
            # Remove layer name prefix
            stem = f.stem
            for name in LAYER_NAMES:
                prefix = f"{name}_"
                if stem.startswith(prefix):
                    version_ids.add(stem[len(prefix):])
                    break

        return sorted(version_ids, reverse=True)

    def restore_version(self, version_id: str) -> int:
        """Restore layers from a specific version.

        Returns the number of layers restored.
        """
        if not self._versions_path.exists():
            raise FileNotFoundError("No versions directory found")

        restored = 0
        for name in LAYER_NAMES:
            version_file = self._versions_path / f"{name}_{version_id}.md"
            if version_file.exists():
                content = version_file.read_text(encoding="utf-8").strip()
                if content:
                    self._write(name, content)
                    restored += 1

        if restored == 0:
            raise FileNotFoundError(f"No layers found for version '{version_id}'")

        logger.info("Restored %d layers from version %s", restored, version_id)
        return restored

    def _prune_versions(self):
        """Remove old versions beyond MAX_VERSIONS."""
        versions = self.list_versions()
        if len(versions) <= MAX_VERSIONS:
            return

        old_versions = versions[MAX_VERSIONS:]
        removed = 0
        for vid in old_versions:
            for name in LAYER_NAMES:
                vf = self._versions_path / f"{name}_{vid}.md"
                if vf.exists():
                    vf.unlink()
                    removed += 1

        if removed:
            logger.info("Pruned %d old version files (keeping last %d versions)",
                        removed, MAX_VERSIONS)
