# Relational Memory — Claude Code Plugin

Claude Code Plugin das Beziehungsgedächtnis über Sessions hinweg aufbaut. Statt nur Fakten über den User zu speichern, modelliert es die Beziehungsdynamik — wie ihr miteinander kommuniziert.

## Was es tut

- **SessionStart**: Lädt den Beziehungsvektor und Memory-Layers, injiziert Kontext in Claudes System-Prompt
- **`/memory-save`**: Extrahiert relationale Signale aus der aktuellen Session (7 Dimensionen), aktualisiert den Vektor via EMA
- **`/sleep`**: Verdichtet die Signal-History in drei Memory-Layers (Base Tone, Patterns, Anchors)
- **`/vector`**: Zeigt den aktuellen Beziehungszustand, Layers und Drift-Warnungen

## Installation

### 1. Python-Package installieren

```bash
pip install relational-memory

# Für Sleep-Time (Haiku-LLM-Call):
pip install relational-memory[anthropic]
```

### 2. Plugin einbinden

Das Plugin-Verzeichnis in Claude Code referenzieren:

```bash
claude --plugin-dir /pfad/zu/plugin
```

Oder als Symlink in `~/.claude/plugins/` ablegen.

### 3. User-ID konfigurieren (optional)

Drei Möglichkeiten, Priorität von oben nach unten:

**a) Umgebungsvariable:**
```bash
export RELATIONAL_MEMORY_USER=florian
```

**b) Config-Datei** (`.claude/relational-memory.local.md` im Projekt oder `~/.claude/`):
```markdown
---
user: florian
---
```

**c) Default:** Ohne Konfiguration wird `default` als User-ID verwendet.

### 4. API-Key (nur für /sleep)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Nur nötig für `/sleep` (Sleep-Time-Condensation via Haiku). Die Signal-Extraktion (`/memory-save`) braucht keinen separaten Key — Claude analysiert direkt.

## Verwendung

### Normaler Workflow

1. Session starten → Plugin lädt automatisch den Beziehungskontext
2. Normal arbeiten/chatten
3. Am Ende: `/memory-save` → Signale werden extrahiert, Vektor aktualisiert
4. Alle 5 Sessions: `/sleep` → Layers werden verdichtet

### Commands

| Command | Beschreibung |
|---------|-------------|
| `/memory-save` | Signale extrahieren + Vektor updaten |
| `/sleep` | Sleep-Time-Verdichtung (braucht API-Key) |
| `/vector` | Aktuellen Zustand anzeigen |

## Storage

Alles in `~/.relational_memory/<user_id>/`:

```
~/.relational_memory/florian/
├── vector.json           # 7D EMA-Vektor
├── signal_log.json       # Signal-History (max 20 Einträge)
├── layers/
│   ├── base_tone.md      # Destilliertes Beziehungsbild
│   ├── patterns.md       # Wenn-dann-Regeln
│   ├── anchors.md        # Wendepunkte
│   └── versions/         # Timestamped Backups
└── temp_signals.json     # Temporär (wird nach Update gelöscht)
```

## Architektur

```
Plugin
├── SessionStart Hook → session_start.py → systemMessage (Kontext-Injection)
├── Stop Hook (prompt) → erinnert an /memory-save
├── /memory-save → Claude analysiert → temp_signals.json → update_vector.py
├── /sleep → run_sleep.py → Library condense() → Haiku
└── /vector → show_vector.py → Vektor + Layers + Drift
```

**Design-Entscheidung:** Claude (Opus) macht die Signal-Extraktion direkt — kein separater Haiku-Call nötig. Die Konversation ist bereits im Kontext. Sleep-Time-Condensation nutzt Haiku über die Library.

## 7 Dimensionen

| Dimension | 0.0 | 1.0 |
|-----------|-----|-----|
| Formality | Slang, Dialekt | "Sie", Titel |
| Warmth | Transaktional | Persönliche Verbindung |
| Humor | Ernst | Banter |
| Depth | Aufgabenausführung | Philosophisch |
| Trust | Reserviert | Verletzlichkeit |
| Energy | "ok" | Leidenschaftlich |
| Resilience | Weicht aus | Hitzige Diskussion, produktiv |

## Voraussetzungen

- Python 3.10+
- `relational-memory` PyPI-Package
- Claude Code
- Optional: `ANTHROPIC_API_KEY` für `/sleep`

## Lizenz

Big Time Public License 2.0.1
