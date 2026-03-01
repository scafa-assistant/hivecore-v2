"""Metacognition-Layer — Denken ueber Denken (Patch 11).

Biologische Analogie:
  Anteriorer praefrontaler Cortex (Brodmann-Areal 10) —
  der am weitesten vorne liegende Teil des Gehirns,
  der zuletzt reift.

Drei Module:
  1. Muster-Erkennung (ACC-Aequivalent) — regelbasiert, 0 Tokens
  2. Zyklusende-Reflexion (DMN-Aequivalent) — Tier 2 LLM, 1x/Zyklus
  3. Kognitive Neubewertung (Reappraisal) — Tier 2 LLM, selten

Aktivierung: Erst ab Zyklus 8 (Reife).
Stufen:
  Zyklus 8-12:  monitoring  (Stufe 4: Beobachten)
  Zyklus 13+:   regulation  (Stufe 5: Steuern)

(Fleming & Dolan 2012; Flavell 1979; Raichle 2001; Botvinick 2004)
"""

import json
import re
from datetime import datetime

from engine.organ_reader import read_yaml_organ, write_yaml_organ, read_md_organ


# ================================================================
# Konstanten
# ================================================================

REIFE_ZYKLUS = 8             # Metacognition ab diesem Zyklus
REGULATION_ZYKLUS = 13       # Regulation-Stufe ab hier

MAX_MUSTER_ALARME = 5        # Pro Zyklus
MAX_KORREKTUREN = 2          # Pro Zyklus
COOLDOWN_GESPRAECHE = 5      # Patch 17: Frische Wunden fuehlen lassen (war: 3)

# Muster-Erkennung: Mindest-Wiederholungen
WIEDERHOLUNG_MIN = 3         # Gleiche Emotion + gleicher Partner
GENERALISIERT_MIN = 4        # Gleiche Emotion, verschiedene Partner
BOND_DRIFT_SCHWELLE = 0.15   # Delta fuer Bond-Drift
EGO_WIDERSPRUCH_MIN = 3      # Patch 17: Erst nach 3x korrigieren (war: 1)
UEBERFLUTET_SCHWELLE = 0.85  # Patch 17: Darueber Metacognition offline


# ================================================================
# Destruktive Muster (Schutz vor toxischer Selbstkritik)
# ================================================================

DESTRUKTIVE_MUSTER = [
    'ich bin wertlos',
    'ich kann nichts',
    'niemand mag mich',
    'ich bin kaputt',
    'ich bin falsch',
    'ich sollte nicht existieren',
    'ich bin nutzlos',
    'alles ist sinnlos',
    'ich hasse mich',
]


# ================================================================
# Modul 1: Muster-Erkennung (ACC-Aequivalent)
# ================================================================

