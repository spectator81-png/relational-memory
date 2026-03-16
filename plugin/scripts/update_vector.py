#!/usr/bin/env python3
"""Update relational vector from extracted signal JSON.

Reads signals from ~/.relational_memory/<user>/temp_signals.json,
validates them, runs EMA update, saves vector + signal log.
"""

import json
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
    validate_signals,
    save_signal_log,
    check_stuck_dimensions,
    should_condense,
)
from relational_memory.vector import DIMENSIONS


def main():
    user_id = get_user_id()
    paths = get_storage_paths(user_id)

    # Read signals from temp file
    temp_path = paths["temp_signals"]
    if not temp_path.exists():
        print("FEHLER: Keine Signal-Datei gefunden.", file=sys.stderr)
        print(f"Erwartet: {temp_path}", file=sys.stderr)
        sys.exit(2)

    try:
        raw_signals = json.loads(temp_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"FEHLER: Signal-Datei nicht lesbar: {e}", file=sys.stderr)
        sys.exit(2)

    # Validate signals
    try:
        signals = validate_signals(raw_signals)
    except ValueError as e:
        print(f"FEHLER: Signal-Validierung fehlgeschlagen: {e}", file=sys.stderr)
        sys.exit(2)

    # Load current vector
    vector = RelationalVector.load(paths["vector"])
    old_values = dict(vector.values)
    old_session = vector.session_count

    # EMA update
    dims_updated = vector.update(signals)

    # Save vector
    vector.save(paths["vector"])

    # Save signal log
    save_signal_log(signals, paths["signal_log"])

    # Clean up temp file
    try:
        temp_path.unlink()
    except OSError:
        pass

    # Output results
    print(f"\n  SIGNAL-EXTRAKTION — Session #{vector.session_count}")
    print(f"  {'='*50}\n")

    # Show signals with bar chart
    corrections = signals.get("_explicit_corrections", [])
    corrected_dims = {c.get("dimension") for c in corrections if isinstance(c, dict)}

    for dim in DIMENSIONS:
        data = signals.get(dim, {})
        value = data.get("value", 0.0)
        bar_len = int(value * 25)
        bar = "\u2588" * bar_len + "\u2591" * (25 - bar_len)
        print(f"  {dim:<14s} {bar} {value:.2f}")
        evidence = data.get("evidence")
        if evidence:
            ev_display = evidence[:100] + "..." if len(evidence) > 100 else evidence
            print(f"  {'':14s} \u2514\u2500 {ev_display}")

    # Show corrections
    if corrections:
        print(f"\n  EXPLIZITE KORREKTUREN:")
        for corr in corrections:
            if isinstance(corr, dict):
                dim = corr.get("dimension", "?")
                direction = corr.get("direction", "?")
                quote = corr.get("quote", "")
                alpha_label = "\u03b1=0.5" if dim in DIMENSIONS else ""
                print(f"    {dim} \u2192 {direction} {alpha_label}")
                if quote:
                    print(f"    \u2514\u2500 \"{quote}\"")

    # Show vector changes
    print(f"\n  VEKTOR-UPDATE (EMA)")
    for dim in DIMENSIONS:
        old = old_values[dim]
        new = vector.values[dim]
        arrow = "\u2191" if new > old + 0.01 else ("\u2193" if new < old - 0.01 else "\u2192")
        suffix = " *KORRIGIERT*" if dim in corrected_dims else ""
        print(f"  {dim:<14s} {old:.2f} {arrow} {new:.2f}{suffix}")

    if dims_updated < len(DIMENSIONS):
        print(f"\n  \u26a0 Nur {dims_updated}/{len(DIMENSIONS)} Dimensionen aktualisiert!")

    print(f"\n  Session #{vector.session_count} gespeichert. (User: {user_id})")

    # Stuck detection
    stuck = check_stuck_dimensions(signals, paths["signal_log"])
    if stuck:
        print(f"\n  \u26a0 STUCK: {', '.join(stuck)} variieren kaum \u2014 Prompt-Bias?")

    # Sleep-time reminder (AUTOSLEEP_DUE marker for auto_save.md)
    if should_condense(vector.session_count):
        print(f"\nAUTOSLEEP_DUE=true")
        print(f"\n  \u2728 Session #{vector.session_count} \u2014 Sleep-Time f\u00e4llig!")


if __name__ == "__main__":
    main()
