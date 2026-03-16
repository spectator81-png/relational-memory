---
description: Relationale Signale aus dieser Session extrahieren und Vektor updaten
allowed-tools: Write, Bash, Read
---

Extrahiere relationale Signale aus der aktuellen Session und aktualisiere den Beziehungsvektor.

## Schritt 1: Signal-Extraktion

Analysiere ALLE User- und Assistant-Nachrichten dieser Session als Beziehungsdynamik-Analyst. Verwende die folgenden Bewertungskriterien:

@${CLAUDE_PLUGIN_ROOT}/prompts/signal_extraction.md

## Schritt 2: JSON erstellen

Erstelle ein JSON-Objekt mit den 7 Dimensionen. Jede Dimension MUSS enthalten:
- `evidence`: Konkretes Zitat oder Beobachtung aus der Konversation
- `value`: Float zwischen 0.0 und 1.0 (nutze die Scale Anchors!)
- `signal`: Einzeiliger Summary

Plus `explicit_corrections` Array (leer wenn keine Korrekturen).

## Schritt 3: Signal-Datei schreiben

Schreibe das JSON mit dem Write-Tool in die Datei:
`~/.relational_memory/$RELATIONAL_MEMORY_USER/temp_signals.json`

Falls `$RELATIONAL_MEMORY_USER` nicht gesetzt ist, verwende `default` als User-ID.

## Schritt 4: Vektor-Update ausführen

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/update_vector.py"
```

## Schritt 5: Ergebnis zeigen

Zeige dem User das Ergebnis aus dem Script-Output: Signalwerte, Vektor-Änderungen, und ob Sleep-Time fällig ist.