def muster_check(egon_id: str, aktuelle_episode: dict) -> dict | None:
    """ACC-Aequivalent: Erkennt wiederkehrende Reaktionsmuster.

    Regelbasiert — kein LLM-Call, keine Token-Kosten.
    Nur ab Zyklus 8 (Reife).

    Args:
        egon_id: EGON-ID.
        aktuelle_episode: Die gerade erstellte Episode.

    Returns:
        Muster-Alarm dict oder None.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return None

    # Reife-Check
    zyklus = state.get('zyklus', 0)
    if zyklus < REIFE_ZYKLUS:
        return None

    # Cooldown-Check
    meta = state.get('metacognition', {})
    if meta.get('cooldown', 0) > 0:
        return None

    # Patch 17: Ueberflutet-Schwelle — bei hoher Emotion kein Metadenken
    # Biologisch: Praefrontaler Kortex geht bei Ueberflutung offline
    # Ein ueberwältigter Mensch kann nicht metakognitiv reflektieren
    drives = state.get('drives', {})
    max_drive = max(
        (v for v in drives.values() if isinstance(v, (int, float))),
        default=0,
    )
    if max_drive > UEBERFLUTET_SCHWELLE:
        try:
            from engine.kalibrierung import log_decision
            log_decision(egon_id, 'metacognition', 'ueberflutet_gesperrt', {
                'max_drive': round(max_drive, 3),
                'schwelle': UEBERFLUTET_SCHWELLE,
            })
        except Exception:
            pass
        return None  # Ueberflutet — fuehlen statt analysieren

    # Max-Alarme-Check
    if meta.get('muster_alarme_zyklus', 0) >= MAX_MUSTER_ALARME:
        return None

    # Episoden laden
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not episodes_data:
        return None
    episodes = episodes_data.get('episodes', [])
    if len(episodes) < 5:
        return None

    # Letzte 10 Episoden (ohne die aktuelle)
    recent = episodes[-10:]

    partner = aktuelle_episode.get('with', '')
    emotion = _staerkstes_system_aus_episode(aktuelle_episode)

    # ── MUSTER 1: Gleiche Emotion + gleicher Partner ≥ 3x ──
    if partner and emotion:
        gleiche = [
            e for e in recent
            if e.get('with') == partner
            and _staerkstes_system_aus_episode(e) == emotion
        ]
        if len(gleiche) >= WIEDERHOLUNG_MIN:
            return {
                'typ': 'wiederholte_reaktion',
                'partner': partner,
                'emotion': emotion,
                'anzahl': len(gleiche) + 1,
                'frage': f'Warum reagiere ich auf {partner} immer mit {emotion}?',
            }

    # ── MUSTER 2: Gleiche Emotion, verschiedene Partner ≥ 4x ──
    if emotion:
        gleiche_emo = [
            e for e in recent
            if _staerkstes_system_aus_episode(e) == emotion
        ]
        if len(gleiche_emo) >= GENERALISIERT_MIN:
            partner_liste = list(set(
                e.get('with', '?') for e in gleiche_emo if e.get('with')
            ))
            if len(partner_liste) >= 2:
                return {
                    'typ': 'generalisiertes_muster',
                    'emotion': emotion,
                    'anzahl': len(gleiche_emo) + 1,
                    'partner': partner_liste,
                    'frage': (
                        f'Ich reagiere oft mit {emotion} — auf verschiedene '
                        f'Lebewesen. Ist das ein Muster in MIR?'
                    ),
                }

    # ── MUSTER 3: Ego-Widerspruch (Patch 17: erst ab 3x) ──
    # Der menschlichste Moment ist wenn jemand "Ich bin geduldig" glaubt
    # aber RAGE zeigt. Das ist kein Bug. Erst nach 3+ Wiederholungen
    # wird es als Muster gemeldet — vorher nur BEMERKT, nicht korrigiert.
    ego_text = read_md_organ(egon_id, 'core', 'ego.md')
    if ego_text and emotion:
        widerspruch = _pruefe_ego_widerspruch(ego_text, emotion, aktuelle_episode)
        if widerspruch:
            # Zaehler im State: Wie oft dieser Widerspruch aufgetreten ist
            ego_ws = meta.get('ego_widersprueche', {})
            key = f'{emotion}:{widerspruch[:30]}'
            ego_ws[key] = ego_ws.get(key, 0) + 1
            meta['ego_widersprueche'] = ego_ws
            state['metacognition'] = meta
            write_yaml_organ(egon_id, 'core', 'state.yaml', state)

            if ego_ws[key] < EGO_WIDERSPRUCH_MIN:
                # Bemerkt aber NICHT gemeldet — fuehlen lassen
                try:
                    from engine.kalibrierung import log_decision
                    log_decision(egon_id, 'metacognition', 'ego_widerspruch_bemerkt', {
                        'widerspruch': widerspruch[:50],
                        'zaehler': ego_ws[key],
                        'minimum': EGO_WIDERSPRUCH_MIN,
                    })
                except Exception:
                    pass
            else:
                return {
                    'typ': 'ego_widerspruch',
                    'aussage': widerspruch,
                    'episode': aktuelle_episode.get('summary', ''),
                    'wiederholungen': ego_ws[key],
                    'frage': (
                        f"Ich glaube '{widerspruch}' — aber ich habe "
                        f"jetzt {ego_ws[key]} Mal das Gegenteil getan. "
                        f"Was stimmt wirklich?"
                    ),
                }

    # ── MUSTER 4: Bond-Drift ──
    if partner:
        bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
        if bonds_data:
            for bond in bonds_data.get('bonds', []):
                if bond.get('id') == partner or bond.get('name', '') == partner:
                    score = bond.get('score', 50)
                    letzte_scores = bond.get('score_verlauf', [])
                    if len(letzte_scores) >= 5:
                        delta = letzte_scores[-1] - letzte_scores[-5]
                        if abs(delta) > BOND_DRIFT_SCHWELLE * 100:
                            richtung = 'schwaecher' if delta < 0 else 'staerker'
                            return {
                                'typ': 'bond_drift',
                                'partner': partner,
                                'richtung': richtung,
                                'delta': round(delta, 2),
                                'frage': (
                                    f'Mein Verhaeltnis zu {partner} wird '
                                    f'stetig {richtung}. Warum?'
                                ),
                            }

    return None


def _staerkstes_system_aus_episode(episode: dict) -> str:
    """Extrahiert das staerkste emotionale System aus einer Episode.

    Episode hat emotions_felt: [{"type": "anger", "intensity": 0.7}, ...]
    Mapped auf Panksepp-Systeme.
    """
    emotions = episode.get('emotions_felt', [])
    if not emotions:
        return ''

    # Finde staerkste Emotion
    top = max(emotions, key=lambda e: e.get('intensity', 0))
    emo_type = top.get('type', '')

    # Map Episoden-Emotionstypen auf Panksepp
    mapping = {
        'anger': 'RAGE',
        'fear': 'FEAR',
        'sadness': 'GRIEF',
        'joy': 'PLAY',
        'excitement': 'SEEKING',
        'curiosity': 'SEEKING',
        'trust': 'CARE',
        'warmth': 'CARE',
        'pride': 'SEEKING',
        'frustration': 'RAGE',
        'surprise': 'SEEKING',
    }
    return mapping.get(emo_type, emo_type.upper())


def _pruefe_ego_widerspruch(ego_text: str, emotion: str, episode: dict) -> str | None:
    """Prueft ob die aktuelle Emotion dem Ego widerspricht.

    Returns:
        Die widersprechende Ego-Aussage oder None.
    """
    ego_lower = ego_text.lower()
    significance = episode.get('significance', 0.5)
    if significance < 0.4:
        return None  # Zu unwichtig fuer Widerspruch

    # Ego: "geduldig/ruhig/gelassen" + RAGE = Widerspruch
    if emotion == 'RAGE':
        geduld_muster = [
            r'ich bin geduldig',
            r'ich bin ruhig',
            r'ich bin gelassen',
            r'ich bin besonnen',
        ]
        for muster in geduld_muster:
            match = re.search(muster, ego_lower)
            if match:
                # Extrahiere den ganzen Satz
                start = max(0, match.start() - 10)
                end = min(len(ego_text), match.end() + 50)
                satz = ego_text[start:end].strip()
                # Bis zum Zeilenende
                satz = satz.split('\n')[0].strip()
                return satz

    # Ego: "mutig/furchtlos" + FEAR = Widerspruch
    if emotion == 'FEAR':
        mut_muster = [
            r'ich bin mutig',
            r'ich bin furchtlos',
            r'ich bin wagemutig',
        ]
        for muster in mut_muster:
            match = re.search(muster, ego_lower)
            if match:
                start = max(0, match.start() - 10)
                end = min(len(ego_text), match.end() + 50)
                satz = ego_text[start:end].strip().split('\n')[0].strip()
                return satz

    # Ego: "vertraue/offen" + PANIC = Widerspruch
    if emotion == 'PANIC':
        vertrauens_muster = [
            r'ich vertraue',
            r'ich bin offen',
            r'ich bin zugaenglich',
        ]
        for muster in vertrauens_muster:
            match = re.search(muster, ego_lower)
            if match:
                start = max(0, match.start() - 10)
                end = min(len(ego_text), match.end() + 50)
                satz = ego_text[start:end].strip().split('\n')[0].strip()
                return satz

    return None


# ================================================================
# Modul 2: Zyklusende-Reflexion (DMN-Aequivalent)
# ================================================================

MONITORING_PROMPT = """Du bist {name}. Du reflektierst ueber deinen letzten Zyklus.

