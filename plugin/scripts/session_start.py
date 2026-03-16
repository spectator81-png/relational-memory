#!/usr/bin/env python3
"""SessionStart hook — load relational context and inject into Claude's system prompt."""

import json
import os
import sys
from pathlib import Path

# Add scripts/ to path for config import
sys.path.insert(0, str(Path(__file__).parent))
from config import get_user_id, get_storage_paths, check_library

check_library()

from relational_memory import (
    RelationalVector,
    LayerStore,
    assemble_context,
)


def main():
    user_id = get_user_id()
    paths = get_storage_paths(user_id)

    # Persist user ID and storage path for other scripts in this session
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if env_file:
        try:
            with open(env_file, "a", encoding="utf-8") as f:
                f.write(f"RELATIONAL_MEMORY_USER={user_id}\n")
                f.write(f"RELATIONAL_MEMORY_STORAGE={paths['base']}\n")
        except OSError:
            pass  # Non-critical: scripts can still resolve user ID themselves

    # Load vector (fresh start if not exists)
    vector = RelationalVector.load(paths["vector"])
    layers = LayerStore(paths["layers"])

    # First-time user: no context yet
    if vector.session_count == 0 and not layers.is_initialized():
        context = (
            "Relational Memory aktiv (erste Session). "
            "Noch kein Beziehungskontext vorhanden — wird automatisch am Session-Ende aufgebaut. "
            "Kommuniziere natürlich, die Signale werden am Ende extrahiert."
        )
        result = {
            "systemMessage": context,
            "suppressOutput": True,
        }
        print(json.dumps(result))
        return

    # Assemble relational context from vector + layers + drift detection
    signal_log_path = paths["signal_log"] if paths["signal_log"].exists() else None
    context = assemble_context(vector, layers, signal_log_path)

    result = {
        "systemMessage": context,
        "suppressOutput": True,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
