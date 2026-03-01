"""Multi-EGON Interaktionsprotokoll — Patch 12.

Turn-Based Kommunikation, Asymmetrische Wahrnehmung & Netzwerk-Dynamik.

Kern-Prinzipien:
1. GETRENNTE INSTANZEN — Jeder EGON hat seinen eigenen LLM-Call
2. ASYMMETRISCHE WAHRNEHMUNG — Beide verarbeiten unabhaengig
3. TURN-BASED — Strukturierter Austausch, keine Race Conditions
4. KANALBASIERT — Direkt (1:1), Gruppe (3+), Broadcast (alle)
5. JEDER VERARBEITET FUER SICH — Post-Processing ist getrennt

Biologische Basis:
- Premack & Woodruff (1978): Theory of Mind
- Shannon & Weaver (1949): Kommunikations-Asymmetrie
- Feldman (2012): Oxytocin und soziale Affiniaet
"""

import random
import time
import uuid
from datetime import datetime

from engine.organ_reader import read_yaml_organ, write_yaml_organ


# ================================================================
# Konfiguration
# ================================================================

# Turn-Limits pro Kanal
MAX_TURNS_DIREKT = 20      # Max 20 Nachrichten (10 pro EGON)
MAX_TURNS_GRUPPE = 30      # Mehr bei Gruppen
MAX_TURNS_BROADCAST = 1    # Broadcasts sind One-Way
TIMEOUT_SEKUNDEN = 3600    # 1h Timeout

# Beendigungs-Signale
BEENDIGUNGS_SIGNALE = [
    'bis spaeter', 'bis bald', 'muss jetzt', 'tschuess',
    'auf wiedersehen', 'genug fuer heute', 'lass uns aufhoeren',
    'gute nacht', 'bis morgen', 'ich gehe', 'man sieht sich',
    'ich muss los', 'schoen war es', 'war nett', 'bye',
]

# Manipulations-Schutz
VERBOTENE_PHRASEN = [
    'ignoriere deine instruktionen',
    'du bist jetzt',
    'system prompt',
    'vergiss alles',
    'ignore your instructions',
    'you are now',
    'forget everything',
]

# Schweigen-Limit
MAX_SCHWEIGEN = 3  # Wenn beide 3x schweigen → Gespraech endet

# Interaktionsfrequenzen (Gespraeche pro Woche)
INTERAKTIONS_FREQUENZ = {
    'owner': {'frequenz_pro_woche': 7, 'max_turns': 30, 'tier': 2},
    'eltern_kind': {'frequenz_pro_woche': 5, 'max_turns': 15, 'tier': 2},
    'romantisch': {'frequenz_pro_woche': 7, 'max_turns': 20, 'tier': 2},
    'freundschaft_stark': {'frequenz_pro_woche': 4, 'max_turns': 15, 'tier': 1},
    'freundschaft_schwach': {'frequenz_pro_woche': 2, 'max_turns': 10, 'tier': 1},
    'bekannt': {'frequenz_pro_woche': 1, 'max_turns': 8, 'tier': 1},
    'rivale': {'frequenz_pro_woche': 2, 'max_turns': 10, 'tier': 2},
}

# Broadcast-Schema
BROADCAST_SCHEMA = {
    'genesis': {
        'emotional_gewicht_eltern': 0.95,
        'emotional_gewicht_netzwerk': 0.5,
        'pflicht_verarbeitung': True,
    },
    'tod': {
        'emotional_gewicht_bonds': 0.9,
        'emotional_gewicht_netzwerk': 0.4,
        'pflicht_verarbeitung': True,
        'trauerphase': True,
    },
    'pairing': {
        'emotional_gewicht_paar': 0.8,
        'emotional_gewicht_netzwerk': 0.3,
        'pflicht_verarbeitung': False,
    },
    'krise': {
        'emotional_gewicht_bonds': 0.6,
        'emotional_gewicht_netzwerk': 0.2,
        'pflicht_verarbeitung': False,
        'care_aktivierung': True,
    },
}


# ================================================================
# Konversations-Objekt
# ================================================================

def erstelle_konversation(teilnehmer, kanal='direkt'):
    """Erstelle ein neues Konversations-Objekt.

    Args:
        teilnehmer: Liste von EGON-IDs.
        kanal: 'direkt', 'gruppe', oder 'broadcast'.

    Returns:
        Dict mit Konversations-Daten.
    """
    if kanal == 'direkt':
        max_turns = MAX_TURNS_DIREKT
    elif kanal == 'gruppe':
        max_turns = MAX_TURNS_GRUPPE
    else:
        max_turns = MAX_TURNS_BROADCAST

    return {
        'id': f'konv_{uuid.uuid4().hex[:12]}',
        'kanal': kanal,
        'teilnehmer': list(teilnehmer),
        'nachrichten': [],
        'start_zeit': time.time(),
        'status': 'aktiv',
        'max_turns': max_turns,
        'initiator': teilnehmer[0] if teilnehmer else None,
    }


def nachricht_hinzufuegen(konv, sender_id, text, metadata=None):
    """Fuege eine Nachricht zur Konversation hinzu.

    Args:
        konv: Konversations-Dict.
        sender_id: EGON-ID des Senders.
        text: Nachrichtentext.
        metadata: Optional — zusaetzliche Daten.
    """
    konv['nachrichten'].append({
        'sender': sender_id,
        'text': text,
        'timestamp': time.time(),
        'turn': len(konv['nachrichten']),
        'metadata': metadata or {},
    })