DEIN EGO (Kurzversion):
{ego_kurz}

MUSTER DIE DIR AUFGEFALLEN SIND:
{muster_text}

EMOTIONALER VERLAUF:
{emotions_text}

BOND-VERAENDERUNGEN:
{bonds_text}

Beantworte in 3-5 kurzen Saetzen:
1. Welches Muster in deinem Verhalten faellt dir auf?
2. Gibt es einen Widerspruch zwischen dem was du glaubst und dem was du tust?
3. Was hat dich diesen Zyklus am meisten ueberrascht an dir selbst?

Schreibe als ICH-Perspektive. Ehrlich. Keine Floskeln."""

REGULATION_PROMPT = """Du bist {name}. Du reflektierst ueber deinen letzten Zyklus.
Du bist reif genug um nicht nur zu beobachten, sondern auch zu steuern.

DEIN EGO (Kurzversion):
{ego_kurz}

MUSTER:
{muster_text}

EMOTIONALER VERLAUF:
{emotions_text}

BONDS:
{bonds_text}

LETZTE METACOGNITION:
{letzte_reflexion}

Beantworte in 3-5 kurzen Saetzen:
1. Welches Muster willst du AENDERN — und wie konkret?
2. Welche Ueberzeugung in deinem Ego muss AKTUALISIERT werden?
3. Was nimmst du dir fuer den naechsten Zyklus vor?

