"""Contact Manager — Adam merkt sich Personen.

Wenn der Owner ueber jemanden redet, merkt Adam sich das.
Erste Erwaehnung → Kontaktkarte erstellen.
Weitere Erwaehnungen → Beobachtungen ergaenzen.
90 Tage ohne Erwaehnung → nach contacts/resting/ verschieben.

Kontaktkarten liegen in: contacts/active/*.yaml
Register in: social/network.yaml (7-Tier Hierarchie)
"""

import re
from datetime import datetime
from pathlib import Path

from engine.organ_reader import (
    read_yaml_organ,
    write_yaml_organ,
    list_contact_cards,
    _egon_path,
)
from llm.router import llm_chat


# ================================================================
# Person Detection
# ================================================================

DETECT_PROMPT = '''Analysiere diese Chat-Nachricht.
Werden ANDERE PERSONEN namentlich erwaehnt (nicht der Sprecher selbst, nicht "Adam")?

Wenn ja: Gib die Namen und was ueber sie gesagt wird zurueck.
Format:
NAME: <Vorname>
INFO: <Was ueber die Person gesagt wird, 1 Satz>
BEZIEHUNG: <Vermutete Beziehung zum Owner: Freund/Kollege/Familie/Partner/Bekannter/Unbekannt>

Bei mehreren Personen: Mehrere Bloecke.
Wenn KEINE Person erwaehnt: Antworte NUR: KEINE_PERSON'''


async def detect_and_process_mentions(
    egon_id: str,
    user_message: str,
    adam_response: str,
) -> list[dict]:
    """Erkennt Personen-Erwaehnungen und aktualisiert Kontaktkarten.

    Returns:
        Liste von Updates: [{'name': '...', 'action': 'created'|'updated'}, ...]
    """
    # Schneller Pre-Check: Enthaelt die Nachricht ueberhaupt Grossbuchstaben-Woerter?
    # (Eigennamen fangen mit Grossbuchstaben an)
    words = user_message.split()
    has_potential_name = any(
        w[0].isupper() and len(w) > 1 and w not in _SKIP_WORDS
        for w in words if w and w[0].isalpha()
    )

    if not has_potential_name:
        return []

    # LLM fragen
    result = await llm_chat(
        system_prompt=DETECT_PROMPT,
        messages=[{
            'role': 'user',
            'content': f'Nachricht: {user_message}',
        }],
        tier='1',
    )

    content = result['content'].strip()

    if 'KEINE_PERSON' in content.upper():
        return []

    # Parse Personen
    mentions = _parse_mentions(content)
    if not mentions:
        return []

    # EGON-eigenen Namen rausfiltern (Eva soll sich nicht selbst als Kontakt eintragen)
    egon_name_lower = egon_id.replace('_', ' ').split()[0].lower()
    mentions = [
        m for m in mentions
        if m.get('name', '').lower() != egon_name_lower
        and m.get('name', '').strip('<>').lower() != egon_name_lower
    ]
    if not mentions:
        return []

    # Kontaktkarten aktualisieren
    updates = []
    for mention in mentions:
        name = mention['name']
        info = mention.get('info', '')
        relation = mention.get('relation', 'Unbekannt')

        action = _update_contact_card(egon_id, name, info, relation)
        updates.append({'name': name, 'action': action})

    return updates


# Woerter die keine Eigennamen sind (haeufige deutsche Satzanfaenge + EGON-Namen)
_SKIP_WORDS = {
    'Ich', 'Du', 'Er', 'Sie', 'Es', 'Wir', 'Ihr', 'Die', 'Der', 'Das',
    'Ein', 'Eine', 'Mein', 'Dein', 'Sein', 'Ihr', 'Unser', 'Euer',
    'Ja', 'Nein', 'Okay', 'Hey', 'Hi', 'Hallo', 'Also', 'Aber',
    'Wenn', 'Weil', 'Dass', 'Und', 'Oder', 'Doch', 'Dann', 'Heute',
    'Gestern', 'Morgen', 'Adam', 'Gerade', 'Danke', 'Bitte',
    'Klar', 'Gut', 'Super', 'Nice', 'Cool', 'Was', 'Wie', 'Wo',
    'Warum', 'Wann', 'Wer', 'Ach', 'Oh', 'Na', 'Hmm',
    # EGON-eigene Namen (sollen sich nicht selbst als Kontakt eintragen)
    'Eva', 'Eve', 'EGON', 'Egon',
}


