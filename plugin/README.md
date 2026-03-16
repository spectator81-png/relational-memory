# Relational Memory — Claude Code Plugin

Claude Code plugin that builds relationship memory across sessions. Instead of storing facts about you, it models the relationship dynamic — how you two communicate.

No separate API key needed. The plugin uses Claude Code's own reasoning for everything.

## What It Does

- **SessionStart**: Loads relationship vector and memory layers, injects context into Claude's system prompt
- **SessionEnd (automatic)**: Extracts relational signals, updates vector, runs sleep-time condensation when due — zero manual steps needed
- **`/memory-save`**: Manual override — extract signals mid-session
- **`/sleep`**: Manual override — force layer condensation
- **`/vector`**: Shows current relationship state, layers, and drift warnings

## Installation

```bash
pip install relational-memory
claude plugin marketplace add spectator81-png/relational-memory
claude plugin install relational-memory@relational-memory-plugins
```

Three commands, done. Restart Claude Code to activate.

### Configure user ID (optional)

Three options, in priority order:

**a) Environment variable:**
```bash
export RELATIONAL_MEMORY_USER=alex
```

**b) Config file** (`.claude/relational-memory.local.md` in project or `~/.claude/`):
```markdown
---
user: alex
---
```

**c) Default:** Without configuration, `default` is used as user ID.

## Usage

### Normal workflow (fully automatic)

1. Start a session → plugin loads relationship context
2. Work/chat normally
3. End the session → plugin automatically extracts signals, updates vector, and runs sleep-time if due

That's it. No manual commands needed.

### First-time calibration

The first 3-5 sessions are a calibration phase. The vector starts at neutral (0.5) and converges toward your actual communication style via EMA. Layers are first created at session #5 (first sleep-time). Expect noticeable adaptation from session 2 onwards.

### Manual overrides

| Command | Description |
|---------|------------|
| `/memory-save` | Force signal extraction mid-session (auto-save skips if already done) |
| `/sleep` | Force layer condensation outside the regular 5-session cycle |
| `/vector` | Show current vector, layers, and drift warnings |

## How It Works (No Separate API Key)

The key design decision: **Claude Code does all the thinking.**

- **Signal extraction** (`/memory-save`): Claude (Opus) analyzes the conversation directly — it's already in context
- **Sleep-time condensation** (`/sleep`): Claude (Opus) reads the signal log and writes the layers — no separate Haiku call needed
- **Helper scripts** only handle file I/O (reading data, writing JSON, EMA math)

This means: if you can run Claude Code, you can run this plugin. No API keys, no provider configuration, no extra cost beyond your normal Claude Code usage.

## Architecture

```
Plugin
├── SessionStart Hook → session_start.py → systemMessage (context injection)
├── Stop Hook (prompt) → auto_save.md → signal extraction + vector update + auto-sleep
├── /memory-save → Claude analyzes → temp_signals.json → update_vector.py (manual override)
├── /sleep → sleep_read.py → Claude condenses → sleep_write.py (manual override)
└── /vector → show_vector.py → vector + layers + drift
```

## Storage

Everything in `~/.relational_memory/<user_id>/`:

```
~/.relational_memory/alex/
├── vector.json           # 7D EMA vector
├── signal_log.json       # Signal history (max 20 entries)
├── layers/
│   ├── base_tone.md      # Distilled relationship portrait
│   ├── patterns.md       # If-then behavioral rules
│   ├── anchors.md        # Relationship turning points
│   └── versions/         # Timestamped backups
└── temp_signals.json     # Temporary (deleted after update)
```

## The 7 Dimensions

| Dimension | 0.0 | 1.0 |
|-----------|-----|-----|
| Formality | Slang, dialect | Formal register |
| Warmth | Transactional | Personal connection |
| Humor | Serious | Banter, running jokes |
| Depth | Task execution | Philosophical |
| Trust | Guarded | Vulnerability |
| Energy | "ok" | Passionate |
| Resilience | Avoids friction | Heated debate, productive |

## Requirements

- Python 3.10+
- `relational-memory` package (pip)
- Claude Code

No API keys needed beyond your Claude Code subscription.

## License

Big Time Public License 2.0.1