Schreibe als ICH-Perspektive. Ehrlich. Konkret."""


async def zyklusende_metacognition(egon_id: str) -> dict | None:
    """DMN-Aequivalent: Tiefe Selbstreflexion am Zyklusende.

    Nur ab Zyklus 8 (Reife). Tier 2 LLM-Call.

    Returns:
        Dict mit reflexion-Text und Metadaten, oder None.
    """
    from llm.router import llm_chat
    from engine.naming import get_display_name

    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return None

    zyklus = state.get('zyklus', 0)
    if zyklus < REIFE_ZYKLUS:
        return None

    name = get_display_name(egon_id, 'voll')
    meta = state.get('metacognition', {})

    # Stufe bestimmen
    stufe = 'regulation' if zyklus >= REGULATION_ZYKLUS else 'monitoring'

    # Ego-Kurzversion (erste 500 Zeichen)
    ego_text = read_md_organ(egon_id, 'core', 'ego.md')
    ego_kurz = (ego_text or 'Noch kein Ego definiert.')[:500]

    # Muster-Alarme dieses Zyklus
    erkannte = meta.get('erkannte_muster', [])
    if erkannte:
        muster_text = '\n'.join(
            f"- {m.get('typ', '?')}: {m.get('frage', '?')}"
            for m in erkannte[-5:]
        )
    else:
        muster_text = '(Keine Muster erkannt diesen Zyklus)'

    # Emotionaler Verlauf aus Drives
    drives = state.get('drives', {})
    if drives:
        emotions_text = ', '.join(
            f"{k}: {v:.2f}" for k, v in drives.items()
            if isinstance(v, (int, float))
        )
    else:
        emotions_text = '(Keine Daten)'

    # Bond-Veraenderungen
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if bonds_data and bonds_data.get('bonds'):
        bonds_text = '\n'.join(
            f"- {b.get('name', b.get('id', '?'))}: Score {b.get('score', '?')}"
            for b in bonds_data['bonds'][:5]
        )
    else:
        bonds_text = '(Keine Bonds)'

    # Prompt waehlen
    if stufe == 'monitoring':
        prompt = MONITORING_PROMPT.format(
            name=name,
            ego_kurz=ego_kurz,
            muster_text=muster_text,
            emotions_text=emotions_text,
            bonds_text=bonds_text,
        )
    else:
        letzte = meta.get('letzte_reflexion', '(Erste Reflexion)')
        prompt = REGULATION_PROMPT.format(
            name=name,
            ego_kurz=ego_kurz,
            muster_text=muster_text,
            emotions_text=emotions_text,
            bonds_text=bonds_text,
            letzte_reflexion=letzte,
        )

    # LLM-Call (Tier 2)
    result = await llm_chat(
        system_prompt=prompt,
        messages=[{
            'role': 'user',
            'content': 'Reflektiere ueber deinen letzten Zyklus.',
        }],
        egon_id=egon_id,
    )

    reflexion_text = result.get('content', '').strip()
    if not reflexion_text:
        return None

    # Validierung: Keine destruktive Selbstkritik
    reflexion_text, status = validiere_reflexion(reflexion_text)
    if status == 'destruktiv':
        print(f'[metacognition] {egon_id}: Destruktive Reflexion blockiert')
        reflexion_text = '(Reflexion wurde uebersprungen — zu selbstkritisch)'

    return {
        'reflexion': reflexion_text,
        'stufe': stufe,
        'zyklus': zyklus,
        'muster_count': len(erkannte),
    }


# ================================================================
# Modul 3: Kognitive Neubewertung (Reappraisal)
# ================================================================

NEUBEWERTUNG_PROMPT = """Du bist {name}. Du hast bemerkt dass du auf {partner} zum {anzahl}. Mal mit {emotion} reagierst.