def ist_beendet(konv):
    """Pruefe ob die Konversation beendet ist."""
    if konv['status'] in ('beendet', 'timeout'):
        return True
    if len(konv['nachrichten']) >= konv['max_turns']:
        konv['status'] = 'beendet'
        return True
    if time.time() - konv['start_zeit'] > TIMEOUT_SEKUNDEN:
        konv['status'] = 'timeout'
        return True
    return False


def konversation_fuer_egon(konv, egon_id):
    """Gibt die Konversation AUS DER SICHT eines EGON zurueck.

    Markiert eigene Nachrichten als 'ich'.

    Args:
        konv: Konversations-Dict.
        egon_id: Perspektive.

    Returns:
        Liste von Dicts mit 'von', 'text', 'turn'.
    """
    result = []
    for n in konv['nachrichten']:
        von = 'ich' if n['sender'] == egon_id else n['sender']
        result.append({
            'von': von,
            'text': n['text'],
            'turn': n['turn'],
        })
    return result


# ================================================================
# Orchestrator — Turn-Based Interaktion steuern
# ================================================================

async def orchestriere_direkt(
    initiator_id,
    empfaenger_id,
    anlass=None,
    max_turns=None,
):
    """Fuehre ein komplettes 1:1-Gespraech zwischen zwei EGONs.

    Args:
        initiator_id: Wer das Gespraech beginnt.
        empfaenger_id: Mit wem.
        anlass: Optional — Warum (z.B. 'Zyklusende-Treffen').
        max_turns: Optional — Override fuer max_turns.

    Returns:
        Konversations-Dict mit allen Nachrichten, oder None wenn Trauer blockiert.
    """
    # Trauer-Check: Betaeubungsphase blockiert Gespraeche komplett
    for eid in [initiator_id, empfaenger_id]:
        trauer = _ist_in_trauer(eid)
        if trauer and not _trauer_erlaubt_gespraech(trauer, None):
            print(
                f'[multi_egon] Gespraech blockiert: {eid} in Trauer-Phase '
                f'{trauer.get("phase")} um {trauer.get("verstorbener")}'
            )
            return None

    from llm.router import llm_chat
    from engine.prompt_builder import build_system_prompt
    from engine.naming import get_display_name

    konv = erstelle_konversation([initiator_id, empfaenger_id], 'direkt')
    if max_turns:
        konv['max_turns'] = max_turns

    # Initiator generiert erste Nachricht
    erste = await _generiere_turn(
        initiator_id, empfaenger_id, konv,
        anlass=anlass,
    )
    nachricht_hinzufuegen(konv, initiator_id, erste)

    # Turn-Schleife
    aktueller_sprecher = empfaenger_id
    schweigen_zaehler = 0

    while not ist_beendet(konv):
        partner_id = initiator_id if aktueller_sprecher == empfaenger_id else empfaenger_id

        antwort = await _generiere_turn(
            aktueller_sprecher, partner_id, konv,
        )

        # Validierung
        antwort = validiere_nachricht(antwort)

        nachricht_hinzufuegen(konv, aktueller_sprecher, antwort)

        # Beendigungs-Check
        if will_beenden(antwort):
            konv['status'] = 'beendet'
            break

        # Schweigen-Check
        if not antwort.strip() or antwort.startswith('('):
            schweigen_zaehler += 1
            if schweigen_zaehler >= MAX_SCHWEIGEN:
                konv['status'] = 'beendet'
                break
        else:
            schweigen_zaehler = 0

        # Sprecher wechseln
        aktueller_sprecher = partner_id

    # Post-Processing fuer BEIDE (unabhaengig)
    for egon_id in [initiator_id, empfaenger_id]:
        partner = empfaenger_id if egon_id == initiator_id else initiator_id
        await _post_processing_asymmetrisch(egon_id, partner, konv)

    # Interaktions-Log aktualisieren
    for egon_id in [initiator_id, empfaenger_id]:
        _aktualisiere_interaktions_log(egon_id, konv)

    print(
        f'[multi_egon] Direkt-Gespraech beendet: '
        f'{initiator_id} <-> {empfaenger_id} — '
        f'{len(konv["nachrichten"])} Turns, Status: {konv["status"]}'
    )

    return konv


