# Plugin Live-Test — 2026-03-16

Claude Code Plugin v1.0, getestet mit `claude --plugin-dir plugin/` gegen echte Daten und API.

## Testumgebung

- **Claude Code:** v2.1.76
- **relational-memory:** v2.1.0 (pip)
- **Python:** 3.14.2
- **OS:** Windows 11 Pro 10.0.22631
- **Testdaten:** `~/.relational_memory/florian/` (7 Sessions, Vektor + Signal-Log)
- **API:** Anthropic (Haiku für Sleep-Time-Condensation)

## Ergebnisse

| Komponente | Hook/Command | Status | Methode |
|---|---|---|---|
| SessionStart-Hook | `hooks.json → command` | **OK** | Script direkt + `claude -p` live |
| `/vector` | `commands/vector.md` | **OK** | Script direkt + `claude -p` live |
| `/memory-save` | `commands/memory-save.md` | **OK** | Script direkt + `claude -p` live |
| `/sleep` | `commands/sleep.md` | **OK** | Script direkt (mit API-Key aus Bitwarden) |
| Stop-Hook | `hooks.json → prompt` | **Nicht testbar** | Prompt-Hook feuert nur bei echtem Session-Ende |

## Detailbefunde

### 1. SessionStart-Hook

**Bestehender User (florian, 7 Sessions):**
- Gibt korrektes JSON mit `systemMessage` + `suppressOutput: true` zurück
- Inhalt: Core Principles (Anti-Sycophancy, Antwortlänge, Sprache) + Vektor + Layers + Guidance
- Sub-Instanz konnte Beziehungskontext korrekt wiedergeben ("buddhistische Grundhaltung", "intellektuelle Verbundenheit als Wärme")

**Neuer User (keine Daten):**
- First-Session-Nachricht: "Relational Memory aktiv (erste Session). Noch kein Beziehungskontext vorhanden..."
- Kein Crash bei fehlendem Storage-Verzeichnis — wird automatisch angelegt

**CLAUDE_ENV_FILE-Integration:**
- Nicht getestet (Variable nur in echtem Hook-Kontext gesetzt)
- Code sieht korrekt aus: schreibt `RELATIONAL_MEMORY_USER` + `RELATIONAL_MEMORY_STORAGE` für Folge-Scripts

### 2. /vector (show_vector.py)

- Bar-Chart mit Unicode-Blöcken (█░) rendert korrekt
- UTF-8-Encoding-Fix (`sys.stdout.reconfigure`) funktioniert auf Windows
- Zeigt: Vektor, Layers, Signal-History, Drift-Status, nächste Sleep-Time
- Neuer User: neutrale 0.50-Baseline, "(Noch nicht initialisiert)"
- Bestehender User: individuelle Werte, korrekter Session-Count

### 3. /memory-save (Signal-Extraktion + update_vector.py)

**Script-Test (update_vector.py):**
- Test-Signal-JSON geschrieben → Script liest, validiert, EMA-Update, speichert
- temp_signals.json wird nach Verarbeitung gelöscht (Cleanup OK)
- vector.json + signal_log.json korrekt erstellt
- EMA-Konvergenz korrekt: Erste Session bewegt Vektor langsam von 0.50 Richtung Signal (α=0.9)

**Live-Test (`claude -p` mit Plugin):**
- Claude (Opus) extrahiert Signale aus Konversation, schreibt JSON, ruft update_vector.py auf
- Ergebnis-Tabelle mit Signal → Vektor-Änderungen wird korrekt dargestellt
- Stärkstes Signal wird interpretiert ("Resilience 0.70 — produktive Reibung")

### 4. /sleep (run_sleep.py)

**Ohne API-Key:**
- Fehler: "ANTHROPIC_API_KEY environment variable not set"
- Exit-Code 2, klare Fehlermeldung mit Installationshinweis
- Fehlerhandling funktioniert wie designed

**Mit API-Key (aus Bitwarden):**
- Haiku-Condensation erfolgreich durchgeführt
- 3 Layers generiert aus 7 Sessions Signal-History:
  - **Base Tone:** Persönlichkeitsprofil (Tiefe, Reibungstoleranz, Humor-Stil)
  - **Patterns:** 10 konkrete Verhaltensregeln ("When human evades a topic → name it directly")
  - **Anchors:** 7 Schlüsselmomente mit Timestamps und Kontext
- Vorher/Nachher-Anzeige korrekt
- Backup-System nicht separat verifiziert (nur indirekt über "Condensation complete")

**Hinweis:** `ANTHROPIC_API_KEY` muss als System-Umgebungsvariable gesetzt sein. Claude Code gibt seinen eigenen Key nicht an Child-Prozesse weiter.

### 5. Stop-Hook

- Prompt-basiert: "Tipp: /memory-save speichert die relationalen Signale dieser Session."
- Feuert nur bei echtem Session-Ende, nicht über `-p` oder Script-Aufruf
- Logik korrekt: nur bei 5+ Nachrichten und wenn /memory-save nicht bereits ausgeführt

## Bekannte Einschränkungen

1. ~~**ANTHROPIC_API_KEY nicht automatisch verfügbar**~~ — **Gelöst in v1.1:** `/sleep` ist jetzt prompt-basiert, Claude Code macht die Condensation selbst. Kein separater API-Key mehr nötig.
2. **Stop-Hook nicht automatisiert testbar** — Prompt-Hooks können nur in echten interaktiven Sessions verifiziert werden.
3. **CLAUDE_ENV_FILE-Persistenz** — nicht isoliert getestet. Sollte in einer echten Session verifiziert werden (SessionStart setzt Env-Variablen für Folge-Commands).

## v1.1 Nachtrag — /sleep prompt-basiert (2026-03-16)

**Problem:** `/sleep` in v1.0 rief Haiku über einen separaten API-Call auf (`run_sleep.py` → `LLMClient`). Das erforderte einen eigenen `ANTHROPIC_API_KEY` als System-Umgebungsvariable — unnötig, wenn der User bereits Claude Code mit einem laufenden Opus hat.

**Lösung:** `/sleep` umgebaut auf prompt-basierte Architektur:
1. `sleep_read.py` — liest Signal-Log, Layers, Vektor und gibt sie als Text aus
2. Claude Code (Opus) — führt die Condensation selbst durch (im Command-Prompt)
3. `sleep_write.py` — schreibt Ergebnis-JSON zurück in Layers mit versioniertem Backup

**Testergebnis:** Live-Test mit `claude --plugin-dir plugin/ -p "Führe /sleep aus"` erfolgreich. Layers korrekt geschrieben, Backup erstellt, Qualität gleichwertig mit der Haiku-basierten Version.

**Entfernt:** `run_sleep.py` ist obsolet (bleibt als Referenz, wird nicht mehr vom Command aufgerufen).

## Fazit

Plugin v1.1 ist **produktionsbereit**. Alle Kernfunktionen (Hook-Injection, Vektor-Anzeige, Signal-Extraktion, Sleep-Time-Condensation) arbeiten korrekt mit echten Daten. **Kein separater API-Key mehr nötig** — das Plugin nutzt ausschließlich Claude Code's eigene Kapazität.
