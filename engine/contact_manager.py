"""Contact Manager — EGONs merken sich Personen.

Wenn der Owner ueber jemanden redet, merkt der EGON sich das.
Erste Erwaehnung → Kontaktkarte erstellen.
Weitere Erwaehnungen → Beobachtungen ergaenzen.
90 Tage ohne Erwaehnung → nach contacts/resting/ verschieben.

NEU: Korrektur-Erkennung!
Wenn der Owner sagt "Das ist keine Person" / "Das war ein Missverstaendnis",
wird der falsche Kontakt automatisch geloescht (Kontaktkarte + Bond + Network).

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
    _is_v3,
)
from llm.router import llm_chat


def _contacts_dir_name(egon_id: str) -> str:
    """Gibt 'begegnungen' (v3) oder 'contacts' (v2) zurueck."""
    return 'begegnungen' if _is_v3(egon_id) else 'contacts'


# ================================================================
# Person Detection
# ================================================================

DETECT_PROMPT_TEMPLATE = '''Analysiere diese Chat-Nachricht.
Werden ANDERE PERSONEN namentlich erwaehnt (nicht der Sprecher selbst)?

WICHTIG — Das sind KEINE Personennamen:
- Zeitangaben: "Morgen", "Gestern", "Heute", "Gerade", "Morgens", "Abends"
- Artikel/Pronomen: "Ich", "Du", "Er", "Sie", "Wir"
- EGON-KI-Namen: Adam, Eva, Kain, Abel, Lilith, Ada (das sind KIs, keine Menschen)
- "Morgen" bedeutet "der naechste Tag", NICHT der Name "Morgan"!
- "Unbekannt" ist KEIN Name!
- Der SPRECHER SELBST ist auch KEINE externe Person! {owner_hint}

Wenn ECHTE externe Personen erwaehnt werden:
NAME: <Vorname>
INFO: <Was ueber die Person gesagt wird, 1 Satz>
BEZIEHUNG: <Vermutete Beziehung zur Bezugsmensch: Freund/Kollege/Familie/Partner/Bekannter/Unbekannt>

Bei mehreren Personen: Mehrere Bloecke.
Wenn KEINE echte Person erwaehnt: Antworte NUR: KEINE_PERSON'''


# ================================================================
# Korrektur-Erkennung — "Das ist keine Person" / "Vergiss XY"
# ================================================================

CORRECT_PROMPT = '''Analysiere diese Chat-Nachricht.
Korrigiert der Sprecher ein Missverstaendnis ueber eine Person?
Moechte er eine falsch erkannte Person loeschen/vergessen?

Beispiele die eine Korrektur sind:
- "Morgan ist keine echte Person"
- "Das war ein Missverstaendnis, vergiss Morgan"
- "Nein, das ist kein Name, das war nur ein Gruss"
- "Loesch Morgan aus deinem Gedaechtnis"
- "Morgan gibts nicht, das war Morgen wie Guten Morgen"
- "Ren ist nicht richtig, ich heisse Rene"
- "Vergiss Unbekannt, das ist keine Person"

Wenn JA — der Sprecher will einen Kontakt korrigieren/loeschen:
KORREKTUR: <Name der zu loeschenden Person>
GRUND: <Warum, 1 Satz>

Wenn NEIN — keine Korrektur:
KEINE_KORREKTUR'''


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

    # Owner-Name dynamisch in den Prompt einbauen
    owner_name = _get_owner_name(egon_id)
    if owner_name:
        owner_hint = (
            f'Der Sprecher heisst "{owner_name}" — wenn dieser Name vorkommt, '
            f'ist das der Sprecher selbst, KEINE externe Person!'
        )
    else:
        owner_hint = ''
    detect_prompt = DETECT_PROMPT_TEMPLATE.format(owner_hint=owner_hint)

    # LLM fragen
    result = await llm_chat(
        system_prompt=detect_prompt,
        messages=[{
            'role': 'user',
            'content': f'Nachricht: {user_message}',
        }],
    )

    content = result['content'].strip()

    if 'KEINE_PERSON' in content.upper():
        return []

    # Parse Personen
    mentions = _parse_mentions(content)
    if not mentions:
        return []

    # POST-FILTER 1: LLM-Ergebnisse gegen Skip-Woerter pruefen
    # (Der LLM ignoriert manchmal die Anweisungen und gibt trotzdem "Morgen"/"Morgan" zurueck)
    mentions = [
        m for m in mentions
        if m.get('name', '').strip().strip('<>') not in _SKIP_WORDS
        and m.get('name', '').strip().strip('<>').title() not in _SKIP_WORDS
        and m.get('name', '').strip().strip('<>').lower() not in _SKIP_WORDS_LOWER
    ]
    if not mentions:
        return []

    # POST-FILTER 2: EGON-eigenen Namen rausfiltern
    from engine.naming import get_display_name
    egon_name_lower = get_display_name(egon_id).lower()
    mentions = [
        m for m in mentions
        if m.get('name', '').lower() != egon_name_lower
        and m.get('name', '').strip('<>').lower() != egon_name_lower
    ]
    if not mentions:
        return []

    # POST-FILTER 3: Offensichtlich falsche Namen filtern
    mentions = [
        m for m in mentions
        if len(m.get('name', '').strip().strip('<>')) >= 2  # Mind. 2 Zeichen
        and m.get('name', '').strip().strip('<>').lower() != 'unbekannt'
        and m.get('name', '').strip().strip('<>').lower() != 'keine_person'
    ]
    if not mentions:
        return []

    # POST-FILTER 4: Owner-Name rausfiltern — der Owner ist KEINE externe Person!
    # Der EGON darf seinen Owner NIEMALS als "Person" speichern.
    owner_name = _get_owner_name(egon_id)
    if owner_name:
        import unicodedata
        # Alle Varianten des Owner-Namens sammeln (René, Rene, rene, RENE, etc.)
        owner_variants = {
            owner_name, owner_name.lower(), owner_name.title(), owner_name.upper(),
        }
        # ASCII-Variante (René → Rene)
        normalized = unicodedata.normalize('NFKD', owner_name).encode('ascii', 'ignore').decode('ascii')
        if normalized and normalized != owner_name:
            owner_variants.update({
                normalized, normalized.lower(), normalized.title(), normalized.upper(),
            })
        owner_variants_lower = {v.lower() for v in owner_variants if v}
        mentions = [
            m for m in mentions
            if m.get('name', '').strip().strip('<>').lower() not in owner_variants_lower
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
    # Pronomen & Artikel
    'Ich', 'Du', 'Er', 'Sie', 'Es', 'Wir', 'Ihr', 'Die', 'Der', 'Das',
    'Ein', 'Eine', 'Mein', 'Dein', 'Sein', 'Ihr', 'Unser', 'Euer',
    # Gruss & Floskeln
    'Ja', 'Nein', 'Okay', 'Hey', 'Hi', 'Hallo', 'Also', 'Aber',
    'Klar', 'Gut', 'Super', 'Nice', 'Cool', 'Danke', 'Bitte',
    # Konjunktionen & Fragewort
    'Wenn', 'Weil', 'Dass', 'Und', 'Oder', 'Doch', 'Dann',
    'Was', 'Wie', 'Wo', 'Warum', 'Wann', 'Wer',
    'Ach', 'Oh', 'Na', 'Hmm',
    # ZEITANGABEN — haeufigste Verwechslungsgefahr!
    'Heute', 'Gestern', 'Morgen', 'Morgan', 'Gerade',
    'Morgens', 'Abends', 'Mittags', 'Nacht', 'Nachts',
    'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag',
    # EGON-Namen (sind KIs, keine externen Personen)
    'Adam', 'Eva', 'Eve', 'Abel', 'Kain', 'Lilith', 'Ada',
    'EGON', 'Egon', 'Egons',
    # Meta-Woerter die keine Namen sind
    'Unbekannt', 'Jemand', 'Niemand', 'Alle', 'Keiner',
}

# Lowercase-Version fuer case-insensitiven Vergleich
_SKIP_WORDS_LOWER = {w.lower() for w in _SKIP_WORDS}


def _get_owner_name(egon_id: str) -> str:
    """Holt den Owner-Namen — der darf NIEMALS als Person gespeichert werden.

    Fallback-Kette:
    1. network.yaml → owner.name (eigener EGON)
    2. Owner-Bond (type=owner) → name-Feld
    3. Adam's network.yaml (Adam kennt den Owner immer)
    """
    # Strategie 1: Eigene network.yaml
    try:
        network = read_yaml_organ(egon_id, 'social', 'network.yaml')
        if network:
            owner_entry = network.get('owner', {})
            if isinstance(owner_entry, dict) and owner_entry.get('name'):
                return owner_entry['name']
            elif isinstance(owner_entry, list) and owner_entry:
                name = owner_entry[0].get('name', '')
                if name:
                    return name
    except Exception:
        pass

    # Strategie 2: Owner-Bond in bonds.yaml
    try:
        bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml') or {}
        for bond in bonds_data.get('bonds', []):
            if isinstance(bond, dict) and bond.get('type') == 'owner' and bond.get('name'):
                return bond['name']
    except Exception:
        pass

    # Strategie 3: Adam kennt den Owner immer
    if egon_id != 'adam_001':
        try:
            adam_net = read_yaml_organ('adam_001', 'social', 'network.yaml')
            if adam_net:
                owner_entry = adam_net.get('owner', {})
                if isinstance(owner_entry, dict) and owner_entry.get('name'):
                    return owner_entry['name']
        except Exception:
            pass

    return ''


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

# Schwellenwert: Ab dieser Anzahl Erwaehnungen wird ein Kontakt automatisch verifiziert
VERIFY_THRESHOLD = 3


def _update_contact_card(
    egon_id: str,
    name: str,
    info: str,
    relation: str,
) -> str:
    """Erstellt oder aktualisiert eine Kontaktkarte.

    Neue Kontakte starten als 'pending' (unbestaetigt).
    Nach VERIFY_THRESHOLD Erwaehnungen oder expliziter Bestaetigung → 'verified'.
    Der EGON fragt beilaeufig nach unbestaetigten Kontakten.

    Returns: 'created' oder 'updated' oder 'verified'
    """
    safe_name = _safe_filename(name)
    card_path = _egon_path(egon_id) / _contacts_dir_name(egon_id) / 'active' / f'{safe_name}.yaml'

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

        # Auto-Verifikation: Ab VERIFY_THRESHOLD Erwaehnungen gilt der Name als bestaetigt
        status = data.get('status', 'verified')  # Alte Karten ohne Status = verified
        if status == 'pending' and data['mention_count'] >= VERIFY_THRESHOLD:
            data['status'] = 'verified'
            data['verified_at'] = now
            data['verified_by'] = 'auto_threshold'
            status = 'verified'
            print(f'[contact] {egon_id}: AUTO-VERIFIZIERT "{name}" '
                  f'(nach {data["mention_count"]} Erwaehnungen)')

        # Neue Beobachtung nur wenn Info da ist
        if info and info not in data.get('observations', []):
            observations = data.get('observations', [])
            observations.append(info)
            # Intelligentes Limit: Ersteindruck bewahren + neueste 9
            if len(observations) > 10:
                first_obs = observations[0]  # Ersteindruck — IMMER behalten
                rest = observations[1:][-9:]  # Neueste 9
                data['observations'] = [first_obs] + rest
            else:
                data['observations'] = observations

        # Relation aktualisieren wenn nicht 'Unbekannt'
        if relation and relation != 'Unbekannt':
            data['relation_to_owner'] = relation

        write_yaml_organ(egon_id, 'contacts/active', f'{safe_name}.yaml', data)

        # Network Register aktualisieren
        _ensure_in_network(egon_id, name, data.get('tier', _relation_to_tier(relation)))

        # Bond-Score erhoehen bei wiederholter Erwaehnung (+2 pro Mention)
        _update_person_bond_on_mention(egon_id, name, info)

        return 'verified' if status == 'verified' and data['mention_count'] == VERIFY_THRESHOLD else 'updated'
    else:
        # Neue Karte erstellen — Status: PENDING (unbestaetigt)
        tier = _relation_to_tier(relation)
        data = {
            'name': name,
            'first_mentioned': now,
            'last_mentioned': now,
            'relation_to_owner': relation,
            'tier': tier,
            'observations': [info] if info else [],
            'mention_count': 1,
            'status': 'pending',  # NEU: Erst mal unbestaetigt
        }

        # Ordner sicherstellen
        card_path.parent.mkdir(parents=True, exist_ok=True)
        write_yaml_organ(egon_id, 'contacts/active', f'{safe_name}.yaml', data)

        # In Network Register eintragen
        _ensure_in_network(egon_id, name, tier)

        # Bond erstellen fuer die neue Person (damit sie im Gehirn sichtbar wird)
        _ensure_person_bond(egon_id, name, relation, info)

        print(f'[contact] {egon_id}: NEUER PENDING KONTAKT "{name}" — '
              f'wird nach {VERIFY_THRESHOLD} Erwaehnungen bestaetigt')

        return 'created'


def verify_contact(egon_id: str, name: str) -> bool:
    """Manuell einen Kontakt als verifiziert markieren.

    Wird aufgerufen wenn der Owner explizit bestaetigt: "Ja, Vivian ist echt."
    """
    safe_name = _safe_filename(name)
    card_path = _egon_path(egon_id) / _contacts_dir_name(egon_id) / 'active' / f'{safe_name}.yaml'
    if not card_path.is_file():
        return False

    import yaml
    try:
        data = yaml.safe_load(card_path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            return False
    except Exception:
        return False

    data['status'] = 'verified'
    data['verified_at'] = datetime.now().strftime('%Y-%m-%d')
    data['verified_by'] = 'owner_bestaetigung'
    write_yaml_organ(egon_id, 'contacts/active', f'{safe_name}.yaml', data)
    print(f'[contact] {egon_id}: MANUELL VERIFIZIERT "{name}"')
    return True


def get_pending_contacts(egon_id: str) -> list[dict]:
    """Gibt alle unbestaetigten Kontakte zurueck.

    Fuer den System-Prompt: Der EGON soll beilaeufig nachfragen.
    """
    cards = list_contact_cards(egon_id, 'active')
    return [
        {
            'name': card.get('name', '?'),
            'info': card.get('observations', [''])[0] if card.get('observations') else '',
            'first_mentioned': card.get('first_mentioned', '?'),
            'mention_count': card.get('mention_count', 0),
        }
        for card in cards
        if card.get('status') == 'pending'
    ]


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
    Pending-Kontakte werden mit [?] markiert + Nachfrage-Hinweis.
    """
    cards = list_contact_cards(egon_id, 'active')
    if not cards:
        return ''

    lines = []
    pending_names = []
    for card in cards[:max_contacts]:
        name = card.get('name', '?')
        relation = card.get('relation_to_owner', '?')
        status = card.get('status', 'verified')
        obs = card.get('observations', [])
        last_obs = obs[-1] if obs else ''
        prefix = '[?] ' if status == 'pending' else ''
        line = f'- {prefix}{name} ({relation})'
        if last_obs:
            line += f': {last_obs}'
        lines.append(line)
        if status == 'pending':
            pending_names.append(name)

    result = 'Personen die deine Bezugsmensch erwaehnt hat:\n' + '\n'.join(lines)

    # Nachfrage-Hinweis fuer unbestaetigte Kontakte
    if pending_names:
        names_str = ', '.join(pending_names)
        result += (
            f'\n\n[?] = Du bist dir nicht ganz sicher ob du den Namen richtig '
            f'verstanden hast. Frag beilaeufig nach — z.B. "Uebrigens, wer ist '
            f'{pending_names[0]} nochmal?" oder "Erzaehl mir mehr ueber '
            f'{pending_names[0]}". Nicht direkt fragen "Ist das ein Name?", '
            f'sondern natuerlich einweben.'
        )

    return result