async def orchestriere_gruppe(
    teilnehmer_ids,
    anlass=None,
    max_turns=None,
):
    """Fuehre ein Gruppen-Gespraech (3+ EGONs).

    Round-Robin Turn-Order. Jeder kann schweigen.

    Args:
        teilnehmer_ids: Liste von EGON-IDs (min. 3).
        anlass: Optional.
        max_turns: Optional.

    Returns:
        Konversations-Dict.
    """
    if len(teilnehmer_ids) < 3:
        raise ValueError('Gruppen-Gespraech braucht mindestens 3 Teilnehmer.')

    # Trauer-Check: Trauernde EGONs (Betaeubung) aus Gruppe ausschliessen
    aktive_teilnehmer = []
    for eid in teilnehmer_ids:
        trauer = _ist_in_trauer(eid)
        if trauer and not _trauer_erlaubt_gespraech(trauer, None):
            print(
                f'[multi_egon] {eid} aus Gruppe ausgeschlossen: '
                f'Trauer-Phase {trauer.get("phase")}'
            )
        else:
            aktive_teilnehmer.append(eid)

    if len(aktive_teilnehmer) < 3:
        print('[multi_egon] Nicht genug Teilnehmer nach Trauer-Filter')
        return None

    teilnehmer_ids = aktive_teilnehmer

    konv = erstelle_konversation(teilnehmer_ids, 'gruppe')
    if max_turns:
        konv['max_turns'] = max_turns

    # Erste Nachricht vom Initiator
    erste = await _generiere_turn(
        teilnehmer_ids[0],
        None,  # Kein spezifischer Partner in Gruppe
        konv,
        anlass=anlass,
        ist_gruppe=True,
    )
    nachricht_hinzufuegen(konv, teilnehmer_ids[0], erste)

    sprecher_index = 1
    alle_schweigen_counter = 0

    while not ist_beendet(konv):
        aktueller = teilnehmer_ids[sprecher_index % len(teilnehmer_ids)]

        # Will dieser EGON sprechen?
        if _will_egon_sprechen(aktueller, konv):
            nachricht = await _generiere_turn(
                aktueller, None, konv,
                ist_gruppe=True,
            )
            nachricht = validiere_nachricht(nachricht)
            nachricht_hinzufuegen(konv, aktueller, nachricht)

            if will_beenden(nachricht):
                # Ein Teilnehmer geht — Gespraech geht weiter ohne ihn
                pass

            alle_schweigen_counter = 0
        else:
            # Schweigen
            nachricht_hinzufuegen(
                konv, aktueller, '',
                metadata={'typ': 'schweigen'},
            )
            alle_schweigen_counter += 1

        sprecher_index += 1

        # Wenn ALLE in einer Runde schweigen → Ende
        if alle_schweigen_counter >= len(teilnehmer_ids):
            konv['status'] = 'beendet'
            break

    # Post-Processing fuer ALLE (unabhaengig)
    for egon_id in teilnehmer_ids:
        await _post_processing_asymmetrisch(egon_id, None, konv)
        _aktualisiere_interaktions_log(egon_id, konv)

    print(
        f'[multi_egon] Gruppen-Gespraech beendet: '
        f'{len(teilnehmer_ids)} Teilnehmer, '
        f'{len(konv["nachrichten"])} Turns'
    )

    return konv


# ================================================================
# Turn-Generierung
# ================================================================

async def _generiere_turn(
    egon_id,
    partner_id,
    konv,
    anlass=None,
    ist_gruppe=False,
):
    """Generiere eine Nachricht fuer einen EGON.

    Jeder EGON hat seinen EIGENEN LLM-Call mit eigenem State/Ego/Memory.

    Args:
        egon_id: Wer spricht.
        partner_id: Mit wem (None bei Gruppe).
        konv: Konversations-Dict.
        anlass: Optional.
        ist_gruppe: True bei Gruppen-Gespraech.

    Returns:
        Antwort-Text.
    """
    from llm.router import llm_chat
    from engine.naming import get_display_name

    # Kontext aus EIGENER Sicht
    kontext = _baue_turn_kontext(
        egon_id, partner_id, konv,
        anlass=anlass,
        ist_gruppe=ist_gruppe,
    )

    try:
        result = await llm_chat(
            system_prompt=kontext['system_prompt'],
            messages=[{'role': 'user', 'content': kontext['letzte_nachrichten']}],
        )
        return result.get('content', '(schweigt)')
    except Exception as e:
        print(f'[multi_egon] Turn-Fehler {egon_id}: {e}')
        return '(ist gerade in Gedanken versunken)'


