"""Context Budget v2 — Token-Verwaltung fuer das 12-Organe-Gehirn.

Moonshot (Tier 1): 8192 Token Limit → 6000 fuer System-Prompt
Kimi K2.5 (Tier 2): 128K → viel mehr Raum
Sonnet (Tier 3): 200K → maximaler Raum

Die Budgets passen sich an den LLM-Tier an.
yaml_to_prompt() komprimiert YAML-Organe massiv,
daher sind die Budgets kleiner als bei rohem Text.
"""

MAX_CONTEXT_TIER1 = 6000   # Moonshot 8K
MAX_CONTEXT_TIER2 = 30000  # Kimi K2.5 (konservativ)
MAX_CONTEXT_TIER3 = 50000  # Sonnet (konservativ)
ANSWER_RESERVE = 2000      # Tokens fuer Antwort


# ================================================================
# TIER 1 Budget (Moonshot 8K) — Eng, jedes Token zaehlt
# ================================================================
BUDGET_TIER1 = {
    'dna_compressed': 1500,    # DNA ist WER ICH BIN — Persoenlichkeit, Sprechstil,
                               # Werte, Regeln. Wie Adams soul.md. MUSS gross sein.
    'ego': 200,                # Dynamische Persoenlichkeit (klein)
    'egon_self_short': 300,    # Selbstbild: Erste 2 Abschnitte (Wer ich bin + Wie ich aussehe)
    'state': 300,              # yaml_to_prompt Output (gekuerzt)
    'inner_voice': 300,        # Letzte 3-5 Eintraege (gekuerzt)
    'owner': 150,              # Owner-Portrait (kompakt)
    'bonds_owner': 100,        # Nur Owner-Bond (gekuerzt)
    'episodes': 500,           # Letzte 5-8 Episoden (gekuerzt)
    'experience': 100,         # Top 3 relevante Erkenntnisse (gekuerzt)
    'dreams': 150,             # Letzte 2-3 Traeume (narrativ)
    'sparks': 100,             # Letzte 2-3 Sparks (Einsichten)
    'skills': 100,             # Kompakte Skill-Liste (gekuerzt)
    'wallet': 80,              # Nur Kontostand (gekuerzt)
    'body_md': 300,             # body.md — Koerper-Beschreibung + Bewegungs-Vokabular
    'motor_instruction': 200,   # Motor-Instruktion (###BODY### Output-Format)
    'ecr_instruction': 150,    # ECR-Chain Anweisung
    'somatic_gate': 100,       # Patch 1: Somatischer Impuls
    'circadian': 80,           # Patch 2: Tagesrhythmus
    'lobby': 150,              # Patch 3: Lobby-Nachrichten
    'social_maps': 100,        # Patch 3: Social Maps
    'recent_memory': 400,      # Patch 5: Letzte 7 Tage
    'workspace_rules': 200,    # Workspace + Action Regeln
    'persona_rules': 100,      # Persona Refresher (alle 8 Messages)
    'chat_history': 2000,      # Letzte 8-10 Messages
}


# ================================================================
# TIER 2 Budget (Kimi K2.5, 128K) — Mehr Raum fuer alles
# ================================================================
BUDGET_TIER2 = {
    'dna_compressed': 1500,    # Mehr DNA-Sektionen geladen
    'ego': 400,                # Volle Persoenlichkeit
    'egon_self_short': 600,    # Mehr Selbstbild-Sektionen
    'state': 600,              # Ausfuehrlicherer Zustand
    'inner_voice': 1000,       # Letzte 10+ Eintraege
    'owner': 500,              # Ausfuehrliches Owner-Portrait
    'bonds_owner': 400,        # Owner-Bond + History
    'bonds_others': 400,       # Andere wichtige Bonds
    'episodes': 2000,          # Letzte 20 + Thread-Episoden
    'experience': 400,         # Top 5-8 Erkenntnisse
    'dreams': 400,             # Letzte 3-5 Traeume (ausfuehrlich)
    'sparks': 200,             # Alle Sparks
    'skills': 300,             # Volle Skill-Liste
    'wallet': 200,             # Kontostand + Transaktionen
    'network': 200,            # Netzwerk-Ueberblick
    'contacts': 300,           # Relevante Kontaktkarten
    'body_md': 600,             # body.md — Volle Koerper-Beschreibung
    'motor_instruction': 400,   # Motor-Instruktion (ausfuehrlicher)
    'ecr_instruction': 200,    # ECR-Chain ausfuehrlicher
    'somatic_gate': 150,       # Patch 1: Somatischer Impuls
    'circadian': 120,          # Patch 2: Tagesrhythmus
    'lobby': 300,              # Patch 3: Lobby-Nachrichten
    'social_maps': 300,        # Patch 3: Social Maps
    'recent_memory': 600,      # Patch 5: Letzte 7 Tage (ausfuehrlicher)
    'workspace_rules': 300,    # Workspace + Action Regeln
    'persona_rules': 150,      # Persona Refresher
    'chat_history': 4000,      # Mehr Chat-History
}


def get_budget(tier: int = 1) -> dict:
    """Hole das passende Budget fuer den LLM-Tier."""
    if tier >= 3:
        return BUDGET_TIER2.copy()  # Tier 3 nutzt gleiche Budgets wie Tier 2 (vorerst)
    elif tier >= 2:
        return BUDGET_TIER2.copy()
    else:
        return BUDGET_TIER1.copy()


def get_max_context(tier: int = 1) -> int:
    """Hole das maximale Context-Limit fuer den LLM-Tier."""
    if tier >= 3:
        return MAX_CONTEXT_TIER3
    elif tier >= 2:
        return MAX_CONTEXT_TIER2
    else:
        return MAX_CONTEXT_TIER1


def trim_to_budget(content: str, max_tokens: int) -> str:
    """Kuerze Content auf max_tokens (grob: 1 Token ~ 4 chars)."""
    max_chars = max_tokens * 4
    if len(content) <= max_chars:
        return content
    return content[:max_chars] + '\n[...gekuerzt]'


def estimate_tokens(text: str) -> int:
    """Schaetze Token-Anzahl (grob: 1 Token ~ 4 chars)."""
    return len(text) // 4