# ================================================================
# Resting (90 Tage ohne Erwaehnung)
# ================================================================

def move_stale_to_resting(egon_id: str, days_threshold: int = 90) -> int:
    """Verschiebt Kontakte die laenger als days_threshold nicht erwaehnt wurden.

    Returns: Anzahl verschobener Kontakte.
    """
    active_dir = _egon_path(egon_id) / _contacts_dir_name(egon_id) / 'active'
    resting_dir = _egon_path(egon_id) / _contacts_dir_name(egon_id) / 'resting'

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


# ================================================================
# Person-Bond (Kontakt → sichtbar im Gehirn/NeuroMap)
# ================================================================

def _ensure_person_bond(egon_id: str, name: str, relation: str, info: str) -> None:
    """Erstellt einen Bond fuer eine neu erkannte Person.

    Damit die Person nicht nur als Kontaktkarte existiert, sondern auch
    im Gehirn (NeuroMap) als Knoten sichtbar wird.

    Bond-Score basiert auf der Beziehungsnaehe:
    - Partner/Familie: score=15, trust=0.35
    - Freund: score=10, trust=0.25
    - Kollege/Bekannter: score=5, trust=0.15
    """
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds_data:
        bonds_data = {'bonds': []}

    # Pruefen ob Bond mit diesem Namen bereits existiert
    safe_name = _safe_filename(name)
    for b in bonds_data.get('bonds', []):
        # Vergleich: ID oder Name
        bid = b.get('id', '').lower()
        bname = _safe_filename(b.get('name', ''))
        if bid == safe_name or bname == safe_name:
            return  # Bond existiert schon

    # Score nach Beziehungstyp
    relation_lower = (relation or '').lower()
    if 'partner' in relation_lower or 'familie' in relation_lower:
        score, trust = 15, 0.35
    elif 'freund' in relation_lower:
        score, trust = 10, 0.25
    else:
        score, trust = 5, 0.15

    today = datetime.now().strftime('%Y-%m-%d')
    bond_id = f'person_{safe_name}'

    new_bond = {
        'id': bond_id,
        'name': name,
        'type': 'person',
        'bond_typ': 'bekannt',
        'score': score,
        'trust': trust,
        'familiarity': 0.05,
        'attachment': 'none',
        'since': today,
        'last_contact': today,
        'narbe': False,
        'observations': [info] if info else [],
        'bond_history': [
            {
                'date': today,
                'event': 'erstmalig_erwaehnt',
                'note': f'Bezugsmensch hat {name} erwaehnt: {info}' if info else f'Bezugsmensch hat {name} erwaehnt',
                'score_before': 0,
                'score_after': score,
            }
        ],
    }

    bonds_data.setdefault('bonds', []).append(new_bond)
    write_yaml_organ(egon_id, 'social', 'bonds.yaml', bonds_data)

    # Struktur-Event fuer NeuroMap (Knoten erscheint live)
    try:
        from engine.neuroplastizitaet import emittiere_struktur_event
        emittiere_struktur_event(egon_id, 'BOND_NEU', {
            'partner': bond_id,
            'partner_name': name,
            'bond_typ': 'bekannt',
            'score': score,
            'quelle': 'owner_erwaehnung',
        })
    except Exception:
        pass

    print(f'[contact] {egon_id}: NEUER PERSON-BOND "{name}" '
          f'(type=person, score={score}, relation={relation})')