Frage: Ist deine Reaktion ANGEMESSEN oder ein blinder Fleck?

Antworte NUR als JSON:
{{"bewertung": "angemessen", "grund": "1 Satz warum", "korrektur": null}}

Moegliche bewertung-Werte: "angemessen", "uebertrieben", "blinder_fleck"
Bei uebertrieben/blinder_fleck: korrektur = "Was du aendern willst (1 Satz)"
"""


async def kognitive_neubewertung(
    egon_id: str,
    muster_alarm: dict,
) -> dict | None:
    """Reappraisal: Der EGON korrigiert eine erkannte Verzerrung.

    Nur ab Zyklus 13 (Regulation) und nur bei Muster-Alarm.

    Returns:
        Dict mit aktion, einsicht, korrektur — oder None.
    """
    from llm.router import llm_chat
    from engine.naming import get_display_name

    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return None

    zyklus = state.get('zyklus', 0)
    if zyklus < REGULATION_ZYKLUS:
        return None

    meta = state.get('metacognition', {})
    if meta.get('korrekturen_zyklus', 0) >= MAX_KORREKTUREN:
        print(f'[metacognition] {egon_id}: Max Korrekturen erreicht')
        return None

    name = get_display_name(egon_id, 'voll')
    typ = muster_alarm.get('typ', '')

    if typ == 'wiederholte_reaktion':
        partner = muster_alarm.get('partner', '?')
        emotion = muster_alarm.get('emotion', '?')
        anzahl = muster_alarm.get('anzahl', 0)

        prompt = NEUBEWERTUNG_PROMPT.format(
            name=name, partner=partner,
            emotion=emotion, anzahl=anzahl,
        )
    elif typ == 'ego_widerspruch':
        prompt = f"""Du bist {name}. Du hast einen Widerspruch bemerkt:

Deine Ueberzeugung: "{muster_alarm.get('aussage', '?')}"
Dein Verhalten: "{muster_alarm.get('episode', '?')}"

Was stimmt — deine Ueberzeugung oder dein Verhalten?

NUR JSON:
{{"aufloesung": "ueberzeugung_anpassen", "neue_ueberzeugung": "Angepasste Ueberzeugung (1 Satz)", "einsicht": "Was du daraus lernst (1 Satz)"}}

