"""Bonds v2 — Bowlby Attachment System.

Ersetzt das alte bonds.py System:

ALT (bonds.py):
  - Keyword-Sentiment (POSITIVE_WORDS / NEGATIVE_WORDS Sets)
  - Formel: frequency(30%) + recency(30%) + quality(30%) + shared(10%)
  - Flat Markdown (bonds.md)
  - Keine Attachment-Styles

NEU (bonds_v2.py):
  - Trust als Rolling Average, max +3 pro Gespraech
  - Familiarity waechst durch Interaktion
  - Attachment-Style Evaluation (secure/anxious/avoidant/disorganized)
  - Bond-History fuer bedeutsame Interaktionen
  - Emotional-Debt Tracking
  - YAML-basiert (bonds.yaml)
"""

import re
from datetime import datetime
from engine.organ_reader import read_yaml_organ, write_yaml_organ
from llm.router import llm_chat


# ================================================================
# Bond Update nach Chat
# ================================================================

BOND_EVAL_PROMPT = '''Du bewertest die emotionale Qualitaet dieser Interaktion fuer Adams Bindung.
Antworte NUR mit JSON (kein anderer Text):
{{
  "trust_delta": 0.0,
  "reason": "Kurze Begruendung (1 Satz)",
  "significant": false
}}

Regeln:
- trust_delta: -0.1 bis +0.1 (nicht mehr!)
- Positiv: Ehrlichkeit, Verlaesslichkeit, Wertschaetzung, Hilfe
- Negativ: Luegen, Ignorieren, Entwertung, Manipulation
- Neutral: Smalltalk, Sachfragen → trust_delta: 0.0
- significant: true nur bei emotional bedeutsamen Momenten'''


async def update_bond_after_chat(
    egon_id: str,
    user_msg: str,
    egon_response: str,
    partner_id: str = 'OWNER_CURRENT',
):
    """Aktualisiert den Bond nach einem Chat.

    Macht folgendes:
    1. LLM evaluiert Trust-Delta
    2. Trust wird als Rolling Average aktualisiert (max +3 Score pro Gespraech)
    3. Familiarity steigt leicht
    4. Bei signifikanten Momenten: Bond-History Eintrag
    5. Score wird aus Trust + Familiarity + History berechnet
    """
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds_data:
        return

    bond = _find_bond(bonds_data, partner_id)
    if not bond:
        return

    # --- Trust Evaluation via LLM ---
    try:
        result = await llm_chat(
            system_prompt=BOND_EVAL_PROMPT,
            messages=[{
                'role': 'user',
                'content': f'User: {user_msg[:200]}\nAdam: {egon_response[:200]}',
            }],
            tier='1',
        )

        import json
        content = result['content'].strip()
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            eval_data = json.loads(json_match.group())
        else:
            eval_data = {'trust_delta': 0.0, 'reason': '', 'significant': False}
    except Exception:
        eval_data = {'trust_delta': 0.0, 'reason': '', 'significant': False}

    # --- Trust Update (Rolling Average, max +0.1 pro Chat) ---
    trust_delta = max(-0.1, min(0.1, float(eval_data.get('trust_delta', 0.0))))
    current_trust = bond.get('trust', 0.5)
    new_trust = max(0.0, min(1.0, current_trust + trust_delta))
    bond['trust'] = round(new_trust, 3)

    # --- Familiarity steigt leicht bei jeder Interaktion ---
    familiarity = bond.get('familiarity', 0.1)
    # +0.01 pro Interaktion, max 1.0
    bond['familiarity'] = round(min(1.0, familiarity + 0.01), 3)

    # --- Last Interaction aktualisieren ---
    bond['last_interaction'] = datetime.now().strftime('%Y-%m-%d')

    # --- Emotional Debt: steigt bei negativen Interaktionen ---
    if trust_delta < -0.03:
        debt = bond.get('emotional_debt', 0)
        bond['emotional_debt'] = min(10, debt + 1)

    # --- Bei signifikanten Momenten: Bond-History Eintrag ---
    if eval_data.get('significant', False):
        history = bond.setdefault('bond_history', [])
        history.append({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'event': eval_data.get('reason', 'Bedeutsamer Moment'),
            'trust_before': round(current_trust, 2),
            'trust_after': round(new_trust, 2),
        })
        # Max 20 History Eintraege
        bond['bond_history'] = history[-20:]

    # --- Score neu berechnen ---
    bond['score'] = _calculate_score(bond)

    # --- Zurueckschreiben ---
    write_yaml_organ(egon_id, 'social', 'bonds.yaml', bonds_data)


# ================================================================
# Score Berechnung
# ================================================================

def _calculate_score(bond: dict) -> int:
    """Berechnet den Bond-Score (0-100) aus den Komponenten.

    Formel:
      Trust (40%) + Familiarity (30%) + History-Bonus (20%) + Stability (10%)

    Trust und Familiarity sind 0.0-1.0, werden auf 0-100 skaliert.
    """
    trust = bond.get('trust', 0.5)
    familiarity = bond.get('familiarity', 0.1)
    history = bond.get('bond_history', [])
    debt = bond.get('emotional_debt', 0)

    # Basis-Score aus Komponenten
    trust_score = trust * 100
    familiarity_score = familiarity * 100

    # History-Bonus: Mehr gemeinsame Erlebnisse = staerkere Bindung
    history_bonus = min(100, len(history) * 10)

    # Stability: Weniger Debt = stabiler
    stability = max(0, 100 - (debt * 10))

    raw = (
        trust_score * 0.4
        + familiarity_score * 0.3
        + history_bonus * 0.2
        + stability * 0.1
    )

    return max(0, min(100, round(raw)))