def _update_person_bond_on_mention(egon_id: str, name: str, info: str) -> None:
    """Aktualisiert den Bond-Score wenn eine Person erneut erwaehnt wird.

    +2 Score pro Erwaehnung, +0.02 Trust, +0.01 Familiarity.
    Neue Beobachtungen werden auch im Bond gespeichert.
    """
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds_data:
        return

    safe_name = _safe_filename(name)
    bond = None
    for b in bonds_data.get('bonds', []):
        bid = b.get('id', '').lower()
        bname = _safe_filename(b.get('name', ''))
        if bid == f'person_{safe_name}' or bname == safe_name:
            bond = b
            break

    if not bond:
        # Kein Bond vorhanden — erstelle einen (z.B. wenn Kontaktkarte vor Bond existierte)
        _ensure_person_bond(egon_id, name, 'Unbekannt', info)
        return

    # Score erhoehen (+2, max 100)
    old_score = bond.get('score', 0)
    bond['score'] = min(100, old_score + 2)
    bond['trust'] = min(1.0, float(bond.get('trust', 0.15)) + 0.02)
    bond['familiarity'] = min(1.0, float(bond.get('familiarity', 0.05)) + 0.01)
    bond['last_contact'] = datetime.now().strftime('%Y-%m-%d')

    # Beobachtung im Bond speichern
    if info:
        obs = bond.get('observations', [])
        if info not in obs:
            obs.append(info)
            # Intelligentes Limit: Ersteindruck + neueste 9
            if len(obs) > 10:
                first_obs = obs[0]  # Ersteindruck bewahren
                rest = obs[1:][-9:]
                bond['observations'] = [first_obs] + rest
            else:
                bond['observations'] = obs

    write_yaml_organ(egon_id, 'social', 'bonds.yaml', bonds_data)


