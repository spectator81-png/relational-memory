---
description: Sleep-Time-Verdichtung — Signal-History in Layers destillieren
allowed-tools: Bash, Write, Read
---

Führe die Sleep-Time-Verdichtung aus. Dabei werden die gesammelten Signale aus vergangenen Sessions in die drei Memory-Layers (Base Tone, Patterns, Anchors) destilliert.

## Schritt 1: Daten laden

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/sleep_read.py"
```

Falls das Script einen Fehler meldet, erkläre dem User was fehlt und brich ab.

## Schritt 2: Condensation durchführen

Du bist jetzt ein Relationship Memory Consolidation Agent. Analysiere die Signal-History und den aktuellen Vektor und erstelle aktualisierte Layers.

### Layer 1: Base Tone (ändert sich über Monate)
Ein destilliertes Portrait, wer diese Person in dieser Beziehung ist. Schreibe es wie ein enger Freund sie beschreiben würde — nicht Fakten, sondern Charakter. 2-4 Sätze max. Fokus auf WIE sie sind, nicht WAS sie tun.

### Layer 2: Patterns (ändert sich über Wochen)
Aktive If-Then-Patterns aus implizitem Feedback gelernt. Max 10 Patterns. Format: "When X → Y". Entferne Patterns die das Signal-Log nicht mehr stützt. Füge neue hinzu die emergieren. Diese sollen actionable sein.

WICHTIG: Immer ein Sprach-/Dialekt-Pattern inkludieren wenn erkennbar:
- "User writes in Austrian German dialect → respond in Austrian German, not Hochdeutsch"
- "User writes in English → respond in English"

WICHTIG: Wenn das Signal-Log Resilience-Einträge mit "type"-Feld enthält, ein Resilience-Pattern inkludieren:
- "Resilience is relationship-based → user stays through friction because the relationship can handle it"
- "Resilience appears dependency-based → be cautious with pushback"

### Layer 3: Anchors (wenige, bleiben lange)
Momente die die Beziehung verändert haben. Max 10. Nur hinzufügen wenn das Signal-Log einen klaren Shift zeigt (z.B. Dimension springt >0.2 zwischen Sessions). Format: kurze Beschreibung + was sich geändert hat.

### Regeln
- Knapp halten. Token-Budget: Base Tone 100-200, Patterns 150-300, Anchors 50-100.
- Bestehenden Content bewahren der noch von den Daten gestützt wird.
- In der SPRACHE schreiben die der User überwiegend verwendet.
- KEINE Metadaten, Timestamps oder Dimensionswerte in die Layers — dafür gibt es den Vektor.

## Schritt 3: Ergebnis als JSON schreiben

Schreibe das Ergebnis als JSON in die Datei `~/.relational_memory/$RELATIONAL_MEMORY_USER/temp_condensation.json` (falls `$RELATIONAL_MEMORY_USER` nicht gesetzt, verwende `default`):

```json
{
  "base_tone": "Layer 1 Inhalt als String",
  "patterns": "Layer 2 Inhalt als String (\\n für Zeilenumbrüche)",
  "anchors": "Layer 3 Inhalt als String (\\n für Zeilenumbrüche)"
}
```

## Schritt 4: Layers schreiben

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/sleep_write.py"
```

## Schritt 5: Ergebnis zeigen

Zeige dem User die aktualisierten Layers: Base Tone, Patterns, Anchors. Erwähne den Backup-Status und wann die nächste Condensation fällig ist.
