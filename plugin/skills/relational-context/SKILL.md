---
name: Relational Context
description: This skill provides background knowledge about the Relational Memory system. Use when Claude needs to understand the 7D vector, 3-layer model, EMA updates, drift detection, or the friction thesis. Triggers when user asks about "relational memory", "vector dimensions", "how does the memory work", "what are layers", "how does signal extraction work", or discusses the relational memory architecture.
---

# Relational Memory — Hintergrundwissen

Dieses Plugin implementiert ein relationales Gedächtnissystem das nicht Information ÜBER jemanden speichert, sondern die Beziehung SELBST modelliert.

## Kernthese

Relationales Gedächtnis gibt der AI die Sicherheit, unbequem zu sein. Nicht nur "AI die sich erinnert", sondern AI die durch Beziehungswissen den Mut hat, produktive Reibung zu erzeugen — wie ein guter Freund.

## 7D Beziehungsvektor

Jede Session wird auf 7 Dimensionen analysiert (0.0–1.0):

| Dimension | Bedeutung | Low | High |
|-----------|-----------|-----|------|
| Formality | Sprachregister | Slang, Dialekt | "Sie", Titel |
| Warmth | Verbundenheit (emotional ODER intellektuell) | Transaktional | Persönliche Verbindung |
| Humor | Humor als Element der Interaktion | Ernst | Banter, Running Jokes |
| Depth | Tiefe der Themen | Aufgabenausführung | Philosophisch, existenziell |
| Trust | Offenheit und Vertrauen | Reserviert, prüfend | Verletzlichkeit, Delegation |
| Energy | Engagement und Antrieb | "ok", minimal | Leidenschaftlich, rapid-fire |
| Resilience | Belastbarkeit bei Meinungsverschiedenheiten | Weicht aus | Hitzige Diskussion, produktiv |

**EMA-Update:** `V_neu = α · V_alt + (1-α) · signal`
- α=0.9 normal (langsames Lernen, ignoriert natürliche Variation)
- α=0.5 bei expliziter Korrektur (schnelles Lernen)

## 3-Schichten-Modell

| Schicht | Ändert sich | Inhalt | Budget |
|---------|------------|--------|--------|
| Base Tone | Über Monate | Destilliertes Beziehungsbild, wie ein Freund sie beschreiben würde | 100-200 Tokens |
| Patterns | Über Wochen | Wenn-dann-Regeln aus implizitem Feedback | 150-300 Tokens |
| Anchors | Selten | Wendepunkte die die Beziehung verändert haben | 50-100 Tokens |

Layers werden alle 5 Sessions via Sleep-Time-Condensation aktualisiert (LLM destilliert Signal-History in Layers).

## Drift-Detection

Ab 5 Sessions: Baseline aus Signal-History. Wenn eine Dimension >0.25 abweicht → Drift-Warning im System-Prompt. Ziel: Transparenz statt stilles Anpassen.

## Anti-Sycophancy

Das System optimiert auf User-Wachstum, nicht auf Zufriedenheit. Resilience-Guidance passt sich an:
- Resilience >0.7: "Push back when you disagree"
- Resilience <0.3: "Be gentle, frame challenges as questions"

## Plugin-Ablauf

1. **SessionStart**: Vektor + Layers laden → Kontext in System-Prompt injizieren
2. **Während Session**: Claude kommuniziert natürlich, informiert durch den Kontext
3. **`/memory-save`**: Signale extrahieren → EMA-Update → Vektor speichern
4. **`/sleep`**: Signal-History in Layers verdichten (alle 5 Sessions empfohlen)
5. **`/vector`**: Aktuellen Zustand anzeigen

## Wichtige Unterscheidung

- **Beziehungsbasierte Resilienz**: User bleibt durch Reibung weil die Beziehung es trägt → echt
- **Abhängigkeitsbasierte Resilienz**: User bleibt weil keine Alternative → gefährlich, nicht als Belastbarkeit werten