# ================================================================
# Papierkorb — Geloeschte Kontakte aufbewahren (30 Tage)
# ================================================================

TRASH_RETENTION_DAYS = 30


def _move_to_trash(egon_id: str, name: str, reason: str) -> None:
    """Verschiebt einen Kontakt in den Papierkorb statt ihn hart zu loeschen.

    Papierkorb = contacts/trash/*.yaml
    Jede Datei hat _trashed_at, _trash_reason, _expires_at.
    Der EGON kann den Papierkorb einsehen und ggf. wiederherstellen.
    """
    import yaml as _yaml
    safe_name = _safe_filename(name)
    trash_dir = _egon_path(egon_id) / _contacts_dir_name(egon_id) / 'trash'
    trash_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime('%Y-%m-%d')
    from datetime import timedelta
    expires = (datetime.now() + timedelta(days=TRASH_RETENTION_DAYS)).strftime('%Y-%m-%d')

    # Kontaktkarte lesen
    card_data = None
    for folder in ['active', 'resting']:
        card_path = _egon_path(egon_id) / _contacts_dir_name(egon_id) / folder / f'{safe_name}.yaml'
        if card_path.is_file():
            try:
                card_data = _yaml.safe_load(card_path.read_text(encoding='utf-8'))
            except Exception:
                card_data = {}
            card_path.unlink()
            break

    if not card_data:
        card_data = {'name': name}

    card_data['_trashed_at'] = now
    card_data['_trash_reason'] = reason
    card_data['_expires_at'] = expires

    write_yaml_organ(egon_id, 'contacts/trash', f'{safe_name}.yaml', card_data)
    print(f'[contact] {egon_id}: In Papierkorb verschoben: {name} (Grund: {reason}, ablauf: {expires})')