def _parse_mentions(content: str) -> list[dict]:
    """Parsed LLM-Output in Liste von Personen-Dicts."""
    mentions = []
    current = {}

    for line in content.split('\n'):
        line = line.strip()
        if not line:
            if current.get('name'):
                mentions.append(current)
                current = {}
            continue

        if line.upper().startswith('NAME:'):
            if current.get('name'):
                mentions.append(current)
            current = {'name': line.split(':', 1)[1].strip()}
        elif line.upper().startswith('INFO:'):
            current['info'] = line.split(':', 1)[1].strip()
        elif line.upper().startswith('BEZIEHUNG:'):
            current['relation'] = line.split(':', 1)[1].strip()

    if current.get('name'):
        mentions.append(current)

    return mentions


# ================================================================
# Contact Card CRUD
# ================================================================

def _update_contact_card(
    egon_id: str,
    name: str,
    info: str,
    relation: str,
) -> str:
    """Erstellt oder aktualisiert eine Kontaktkarte.

    Returns: 'created' oder 'updated'
    """
    safe_name = _safe_filename(name)
    card_path = _egon_path(egon_id) / 'contacts' / 'active' / f'{safe_name}.yaml'

    now = datetime.now().strftime('%Y-%m-%d')

    if card_path.is_file():
        # Existierende Karte aktualisieren
        import yaml
        try:
            data = yaml.safe_load(card_path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

        data['last_mentioned'] = now
        data['mention_count'] = data.get('mention_count', 0) + 1

        # Neue Beobachtung nur wenn Info da ist
        if info and info not in data.get('observations', []):
            observations = data.get('observations', [])
            observations.append(info)
            # Max 10 Beobachtungen behalten
            data['observations'] = observations[-10:]

        # Relation aktualisieren wenn nicht 'Unbekannt'
        if relation and relation != 'Unbekannt':
            data['relation_to_owner'] = relation

        write_yaml_organ(egon_id, 'contacts/active', f'{safe_name}.yaml', data)

        # Network Register aktualisieren
        _ensure_in_network(egon_id, name, data.get('tier', _relation_to_tier(relation)))

        return 'updated'
    else:
        # Neue Karte erstellen
        tier = _relation_to_tier(relation)
        data = {
            'name': name,
            'first_mentioned': now,
            'last_mentioned': now,
            'relation_to_owner': relation,
            'tier': tier,
            'observations': [info] if info else [],
            'mention_count': 1,
        }

        # Ordner sicherstellen
        card_path.parent.mkdir(parents=True, exist_ok=True)
        write_yaml_organ(egon_id, 'contacts/active', f'{safe_name}.yaml', data)

        # In Network Register eintragen
        _ensure_in_network(egon_id, name, tier)

        return 'created'


def _relation_to_tier(relation: str) -> str:
    """Mappt eine Beziehungsbeschreibung auf einen Network-Tier."""
    relation_lower = relation.lower() if relation else ''

    if 'partner' in relation_lower or 'familie' in relation_lower:
        return 'inner_circle'
    elif 'freund' in relation_lower:
        return 'friends'
    elif 'kollege' in relation_lower or 'arbeit' in relation_lower:
        return 'work'
    elif 'bekannt' in relation_lower:
        return 'acquaintances'
    else:
        return 'acquaintances'


def _safe_filename(name: str) -> str:
    """Macht einen Namen filesystem-safe (lowercase, keine Sonderzeichen)."""
    safe = name.lower().strip()
    safe = re.sub(r'[^a-z0-9_\-]', '_', safe)
    safe = re.sub(r'_+', '_', safe).strip('_')
    return safe or 'unknown'


# ================================================================
# Network Register (social/network.yaml)
# ================================================================

def _ensure_in_network(egon_id: str, name: str, tier: str) -> None:
    """Stellt sicher dass die Person im Network Register steht."""
    network = read_yaml_organ(egon_id, 'social', 'network.yaml')
    if not network:
        return

    # Pruefe ob schon drin (in irgendeinem Tier)
    all_tiers = ['inner_circle', 'friends', 'work', 'acquaintances']
    for t in all_tiers:
        entries = network.get(t, [])
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and entry.get('name') == name:
                    # Schon drin — Tier-Upgrade pruefen
                    if _tier_rank(tier) < _tier_rank(t):
                        # Upgrade: Aus altem Tier entfernen
                        entries.remove(entry)
                        network[t] = entries
                        # In neuen Tier eintragen
                        _add_to_tier(network, tier, name)
                        write_yaml_organ(egon_id, 'social', 'network.yaml', network)
                    return
                elif isinstance(entry, str) and entry == name:
                    return  # Schon drin als String

    # Nicht gefunden — neu eintragen
    _add_to_tier(network, tier, name)
    write_yaml_organ(egon_id, 'social', 'network.yaml', network)


def _add_to_tier(network: dict, tier: str, name: str) -> None:
    """Fuegt einen Namen in den richtigen Tier ein."""
    if tier not in network:
        network[tier] = []
    if not isinstance(network[tier], list):
        network[tier] = []

    now = datetime.now().strftime('%Y-%m-%d')
    network[tier].append({
        'name': name,
        'since': now,
    })


def _tier_rank(tier: str) -> int:
    """Gibt den Rang eines Tiers zurueck (niedriger = naeher)."""
    ranks = {
        'inner_circle': 0,
        'friends': 1,
        'work': 2,
        'acquaintances': 3,
        'archive': 4,
    }
    return ranks.get(tier, 3)


# ================================================================
# Kontakt-Suche
# ================================================================

def get_contact(egon_id: str, name: str) -> dict:
    """Sucht eine Kontaktkarte nach Name.

    Sucht zuerst in active, dann in resting.
    Returns: Kontaktkarte als dict, oder {} wenn nicht gefunden.
    """
    safe_name = _safe_filename(name)

    # Active suchen
    for card in list_contact_cards(egon_id, 'active'):
        if _safe_filename(card.get('name', '')) == safe_name:
            return card

    # Resting suchen
    for card in list_contact_cards(egon_id, 'resting'):
        if _safe_filename(card.get('name', '')) == safe_name:
            return card

    return {}


def get_contacts_summary(egon_id: str, max_contacts: int = 5) -> str:
    """Gibt eine Kurzzusammenfassung aller aktiven Kontakte zurueck.

    Fuer den System-Prompt bei owner_chat.
    """
    cards = list_contact_cards(egon_id, 'active')
    if not cards:
        return ''

    lines = []
    for card in cards[:max_contacts]:
        name = card.get('name', '?')
        relation = card.get('relation_to_owner', '?')
        obs = card.get('observations', [])
        last_obs = obs[-1] if obs else ''
        line = f'- {name} ({relation})'
        if last_obs:
            line += f': {last_obs}'
        lines.append(line)

    return 'Personen die dein Owner erwaehnt hat:\n' + '\n'.join(lines)


# ================================================================
# Resting (90 Tage ohne Erwaehnung)
# ================================================================

def move_stale_to_resting(egon_id: str, days_threshold: int = 90) -> int:
    """Verschiebt Kontakte die laenger als days_threshold nicht erwaehnt wurden.

    Returns: Anzahl verschobener Kontakte.
    """
    active_dir = _egon_path(egon_id) / 'contacts' / 'active'
    resting_dir = _egon_path(egon_id) / 'contacts' / 'resting'

    if not active_dir.is_dir():
        return 0

    resting_dir.mkdir(parents=True, exist_ok=True)
    moved = 0
    now = datetime.now()

    for card_file in active_dir.glob('*.yaml'):
        import yaml
        try:
            data = yaml.safe_load(card_file.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                continue
        except Exception:
            continue

        last = data.get('last_mentioned', '')
        if not last:
            continue

        try:
            last_date = datetime.strptime(last, '%Y-%m-%d')
            days = (now - last_date).days
            if days >= days_threshold:
                # Verschieben
                target = resting_dir / card_file.name
                card_file.rename(target)
                moved += 1
        except ValueError:
            continue

    return moved