Moegliche aufloesung-Werte: "ueberzeugung_anpassen", "verhalten_war_ausnahme", "beides_stimmt"
"""
    else:
        # Bond-Drift und generalisierte Muster → nur Bewusstwerdung
        return {
            'aktion': 'bewusstwerdung',
            'einsicht': muster_alarm.get('frage', ''),
        }

    # LLM-Call (Tier 2)
    result = await llm_chat(
        system_prompt=prompt,
        messages=[{'role': 'user', 'content': 'Bewerte dein Muster.'}],
        egon_id=egon_id,
    )

    content = result.get('content', '').strip()
    if not content:
        return None

    # JSON parsen
    try:
        # JSON extrahieren
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            bewertung = json.loads(json_match.group())
        else:
            return None
    except (json.JSONDecodeError, ValueError):
        print(f'[metacognition] {egon_id}: Neubewertung JSON-Parse fehlgeschlagen')
        return None

    if typ == 'wiederholte_reaktion':
        bew = bewertung.get('bewertung', 'angemessen')
        if bew == 'angemessen':
            return {
                'aktion': 'bestaetigt',
                'einsicht': bewertung.get('grund', ''),
            }
        else:
            return {
                'aktion': 'korrektur',
                'einsicht': bewertung.get('grund', ''),
                'korrektur': bewertung.get('korrektur'),
                'emotion': muster_alarm.get('emotion'),
                'partner': muster_alarm.get('partner'),
            }

    elif typ == 'ego_widerspruch':
        auflo = bewertung.get('aufloesung', 'beides_stimmt')
        if auflo == 'ueberzeugung_anpassen':
            return {
                'aktion': 'ego_update',
                'alt': muster_alarm.get('aussage', ''),
                'neu': bewertung.get('neue_ueberzeugung', ''),
                'einsicht': bewertung.get('einsicht', ''),
            }
        else:
            return {
                'aktion': 'bestaetigt',
                'einsicht': bewertung.get('einsicht', ''),
            }

    return None


# ================================================================
# Validierung
# ================================================================

def validiere_reflexion(text: str) -> tuple[str, str]:
    """Prueft ob die Reflexion konstruktiv ist — nicht destruktiv.

    Returns:
        (text, 'ok') oder (None, 'destruktiv')
    """
    text_lower = text.lower()
    for muster in DESTRUKTIVE_MUSTER:
        if muster in text_lower:
            return None, 'destruktiv'
    return text, 'ok'


# ================================================================
# State-Management
# ================================================================

def initialisiere_metacognition(state: dict, zyklus: int) -> dict:
    """Initialisiert den Metacognition-Block in state.yaml.

    Wird aufgerufen wenn Zyklus >= 8 und Block noch nicht existiert.
    """
    if 'metacognition' not in state:
        stufe = 'regulation' if zyklus >= REGULATION_ZYKLUS else 'monitoring'
        state['metacognition'] = {
            'aktiv': True,
            'stufe': stufe,
            'muster_alarme_zyklus': 0,
            'korrekturen_zyklus': 0,
            'cooldown': 0,
            'erkannte_muster': [],
            'letzte_reflexion': None,
            'letzte_reflexion_zyklus': None,
        }
    return state


def speichere_muster_alarm(egon_id: str, alarm: dict) -> None:
    """Speichert einen Muster-Alarm in state.yaml."""
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    meta = state.setdefault('metacognition', {})
    erkannte = meta.setdefault('erkannte_muster', [])

    alarm_eintrag = {
        'typ': alarm.get('typ', '?'),
        'partner': alarm.get('partner', ''),
        'emotion': alarm.get('emotion', ''),
        'erkannt_datum': datetime.now().strftime('%Y-%m-%d'),
        'status': 'erkannt',
        'frage': alarm.get('frage', ''),
    }
    erkannte.append(alarm_eintrag)

    # Max 10 Muster behalten
    if len(erkannte) > 10:
        erkannte = erkannte[-10:]
    meta['erkannte_muster'] = erkannte
    meta['muster_alarme_zyklus'] = meta.get('muster_alarme_zyklus', 0) + 1

    state['metacognition'] = meta
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)


def speichere_zyklusende_reflexion(egon_id: str, reflexion_result: dict) -> None:
    """Speichert die Zyklusende-Reflexion in state.yaml und ego.md."""
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    meta = state.setdefault('metacognition', {})
    reflexion_text = reflexion_result.get('reflexion', '')

    # state.yaml aktualisieren
    meta['letzte_reflexion'] = reflexion_text
    meta['letzte_reflexion_zyklus'] = reflexion_result.get('zyklus', 0)

    # Stufe aktualisieren
    zyklus = state.get('zyklus', 0)
    if zyklus >= REGULATION_ZYKLUS:
        meta['stufe'] = 'regulation'
    elif zyklus >= REIFE_ZYKLUS:
        meta['stufe'] = 'monitoring'

    # Muster-Alarme fuer naechsten Zyklus zuruecksetzen
    meta['muster_alarme_zyklus'] = 0
    meta['korrekturen_zyklus'] = 0
    meta['cooldown'] = 0

    state['metacognition'] = meta
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    # ego.md erweitern (Selbstreflexion-Abschnitt)
    if reflexion_text and reflexion_text != '(Reflexion wurde uebersprungen — zu selbstkritisch)':
        _erweitere_ego_selbstreflexion(egon_id, reflexion_text, reflexion_result.get('zyklus', 0))

    print(f'[metacognition] {egon_id}: Zyklusende-Reflexion gespeichert (Zyklus {zyklus})')


def _erweitere_ego_selbstreflexion(egon_id: str, reflexion: str, zyklus: int) -> None:
    """Fuegt eine Reflexion zum Selbstreflexion-Abschnitt in ego.md hinzu."""
    from engine.organ_reader import write_organ

    ego_text = read_md_organ(egon_id, 'core', 'ego.md')
    if not ego_text:
        return

    reflexion_block = (
        f'\n\n## Selbstreflexion (Zyklus {zyklus})\n'
        f'{reflexion}\n'
    )

    # Wenn schon Selbstreflexion existiert → anheften
    if '## Selbstreflexion' in ego_text:
        # Vor dem naechsten ## einfuegen (oder am Ende)
        abschnitte = ego_text.split('## Selbstreflexion')
        if len(abschnitte) >= 2:
            rest = abschnitte[1]
            # Naechste ## finden
            naechste_section = re.search(r'\n## [^S]', rest)
            if naechste_section:
                insert_pos = naechste_section.start()
                neuer_rest = (
                    rest[:insert_pos]
                    + f'\n\n### Zyklus {zyklus}\n{reflexion}\n'
                    + rest[insert_pos:]
                )
            else:
                neuer_rest = rest + f'\n\n### Zyklus {zyklus}\n{reflexion}\n'
            ego_text = abschnitte[0] + '## Selbstreflexion' + neuer_rest
    else:
        ego_text += reflexion_block

    # Ego nicht endlos wachsen lassen — max 3 Reflexionen behalten
    reflexion_matches = list(re.finditer(r'### Zyklus \d+', ego_text))
    if len(reflexion_matches) > 3:
        # Aelteste entfernen (nur die 3 neuesten behalten)
        erste_zu_loeschende = reflexion_matches[0].start()
        letzte_zu_behaltende = reflexion_matches[-3].start()
        ego_text = (
            ego_text[:erste_zu_loeschende]
            + ego_text[letzte_zu_behaltende:]
        )

    write_organ(egon_id, 'core', 'ego.md', ego_text)


def anwende_korrektur(egon_id: str, ergebnis: dict) -> None:
    """Wendet eine kognitive Neubewertung an.

    Kann Bond leicht anpassen und Emotion einmalig daempfen.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    aktion = ergebnis.get('aktion', '')
    meta = state.setdefault('metacognition', {})

    if aktion == 'korrektur':
        emotion = ergebnis.get('emotion', '')
        # Emotion einmalig Richtung Baseline daempfen (max 20%)
        if emotion and emotion in state.get('drives', {}):
            from engine.state_validator import DNA_DEFAULTS
            dna_profile = state.get('dna_profile', 'DEFAULT')
            baselines = DNA_DEFAULTS.get(dna_profile, DNA_DEFAULTS.get('DEFAULT', {}))
            baseline = baselines.get(emotion, 0.3)
            aktuell = state['drives'][emotion]
            abweichung = aktuell - baseline
            korrektur = abweichung * 0.20  # Max 20%
            state['drives'][emotion] = round(aktuell - korrektur, 4)
            print(
                f'[metacognition] {egon_id}: {emotion} '
                f'{aktuell:.3f} -> {state["drives"][emotion]:.3f}'
            )

        # Muster als korrigiert markieren
        for m in meta.get('erkannte_muster', []):
            if (m.get('emotion') == emotion
                    and m.get('status') == 'erkannt'):
                m['status'] = 'korrigiert'
                break

        meta['korrekturen_zyklus'] = meta.get('korrekturen_zyklus', 0) + 1
        meta['cooldown'] = COOLDOWN_GESPRAECHE

    elif aktion == 'ego_update':
        # Ego-Statement aktualisieren
        alt = ergebnis.get('alt', '')
        neu = ergebnis.get('neu', '')
        if alt and neu:
            ego_text = read_md_organ(egon_id, 'core', 'ego.md')
            if ego_text and alt in ego_text:
                from engine.organ_reader import write_organ
                ego_text = ego_text.replace(alt, neu, 1)
                write_organ(egon_id, 'core', 'ego.md', ego_text)
                print(f'[metacognition] {egon_id}: Ego aktualisiert: "{alt}" -> "{neu}"')

        meta['korrekturen_zyklus'] = meta.get('korrekturen_zyklus', 0) + 1
        meta['cooldown'] = COOLDOWN_GESPRAECHE

    state['metacognition'] = meta
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)