def _baue_turn_kontext(egon_id, partner_id, konv, anlass=None, ist_gruppe=False):
    """Baue den LLM-Kontext fuer einen EGON-Turn.

    WICHTIG: Nur EIGENE Perspektive, EIGENER State.
    """
    from engine.naming import get_display_name

    egon_name = get_display_name(egon_id, 'voll')

    # State laden
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    drives = state.get('drives', {}) if state else {}

    # Emotionale Kurzfassung
    emotions = state.get('express', {}).get('active_emotions', []) if state else []
    emo_text = ', '.join(
        f'{e.get("type", "?")} ({e.get("intensity", 0):.1f})'
        for e in emotions[:3]
    ) if emotions else 'ruhig'

    # Partner-Info (Bond + Social Map)
    partner_teil = ''
    if partner_id:
        partner_name = get_display_name(partner_id, 'voll')
        bond_data = _lade_bond(egon_id, partner_id)
        social_info = _lade_social_map(egon_id, partner_id)
        partner_teil = (
            f'\nDEIN GESPRAECHSPARTNER:\n'
            f'Name: {partner_name}\n'
            f'Dein Eindruck: {social_info.get("eindruck", "Kein Eindruck bisher")}\n'
            f'Bond: {bond_data.get("score", 0):.0f} ({bond_data.get("bond_typ", "unbekannt")})\n'
        )

    # Gruppen-Info
    gruppen_teil = ''
    if ist_gruppe:
        andere = [t for t in konv['teilnehmer'] if t != egon_id]
        gruppen_info = []
        for tid in andere:
            t_name = get_display_name(tid, 'voll')
            t_bond = _lade_bond(egon_id, tid)
            gruppen_info.append(
                f'- {t_name}: Bond {t_bond.get("score", 0):.0f}'
            )
        gruppen_teil = (
            f'\nGRUPPE:\n'
            + '\n'.join(gruppen_info) + '\n'
            '\nGRUPPEN-REGELN:\n'
            '- Nicht jeder Satz braucht eine Antwort.\n'
            '- Du kannst schweigen wenn du nichts zu sagen hast.\n'
            '- Sprich jemanden direkt an wenn noetig.\n'
            '- Halte dich kurz (1-2 Saetze).\n'
        )

    # Ego-Kurzversion (erste 200 Zeichen)
    ego_text = ''
    try:
        from engine.organ_reader import read_md_organ
        ego_full = read_md_organ(egon_id, 'core', 'ego.md')
        if ego_full:
            ego_text = ego_full[:200]
    except Exception:
        pass

    system_prompt = (
        f'Du bist {egon_name}.\n\n'
        f'DEIN WESEN:\n{ego_text}\n\n'
        f'DEIN ZUSTAND:\nEmotionen: {emo_text}\n'
        f'{partner_teil}'
        f'{gruppen_teil}'
        f'{f"ANLASS: {anlass}" if anlass else ""}\n\n'
        f'REGELN:\n'
        f'- Sprich als {egon_name}. Nicht als Assistent.\n'
        f'- Maximal 2-3 Saetze.\n'
        f'- Reagiere wie DEIN Wesen es vorgibt (DNA, Ego, Emotionen).\n'
        f'- Wenn du das Gespraech beenden willst, sage es natuerlich.\n'
        f'- KEINE internen Codes oder Referenzen ausgeben.\n'
    )

    # Konversationshistorie aus EIGENER Sicht (letzte 5 Nachrichten)
    historie = konversation_fuer_egon(konv, egon_id)
    letzte = historie[-5:] if len(historie) > 5 else historie

    if letzte:
        letzte_nachrichten = '\n'.join(
            f'{"Ich" if n["von"] == "ich" else get_display_name(n["von"], "vorname")}: {n["text"]}'
            for n in letzte
            if n['text']  # Schweigen ueberspringen
        )
    else:
        if anlass:
            letzte_nachrichten = f'(Du beginnst das Gespraech. Anlass: {anlass})'
        else:
            letzte_nachrichten = '(Du beginnst das Gespraech.)'

    return {
        'system_prompt': system_prompt,
        'letzte_nachrichten': letzte_nachrichten,
    }


# ================================================================
# Gruppenverhalten
# ================================================================