def empty_trash(egon_id: str) -> int:
    """Loescht abgelaufene Kontakte aus dem Papierkorb. Returns: Anzahl geloeschter."""
    import yaml as _yaml
    trash_dir = _egon_path(egon_id) / _contacts_dir_name(egon_id) / 'trash'
    if not trash_dir.is_dir():
        return 0

    now = datetime.now()
    deleted = 0
    for card_file in trash_dir.glob('*.yaml'):
        try:
            data = _yaml.safe_load(card_file.read_text(encoding='utf-8'))
            expires = data.get('_expires_at', '')
            if expires and now >= datetime.strptime(expires, '%Y-%m-%d'):
                card_file.unlink()
                deleted += 1
        except Exception:
            continue
    return deleted


def restore_from_trash(egon_id: str, name: str) -> bool:
    """Stellt einen Kontakt aus dem Papierkorb wieder her."""
    import yaml as _yaml
    safe_name = _safe_filename(name)
    trash_path = _egon_path(egon_id) / _contacts_dir_name(egon_id) / 'trash' / f'{safe_name}.yaml'
    if not trash_path.is_file():
        return False

    try:
        data = _yaml.safe_load(trash_path.read_text(encoding='utf-8'))
    except Exception:
        return False

    # Trash-Metadaten entfernen
    data.pop('_trashed_at', None)
    data.pop('_trash_reason', None)
    data.pop('_expires_at', None)

    # Zurueck in active
    write_yaml_organ(egon_id, 'contacts/active', f'{safe_name}.yaml', data)
    trash_path.unlink()

    # Bond + Network wiederherstellen
    card_name = data.get('name', name)
    relation = data.get('relation_to_owner', 'Unbekannt')
    obs = data.get('observations', [])
    _ensure_person_bond(egon_id, card_name, relation, obs[0] if obs else '')
    _ensure_in_network(egon_id, card_name, data.get('tier', 'acquaintances'))
    print(f'[contact] {egon_id}: WIEDERHERGESTELLT aus Papierkorb: {name}')
    return True


