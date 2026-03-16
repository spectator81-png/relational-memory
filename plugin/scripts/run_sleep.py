#!/usr/bin/env python3
"""Run sleep-time condensation — distill signal history into layers.

Requires ANTHROPIC_API_KEY (or another provider key) for the Haiku/Mini LLM call.
"""

import sys
from pathlib import Path

# Windows cp1252 can't handle Unicode bar chars — force UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
from config import get_user_id, get_storage_paths, check_library

check_library()

from relational_memory import (
    RelationalVector,
    LayerStore,
    LLMClient,
    LLMConfigError,
    LLMAuthError,
    should_condense,
    condense,
    load_signal_log,
)


def main():
    user_id = get_user_id()
    paths = get_storage_paths(user_id)

    # Load state
    vector = RelationalVector.load(paths["vector"])
    layers = LayerStore(paths["layers"])
    signal_log = load_signal_log(paths["signal_log"])

    if not signal_log:
        print("Keine Signal-History vorhanden. Führe zuerst /memory-save aus.")
        return

    print(f"  Sleep-Time Condensation — User: {user_id}")
    print(f"  Sessions: {vector.session_count} | Signale: {len(signal_log)}")

    # Show current layers (before)
    print(f"\n  VORHER:")
    bt = layers.read_base_tone()
    print(f"  Base Tone: {bt[:80] + '...' if bt and len(bt) > 80 else bt or '(leer)'}")
    pt = layers.read_patterns()
    print(f"  Patterns:  {pt[:80] + '...' if pt and len(pt) > 80 else pt or '(leer)'}")
    an = layers.read_anchors()
    print(f"  Anchors:   {an[:80] + '...' if an and len(an) > 80 else an or '(leer)'}")

    # Determine provider from env
    import os
    provider = os.environ.get("RELATIONAL_MEMORY_PROVIDER", "anthropic")

    try:
        llm = LLMClient(provider=provider)
    except LLMConfigError as e:
        print(f"\n  FEHLER: {e}", file=sys.stderr)
        print(
            "  Für Sleep-Time wird ein LLM-Provider benötigt.\n"
            "  Installation: pip install relational-memory[anthropic]\n"
            "  Dann: ANTHROPIC_API_KEY als Umgebungsvariable setzen.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Run condensation
    try:
        condense(paths["signal_log"], layers, vector, llm)
    except LLMAuthError as e:
        print(f"\n  FEHLER: Authentifizierung fehlgeschlagen: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"\n  FEHLER: Condensation fehlgeschlagen: {e}", file=sys.stderr)
        sys.exit(2)

    # Show updated layers (after)
    print(f"\n  NACHHER:")
    bt = layers.read_base_tone()
    print(f"  Base Tone: {bt[:120] + '...' if bt and len(bt) > 120 else bt or '(leer)'}")
    pt = layers.read_patterns()
    print(f"  Patterns:  {pt[:120] + '...' if pt and len(pt) > 120 else pt or '(leer)'}")
    an = layers.read_anchors()
    print(f"  Anchors:   {an[:120] + '...' if an and len(an) > 120 else an or '(leer)'}")

    if not should_condense(vector.session_count):
        print(f"\n  Hinweis: Nächste automatische Condensation bei Session #{vector.session_count + (5 - vector.session_count % 5)}")


if __name__ == "__main__":
    main()
