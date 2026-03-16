"""Secure file I/O with restricted permissions.

On Unix/Mac: directories get 0o700 (owner-only), files get 0o600.
On Windows: best-effort via icacls (removes Authenticated Users inheritance).
"""

import json
import logging
import os
import platform
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"


def secure_mkdir(path: Path) -> Path:
    """Create directory with restricted permissions (owner-only access)."""
    path.mkdir(parents=True, exist_ok=True)

    if not IS_WINDOWS:
        try:
            os.chmod(path, stat.S_IRWXU)  # 0o700
        except OSError as e:
            logger.warning("Could not set permissions on %s: %s", path, e)
    else:
        _windows_restrict(path)

    return path


def secure_write_text(path: Path, content: str, encoding: str = "utf-8"):
    """Write text file with restricted permissions."""
    secure_mkdir(path.parent)
    path.write_text(content, encoding=encoding)
    _restrict_file(path)


def secure_write_json(path: Path, data, indent: int = 2):
    """Write JSON file with restricted permissions."""
    secure_mkdir(path.parent)
    path.write_text(
        json.dumps(data, indent=indent, ensure_ascii=False),
        encoding="utf-8",
    )
    _restrict_file(path)


def _restrict_file(path: Path):
    """Restrict file to owner-only access."""
    if not IS_WINDOWS:
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        except OSError as e:
            logger.warning("Could not set permissions on %s: %s", path, e)
    else:
        _windows_restrict(path)


def _windows_restrict(path: Path):
    """Best-effort permission restriction on Windows via icacls.

    Disables inheritance (copies existing ACEs as explicit), then removes
    access for 'Everyone' and 'Users' groups. Does NOT strip all inherited
    permissions to avoid locking out the owner.
    Falls back silently if icacls is not available.
    """
    try:
        import subprocess

        # /inheritance:d → copy inherited ACEs as explicit (safe, preserves access)
        subprocess.run(
            ["icacls", str(path), "/inheritance:d"],
            capture_output=True,
            timeout=5,
        )
        # Remove broad groups (best-effort, ignores errors for non-existent groups)
        for group in ("Everyone", "Users", "BUILTIN\\Users"):
            subprocess.run(
                ["icacls", str(path), "/remove", group],
                capture_output=True,
                timeout=5,
            )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        logger.debug("Windows permission restriction skipped: %s", e)