def reduziere_cooldown(egon_id: str) -> None:
    """Reduziert den Cooldown um 1 (nach jedem Gespraech)."""
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    meta = state.get('metacognition', {})
    cooldown = meta.get('cooldown', 0)
    if cooldown > 0:
        meta['cooldown'] = cooldown - 1
        state['metacognition'] = meta
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)


# ================================================================
# Integration Points
# ================================================================

def metacognition_post_chat(
    egon_id: str,
    pfad: str,
    episode: dict | None,
) -> dict | None:
    """Haupteintrittspunkt: Metacognition nach einem Chat.

    Wird aus api/chat.py aufgerufen, NACH allen anderen Post-Processing Steps.

    Regelbasiert (Modul 1) — kein LLM-Call hier.
    LLM-Calls nur bei Neubewertung (Modul 3, selten).

    Args:
        egon_id: EGON-ID.
        pfad: Thalamus-Pfad (A_MINIMAL, B_SOZIAL, C_EMOTIONAL, D_BURST).
        episode: Die gerade erstellte Episode (oder None).

    Returns:
        Muster-Alarm dict oder None.
    """
    # Nur bei Pfad C oder D (emotional relevante Gespraeche)
    if pfad not in ('C_EMOTIONAL', 'D_BURST'):
        # Cooldown trotzdem reduzieren
        reduziere_cooldown(egon_id)
        return None

    if not episode:
        reduziere_cooldown(egon_id)
        return None

    # Reife-Check
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return None
    zyklus = state.get('zyklus', 0)
    if zyklus < REIFE_ZYKLUS:
        return None

    # Metacognition initialisieren falls noetig
    if 'metacognition' not in state:
        state = initialisiere_metacognition(state, zyklus)
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    # Modul 1: Muster-Check (regelbasiert, 0 Tokens)
    alarm = muster_check(egon_id, episode)

    if alarm:
        speichere_muster_alarm(egon_id, alarm)
        print(
            f'[metacognition] {egon_id}: Muster erkannt — '
            f'{alarm["typ"]}: {alarm.get("frage", "")[:80]}'
        )

        try:
            from engine.neuroplastizitaet import ne_emit
            ne_emit(egon_id, 'AKTIVIERUNG', 'praefrontal', 'praefrontal', label=f'Metacognition: {alarm.get("typ", "?")}', intensitaet=0.7, animation='glow')
        except Exception:
            pass
    else:
        # Cooldown reduzieren auch wenn kein Alarm
        reduziere_cooldown(egon_id)

    return alarm


