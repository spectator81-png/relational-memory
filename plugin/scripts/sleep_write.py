#!/usr/bin/env python3
"""Write condensation results back to layers with versioned backup.

Reads JSON from ~/.relational_memory/<user>/temp_condensation.json,
creates a version backup of existing layers, writes new layers.
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
from relational_memory.storage import secure_write_json

MAX_SIGNAL_LOG_ENTRIES = 20


def main():
    user_id = get_user_id()
    paths = get_storage_paths(user_id)

    # Read condensation result from temp file
    temp_path = paths["base"] / "temp_condensation.json"
    if not temp_path.exists():
        print("FEHLER: Keine Condensation-Datei gefunden.", file=sys.stderr)
        print(f"Erwartet: {temp_path}", file=sys.stderr)
        sys.exit(2)

    try:
        result = json.loads(temp_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"FEHLER: Condensation-Datei nicht lesbar: {e}", file=sys.stderr)
        sys.exit(2)

    layers = LayerStore(paths["layers"])

    # Versioned backup before overwriting
    version_id = layers.save_version(label="pre-condensation")
    if version_id:
        print(f"  Version gesichert: {version_id}")

    # Write updated layers
    written = 0
    if result.get("base_tone"):
        layers.write_base_tone(result["base_tone"])
        print("  Base Tone aktualisiert")
        written += 1

    if result.get("patterns"):
        layers.write_patterns(result["patterns"])
        print("  Patterns aktualisiert")
        written += 1

    if result.get("anchors"):
        layers.write_anchors(result["anchors"])
        print("  Anchors aktualisiert")
        written += 1

    if written == 0:
        print("  WARNUNG: Keine Layers geschrieben — JSON war leer?")

    # Trim signal log
    signal_log = load_signal_log(paths["signal_log"])
    if len(signal_log) > MAX_SIGNAL_LOG_ENTRIES:
        signal_log = signal_log[-MAX_SIGNAL_LOG_ENTRIES:]
        secure_write_json(paths["signal_log"], signal_log)
        print(f"  Signal-Log auf {MAX_SIGNAL_LOG_ENTRIES} Einträge gekürzt")

    # Cleanup temp file
    try:
        temp_path.unlink()
    except OSError:
        pass

    # Next condensation info
    vector = RelationalVector.load(paths["vector"])
    if not should_condense(vector.session_count):
        next_at = vector.session_count + (5 - vector.session_count % 5)
        print(f"\n  Nächste Sleep-Time bei Session #{next_at}")

    print(f"\n  Sleep-Time abgeschlossen. ({written} Layer(s) aktualisiert)")


if __name__ == "__main__":
    main()
