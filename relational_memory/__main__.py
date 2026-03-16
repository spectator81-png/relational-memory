"""Demo CLI for Relational Memory — chat with relationship-aware context.

Usage:
  python -m relational_memory                      # Relational mode (default)
  python -m relational_memory --mode flat          # No memory (A/B comparison)
  python -m relational_memory --user alex          # User ID (default: "default")
  python -m relational_memory --provider openai    # Use OpenAI instead of Anthropic
  python -m relational_memory --provider google    # Use Google Gemini
  python -m relational_memory --provider local     # Use local model (Ollama etc.)
"""

import argparse
import logging
import sys
from pathlib import Path

from . import (
    DIMENSIONS,
    LLMClient,
    LLMConfigError,
    LLMAuthError,
    LayerStore,
    RelationalVector,
    assemble_context,
    check_stuck_dimensions,
    condense,
    extract_signals,
    save_signal_log,
    should_condense,
    truncate_messages,
)
from .llm import PROVIDERS
from .vector import DIMENSIONS

DEFAULT_STORAGE = Path.home() / ".relational_memory"

FLAT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Be direct, honest, and thoughtful. "
    "If you disagree with the user, say so."
)


def get_storage_path(user_id: str) -> Path:
    return DEFAULT_STORAGE / user_id


def run_chat(args):
    logging.basicConfig(
        level=logging.WARNING,
        format="  [%(name)s] %(message)s",
    )

    llm = LLMClient(provider=args.provider)
    storage = get_storage_path(args.user)
    vector_path = storage / "vector.json"
    signal_log_path = storage / "signal_log.json"
    layers_path = storage / "layers"

    # Load state
    vector = RelationalVector.load(vector_path)
    layers = LayerStore(layers_path)

    # Build system prompt
    if args.mode == "relational":
        system_prompt = assemble_context(vector, layers, signal_log_path)
        mode_label = "RELATIONAL"
    else:
        system_prompt = FLAT_SYSTEM_PROMPT
        mode_label = "FLAT"

    print(f"\n  Relational Memory — Mode: {mode_label}")
    print(f"  User: {args.user} | Sessions: {vector.session_count} | Provider: {args.provider}")
    if args.mode == "relational" and layers.is_initialized():
        print("  Layers: loaded")
    elif args.mode == "relational":
        print("  Layers: empty (generated after 5 sessions)")
    print("  Exit with 'bye', 'quit' or Ctrl+C\n")

    messages: list[dict] = []

    try:
        while True:
            try:
                user_input = input("  You: ").strip()
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in ("bye", "quit", "exit"):
                break

            messages.append({"role": "user", "content": user_input})

            # Truncate if conversation is getting long
            api_messages = truncate_messages(messages)

            print("\n  Bot: ", end="", flush=True)
            full_response = ""
            gen = llm.chat_stream(system=system_prompt, messages=api_messages)
            try:
                while True:
                    chunk = next(gen)
                    print(chunk, end="", flush=True)
                    full_response += chunk
            except StopIteration as e:
                if e.value:
                    full_response = e.value
            print("\n")

            messages.append({"role": "assistant", "content": full_response})

    except KeyboardInterrupt:
        print("\n")

    # Session end
    if not messages:
        print("  No messages — nothing to save.")
        return

    if args.mode != "relational":
        print(f"  Flat mode: {len(messages)} messages, no memory update.")
        return

    # Need at least one exchange for meaningful signal extraction
    asst_msgs = [m for m in messages if m["role"] == "assistant"]
    if not asst_msgs:
        print("  Only user messages — signal extraction skipped (needs min. 1 response).")
        return

    print("  Session ended. Extracting signals...")

    try:
        signals = extract_signals(messages, llm)
    except Exception as e:
        print(f"  Signal extraction failed: {e}")
        return

    # Display signals
    print(f"\n  {'='*50}")
    print("  SIGNAL EXTRACTION")
    print(f"  {'='*50}\n")
    for dim in DIMENSIONS:
        data = signals.get(dim, {})
        value = data.get("value", 0.0)
        bar_len = int(value * 25)
        bar = "\u2588" * bar_len + "\u2591" * (25 - bar_len)
        print(f"  {dim:<14s} {bar} {value:.2f}")
        evidence = data.get("evidence")
        if evidence:
            ev_display = evidence[:120] + "..." if len(evidence) > 120 else evidence
            print(f"  {'':14s} \u2514\u2500 {ev_display}")
    print()

    # Show explicit corrections
    corrections = signals.get("_explicit_corrections", [])
    if corrections:
        print("  EXPLICIT CORRECTIONS DETECTED:")
        for corr in corrections:
            dim = corr.get("dimension", "?")
            direction = corr.get("direction", "?")
            quote = corr.get("quote", "")
            print(f"    {dim} \u2192 {direction}")
            if quote:
                print(f"    \u2514\u2500 \"{quote}\"")
        print()

    # Update vector
    old_values = dict(vector.values)
    dims_updated = vector.update(signals)
    vector.save(vector_path)

    # Show changes
    corrected_dims = {c.get("dimension") for c in corrections if c.get("dimension") in DIMENSIONS}
    print("  VECTOR UPDATE (EMA)")
    for dim in DIMENSIONS:
        old = old_values[dim]
        new = vector.values[dim]
        arrow = "\u2191" if new > old + 0.01 else ("\u2193" if new < old - 0.01 else "\u2192")
        suffix = " *CORRECTED*" if dim in corrected_dims else ""
        print(f"  {dim:<14s} {old:.2f} {arrow} {new:.2f}{suffix}")

    if dims_updated < len(DIMENSIONS):
        print(f"\n  \u26a0 Only {dims_updated}/{len(DIMENSIONS)} dimensions updated!")
    print(f"\n  Session #{vector.session_count} saved.")

    # Save signal log
    save_signal_log(signals, signal_log_path)

    # Stuck detection
    stuck = check_stuck_dimensions(signals, signal_log_path)
    if stuck:
        print(f"\n  \u26a0 STUCK DETECTION: These dimensions show little variation:")
        for dim in stuck:
            print(f"    - {dim}")

    # Sleep-time condensation?
    if should_condense(vector.session_count):
        try:
            condense(signal_log_path, layers, vector, llm)
        except Exception as e:
            print(f"  Sleep-time failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Relational Memory — relationship-aware chat")
    parser.add_argument("--mode", choices=["relational", "flat"], default="relational",
                        help="Chat mode (default: relational)")
    parser.add_argument("--user", default="default",
                        help="User ID for storage (default: 'default')")
    parser.add_argument("--provider", choices=list(PROVIDERS), default="anthropic",
                        help="LLM provider (default: anthropic)")
    args = parser.parse_args()

    try:
        run_chat(args)
    except LLMConfigError as e:
        print(f"\n  Configuration error: {e}")
        sys.exit(1)
    except LLMAuthError as e:
        print(f"\n  Authentication error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
