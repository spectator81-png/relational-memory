#!/usr/bin/env python3
"""Read all data needed for sleep-time condensation and output as text.

Used by the /sleep command — Claude Code does the condensation itself,
this script just reads and formats the input data.
"""

import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
from config import get_user_id, get_storage_paths, check_library

check_library()

from relational_memory import (
    RelationalVector,
    LayerStore,
    load_signal_log,
    should_condense,
)


def main():
    user_id = get_user_id()
    paths = get_storage_paths(user_id)

    vector = RelationalVector.load(paths["vector"])
    layers = LayerStore(paths["layers"])
    signal_log = load_signal_log(paths["signal_log"])

    if not signal_log:
        print("FEHLER: Keine Signal-History vorhanden. Führe zuerst /memory-save aus.")
        sys.exit(2)

    # Output structured data for Claude to process
    print(f"USER_ID: {user_id}")
    print(f"SESSIONS: {vector.session_count}")
    print(f"SIGNALS: {len(signal_log)}")
    print()

    # Current vector
    print("=== CURRENT VECTOR ===")
    vector_text = ", ".join(f"{k}={v:.2f}" for k, v in vector.values.items())
    print(vector_text)
    print()

    # Current layers
    print("=== CURRENT LAYERS ===")
    bt = layers.read_base_tone()
    pt = layers.read_patterns()
    an = layers.read_anchors()
    print(f"Base Tone:\n{bt or '(leer — erste Condensation)'}")
    print(f"\nPatterns:\n{pt or '(leer — erste Condensation)'}")
    print(f"\nAnchors:\n{an or '(leer — erste Condensation)'}")
    print()

    # Signal log
    print("=== SIGNAL LOG ===")
    print(json.dumps(signal_log, indent=2, ensure_ascii=False))
    print()

    # Storage path for write-back
    print(f"=== PATHS ===")
    print(f"LAYERS_DIR: {paths['layers']}")
    print(f"SIGNAL_LOG: {paths['signal_log']}")


if __name__ == "__main__":
    main()
