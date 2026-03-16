"""Shared configuration for relational-memory plugin scripts."""

import os
import re
from pathlib import Path

DEFAULT_USER = "default"
DEFAULT_STORAGE = Path.home() / ".relational_memory"
LOCAL_MD_NAME = "relational-memory.local.md"


def _parse_local_md_user(project_dir: str | None = None) -> str | None:
    """Read user ID from .claude/relational-memory.local.md YAML frontmatter.

    Searches in project directory first, then home directory.
    """
    candidates = []
    if project_dir:
        candidates.append(Path(project_dir) / ".claude" / LOCAL_MD_NAME)
    candidates.append(Path.home() / ".claude" / LOCAL_MD_NAME)

    for path in candidates:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
            # Parse YAML frontmatter (between --- delimiters)
            match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if not match:
                continue
            frontmatter = match.group(1)
            for line in frontmatter.splitlines():
                line = line.strip()
                if line.startswith("user:"):
                    value = line[5:].strip().strip('"').strip("'")
                    if value:
                        return value
        except (OSError, UnicodeDecodeError):
            continue
    return None


def get_user_id() -> str:
    """Determine user ID with 3-level fallback.

    1. RELATIONAL_MEMORY_USER environment variable
    2. .claude/relational-memory.local.md frontmatter (project → global)
    3. "default"
    """
    # 1. Environment variable
    env_user = os.environ.get("RELATIONAL_MEMORY_USER", "").strip()
    if env_user:
        return env_user

    # 2. .local.md config
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    local_user = _parse_local_md_user(project_dir)
    if local_user:
        return local_user

    # 3. Default
    return DEFAULT_USER


def get_storage_paths(user_id: str) -> dict:
    """Return all storage paths for a given user."""
    base = DEFAULT_STORAGE / user_id
    return {
        "base": base,
        "vector": base / "vector.json",
        "signal_log": base / "signal_log.json",
        "layers": base / "layers",
        "temp_signals": base / "temp_signals.json",
    }


def check_library():
    """Check if relational-memory package is installed. Exit with helpful message if not."""
    try:
        import relational_memory  # noqa: F401
        return True
    except ImportError:
        import sys
        print(
            "FEHLER: relational-memory Package nicht installiert.\n"
            "Installation: pip install relational-memory\n"
            "Für Sleep-Time (Haiku): pip install relational-memory[anthropic]",
            file=sys.stderr,
        )
        sys.exit(2)
