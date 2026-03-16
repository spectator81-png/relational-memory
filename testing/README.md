# Testing — Relational Memory Prototype v1

Testdokumentation für den Relational Memory Prototyp. Jeder Tester hat einen eigenen Ordner mit Rohdaten, Analyse und Erkenntnissen.

## Übersicht

| Tester | Profil | Sessions | Zeitraum | Highlights |
|--------|--------|----------|----------|------------|
| [Florian](florian/) | Erwachsener, Entwickler des Systems | 7 relational + 1 flat | 2026-03-13 | Erste Validierung, A/B-Test, Sleep-Time-Layers |
| [Max](max/) | Teenager, keine Vorkenntnisse | 6 relational + 3 flat | 2026-03-14 | Zweiter unabhängiger Tester, Dialektanpassung, Warmth-Bug entdeckt |
| [Plugin Live](plugin_live/) | Claude Code Plugin v1.0 | — | 2026-03-16 | Live-Test aller Hooks + Commands gegen echte Daten + API |

## Methodik

- **Relational Mode:** `python chat.py --user <id>` — Bot lernt über Sessions hinweg (EMA-Vektor + Sleep-Time-Layers)
- **Flat Mode:** `python chat.py --user <id> --mode flat` — kein Gedächtnis, generischer System-Prompt
- **A/B-Vergleich:** Gleiche oder ähnliche Themen in beiden Modi, um Unterschiede zu isolieren
- **Signal-Extraktion:** Nach jeder Session automatisch (Haiku), 7 Dimensionen
- **Sleep-Time:** Automatisch nach 5 Sessions — generiert Grundton, Muster, Ankerpunkte

## Dateistruktur

```
testing/
  README.md                  ← diese Datei
  florian/
    session_log.md           — Vektor-Verlauf, Signale, Layers, qualitative Beobachtungen (7 Sessions)
    ab_test_public.md        — A/B-Transkript (fiktionalisierte Persona, veröffentlicht auf GitHub)
  max/
    analyse.md               — Vollständige Analyse: Session-für-Session, Signale, A/B-Vergleich, Bugs, Vorschläge
    feedback.md              — Kurzes qualitatives Feedback nach dem Test
    chat_raw.txt             — Rohes Chat-Log (PowerShell-Output, NICHT veröffentlichen — enthält API-Key-Setup)
  plugin_live/
    test_report.md           — Live-Test Claude Code Plugin v1.0: SessionStart, /vector, /memory-save, /sleep
```

## Konsolidierte Erkenntnisse (beide Tester)

### Was funktioniert

1. **Tonanpassung ab Session 2** — beide Tester berichten spürbare Veränderung
2. **Signal-Extraktion kontextsensitiv** — Humor 0.78 bei Satire vs. 0.15 bei Ernst (Max), Depth 0.90 bei Philosophie vs. 0.25 bei Humor (Florian)
3. **Sleep-Time-Layers qualitativ hochwertig** — bei beiden Testern plausible Patterns und Ankerpunkte
4. **A/B-Unterschied dramatisch** — Relational = Gesprächspartner, Flat = Lexikon/Coach
5. **Anti-Sycophancy funktioniert** — Selbstkorrektur (Max S5), Gegenposition halten (Florian S3), Ablenkungsmanöver erkennen (Florian A/B)
6. **Dialektanpassung** (Max) — Bot schaltet auf Österreichisch und hält es durch
7. **Transparenz über Gedächtnis-Grenzen** — Bot halluziniert keine konkreten Erinnerungen

### Bekannte Probleme

| Problem | Entdeckt bei | Schwere | Details |
|---------|-------------|---------|---------|
| **Warmth konstant 0.72** | Max (6 Sessions) | Mittel | Signal-Extraktions-Prompt differenziert Warmth nicht nach Session-Kontext |
| **Antworten zu lang für Teenager** | Max | Niedrig | 150–250 Wörter Bot vs. 5–15 Wörter User — adaptive Antwortlänge fehlt |
| **Cold-Start: Englisch-Angebot** | Max (Session 1) | Niedrig | Bot bietet Englisch an obwohl User auf Deutsch schreibt |
| **Sycophancy bei sozialem Druck** | Max (Session 5) | Mittel | "Ich kenne die Antwort" → Bot bestätigt zu schnell (korrigiert sich dann) |
| **Markdown im CLI** | Max | Niedrig | ##-Überschriften und Bullet-Listen schlecht lesbar im Terminal |

### Vorschläge für v2

1. **Adaptive Antwortlänge** — Bot-Antworten an User-Nachrichtenlänge koppeln
2. **Warmth-Dimension aufteilen** — `intellectual_warmth` vs. `emotional_warmth`
3. **Sprachpräferenz in Layers** — Dialekt-Erkennung persistieren
4. **Teenager-Modus** — kürzere Antworten, weniger Struktur, mehr Fragen
5. **Warmth-Bug fixen** — Signal-Extraktions-Prompt: Session-Warmth ≠ User-Trait
