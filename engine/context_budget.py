"""Context Budget System — verhindert Context Window Overflow.

Moonshot moonshot-v1-8k hat 8192 Token Limit.
System-Prompt darf max 6000 Tokens verbrauchen.
Rest (2000+) bleibt fuer die Antwort.
"""

MAX_CONTEXT = 6000  # Tokens fuer System-Prompt
ANSWER_RESERVE = 2000  # Tokens fuer Antwort

BUDGET = {
    'soul': 800,        # Immer voll laden
    'memory': 1800,     # Max 1800 Tokens = ~12 Eintraege
    'markers': 400,     # Top 3 nach Intensitaet
    'bonds': 300,       # Nur aktive Bonds (Score > 0.3)
    'inner_voice': 200, # Nur letzter Gedanke
    'skills': 300,      # Nur aktive Skills
    'wallet': 200,      # Kontostand + Oekonomie-Regeln
    'experience': 200,  # Letzte Erfahrungen + Learnings
    'chat_history': 2000,  # Letzte 8-10 Messages
}


def trim_to_budget(content: str, max_tokens: int) -> str:
    """Kuerze Content auf max_tokens (grob: 1 Token ~ 4 chars)."""
    max_chars = max_tokens * 4
    if len(content) <= max_chars:
        return content
    return content[:max_chars] + '\n[...gekuerzt]'


def select_memories(memories: list[dict], budget: int) -> list[dict]:
    """Waehle Memories nach Relevanz, nicht nur Aktualitaet."""
    if not memories:
        return []

    # Neueste 5 IMMER
    recent = memories[:5]
    # Rest: nach importance sortieren
    rest = sorted(
        memories[5:],
        key=lambda m: {'high': 3, 'medium': 2, 'low': 1}.get(
            m.get('importance', 'low'), 0
        ),
        reverse=True,
    )

    selected = list(recent)
    chars = sum(len(str(m)) for m in selected)
    for m in rest:
        entry_size = len(str(m))
        if chars + entry_size > budget * 4:
            break
        selected.append(m)
        chars += entry_size

    return selected