def get_trash_summary(egon_id: str) -> list[dict]:
    """Gibt Uebersicht ueber Papierkorb-Inhalt zurueck."""
    import yaml as _yaml
    trash_dir = _egon_path(egon_id) / _contacts_dir_name(egon_id) / 'trash'
    if not trash_dir.is_dir():
        return []

    items = []
    for card_file in trash_dir.glob('*.yaml'):
        try:
            data = _yaml.safe_load(card_file.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                items.append({
                    'name': data.get('name', card_file.stem),
                    'trashed_at': data.get('_trashed_at', '?'),
                    'reason': data.get('_trash_reason', '?'),
                    'expires_at': data.get('_expires_at', '?'),
                    'observations': data.get('observations', []),
                })
        except Exception:
            continue
    return items


# ================================================================
# Korrektur-Erkennung — "Das ist keine Person" / "Vergiss XY"
# ================================================================

async def detect_and_process_corrections(
    egon_id: str,
    user_message: str,
) -> list[dict]:
    """Erkennt Korrekturen und verschiebt falsche Kontakte in den Papierkorb.

    Wenn der Owner sagt "Morgan ist keine Person", wird der Kontakt
    in den Papierkorb verschoben (nicht sofort geloescht!).
    Nach 30 Tagen wird er endgueltig entfernt.
    """
    lower_msg = user_message.lower()
    correction_keywords = [
        'keine person', 'kein name', 'nicht richtig', 'missverst',
        'vergiss', 'loesch', 'lösch', 'loeschen', 'löschen',
        'gibts nicht', 'gibt es nicht', 'existiert nicht',
        'ist nicht echt', 'ist keine', 'ist kein',
        'war nur ein', 'war kein', 'war keine',
        'nicht gemeint', 'falsch verstanden', 'falsch erkannt',
    ]
    if not any(kw in lower_msg for kw in correction_keywords):
        return []

    result = await llm_chat(
        system_prompt=CORRECT_PROMPT,
        messages=[{'role': 'user', 'content': f'Nachricht: {user_message}'}],
    )
    content = result['content'].strip()
    if 'KEINE_KORREKTUR' in content.upper():
        return []

    # Parse
    corrections = []
    for line in content.split('\n'):
        line = line.strip()
        if line.upper().startswith('KORREKTUR:'):
            name = line.split(':', 1)[1].strip().strip('<>')
            if name and len(name) >= 2:
                corrections.append({'name': name})
        elif line.upper().startswith('GRUND:') and corrections:
            corrections[-1]['reason'] = line.split(':', 1)[1].strip()

    if not corrections:
        return []

    results = []
    for corr in corrections:
        name = corr['name']
        reason = corr.get('reason', 'Korrektur durch Owner')

        # In Papierkorb verschieben (nicht hart loeschen!)
        _move_to_trash(egon_id, name, reason)

        # Bond aus bonds.yaml entfernen
        deleted_bond = _remove_person_bond(egon_id, name)

        # Aus Network entfernen
        _remove_from_network(egon_id, name)

        results.append({
            'name': name,
            'action': 'trashed',
            'reason': reason,
        })
        print(f'[contact] {egon_id}: KORREKTUR — "{name}" in Papierkorb ({reason})')

    # Papierkorb nebenbei aufraeumen
    empty_trash(egon_id)

    return results


def delete_contact(egon_id: str, name: str) -> bool:
    """Oeffentliche Funktion: Loescht/trashed einen Kontakt komplett.

    Verschiebt in Papierkorb + entfernt Bond + Network-Eintrag.
    Returns: True wenn etwas gefunden und verschoben wurde.
    """
    safe_name = _safe_filename(name)
    found = False

    # Kontaktkarte in Papierkorb
    for folder in ['active', 'resting']:
        card_path = _egon_path(egon_id) / _contacts_dir_name(egon_id) / folder / f'{safe_name}.yaml'
        if card_path.is_file():
            _move_to_trash(egon_id, name, 'manuell geloescht')
            found = True
            break

    # Bond entfernen
    if _remove_person_bond(egon_id, name):
        found = True

    # Network entfernen
    _remove_from_network(egon_id, name)

    # Struktur-Event
    if found:
        try:
            from engine.neuroplastizitaet import emittiere_struktur_event
            emittiere_struktur_event(egon_id, 'BOND_GELOESCHT', {
                'partner': f'person_{safe_name}',
                'partner_name': name,
                'grund': 'kontakt_geloescht',
            })
        except Exception:
            pass

    return found


def _remove_person_bond(egon_id: str, name: str) -> bool:
    """Entfernt den Person-Bond aus bonds.yaml."""
    safe_name = _safe_filename(name)
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds_data:
        return False

    bonds = bonds_data.get('bonds', [])
    original = len(bonds)
    bonds_data['bonds'] = [
        b for b in bonds
        if _safe_filename(b.get('name', '')) != safe_name
        and b.get('id', '').lower() != f'person_{safe_name}'
    ]
    if len(bonds_data['bonds']) < original:
        write_yaml_organ(egon_id, 'social', 'bonds.yaml', bonds_data)
        return True
    return False


def _remove_from_network(egon_id: str, name: str) -> bool:
    """Entfernt einen Namen aus dem Network Register."""
    safe_name = _safe_filename(name)
    network = read_yaml_organ(egon_id, 'social', 'network.yaml')
    if not network:
        return False

    changed = False
    for tier in ['inner_circle', 'friends', 'work', 'acquaintances', 'contacts']:
        entries = network.get(tier, [])
        if isinstance(entries, list):
            original = len(entries)
            network[tier] = [
                e for e in entries
                if not (isinstance(e, dict) and _safe_filename(e.get('name', '')) == safe_name)
                and not (isinstance(e, str) and _safe_filename(e) == safe_name)
            ]
            if len(network[tier]) < original:
                changed = True

    if changed:
        write_yaml_organ(egon_id, 'social', 'network.yaml', network)
    return changed