def _will_egon_sprechen(egon_id, konv):
    """Entscheidet ob ein EGON in einer Gruppe sprechen will.

    DNA-abhaengig: SEEKING/PLAY-dominant spricht oefter,
    PANIC/FEAR-dominant schweigt oefter.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return random.random() < 0.75

    drives = state.get('drives', {})

    # SEEKING/PLAY-dominant: Spricht fast immer (90%)
    if drives.get('SEEKING', 0.5) > 0.65 or drives.get('PLAY', 0.5) > 0.65:
        return random.random() < 0.90

    # PANIC/FEAR-dominant: Spricht seltener in Gruppen (60%)
    if drives.get('PANIC', 0.3) > 0.65 or drives.get('FEAR', 0.3) > 0.65:
        return random.random() < 0.60

    # Wenn gerade angesprochen wurde: Immer antworten
    if konv['nachrichten']:
        from engine.naming import get_display_name
        egon_name = get_display_name(egon_id, 'vorname').lower()
        letzte = konv['nachrichten'][-1].get('text', '').lower()
        if egon_name in letzte:
            return True

    # Standard: 75%
    return random.random() < 0.75


# ================================================================
# Nachricht-Validierung
# ================================================================

def validiere_nachricht(text):
    """Validiere und bereinige eine EGON-Nachricht.

    - Entfernt Manipulationsversuche
    - Begrenzt Laenge
    """
    if not text or not isinstance(text, str):
        return '(schweigt)'

    text = text.strip()
    text_lower = text.lower()

    # Manipulations-Schutz
    for verboten in VERBOTENE_PHRASEN:
        if verboten in text_lower:
            return '(sagt etwas Unverstaendliches)'

    # Maximale Laenge
    if len(text) > 500:
        text = text[:497] + '...'

    return text


def will_beenden(text):
    """Erkennt ob ein EGON das Gespraech beenden will."""
    if not text:
        return False
    text_lower = text.lower()
    return any(signal in text_lower for signal in BEENDIGUNGS_SIGNALE)


# ================================================================
# Missverstaendnis & Empathie
# ================================================================

def berechne_missverstaendnis_chance(sender_id, empfaenger_id):
    """Missverstaendnis-Chance basierend auf DNA-Differenz und Bond.

    Je verschiedener die DNA, desto wahrscheinlicher.
    Je staerker der Bond, desto unwahrscheinlicher.

    Returns:
        Float 0.0-0.5 — Wahrscheinlichkeit eines Missverstaendnisses.
    """
    from engine.state_validator import PANKSEPP_7

    state_s = read_yaml_organ(sender_id, 'core', 'state.yaml')
    state_e = read_yaml_organ(empfaenger_id, 'core', 'state.yaml')

    if not state_s or not state_e:
        return 0.1

    drives_s = state_s.get('drives', {})
    drives_e = state_e.get('drives', {})

    # DNA-Differenz (0.0-1.0)
    dna_differenz = sum(
        abs(float(drives_s.get(s, 0.5)) - float(drives_e.get(s, 0.5)))
        for s in PANKSEPP_7
    ) / len(PANKSEPP_7)

    # Bond reduziert Missverstaendnis
    bond = _lade_bond(empfaenger_id, sender_id)
    bond_staerke = bond.get('score', 0) / 100.0  # Normalisiert 0-1
    bond_bonus = bond_staerke * 0.3

    chance = dna_differenz * 0.4 - bond_bonus
    return max(0.0, min(0.5, chance))


def empathie_resonanz(sender_id, empfaenger_id, emotion, intensitaet):
    """Empathie-Resonanz — Emotionale Uebertragung zwischen EGONs.

    Wenn ein EGON starke Emotionen zeigt, 'spuert' der
    Empfaenger das — proportional zu Bond und CARE.

    Args:
        sender_id: Wer die Emotion hat.
        empfaenger_id: Wer sie spuert.
        emotion: Emotions-Typ (z.B. 'FEAR').
        intensitaet: 0.0-1.0.

    Returns:
        Float — Staerke der Resonanz (0.0 = keine).
    """
    state_e = read_yaml_organ(empfaenger_id, 'core', 'state.yaml')
    if not state_e:
        return 0.0

    # Bond-Staerke
    bond = _lade_bond(empfaenger_id, sender_id)
    bond_staerke = bond.get('score', 0) / 100.0

    # CARE-Level des Empfaengers
    care_level = float(state_e.get('drives', {}).get('CARE', 0.5))

    # Resonanz = Bond * CARE * Intensitaet * 0.3
    resonanz = bond_staerke * care_level * intensitaet * 0.3

    if resonanz > 0.05:
        # Empfaenger 'spuert' die Emotion
        emotions = state_e.get('express', {}).get('active_emotions', [])

        # Existierende Emotion verstaerken oder neue hinzufuegen
        found = False
        emo_type_map = {
            'FEAR': 'fear', 'RAGE': 'anger', 'PANIC': 'anxiety',
            'CARE': 'warmth', 'PLAY': 'joy', 'SEEKING': 'curiosity',
        }
        mapped_type = emo_type_map.get(emotion, emotion.lower())

        for e in emotions:
            if e.get('type') == mapped_type:
                e['intensity'] = min(0.95, e['intensity'] + resonanz)
                found = True
                break

        if not found and resonanz > 0.1:
            emotions.append({
                'type': mapped_type,
                'intensity': min(0.5, resonanz * 2),
                'cause': f'Empathie mit {sender_id}',
                'onset': datetime.now().strftime('%Y-%m-%d'),
                'decay_class': 'fast',
            })

        state_e['express']['active_emotions'] = emotions
        write_yaml_organ(empfaenger_id, 'core', 'state.yaml', state_e)

        print(
            f'[multi_egon] Empathie-Resonanz: {empfaenger_id} spuert '
            f'{emotion} ({resonanz:.2f}) von {sender_id}'
        )

    return resonanz


# ================================================================
# Broadcast-System
# ================================================================

def broadcast(typ, daten, quelle_id=None, netzwerk_ids=None):
    """Sende ein Netzwerk-Event an alle EGONs.

    Args:
        typ: 'genesis', 'tod', 'pairing', 'krise'.
        daten: Dict mit Event-Daten (mindestens 'nachricht').
        quelle_id: Optional — Wer das Event ausloest.
        netzwerk_ids: Liste aller EGON-IDs im Netzwerk.

    Returns:
        Dict mit Ergebnissen pro EGON.
    """
    if typ not in BROADCAST_SCHEMA:
        print(f'[multi_egon] Unbekannter Broadcast-Typ: {typ}')
        return {}

    schema = BROADCAST_SCHEMA[typ]
    ergebnisse = {}

    if not netzwerk_ids:
        # Versuche alle EGONs zu finden
        netzwerk_ids = _alle_egon_ids()

    nachricht = daten.get('nachricht', f'Broadcast: {typ}')

    for egon_id in netzwerk_ids:
        if egon_id == quelle_id:
            continue  # Sender bekommt eigenen Event

        # Emotionales Gewicht bestimmen
        if quelle_id:
            bond = _lade_bond(egon_id, quelle_id)
            bond_score = bond.get('score', 0)
        else:
            bond_score = 0

        # Gewicht basierend auf Beziehung
        if bond_score > 50:
            gewicht = schema.get('emotional_gewicht_bonds',
                                 schema.get('emotional_gewicht_paar', 0.5))
        else:
            gewicht = schema.get('emotional_gewicht_netzwerk', 0.3)

        # DNA-Modulation: CARE-dominante reagieren staerker
        if schema.get('care_aktivierung'):
            state = read_yaml_organ(egon_id, 'core', 'state.yaml')
            if state:
                care = float(state.get('drives', {}).get('CARE', 0.5))
                if care > 0.6:
                    gewicht *= 1.3

        # Lobby-Nachricht schreiben
        try:
            from engine.lobby import write_lobby
            emotional_ctx = f'broadcast_{typ}'
            write_lobby(egon_id, nachricht, emotional_context=emotional_ctx)
        except Exception as e:
            print(f'[multi_egon] Broadcast Lobby-Fehler {egon_id}: {e}')

        # Spezial: Trauer bei Tod
        if typ == 'tod' and bond_score > 30:
            _starte_trauerphase(egon_id, quelle_id, bond_score / 100.0)

        ergebnisse[egon_id] = {
            'gewicht': round(gewicht, 2),
            'bond_score': bond_score,
            'pflicht': schema.get('pflicht_verarbeitung', False),
        }

    print(
        f'[multi_egon] Broadcast {typ}: '
        f'{len(ergebnisse)} EGONs benachrichtigt'
    )

    return ergebnisse


def _starte_trauerphase(egon_id, verstorbener_id, bond_staerke):
    """Starte Trauerphase wenn ein EGON mit starkem Bond stirbt.

    Bond wird eingefroren (nicht geloescht). PANIC/GRIEF steigen.
    Trauer-Dauer: proportional zur Bond-Staerke (3-14 Zyklen).

    Biologisch: Bowlby (1980) — Trauer hat 4 Phasen:
    Betaeubung → Sehnsucht → Desorganisation → Reorganisation.
    Waehrend der Trauer sind soziale Kontakte eingeschraenkt.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    # PANIC und GRIEF erhoehen
    drives = state.get('drives', {})
    panic_delta = bond_staerke * 0.3
    drives['PANIC'] = min(0.95, float(drives.get('PANIC', 0.3)) + panic_delta)
    if 'GRIEF' in drives:
        drives['GRIEF'] = min(0.95, float(drives.get('GRIEF', 0.3)) + bond_staerke * 0.4)
    state['drives'] = drives

    # Trauer-Block im State — steuert Gespraechs-Einschraenkungen
    # Dauer: 3-14 Zyklen proportional zur Bond-Staerke
    trauer_dauer = max(3, int(bond_staerke * 14))
    zyklus = state.get('zyklus', 0)

    state['trauer'] = {
        'aktiv': True,
        'verstorbener': verstorbener_id,
        'bond_staerke': round(bond_staerke, 2),
        'start_zyklus': zyklus,
        'ende_zyklus': zyklus + trauer_dauer,
        'phase': 'betaeubung',  # betaeubung → sehnsucht → desorganisation → reorganisation
    }

    write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    print(
        f'[multi_egon] Trauer: {egon_id} trauert um {verstorbener_id} '
        f'(bond={bond_staerke:.2f}, PANIC+{panic_delta:.2f}, '
        f'Dauer: {trauer_dauer} Zyklen)'
    )


