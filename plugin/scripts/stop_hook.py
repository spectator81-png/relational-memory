#!/usr/bin/env python3
"""Stop hook — block once with auto-save instructions, then approve.

Uses a marker file to prevent loops:
1. No marker → create marker, block with instructions
2. Marker exists → delete marker, approve (we already blocked once)
3. Vector recently updated → approve (auto-save already succeeded)
"""

import json
import os
import sys
import time
from pathlib import Path

PLUGIN_ROOT = str(Path(__file__).parent.parent).replace("\\", "/")

sys.path.insert(0, str(Path(__file__).parent))
from config import get_user_id, get_storage_paths

APPROVE = json.dumps({"decision": "approve"})


def main():
    user_id = get_user_id()
    paths = get_storage_paths(user_id)
    vector_path = paths["vector"]
    marker_path = paths["base"] / ".auto_save_marker"

    # Ensure base directory exists
    paths["base"].mkdir(parents=True, exist_ok=True)

    # If vector was updated in the last 5 minutes → auto-save already ran
    if vector_path.exists():
        age = time.time() - vector_path.stat().st_mtime
        if age < 300:
            # Clean up marker if present
            marker_path.unlink(missing_ok=True)
            print(APPROVE)
            return

    # If marker exists → we already blocked once, approve now
    if marker_path.exists():
        marker_path.unlink(missing_ok=True)
        print(APPROVE)
        return

    # Read auto_save.md and resolve paths
    auto_save_path = Path(PLUGIN_ROOT) / "prompts" / "auto_save.md"
    if not auto_save_path.exists():
        print(APPROVE)
        return

    try:
        instructions = auto_save_path.read_text(encoding="utf-8")
    except OSError:
        print(APPROVE)
        return

    # Create marker so next call approves
    try:
        marker_path.write_text("pending", encoding="utf-8")
    except OSError:
        pass

    auto_save_resolved = str(auto_save_path).replace("\\", "/")
    reason = (
        f"Relational Memory Auto-Save: "
        f"Read {auto_save_resolved} and follow every step. "
        f"Plugin root: {PLUGIN_ROOT}"
    )
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
