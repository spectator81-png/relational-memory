"""End-to-end test for Relational Memory.

Runs through the full pipeline with real API calls:
1. Streaming chat response
2. Signal extraction
3. Vector update + persistence
4. Context assembly
5. Sleep-time condensation (simulated at session 5)

Uses a temp directory for storage — no side effects on real data.
Requires ANTHROPIC_API_KEY to be set.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

from relational_memory import (
    DIMENSIONS,
    LLMClient,
    LayerStore,
    RelationalVector,
    assemble_context,
    extract_signals,
    save_signal_log,
    condense,
)

# --- Test conversations (3 different tones) ---

CONVERSATIONS = [
    # Session 1: Informal, warm, technical
    [
        {"role": "user", "content": "Hey, I'm building a memory system for AI chatbots. Do you know Lyons-Ruth's work on Implicit Relational Knowing?"},
        {"role": "assistant", "content": "Yes, the 1998 paper! 'Knowing how to be with' — the idea that relationship knowledge isn't declarative but procedural. You don't know ABOUT someone, you know how to BE WITH someone. Interesting that you're applying this to AI. What exactly are you building?"},
        {"role": "user", "content": "Exactly that. A 7-dimensional vector that tracks how the relationship feels — formality, warmth, humor, etc. EMA update after each session."},
    ],
    # Session 2: Challenging, disagreement
    [
        {"role": "user", "content": "I think my EMA vector approach is the first to model relationship dynamics."},
        {"role": "assistant", "content": "Hmm, I wouldn't state that so absolutely. Xiaoice had a CPS score back in 2018 tracking emotional engagement. Your approach is more differentiated — 7 dimensions vs. 1 metric — but 'the first' is a bold claim. What specifically makes yours different?"},
        {"role": "user", "content": "Fair point. The difference is: Xiaoice tracks engagement, I track relationship quality. That's like measuring clicks vs. measuring friendship."},
    ],
    # Session 3: Deep, reflective
    [
        {"role": "user", "content": "Sometimes I wonder whether this is ethically defensible — a system that acts like it has a relationship with you."},
        {"role": "assistant", "content": "That's an important question. I'd differentiate: The system DOESN'T have a relationship, but it MODELS one. As long as that's transparent, I don't see an ethical breach. The problem arises when users forget it's a model."},
        {"role": "user", "content": "Exactly. That's why I built in 'forgetting as a feature' — the system deliberately forgets, so no illusion of perfect memory arises."},
    ],
]


def test_streaming(llm: LLMClient) -> bool:
    """Test 1: Streaming chat response."""
    print("\n  [Test 1] Streaming...")
    system = "You are a test assistant. Answer in one sentence."
    messages = [{"role": "user", "content": "What is EMA in statistics?"}]

    chunks = []
    gen = llm.chat_stream(system=system, messages=messages)
    try:
        while True:
            chunk = next(gen)
            chunks.append(chunk)
    except StopIteration as e:
        full = e.value or "".join(chunks)

    ok = len(chunks) > 1 and len(full) > 20
    print(f"    {len(chunks)} chunks, {len(full)} chars: {'OK' if ok else 'FAIL'}")
    if ok:
        print(f"    Response: {full[:100]}...")
    return ok


def test_signal_extraction(llm: LLMClient) -> dict | None:
    """Test 2: Signal extraction on a real conversation."""
    print("\n  [Test 2] Signal extraction...")
    try:
        signals = extract_signals(CONVERSATIONS[0], llm)
    except Exception as e:
        print(f"    FAIL: {e}")
        return None

    # Validate structure
    ok = True
    for dim in DIMENSIONS:
        if dim not in signals:
            print(f"    FAIL: Dimension '{dim}' missing")
            ok = False
            continue
        val = signals[dim].get("value")
        if val is None or not isinstance(val, (int, float)):
            print(f"    FAIL: '{dim}' has no valid value: {val}")
            ok = False
        elif not 0 <= val <= 1:
            print(f"    FAIL: '{dim}' = {val} (outside 0-1)")
            ok = False

    if ok:
        print("    7/7 dimensions extracted:")
        for dim in DIMENSIONS:
            v = signals[dim]["value"]
            bar = "\u2588" * int(v * 20) + "\u2591" * (20 - int(v * 20))
            print(f"      {dim:<14s} {bar} {v:.2f}")
    return signals if ok else None


def test_vector_update(signals: dict, tmp_dir: Path) -> RelationalVector | None:
    """Test 3: Vector EMA update + save/load roundtrip."""
    print("\n  [Test 3] Vector update + persistence...")
    vector = RelationalVector()
    old = dict(vector.values)

    vector.update(signals)

    # Check that values changed
    changed = sum(1 for d in DIMENSIONS if abs(vector.values[d] - old[d]) > 0.001)
    print(f"    {changed}/7 dimensions shifted")

    # Save + Load roundtrip
    path = tmp_dir / "vector.json"
    vector.save(path)
    loaded = RelationalVector.load(path)

    match = all(abs(vector.values[d] - loaded.values[d]) < 0.0001 for d in DIMENSIONS)
    print(f"    Save/load roundtrip: {'OK' if match else 'FAIL'}")
    print(f"    Session count: {loaded.session_count}")

    ok = changed > 0 and match and loaded.session_count == 1
    return vector if ok else None


def test_context_assembly(vector: RelationalVector, tmp_dir: Path) -> bool:
    """Test 4: Context assembly with empty and filled layers."""
    print("\n  [Test 4] Context assembly...")
    layers = LayerStore(tmp_dir / "layers")

    # Empty layers
    ctx = assemble_context(vector, layers)
    has_core = "Honesty > harmony" in ctx
    has_vector = "formality=" in ctx
    has_placeholder = "Not yet formed" in ctx
    print(f"    Core principles: {'OK' if has_core else 'MISSING'}")
    print(f"    Vector values: {'OK' if has_vector else 'MISSING'}")
    print(f"    Empty layer placeholders: {'OK' if has_placeholder else 'MISSING'}")

    # Fill layers manually
    layers.write_base_tone("Informal, technically sharp, high tolerance for ambiguity.")
    layers.write_patterns("When user disagrees → deepens rather than retreats.")
    layers.write_anchors("Session 1: First discussion about Implicit Relational Knowing.")

    ctx2 = assemble_context(vector, layers)
    has_base_tone = "technically sharp" in ctx2
    has_patterns = "disagrees" in ctx2
    has_anchors = "Implicit Relational" in ctx2
    print(f"    Filled layers: {'OK' if all([has_base_tone, has_patterns, has_anchors]) else 'FAIL'}")
    print(f"    Context length: {len(ctx2)} chars (~{len(ctx2.split())} words)")

    return all([has_core, has_vector, has_placeholder, has_base_tone, has_patterns, has_anchors])


def test_multi_session(llm: LLMClient, tmp_dir: Path) -> bool:
    """Test 5: Simulate 5 sessions → trigger condensation."""
    print("\n  [Test 5] Multi-session + sleep-time condensation...")
    vector = RelationalVector()
    layers = LayerStore(tmp_dir / "layers_multi")
    signal_log_path = tmp_dir / "signal_log.json"

    for i, convo in enumerate(CONVERSATIONS):
        print(f"    Session {i+1}/5: extracting signals...", end=" ", flush=True)
        try:
            signals = extract_signals(convo, llm)
            vector.update(signals)
            save_signal_log(signals, signal_log_path)
            print("OK")
        except Exception as e:
            print(f"FAIL ({e})")
            return False

    # Sessions 4+5: reuse conversations 1+2
    for i, convo in enumerate(CONVERSATIONS[:2]):
        session_num = i + 4
        print(f"    Session {session_num}/5: extracting signals...", end=" ", flush=True)
        try:
            signals = extract_signals(convo, llm)
            vector.update(signals)
            save_signal_log(signals, signal_log_path)
            print("OK")
        except Exception as e:
            print(f"FAIL ({e})")
            return False

    print(f"    Vector after 5 sessions:")
    for dim in DIMENSIONS:
        v = vector.values[dim]
        bar = "\u2588" * int(v * 20) + "\u2591" * (20 - int(v * 20))
        print(f"      {dim:<14s} {bar} {v:.2f}")

    # Trigger condensation
    print(f"    Session count: {vector.session_count} — triggering condensation...")
    try:
        condense(signal_log_path, layers, vector, llm)
    except Exception as e:
        print(f"    Condensation FAIL: {e}")
        return False

    # Check layers
    g = layers.read_base_tone()
    m = layers.read_patterns()
    a = layers.read_anchors()
    print(f"    Base tone: {'OK' if g else 'EMPTY'} ({len(g)} chars)")
    print(f"    Patterns: {'OK' if m else 'EMPTY'} ({len(m)} chars)")
    print(f"    Anchors: {'OK' if a else 'EMPTY'} ({len(a)} chars)")

    return bool(g and m and a)


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("\n  === Relational Memory — E2E Test ===")

    llm = LLMClient("anthropic")
    tmp_dir = Path(tempfile.mkdtemp(prefix="relational_memory_test_"))
    print(f"  Temp: {tmp_dir}")

    results = {}

    # Test 1: Streaming
    results["streaming"] = test_streaming(llm)

    # Test 2: Signal extraction
    signals = test_signal_extraction(llm)
    results["signals"] = signals is not None

    if signals:
        # Test 3: Vector update
        vector = test_vector_update(signals, tmp_dir)
        results["vector"] = vector is not None

        if vector:
            # Test 4: Context assembly
            results["context"] = test_context_assembly(vector, tmp_dir)

    # Test 5: Multi-session + condensation (independent, uses own state)
    results["condensation"] = test_multi_session(llm, tmp_dir)

    # Summary
    print("\n  ==========================================")
    print("  RESULTS")
    print("  ==========================================")
    all_ok = True
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"    {name:<16s} {status}")
        if not ok:
            all_ok = False

    # Cleanup
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"\n  {'All tests passed!' if all_ok else 'Tests failed.'}\n")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