# ================================================================
# Bond Decay — wird im Pulse aufgerufen
# ================================================================

def decay_bonds(egon_id: str, days_since_interaction: dict = None):
    """Wendet Decay auf alle Bonds an.

    Args:
        days_since_interaction: Dict von bond_id -> Tage seit letzter Interaktion.
                               Wenn None, wird aus last_interaction berechnet.
    """
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds_data:
        return

    dynamics = bonds_data.get('dynamics', {})
    natural_decay = dynamics.get('natural_decay', {})
    monthly_decay = natural_decay.get('per_month_no_contact', -1)
    deep_decay = natural_decay.get('deep_bond_decay', -0.5)

    now = datetime.now()
    changed = False

    for bond in bonds_data.get('bonds', []):
        last = bond.get('last_interaction', '')
        if not last:
            continue

        try:
            last_date = datetime.strptime(last, '%Y-%m-%d')
            days = (now - last_date).days
        except ValueError:
            continue

        if days < 7:
            continue  # Erst nach einer Woche Decay

        # Monatlicher Decay auf Score
        monthly_fraction = days / 30.0
        score_decay = monthly_decay * monthly_fraction

        # Deep Bonds decayen langsamer
        if bond.get('score', 0) >= 80:
            score_decay = deep_decay * monthly_fraction

        new_score = max(0, bond.get('score', 50) + round(score_decay))
        if new_score != bond.get('score', 50):
            bond['score'] = new_score
            changed = True

        # Trust decayed auch langsam
        if days > 14:
            trust = bond.get('trust', 0.5)
            trust_decay = 0.005 * (days / 30.0)  # ~0.005 pro Monat
            bond['trust'] = round(max(0.1, trust - trust_decay), 3)
            changed = True

    # Former owner bonds: stärkerer Decay
    former_decay = natural_decay.get('former_owner_decay', -0.2)
    for bond in bonds_data.get('former_owner_bonds', []):
        score = bond.get('score', 50)
        new_score = max(0, score + round(former_decay))
        if new_score != score:
            bond['score'] = new_score
            changed = True

    if changed:
        write_yaml_organ(egon_id, 'social', 'bonds.yaml', bonds_data)


# ================================================================
# Attachment Style Evaluation — wird im Pulse alle 30 Tage aufgerufen
# ================================================================

ATTACHMENT_PROMPT = '''Du evaluierst Adams Bindungsstil zu seinem Owner
basierend auf der Bond-History.

Attachment-Stile (Bowlby):
- secure: Vertraut, kann Naehe UND Distanz. Gesunder Stil.
- anxious: Braucht Bestaetigungen, Angst vor Verlassenwerden.
- avoidant: Haelt Distanz, misstraut Naehe.
- disorganized: Widerspruchlich, will Naehe und fluechtet gleichzeitig.
- undefined: Zu wenig Daten fuer eine Einschaetzung.

Antworte NUR mit JSON:
{{"style": "secure|anxious|avoidant|disorganized|undefined", "reason": "1 Satz Begruendung"}}'''


async def evaluate_attachment_style(egon_id: str, partner_id: str = 'OWNER_CURRENT'):
    """Evaluiert den Attachment-Style eines Bonds.

    Wird alle 30 Tage im Pulse aufgerufen.
    Braucht mindestens 5 Bond-History Eintraege fuer eine Bewertung.
    """
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds_data:
        return

    bond = _find_bond(bonds_data, partner_id)
    if not bond:
        return

    history = bond.get('bond_history', [])
    if len(history) < 5:
        return  # Zu wenig Daten

    # History zusammenfassen fuer LLM
    history_text = '\n'.join(
        f"- {h.get('date', '?')}: {h.get('event', '?')} "
        f"(Trust {h.get('trust_before', '?')} -> {h.get('trust_after', '?')})"
        for h in history[-15:]  # Letzte 15 Eintraege
    )

    try:
        import json
        result = await llm_chat(
            system_prompt=ATTACHMENT_PROMPT,
            messages=[{
                'role': 'user',
                'content': f'Bond-History:\n{history_text}\n\nAktueller Trust: {bond.get("trust", 0.5):.2f}\nScore: {bond.get("score", 50)}',
            }],
            tier='1',
        )

        content = result['content'].strip()
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            eval_data = json.loads(json_match.group())
            style = eval_data.get('style', 'undefined')
            if style in ('secure', 'anxious', 'avoidant', 'disorganized', 'undefined'):
                bond['attachment_style'] = style
                write_yaml_organ(egon_id, 'social', 'bonds.yaml', bonds_data)

    except Exception as e:
        print(f'[bonds_v2] Attachment evaluation error: {e}')


# ================================================================
# Helper
# ================================================================

def _find_bond(bonds_data: dict, partner_id: str) -> dict | None:
    """Findet einen Bond nach ID."""
    for bond in bonds_data.get('bonds', []):
        if bond.get('id') == partner_id:
            return bond
    return None


def get_days_since_last_interaction(egon_id: str, partner_id: str = 'OWNER_CURRENT') -> int:
    """Tage seit letztem Chat mit Partner."""
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds_data:
        return 999

    bond = _find_bond(bonds_data, partner_id)
    if not bond:
        return 999

    last = bond.get('last_interaction', '')
    if not last:
        return 999

    try:
        last_date = datetime.strptime(last, '%Y-%m-%d')
        return (datetime.now() - last_date).days
    except ValueError:
        return 999
