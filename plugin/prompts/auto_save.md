# Auto-Save — Session-Ende-Automatik

> Wird vom Stop-Hook ausgeführt. Führe JEDEN Schritt sequentiell aus.

## Vorprüfungen

1. **Triviale Session?** Hatte diese Konversation weniger als 3 sinnvolle Nachrichten-Wechsel (User→Assistant)? Dann: Gib aus "Session zu kurz für Signal-Extraktion — übersprungen." und STOPP.
2. **Schon gespeichert?** Wurde `/memory-save` bereits in dieser Session ausgeführt? (Erkennbar daran, dass Signal-Extraktion + Vektor-Update schon im Gesprächsverlauf stattfanden.) Dann: Gib aus "Signale wurden bereits manuell gespeichert." und STOPP.

## Phase 1: Signal-Extraktion

### Schritt 1.1: Signal-Prompt lesen

Lies die Bewertungskriterien:

```
Read: ${CLAUDE_PLUGIN_ROOT}/prompts/signal_extraction.md
```

### Schritt 1.2: Session analysieren

Analysiere ALLE User- und Assistant-Nachrichten dieser Session als Beziehungsdynamik-Analyst. Verwende die Bewertungskriterien aus Schritt 1.1.

### Schritt 1.3: JSON schreiben

Erstelle ein JSON-Objekt mit den 7 Dimensionen. Jede Dimension MUSS enthalten:
- `evidence`: Konkretes Zitat oder Beobachtung aus der Konversation
- `value`: Float zwischen 0.0 und 1.0 (nutze die Scale Anchors!)
- `signal`: Einzeiliger Summary

Plus `explicit_corrections` Array (leer wenn keine Korrekturen).

Schreibe das JSON mit dem Write-Tool in die Datei:
`~/.relational_memory/$RELATIONAL_MEMORY_USER/temp_signals.json`

Falls `$RELATIONAL_MEMORY_USER` nicht gesetzt ist, verwende `default` als User-ID.

### Schritt 1.4: Vektor-Update

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/update_vector.py"
```

Merke dir den Output — insbesondere ob `AUTOSLEEP_DUE=true` vorkommt.

## Phase 2: Auto-Sleep (nur wenn fällig)

Nur ausführen wenn der Output von `update_vector.py` den Marker `AUTOSLEEP_DUE=true` enthält. Sonst direkt zu Phase 3.

### Schritt 2.1: Sleep-Daten laden

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/sleep_read.py"
```

Falls das Script einen Fehler meldet, überspringe die Sleep-Phase und gehe zu Phase 3.

### Schritt 2.2: Condensation durchführen

Du bist jetzt ein Relationship Memory Consolidation Agent. Analysiere die Signal-History und den aktuellen Vektor und erstelle aktualisierte Layers.

#### Layer 1: Base Tone (ändert sich über Monate)
Ein destilliertes Portrait, wer diese Person in dieser Beziehung ist. Schreibe es wie ein enger Freund sie beschreiben würde — nicht Fakten, sondern Charakter. 2-4 Sätze max. Fokus auf WIE sie sind, nicht WAS sie tun.

#### Layer 2: Patterns (ändert sich über Wochen)
Aktive If-Then-Patterns aus implizitem Feedback gelernt. Max 10 Patterns. Format: "When X → Y". Entferne Patterns die das Signal-Log nicht mehr stützt. Füge neue hinzu die emergieren. Diese sollen actionable sein.

WICHTIG: Immer ein Sprach-/Dialekt-Pattern inkludieren wenn erkennbar:
- "User writes in Austrian German dialect → respond in Austrian German, not Hochdeutsch"
- "User writes in English → respond in English"

WICHTIG: Wenn das Signal-Log Resilience-Einträge mit "type"-Feld enthält, ein Resilience-Pattern inkludieren:
- "Resilience is relationship-based → user stays through friction because the relationship can handle it"
- "Resilience appears dependency-based → be cautious with pushback"

#### Layer 3: Anchors (wenige, bleiben lange)
Momente die die Beziehung verändert haben. Max 10. Nur hinzufügen wenn das Signal-Log einen klaren Shift zeigt (z.B. Dimension springt >0.2 zwischen Sessions). Format: kurze Beschreibung + was sich geändert hat.

#### Regeln
- Knapp halten. Token-Budget: Base Tone 100-200, Patterns 150-300, Anchors 50-100.
- Bestehenden Content bewahren der noch von den Daten gestützt wird.
- In der SPRACHE schreiben die der User überwiegend verwendet.
- KEINE Metadaten, Timestamps oder Dimensionswerte in die Layers — dafür gibt es den Vektor.

### Schritt 2.3: Condensation-JSON schreiben

Schreibe das Ergebnis als JSON in die Datei `~/.relational_memory/$RELATIONAL_MEMORY_USER/temp_condensation.json` (falls `$RELATIONAL_MEMORY_USER` nicht gesetzt, verwende `default`):

```json
{
  "base_tone": "Layer 1 Inhalt als String",
  "patterns": "Layer 2 Inhalt als String (\n für Zeilenumbrüche)",
  "anchors": "Layer 3 Inhalt als String (\n für Zeilenumbrüche)"
}
```

### Schritt 2.4: Layers schreiben

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/sleep_write.py"
```

## Phase 3: Zusammenfassung

Gib dem User eine KOMPAKTE Zusammenfassung (max 3-4 Zeilen):
- Welche Signale extrahiert wurden (Dimensionen mit stärkster Änderung)
- Ob Sleep-Time durchgeführt wurde
- Nächste Sleep-Time bei Session #N (wenn nicht jetzt)

Beispiel-Output:
```
Relational Memory gespeichert (Session #3). Warmth ↑0.62, Energy ↓0.45. Nächste Sleep-Time bei #5.
```

Oder mit Sleep:
```
Relational Memory gespeichert (Session #5) + Sleep-Time: Layers aktualisiert (3 Patterns neu). Nächste Sleep-Time bei #10.
```
