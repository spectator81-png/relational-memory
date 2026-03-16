#!/usr/bin/env python3
"""Display current relational vector, layers, and drift information."""

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
    load_signal_log,
    detect_drift,
    format_drift_warning,
    should_condense,
)
from relational_memory.vector import DIMENSIONS


def main():
    user_id = get_user_id()
    paths = get_storage_paths(user_id)

    vector = RelationalVector.load(paths["vector"])
    layers = LayerStore(paths["layers"])

    print(f"\n  RELATIONAL MEMORY — User: {user_id}")
    print(f"  Sessions: {vector.session_count} | Letztes Update: {vector.last_updated}")
    print(f"  Storage: {paths['base']}")
    print(f"  {'='*50}\n")

    # Vector with bar chart
    print("  VEKTOR (7D EMA)")
    for dim in DIMENSIONS:
        value = vector.values[dim]
        bar_len = int(value * 25)
        bar = "\u2588" * bar_len + "\u2591" * (25 - bar_len)
        print(f"  {dim:<14s} {bar} {value:.2f}")

    # Layers
    print(f"\n  LAYERS")
    bt = layers.read_base_tone()
    pt = layers.read_patterns()
    an = layers.read_anchors()

    if layers.is_initialized():
        print(f"\n  Base Tone:")
        if bt:
            for line in bt.strip().splitlines():
                print(f"    {line}")
        print(f"\n  Patterns:")
        if pt:
            for line in pt.strip().splitlines():
                print(f"    {line}")
        print(f"\n  Anchors:")
        if an:
            for line in an.strip().splitlines():
                print(f"    {line}")
    else:
        remaining = 5 - (vector.session_count % 5) if vector.session_count > 0 else 5
        print(f"  (Noch nicht initialisiert — werden nach {remaining} weiteren Sessions generiert)")

    # Layer versions
    versions = layers.list_versions()
    if versions:
        print(f"\n  Versionen: {len(versions)} Backups vorhanden")
        print(f"    Neueste: {versions[0]}")

    # Drift detection
    signal_log = load_signal_log(paths["signal_log"])
    if signal_log:
        print(f"\n  SIGNAL-HISTORY: {len(signal_log)} Sessions")
        drift_alerts = detect_drift(vector, signal_log)
        if drift_alerts:
            print(f"\n  {format_drift_warning(drift_alerts)}")
        else:
            if len(signal_log) >= 5:
                print("  Kein Drift erkannt (alle Dimensionen stabil)")
            else:
                print(f"  Drift-Detection ab Session 5 aktiv (noch {5 - len(signal_log)} Sessions)")

    # Next condensation
    if vector.session_count > 0:
        if should_condense(vector.session_count):
            print(f"\n  \u2728 Sleep-Time fällig! Führe /sleep aus.")
        else:
            next_at = vector.session_count + (5 - vector.session_count % 5)
            print(f"\n  Nächste Sleep-Time bei Session #{next_at}")

    print()


if __name__ == "__main__":
    main()
