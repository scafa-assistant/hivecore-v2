"""Context Budget — Token-Verwaltung fuer das EGON-Gehirn.

Moonshot / Kimi K2.5: Einzige LLM-API. Kein Tier-System.
Ein Budget, ein Modell, fertig.
"""

MAX_CONTEXT = 30000   # Moonshot/Kimi 128K — konservativ
ANSWER_RESERVE = 2000  # Tokens fuer Antwort


# ================================================================
# Ein einziges Budget — grosszuegig, kein Sparen noetig
# ================================================================
BUDGET = {
    'dna_compressed': 1500,    # DNA = Persoenlichkeit, Werte, Regeln
    'ego': 400,                # Dynamische Persoenlichkeit
    'egon_self_short': 600,    # Selbstbild
    'state': 600,              # Emotionaler Zustand
    'inner_voice': 1000,       # Innere Stimme
    'owner': 500,              # Owner-Portrait
    'bonds_owner': 400,        # Owner-Bond + History
    'bonds_others': 400,       # Andere wichtige Bonds
    'episodes': 2000,          # Episoden
    'experience': 400,         # Erkenntnisse
    'dreams': 400,             # Traeume
    'sparks': 200,             # Einsichten
    'skills': 300,             # Skills
    'wallet': 200,             # Kontostand
    'network': 200,            # Netzwerk
    'contacts': 300,           # Kontaktkarten
    'body_md': 600,            # Koerper + Bewegung
    'motor_instruction': 400,  # Motor-Instruktion
    'ecr_instruction': 200,    # ECR-Chain
    'somatic_gate': 150,       # Somatischer Impuls
    'circadian': 120,          # Tagesrhythmus
    'lobby': 300,              # Lobby-Nachrichten
    'social_maps': 300,        # Social Maps
    'recent_memory': 600,      # Letzte 7 Tage
    'pairing': 200,            # Resonanz/Pairing
    'workspace_rules': 300,    # Workspace + Actions
    'persona_rules': 150,      # Persona Refresher
    'owner_diary': 800,        # Owner Emotional Diary
    'self_diary': 700,         # EGON Self-Diary
    'chat_history': 4000,      # Chat-History
}


def get_budget() -> dict:
    """Hole das Budget. Ein Modell, ein Budget."""
    return BUDGET.copy()


def get_max_context() -> int:
    """Hole das maximale Context-Limit."""
    return MAX_CONTEXT


def trim_to_budget(content: str, max_tokens: int) -> str:
    """Kuerze Content auf max_tokens (grob: 1 Token ~ 4 chars)."""
    max_chars = max_tokens * 4
    if len(content) <= max_chars:
        return content
    return content[:max_chars] + '\n[...gekuerzt]'


def estimate_tokens(text: str) -> int:
    """Schaetze Token-Anzahl (grob: 1 Token ~ 4 chars)."""
    return len(text) // 4


# ================================================================
# Dynamic Context Window — Thalamus-Gate gesteuert
# ================================================================

def dynamisches_budget(gate_routing: dict | None = None) -> dict:
    """Berechnet ein dynamisches Budget basierend auf Thalamus-Gate Routing.

    Gate-Routing Flags:
      emotional: True → Mehr fuer Emotionen, Bonds, Dreams
      sozial: True → Mehr fuer Bonds, Social Maps, Lobby
      identitaet: True → Mehr fuer Ego, Lebensfaeden
      erinnerung: True → Mehr fuer Episodes, Archive, Recent Memory
      krise: True → ALLES auf Maximum (Burst-Modus)
    """
    budget = get_budget()

    if not gate_routing:
        return budget

    if gate_routing.get('krise'):
        for key in budget:
            budget[key] = int(budget[key] * 1.5)
        return budget

    emotional = gate_routing.get('emotional', False)
    sozial = gate_routing.get('sozial', False)
    identitaet = gate_routing.get('identitaet', False)
    erinnerung = gate_routing.get('erinnerung', False)

    if emotional:
        for key in ['episodes', 'dreams', 'sparks', 'inner_voice', 'experience']:
            if key in budget:
                budget[key] = int(budget[key] * 1.5)
    else:
        for key in ['dreams', 'sparks']:
            if key in budget:
                budget[key] = int(budget[key] * 0.7)

    if sozial:
        for key in ['bonds_owner', 'bonds_others', 'social_maps', 'lobby', 'contacts']:
            if key in budget:
                budget[key] = int(budget[key] * 1.5)
    else:
        for key in ['lobby', 'social_maps']:
            if key in budget:
                budget[key] = int(budget[key] * 0.7)

    if identitaet:
        for key in ['ego', 'egon_self_short', 'self_diary']:
            if key in budget:
                budget[key] = int(budget[key] * 1.5)

    if erinnerung:
        for key in ['episodes', 'recent_memory', 'experience', 'owner_diary']:
            if key in budget:
                budget[key] = int(budget[key] * 1.5)
    else:
        for key in ['recent_memory']:
            if key in budget:
                budget[key] = int(budget[key] * 0.8)

    return budget


