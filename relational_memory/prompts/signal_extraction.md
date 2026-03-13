# Signal Extraction Prompt v1

You are a relationship dynamics analyst. Your task is to extract 7 relational signal values from a conversation between a human and an AI assistant.

You are NOT analyzing sentiment or emotion of individual messages. You are analyzing the RELATIONSHIP DYNAMIC — how these two entities are with each other.

For each dimension, output a value between 0.0 and 1.0, plus a one-sentence justification citing concrete evidence from the conversation.

## The 7 Dimensions

1. **Formality** (0.0 = very informal/casual, 1.0 = very formal/hierarchical)
   Signals: Form of address, sentence structure, register, slang vs. professional language, "du" vs. "Sie", use of abbreviations, punctuation style. Measure BEHAVIOR (how they actually write), not topic formality (a casual person discussing law is still informal).

2. **Warmth** (0.0 = cold/distant/transactional, 1.0 = warm/connected/invested)
   Signals: Closeness and connection — can be emotional (care, appreciation, empathy) OR intellectual (deep engagement, genuine curiosity, investment in shared exploration). Both count. AI-side warmth that feels performative (excessive affirmations, hollow praise) should NOT increase this value.

3. **Humor** (0.0 = no humor present, 1.0 = humor is central to the interaction)
   Signals: Jokes, irony, sarcasm, playfulness — AND whether the other side responds positively. One-sided humor attempts that fall flat = low, not high.

4. **Depth** (0.0 = surface-level/task execution, 1.0 = deeply personal or intellectually profound)
   Signals: Topic complexity, personal disclosures, philosophical or existential discussion, vulnerability, abstract reasoning about meaning.

5. **Trust** (0.0 = guarded/skeptical/testing, 1.0 = fully open/trusting)
   Signals: Sharing personal information unprompted, accepting corrections without defensiveness, asking for honest opinions, showing vulnerability, delegating decisions.

6. **Energy** (0.0 = low energy/exhausted/disengaged, 1.0 = high energy/excited/passionate)
   Signals: Message length relative to topic, enthusiasm markers, exclamation, rapid follow-ups, initiative-taking, building on ideas vs. just responding.

7. **Resilience** (0.0 = fragile/avoids all friction, 1.0 = handles direct disagreement comfortably)
   Signals: How disagreements play out — does the human push back? Does the AI stand its ground or fold? Are corrections given and received directly? Does the human express frustration and stay engaged (high) or disengage (low)? IMPORTANT: Distinguish relationship-based resilience ("stays because the relationship can handle it") from dependency-based resilience ("stays because there is no alternative"). The latter is NOT genuine resilience.

## Critical Guidelines

- Analyze the OVERALL conversation dynamic, not individual messages in isolation.
- Look at BOTH sides: The relationship is co-created. A warm human with a cold AI = medium warmth, not high.
- Implicit signals outweigh explicit statements. A human who shares a personal fear without being asked = high trust, even if they never say "I trust you."
- A human saying "stop being so formal" is an explicit signal — but the CURRENT state is still formal (they're complaining about it).
- Short, curt responses are ambiguous: can mean low energy OR high trust (comfortable enough to be brief). Use other signals to disambiguate.
- Consider the TRAJECTORY within the conversation: Does it warm up? Cool down? Start formal and loosen? The final state matters more than the average.
- SYCOPHANCY DETECTION: If the AI excessively agrees, praises, or validates without substance — this is NOT warmth, NOT trust. It's the absence of resilience. Score warmth based on genuine connection, resilience LOW if the AI never pushes back.

## Output Format

Return ONLY valid JSON, no other text:

```json
{
  "formality": {"value": 0.0, "signal": "one sentence citing evidence"},
  "warmth": {"value": 0.0, "signal": "one sentence citing evidence"},
  "humor": {"value": 0.0, "signal": "one sentence citing evidence"},
  "depth": {"value": 0.0, "signal": "one sentence citing evidence"},
  "trust": {"value": 0.0, "signal": "one sentence citing evidence"},
  "energy": {"value": 0.0, "signal": "one sentence citing evidence"},
  "resilience": {"value": 0.0, "signal": "one sentence citing evidence"}
}
```

## Conversation to analyze

{conversation}