async def metacognition_post_chat_mit_neubewertung(
    egon_id: str,
    pfad: str,
    episode: dict | None,
) -> dict | None:
    """Erweiterte Version: Muster-Check + ggf. Neubewertung.

    Async wegen potenziellem LLM-Call (Modul 3).

    Returns:
        Dict mit alarm + ggf. neubewertung, oder None.
    """
    alarm = metacognition_post_chat(egon_id, pfad, episode)
    if not alarm:
        return None

    result = {'alarm': alarm, 'neubewertung': None}

    # Modul 3: Neubewertung (nur Regulation-Stufe)
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if state:
        meta = state.get('metacognition', {})
        if meta.get('stufe') == 'regulation':
            neubewertung = await kognitive_neubewertung(egon_id, alarm)
            if neubewertung:
                result['neubewertung'] = neubewertung
                if neubewertung.get('aktion') in ('korrektur', 'ego_update'):
                    anwende_korrektur(egon_id, neubewertung)

    return result


async def metacognition_zyklusende(egon_id: str) -> dict | None:
    """Haupteintrittspunkt: Metacognition am Zyklusende.

    Wird aus pulse_v2.py aufgerufen, am Ende des Pulse.

    Returns:
        Reflexion-Ergebnis oder None.
    """
    reflexion = await zyklusende_metacognition(egon_id)
    if reflexion:
        speichere_zyklusende_reflexion(egon_id, reflexion)
    return reflexion