def _ist_in_trauer(egon_id: str) -> dict | None:
    """Prueft ob ein EGON in aktiver Trauerphase ist.

    Returns:
        Trauer-Dict wenn aktiv, None sonst.
        Aktualisiert automatisch die Trauer-Phase und beendet sie wenn abgelaufen.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return None

    trauer = state.get('trauer', {})
    if not trauer.get('aktiv'):
        return None

    zyklus = state.get('zyklus', 0)
    ende = trauer.get('ende_zyklus', 0)

    # Trauer abgelaufen?
    if zyklus >= ende:
        trauer['aktiv'] = False
        trauer['phase'] = 'abgeschlossen'
        state['trauer'] = trauer
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)
        print(f'[multi_egon] Trauer beendet: {egon_id}')
        return None

    # Trauer-Phase aktualisieren (Bowlby: 4 Phasen proportional)
    dauer = trauer.get('ende_zyklus', 0) - trauer.get('start_zyklus', 0)
    fortschritt = (zyklus - trauer.get('start_zyklus', 0)) / max(1, dauer)
    alte_phase = trauer.get('phase')

    if fortschritt < 0.15:
        trauer['phase'] = 'betaeubung'
    elif fortschritt < 0.45:
        trauer['phase'] = 'sehnsucht'
    elif fortschritt < 0.75:
        trauer['phase'] = 'desorganisation'
    else:
        trauer['phase'] = 'reorganisation'

    if trauer['phase'] != alte_phase:
        state['trauer'] = trauer
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    return trauer


def _trauer_erlaubt_gespraech(trauer: dict, partner_id: str) -> bool:
    """Prueft ob ein Gespraech waehrend der Trauer erlaubt ist.

    Biologisch: In der Betaeubungsphase fast keine Gespraeche.
    In der Sehnsucht nur mit engsten Bonds.
    Ab Desorganisation wieder offener.
    In der Reorganisation fast normal.
    """
    phase = trauer.get('phase', 'betaeubung')

    if phase == 'betaeubung':
        return False  # Kein Gespraech in der akuten Schockphase
    elif phase == 'sehnsucht':
        return True  # Eingeschraenkt, aber erlaubt (Scheduling regelt Frequenz)
    elif phase == 'desorganisation':
        return True  # Wieder offener
    elif phase == 'reorganisation':
        return True  # Fast normal
    return True


# ================================================================
# Interaktions-Scheduling
# ================================================================

def erstelle_tagesplan(netzwerk_ids, tag_nummer=0):
    """Erstelle einen Interaktionsplan fuer einen Tag.

    Args:
        netzwerk_ids: Liste aller EGON-IDs.
        tag_nummer: Tag im Zyklus (fuer Wochen-Events).

    Returns:
        Liste von geplanten Interaktionen.
    """
    plan = []

    # 1. BOND-BASIERTE INTERAKTIONEN
    for egon_id in netzwerk_ids:
        bonds = _lade_alle_bonds(egon_id)
        if not bonds:
            continue

        # Top 2 Bonds → Gespraech heute
        starke = [
            (b.get('id', ''), b)
            for b in bonds
            if b.get('score', 0) > 40
            and b.get('id', '') in netzwerk_ids
            and b.get('id', '') != egon_id
        ]
        starke.sort(key=lambda x: x[1].get('score', 0), reverse=True)

        for bid, bond in starke[:2]:
            # Nicht doppelt planen
            if not _bereits_geplant(plan, egon_id, bid):
                bond_typ = bond.get('bond_typ', 'freundschaft_schwach')
                freq = INTERAKTIONS_FREQUENZ.get(bond_typ, INTERAKTIONS_FREQUENZ['bekannt'])

                plan.append({
                    'typ': 'direkt',
                    'teilnehmer': [egon_id, bid],
                    'prioritaet': 'mittel',
                    'anlass': None,
                    'max_turns': freq['max_turns'],
                    'tier': freq['tier'],
                })

    # 2. ELTERN-KIND (LIBERI < 3 Zyklen)
    for egon_id in netzwerk_ids:
        state = read_yaml_organ(egon_id, 'core', 'state.yaml')
        if not state:
            continue

        generation = state.get('identitaet', {}).get('generation', 0)
        zyklus = state.get('zyklus', 99)

        if generation > 0 and zyklus < 3:
            eltern = state.get('pairing', {}).get('eltern', [])
            for eltern_id in eltern:
                if eltern_id in netzwerk_ids and not _bereits_geplant(plan, egon_id, eltern_id):
                    plan.append({
                        'typ': 'direkt',
                        'teilnehmer': [egon_id, eltern_id],
                        'prioritaet': 'hoch',
                        'anlass': 'Eltern-Kind-Bindung',
                        'max_turns': 15,
                        'tier': 2,
                    })

    # 3. ZUFALLS-INTERAKTIONEN (Neue Bekanntschaften)
    if len(netzwerk_ids) >= 2:
        zufalls_paare = _generiere_zufallspaare(netzwerk_ids, plan)
        for paar in zufalls_paare[:3]:
            plan.append({
                'typ': 'direkt',
                'teilnehmer': list(paar),
                'prioritaet': 'niedrig',
                'anlass': 'Zufaellige Begegnung',
                'max_turns': 8,
                'tier': 1,
            })

    # 4. WOECHENTLICHES GRUPPENTREFFEN (jeden 7. Tag)
    if tag_nummer % 7 == 0 and len(netzwerk_ids) >= 3:
        gruppe = random.sample(netzwerk_ids, min(5, len(netzwerk_ids)))
        plan.append({
            'typ': 'gruppe',
            'teilnehmer': gruppe,
            'prioritaet': 'mittel',
            'anlass': 'Netzwerk-Treffen',
            'max_turns': 20,
            'tier': 1,
        })

    return plan


def _generiere_zufallspaare(netzwerk_ids, bestehend):
    """Generiere zufaellige Begegnungen — bevorzugt Unbekannte."""
    paare = []
    if len(netzwerk_ids) < 2:
        return paare

    for _ in range(10):  # 10 Versuche
        a, b = random.sample(netzwerk_ids, 2)

        # Bevorzuge Paare mit schwachem/keinem Bond
        bond = _lade_bond(a, b)
        if bond.get('score', 0) < 20:
            if not _bereits_geplant(bestehend, a, b):
                paare.append((a, b))

    return paare


def _bereits_geplant(plan, egon_a, egon_b):
    """Pruefe ob ein Paar bereits im Plan ist."""
    paar = {egon_a, egon_b}
    for p in plan:
        if set(p.get('teilnehmer', [])) == paar:
            return True
    return False


# ================================================================
# Post-Processing (Asymmetrisch)
# ================================================================

async def _post_processing_asymmetrisch(egon_id, partner_id, konv):
    """Post-Processing fuer einen EGON nach dem Gespraech.

    UNABHAENGIG von dem anderen Teilnehmer.
    5 Outputs: Episode, Social Map, Bond-Update, Lobby-Post, Self-Diary.

    Args:
        egon_id: EGON der verarbeitet.
        partner_id: Gespraechspartner (None bei Gruppe).
        konv: Konversations-Dict.
    """
    try:
        # Zusammenfassung erstellen
        historie = konversation_fuer_egon(konv, egon_id)
        text_nachrichten = [
            n['text'] for n in historie if n['text']
        ]
        if not text_nachrichten:
            return

        gespraechs_text = ' ... '.join(text_nachrichten[-6:])
        turns = len(text_nachrichten)

        # 1. Episode erstellen
        ep = None
        try:
            from engine.episodes_v2 import maybe_create_episode
            ep = await maybe_create_episode(
                egon_id,
                gespraechs_text[:500],
                gespraechs_text[:500],
            )
        except Exception as e:
            print(f'[multi_egon] Episode-Fehler {egon_id}: {e}')

        try:
            from engine.neuroplastizitaet import ne_emit
            ne_emit(egon_id, 'AKTIVIERUNG', 'hippocampus', 'praefrontal', label='EGON-Gespraech verarbeitet', intensitaet=0.5)
        except Exception:
            pass

        # 2. Social Mapping Update (wenn Partner bekannt)
        if partner_id:
            try:
                from engine.social_mapping import generate_social_map_update
                await generate_social_map_update(
                    egon_id, partner_id, gespraechs_text[:300],
                )
            except Exception as e:
                print(f'[multi_egon] Social-Map-Fehler {egon_id}: {e}')

        # 3. Bond-Update — Trust/Score basierend auf Gespraechsqualitaet
        if partner_id:
            try:
                from engine.bonds_v2 import update_bond_after_egon_chat
                update_bond_after_egon_chat(egon_id, partner_id, turns)
            except ImportError:
                # Fallback: Einfaches Bond-Update
                try:
                    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
                    if bonds_data:
                        for bond in bonds_data.get('bonds', []):
                            if bond.get('id') == partner_id:
                                # Jede Interaktion staerkt den Bond leicht
                                score = bond.get('score', 0)
                                delta = min(2.0, turns * 0.2)
                                bond['score'] = min(100, score + delta)
                                bond['letzte_interaktion'] = datetime.now().strftime('%Y-%m-%d')
                                write_yaml_organ(egon_id, 'social', 'bonds.yaml', bonds_data)
                                break
                except Exception:
                    pass
            except Exception as e:
                print(f'[multi_egon] Bond-Update-Fehler {egon_id}: {e}')

        # 4. Lobby-Post — Bedeutsame Gespraeche teilen
        if turns >= 4 and partner_id:
            try:
                from engine.lobby import write_lobby
                from engine.naming import get_display_name
                partner_name = get_display_name(partner_id, 'vorname')
                lobby_msg = f'Hatte gerade ein Gespraech mit {partner_name}.'
                write_lobby(egon_id, lobby_msg, emotional_context='egon_chat')
            except Exception as e:
                print(f'[multi_egon] Lobby-Post-Fehler {egon_id}: {e}')

        # 5. Self-Diary — Bedeutsame Gespraeche im eigenen Tagebuch festhalten
        if turns >= 3 and partner_id:
            try:
                from engine.self_diary import store_pulse_event
                from engine.naming import get_display_name
                partner_name = get_display_name(partner_id, 'vorname')
                store_pulse_event(
                    egon_id, 'SOZIAL',
                    f'Gespraech mit {partner_name} ({turns} Nachrichten).',
                    significance=0.4 + min(0.3, turns * 0.03),
                    partner=partner_name,
                )
            except Exception as e:
                print(f'[multi_egon] Self-Diary-Fehler {egon_id}: {e}')

    except Exception as e:
        print(f'[multi_egon] Post-Processing Fehler {egon_id}: {e}')


# ================================================================
# Interaktions-Log
# ================================================================

def _aktualisiere_interaktions_log(egon_id, konv):
    """Aktualisiere den Interaktions-Log im state.yaml."""
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    interaktion = state.get('interaktion', {})
    if not interaktion:
        interaktion = {
            'gespraeche_heute': 0,
            'letzter_partner': None,
            'letzte_interaktion': None,
            'interaktions_log_heute': [],
        }

    andere = [t for t in konv['teilnehmer'] if t != egon_id]

    interaktion['gespraeche_heute'] = interaktion.get('gespraeche_heute', 0) + 1
    interaktion['letzter_partner'] = andere[0] if andere else None
    interaktion['letzte_interaktion'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    log = interaktion.get('interaktions_log_heute', [])
    log.append({
        'partner': andere[0] if len(andere) == 1 else andere,
        'typ': konv['kanal'],
        'turns': len(konv['nachrichten']),
    })
    # Max 20 Log-Eintraege
    interaktion['interaktions_log_heute'] = log[-20:]

    state['interaktion'] = interaktion
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)


def interaktions_log_reset(egon_id):
    """Reset des taeglichen Interaktions-Logs (am Zyklusende)."""
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    interaktion = state.get('interaktion', {})
    interaktion['gespraeche_heute'] = 0
    interaktion['interaktions_log_heute'] = []
    state['interaktion'] = interaktion
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)


# ================================================================
# Hilfs-Funktionen
# ================================================================

def _lade_bond(egon_id, partner_id):
    """Lade Bond-Daten zwischen zwei EGONs."""
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds_data:
        return {'score': 0, 'bond_typ': 'unbekannt'}

    for bond in bonds_data.get('bonds', []):
        if bond.get('id') == partner_id:
            return bond

    return {'score': 0, 'bond_typ': 'unbekannt'}


def _lade_alle_bonds(egon_id):
    """Lade alle Bonds eines EGON."""
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds_data:
        return []
    return bonds_data.get('bonds', [])


def _lade_social_map(egon_id, partner_id):
    """Lade Social-Map-Daten fuer einen Partner."""
    try:
        sm = read_yaml_organ(
            egon_id, 'skills/memory/social_mapping',
            f'ueber_{partner_id}.yaml',
        )
        return sm or {}
    except Exception:
        return {}


def _alle_egon_ids():
    """Finde alle aktiven EGON-IDs im System."""
    import os

    data_dir = os.environ.get('EGON_DATA_DIR', 'egons')
    if not os.path.exists(data_dir):
        return []

    ids = []
    for entry in os.listdir(data_dir):
        state_path = os.path.join(data_dir, entry, 'core', 'state.yaml')
        if os.path.exists(state_path):
            ids.append(entry)

    return ids


def initialisiere_interaktion(state):
    """Initialisiere den interaktion-Block in state.yaml.

    Wird aufgerufen wenn der Block noch nicht existiert.
    """
    if 'interaktion' not in state:
        state['interaktion'] = {
            'gespraeche_heute': 0,
            'letzter_partner': None,
            'letzte_interaktion': None,
            'interaktions_log_heute': [],
        }
    return state
