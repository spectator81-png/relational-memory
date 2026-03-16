# Relational Memory — Claude Code Plugin Architecture (Phase 4.1)

> Erstellt: 2026-03-16 | Status: v1.1.0 — prompt-based /sleep (no API key needed)

## Overview

Claude Code Plugin das die `relational-memory` Python Library in Claude Code Sessions integriert.
Gibt Claude beziehungsbewussten Kontext über den User — Kommunikationsstil passt sich über Sessions hinweg an.

## Dependencies

- Python 3.10+
- `pip install relational-memory` (PyPI Package, v2.1.0)
- No separate API key needed (Claude Code does all LLM work)
- `RELATIONAL_MEMORY_USER` (optional, default: "default")

## Storage

Alles in `~/.relational_memory/<user_id>/`:
- `vector.json` — 7D EMA-Vektor
- `signal_log.json` — Signal-History (append-only, max 20)
- `layers/` — 3-Schichten-Memory (base_tone.md, patterns.md, anchors.md)
- `layers/versions/` — Timestamped Backups (max 10)
- `temp_signals.json` — Temporär während /memory-save (wird gelöscht)

## Plugin-Struktur

```
plugin/
├── .claude-plugin/
│   └── plugin.json                  # Manifest
├── hooks/
│   └── hooks.json                   # SessionStart + Stop Hooks
├── commands/
│   ├── memory-save.md               # Signal-Extraktion + Vektor-Update
│   ├── sleep.md                     # Sleep-Time-Verdichtung
│   └── vector.md                    # Zustand anzeigen
├── scripts/
│   ├── config.py                    # Shared: User-ID, Paths, Dependency-Check
│   ├── session_start.py             # SessionStart → systemMessage JSON
│   ├── update_vector.py             # Signale validieren + EMA + speichern
│   ├── show_vector.py               # Vektor + Layers + Drift anzeigen
│   ├── sleep_read.py                # Read signal log + layers for /sleep
│   ├── sleep_write.py               # Write condensation result back to layers
│   └── run_sleep.py                 # (legacy) condense() via Library (Haiku)
├── prompts/
│   └── signal_extraction.md         # Bundled Extraction-Prompt (für Opus angepasst)
├── skills/
│   └── relational-context/
│       └── SKILL.md                 # Hintergrundwissen für Claude
├── ARCHITECTURE.md                  # Diese Datei
└── README.md                        # Installation + Usage
```

## Datenfluss

### SessionStart (automatisch)
```
Session Start
  → hooks.json: SessionStart command hook
  → session_start.py
  → config.py: get_user_id() (env → .local.md → "default")
  → Library: RelationalVector.load() + LayerStore + assemble_context()
  → JSON: {"systemMessage": "<relational context>", "suppressOutput": true}
  → $CLAUDE_ENV_FILE: RELATIONAL_MEMORY_USER + RELATIONAL_MEMORY_STORAGE
  → Claude hat Beziehungskontext im System-Prompt
```

### /memory-save (manuell)
```
User: /memory-save
  → commands/memory-save.md lädt @prompts/signal_extraction.md
  → Claude analysiert die Konversation (Opus als Judge)
  → Claude schreibt JSON → Write Tool → temp_signals.json
  → Claude ruft Bash: python update_vector.py
  → update_vector.py: validate_signals() → EMA-Update → save vector + signal_log
  → Output: Signalbalken, Vektor-Änderungen, Sleep-Time-Reminder
```

### /sleep (manuell, prompt-basiert — v1.1)
```
User: /sleep
  → commands/sleep.md
  → Claude ruft Bash: python sleep_read.py → Signal-Log + Layers + Vektor als Text
  → Claude (Opus) verdichtet selbst → schreibt JSON → Write Tool → temp_condensation.json
  → Claude ruft Bash: python sleep_write.py → Versioned Backup → Layer-Update → Cleanup
  → Output: Aktualisierte Layers
```

**v1.0 (legacy):** `run_sleep.py` nutzte einen separaten Haiku-Call via Library. Bleibt als Referenz für Nicht-Plugin-Nutzung.

### Stop Hook (automatisch, prompt-basiert)
```
Claude will Session beenden
  → hooks.json: Stop prompt hook
  → Claude evaluiert: Gab es 5+ sinnvolle Wechsel?
  → Falls ja und kein /memory-save: Einmaliger Tipp
```

## Design-Entscheidungen

### D1: Claude als Signal-Judge (nicht Haiku)
- **Pro:** Kein API-Key nötig, Konversation bereits im Kontext, höhere Qualität
- **Pro:** Kein Transcript-Serialisierung, kein Temp-File für Konversation
- **Con:** Opus-Tokens (~500-1000 pro Extraktion)
- **Con:** Prompt war für Haiku kalibriert — Opus braucht leicht angepasste Version
- **Entscheidung:** Opus für v1. Prompt angepasst (deutsch, kompakter).

### D2: JSON via Temp-Datei (nicht CLI-Argument)
- **Sicherheit:** JSON im CLI-Argument → Shell-Injection-Risiko (Anführungszeichen in Evidence)
- **Entscheidung:** Claude schreibt JSON via Write-Tool → Script liest Datei → löscht nach Update

### D3: User-ID 3-stufig
1. `RELATIONAL_MEMORY_USER` env var
2. `.claude/relational-memory.local.md` YAML-Frontmatter (Projekt → Global)
3. Fallback: "default"
- SessionStart schreibt User-ID in `$CLAUDE_ENV_FILE` → alle Scripts haben sie

### D4: Manuelle Signal-Extraktion
- User kontrolliert wann/ob Signale extrahiert werden
- Kein Token-Verbrauch bei trivialen Sessions
- Stop-Hook erinnert einmal dezent

### D5: Scripts nutzen pip-Package
- DRY: validate_signals(), EMA, LayerStore etc. kommen aus der Library
- Updates via `pip install --upgrade relational-memory`
- Voraussetzung: pip install — in README dokumentiert

## Bekannte Limitierungen (v1.0)

| # | Limitation | Akzeptanz |
|---|-----------|-----------|
| 1 | Context-Compaction: Claude hat nach Komprimierung nicht die volle Konversation | Akzeptabel — Recency-Bias ist für Signal-Extraktion sogar vorteilhaft |
| 2 | Opus-Prompt nicht empirisch validiert (nur Haiku getestet) | Akzeptabel — Opus ist generell besser als Haiku bei LLM-as-Judge |
| 3 | Stop-Hook feuert bei jeder Stop-Entscheidung, nicht nur Session-Ende | Akzeptabel — Prompt sagt "einmal erwähnen" |
| 4 | Kein Auto-Save bei Session-Ende | Design-Entscheidung: User-Kontrolle bevorzugt |
| 5 | Windows: icacls best-effort für Permissions | Aus Library übernommen — akzeptabel |
