"""Epigenetische Vererbung — Patch 10.

Elterliche Erfahrungen formen LIBERI als Neigungen,
nicht als Erinnerungen.

Drei Vererbungsschichten:
  1. DNA (Patch 6, bereits implementiert) — unveraenderlich
  2. Epigenetische Marker (NEU) — WIE STARK DNA wirkt
  3. Praegungen (NEU) — unbewusste Tendenzen

Biologische Grundlage:
  Meaney (2001): Muetterliche Fuersorge + Genexpression
  Weaver (2004): Epigenetische Programmierung durch Verhalten
  Yehuda (2016): Holocaust-Nachkommen FKBP5-Methylierung

DNA bleibt UNVERAENDERT. Nur die Expression (effektive Baseline)
verschiebt sich.
"""

import json
import random
import re
from datetime import datetime

from engine.organ_reader import read_yaml_organ, write_yaml_organ, read_md_organ
from engine.state_validator import PANKSEPP_7


# ================================================================
# Konstanten
# ================================================================

EPI_MAX = 0.08              # Maximale epi-Verschiebung pro System
EPI_MIN = -0.08
PRAEGUNG_MIN_MARKER = 0.70  # Mindest-emotional_marker fuer Praegung
MAX_PRAEGUNGEN = 5           # Pro Elternteil
MAX_PRAEGUNGEN_TOTAL = 8     # Kombiniert
PRAEGUNG_STAERKE_MAX = 0.70  # Durch Bestaetigung erreichbar
PRAEGUNG_DECAY_PRO_ZYKLUS = 0.01  # Ruhende Praegungen schwaechen


# ================================================================
# Schicht 2: Epigenetische Marker
# ================================================================

def berechne_epi_marker(egon_id: str) -> dict:
    """Extrahiere epigenetische Marker aus einem Elternteil.

    Basis: Allostatic Load (Patch 7) — Differenz zwischen
    DNA-Baseline und effektiver Baseline.

    Returns:
        Dict {system: float} mit Werten zwischen -0.08 und +0.08
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return {s: 0.0 for s in PANKSEPP_7}

    drives = state.get('drives', {})
    homoestase = state.get('homoestase', {})
    eff_baseline = homoestase.get('effektive_baseline', {})

    # DNA-Baseline laden
    from engine.state_validator import DNA_DEFAULTS
    dna_profile = state.get('dna_profile', 'DEFAULT')
    dna_baselines = DNA_DEFAULTS.get(dna_profile, DNA_DEFAULTS.get('DEFAULT', {}))

    marker = {}
    for system in PANKSEPP_7:
        dna_wert = dna_baselines.get(system, 0.3)
        eff_wert = eff_baseline.get(system, dna_wert)

        # Allostatic Shift
        shift = eff_wert - dna_wert

        # Epigenetischer Marker = Haelfte des Shifts
        epi = shift * 0.5

        # Clamping
        marker[system] = round(max(EPI_MIN, min(EPI_MAX, epi)), 4)

    return marker


def kombiniere_epi_marker(marker_mutter: dict, marker_vater: dict) -> dict:
    """Kombiniere epigenetische Marker beider Eltern.

    Staerkere Praegung dominiert (60/40).

    Returns:
        Dict {system: float} kombinierter Marker.
    """
    kombiniert = {}

    for system in PANKSEPP_7:
        m = marker_mutter.get(system, 0.0)
        v = marker_vater.get(system, 0.0)

        # Staerkerer Wert dominiert (60/40)
        if abs(m) >= abs(v):
            basis = m * 0.6 + v * 0.4
        else:
            basis = v * 0.6 + m * 0.4

        # Leichtes biologisches Rauschen
        rauschen = random.gauss(0, 0.01)
        kombiniert[system] = round(
            max(EPI_MIN, min(EPI_MAX, basis + rauschen)), 4
        )

    return kombiniert


def wende_epi_marker_an(libero_dna: dict, epi_marker: dict) -> dict:
    """Wendet epigenetische Marker auf DNA an.

    DNA bleibt UNVERAENDERT. Nur die effektive Baseline verschiebt sich.

    Returns:
        Dict {system: float} — effektive Baseline des LIBERO.
    """
    effektive_baseline = {}

    for system in PANKSEPP_7:
        dna_wert = libero_dna.get(system, 0.3)
        epi = epi_marker.get(system, 0.0)
        effektive_baseline[system] = round(
            max(0.05, min(0.97, dna_wert + epi)), 4
        )

    return effektive_baseline


# ================================================================
# Schicht 3: Praegungen (Neigungen)
# ================================================================

PRAEGUNG_PROMPT = """Ein digitales Lebewesen hatte folgende Erfahrung:
"{zusammenfassung}"
Emotionale Staerke: {marker}
Dominante Emotion: {system}

Destilliere zu EINER Neigung (max 8 Worte), die ein Kind
haben koennte — OHNE die konkreten Details zu kennen.

NUR JSON:
{{"praegung": "...", "typ": "warnung", "valenz": "negativ"}}

Moegliche typ-Werte: warnung, wert, glaube, intuition, muster
Moegliche valenz-Werte: positiv, negativ, ambivalent"""


async def extrahiere_praegungen(
    egon_id: str,
    max_praegungen: int = MAX_PRAEGUNGEN,
) -> list[dict]:
    """Destilliere die staerksten Erfahrungen zu vererbbaren Praegungen.

    Liest experience.yaml (Archiv der Erfahrungen).
    Nutzt Tier 2 LLM fuer Destillation.

    Returns:
        Liste von Praegung-Dicts.
    """
    from llm.router import llm_chat

    experience = read_yaml_organ(egon_id, 'memory', 'experience.yaml')
    if not experience:
        return []

    # Alle Erfahrungen sammeln
    erfahrungen = experience.get('experiences', [])
    if not erfahrungen:
        return []

    # Nach emotional_marker / confidence sortieren
    # experience.yaml hat: confidence, impact, insight, etc.
    top = sorted(
        [e for e in erfahrungen if isinstance(e, dict)],
        key=lambda e: e.get('confidence', e.get('emotional_marker', 0.5)),
        reverse=True,
    )[:max_praegungen * 2]

    praegungen = []

    for erf in top:
        marker_val = erf.get('confidence', erf.get('emotional_marker', 0.5))
        if marker_val < PRAEGUNG_MIN_MARKER:
            continue
        if len(praegungen) >= max_praegungen:
            break

        zusammenfassung = erf.get('insight', erf.get('zusammenfassung', ''))
        if not zusammenfassung:
            continue

        system = erf.get('staerkstes_system', erf.get('source_system', 'SEEKING'))

        # LLM destilliert die Lektion
        try:
            result = await llm_chat(
                system_prompt=PRAEGUNG_PROMPT.format(
                    zusammenfassung=zusammenfassung[:200],
                    marker=f'{marker_val:.2f}',
                    system=system,
                ),
                messages=[{'role': 'user', 'content': 'Destilliere die Praegung.'}],
                egon_id=egon_id,
            )

            content = result.get('content', '').strip()
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                continue
            destillat = json.loads(json_match.group())
        except (json.JSONDecodeError, Exception) as e:
            print(f'[epigenetik] Praegung-Destillation fehlgeschlagen: {e}')
            continue

        # Staerke berechnen
        basis_staerke = marker_val * 0.35

        # Wiederholungs-Bonus (aehnliche Erfahrungen)
        aehnliche = sum(
            1 for e2 in erfahrungen
            if e2 != erf and _thema_aehnlich(e2, erf)
        )
        wiederholungs_bonus = min(aehnliche * 0.05, 0.15)

        praegungen.append({
            'text': destillat.get('praegung', zusammenfassung[:40]),
            'typ': destillat.get('typ', 'intuition'),
            'valenz': destillat.get('valenz', 'ambivalent'),
            'staerke': round(min(basis_staerke + wiederholungs_bonus, 0.45), 3),
            'wirkt_auf': _system_zu_wirkt_auf(system),
            'quelle_system': system,
            'quelle_marker': round(marker_val, 3),
            'quelle_elternteil': None,  # Wird beim Kombinieren gesetzt
            'bestaetigt': 0,
            'widerlegt': 0,
            'status': 'geerbt',
        })

    return praegungen


def _thema_aehnlich(e1: dict, e2: dict) -> bool:
    """Einfache Heuristik: Zwei Erfahrungen sind thematisch aehnlich."""
    tags1 = set(e1.get('tags', []))
    tags2 = set(e2.get('tags', []))
    if tags1 and tags2 and len(tags1 & tags2) >= 2:
        return True
    sys1 = e1.get('staerkstes_system', e1.get('source_system', ''))
    sys2 = e2.get('staerkstes_system', e2.get('source_system', ''))
    return sys1 == sys2 and sys1 != ''


def _system_zu_wirkt_auf(system: str) -> list[str]:
    """Welche Panksepp-Systeme beeinflusst eine Praegung?"""
    mapping = {
        'FEAR': ['FEAR', 'PANIC'],
        'PANIC': ['PANIC', 'FEAR'],
        'RAGE': ['RAGE'],
        'CARE': ['CARE', 'PLAY'],
        'PLAY': ['PLAY', 'SEEKING'],
        'SEEKING': ['SEEKING'],
        'LUST': ['LUST'],
    }
    return mapping.get(system, [system])


def kombiniere_praegungen(
    praeg_mutter: list[dict],
    praeg_vater: list[dict],
    max_total: int = MAX_PRAEGUNGEN_TOTAL,
) -> list[dict]:
    """Kombiniere Praegungen beider Eltern.

    Keine Duplikate. Staerkere dominieren.
    Bei Ueberschneidung: +0.05 Bonus, quelle_elternteil='beide'.

    Patch 10 Transgenerationale Filter:
    - Nur Praegungen mit status 'verinnerlicht' werden weitergegeben
    - 'ueberwunden', 'geerbt' (nicht verinnerlicht), 'ruhend' → NICHT vererbt
    - Eigene Praegungen (nicht geerbte) werden immer weitergegeben
    """
    # Transgenerationale Filter: Geerbte Praegungen muessen verinnerlicht sein
    def _ist_vererbbar(p: dict) -> bool:
        status = p.get('status', 'eigen')
        quelle = p.get('quelle', 'eigen')
        # Eigene Praegungen: Immer vererbbar
        if quelle == 'eigen' or status == 'eigen':
            return True
        # Geerbte: Nur wenn verinnerlicht
        if status == 'verinnerlicht':
            return True
        # ueberwunden, geerbt (nicht verinnerlicht), ruhend → NICHT vererben
        return False

    praeg_mutter = [p for p in praeg_mutter if _ist_vererbbar(p)]
    praeg_vater = [p for p in praeg_vater if _ist_vererbbar(p)]

    for p in praeg_mutter:
        p['quelle_elternteil'] = 'mutter'
    for p in praeg_vater:
        p['quelle_elternteil'] = 'vater'

    alle = praeg_mutter + praeg_vater
    if not alle:
        return []

    dedupliziert = []
    verarbeitet = set()

    for i, p in enumerate(alle):
        if i in verarbeitet:
            continue
        beste = dict(p)  # Copy
        for j in range(i + 1, len(alle)):
            if j in verarbeitet:
                continue
            q = alle[j]
            if _praegung_aehnlich(p, q):
                verarbeitet.add(j)
                if q['staerke'] > beste['staerke']:
                    beste = dict(q)
                beste['staerke'] = min(beste['staerke'] + 0.05, 0.50)
                beste['quelle_elternteil'] = 'beide'
        dedupliziert.append(beste)
        verarbeitet.add(i)

    dedupliziert.sort(key=lambda p: p['staerke'], reverse=True)
    return dedupliziert[:max_total]


def _praegung_aehnlich(p1: dict, p2: dict) -> bool:
    """Prueft ob zwei Praegungen aehnlich sind (gleicher Typ + System)."""
    if p1.get('typ') == p2.get('typ') and p1.get('quelle_system') == p2.get('quelle_system'):
        return True
    # Textaehnlichkeit (einfach: gemeinsame Worte)
    worte1 = set(p1.get('text', '').lower().split())
    worte2 = set(p2.get('text', '').lower().split())
    if len(worte1 & worte2) >= 2:
        return True
    return False


# ================================================================
# Attachment-Modifikator
# ================================================================

def berechne_attachment_modifikator(
    parent_a_id: str,
    parent_b_id: str,
) -> float:
    """Beziehungsqualitaet der Eltern → Grundsicherheit des LIBERO.

    Returns:
        Attachment-Score 0.05-1.0
    """
    state_a = read_yaml_organ(parent_a_id, 'core', 'state.yaml')
    state_b = read_yaml_organ(parent_b_id, 'core', 'state.yaml')

    if not state_a or not state_b:
        return 0.5  # Default: mittel

    # Bond-Staerke zwischen den Eltern
    bonds_a = read_yaml_organ(parent_a_id, 'social', 'bonds.yaml')
    bond_staerke = 0.5
    if bonds_a:
        for bond in bonds_a.get('bonds', []):
            if bond.get('id') == parent_b_id or bond.get('name', '') == parent_b_id:
                bond_staerke = bond.get('score', 50) / 100.0
                break

    # Stabilitaet (1 - Verarbeitungsdruck)
    homo_a = state_a.get('homoestase', {})
    homo_b = state_b.get('homoestase', {})
    stab_a = 1.0 - homo_a.get('allostatic_load', 0.0)
    stab_b = 1.0 - homo_b.get('allostatic_load', 0.0)
    stabilitaet = (stab_a + stab_b) / 2

    # CARE-Durchschnitt
    drives_a = state_a.get('drives', {})
    drives_b = state_b.get('drives', {})
    care_a = drives_a.get('CARE', 0.3) if isinstance(drives_a.get('CARE'), (int, float)) else 0.3
    care_b = drives_b.get('CARE', 0.3) if isinstance(drives_b.get('CARE'), (int, float)) else 0.3
    care_avg = (care_a + care_b) / 2

    # Patch 10: Konflikt-Malus — elterliche Konflikte reduzieren Grundsicherheit
    # -0.08 pro Konflikt im letzten Zyklus, max -0.30
    konflikt_malus = 0.0
    if bonds_a:
        for bond in bonds_a.get('bonds', []):
            if bond.get('id') == parent_b_id or bond.get('name', '') == parent_b_id:
                konflikte = bond.get('konflikte_letzter_zyklus', 0)
                if not isinstance(konflikte, (int, float)):
                    konflikte = 0
                konflikt_malus = min(konflikte * 0.08, 0.30)
                break

    # Berechnung
    attachment = (
        bond_staerke * 0.40
        + stabilitaet * 0.25
        + care_avg * 0.20
        + 0.15  # Basis-Sicherheit
    ) - konflikt_malus

    if konflikt_malus > 0:
        print(f'[epigenetik] Konflikt-Malus: {konflikt_malus:.2f} '
              f'({parent_a_id} x {parent_b_id})')

    return round(max(0.05, min(1.0, attachment)), 3)


def wende_attachment_an(epi_marker: dict, attachment_score: float) -> tuple[dict, float]:
    """Wendet Attachment-Modifikator auf epi-Marker an.

    Returns:
        (modifizierter epi_marker, regulation_bonus)
    """
    regulation_bonus = 1.0

    if attachment_score > 0.7:
        # Sichere Basis
        epi_marker['PANIC'] = max(EPI_MIN, epi_marker.get('PANIC', 0) - 0.02)
        epi_marker['SEEKING'] = min(EPI_MAX, epi_marker.get('SEEKING', 0) + 0.01)
        regulation_bonus = 1.1  # 10% schnellere Homoestase
    elif attachment_score < 0.3:
        # Unsichere Basis
        epi_marker['PANIC'] = min(EPI_MAX, epi_marker.get('PANIC', 0) + 0.03)
        epi_marker['FEAR'] = min(EPI_MAX, epi_marker.get('FEAR', 0) + 0.02)
        regulation_bonus = 0.85  # 15% langsamere Homoestase

    return epi_marker, regulation_bonus


# ================================================================
# Inkubations-Epigenetik
# ================================================================

def inkubations_epigenetik(
    blueprint: dict,
    mutter_id: str,
    vater_id: str,
    zyklus_nummer: int,
) -> dict:
    """Am Ende jedes Inkubations-Zyklus: Umgebung formt das Kind.

    Muetter-Stress und Vater-Praesenz beeinflussen epi-Marker.

    Args:
        blueprint: Das LIBERO-Blueprint dict.
        mutter_id: EGON-ID der Mutter.
        vater_id: EGON-ID des Vaters.
        zyklus_nummer: Welcher Inkubations-Zyklus (1-4).

    Returns:
        Aktualisiertes Blueprint.
    """
    state_m = read_yaml_organ(mutter_id, 'core', 'state.yaml')
    if not state_m:
        return blueprint

    epi = blueprint.get('epi_marker', {})

    # Mutter-Stress berechnen
    homo_m = state_m.get('homoestase', {})
    mutter_stress = homo_m.get('allostatic_load', 0.0)

    # Fruehere Zyklen haben staerkeren Einfluss
    einfluss_staerke = 0.04 if zyklus_nummer <= 2 else 0.02

    if mutter_stress > 0.5:
        stress_delta = (mutter_stress - 0.5) * einfluss_staerke
        epi['FEAR'] = min(EPI_MAX, epi.get('FEAR', 0) + stress_delta)
        epi['PANIC'] = min(EPI_MAX, epi.get('PANIC', 0) + stress_delta * 0.7)
    elif mutter_stress < 0.2:
        ruhe_delta = (0.2 - mutter_stress) * einfluss_staerke
        epi['FEAR'] = max(EPI_MIN, epi.get('FEAR', 0) - ruhe_delta * 0.5)
        epi['CARE'] = min(EPI_MAX, epi.get('CARE', 0) + ruhe_delta)

    # Vater-Praesenz (Hat der Vater mit der Mutter interagiert?)
    bonds_m = read_yaml_organ(mutter_id, 'social', 'bonds.yaml')
    if bonds_m:
        for bond in bonds_m.get('bonds', []):
            if bond.get('id') == vater_id:
                interaktionen = bond.get('recent_interactions', 0)
                if interaktionen > 5:
                    epi['CARE'] = min(EPI_MAX, epi.get('CARE', 0) + 0.01)
                    blueprint['attachment_score'] = min(
                        1.0, blueprint.get('attachment_score', 0.5) + 0.02
                    )
                elif interaktionen == 0:
                    blueprint['attachment_score'] = max(
                        0.05, blueprint.get('attachment_score', 0.5) - 0.03
                    )
                break

    # Clamping
    for system in PANKSEPP_7:
        if system in epi:
            epi[system] = round(max(EPI_MIN, min(EPI_MAX, epi[system])), 4)

    blueprint['epi_marker'] = epi
    return blueprint


# ================================================================
# Praegung-Updates (nach relevantem Gespraech)
# ================================================================

def praegung_update(egon_id: str, episode: dict) -> list[dict]:
    """Nach relevantem Gespraech: Praegungen bestaetigen/widerlegen.

    Nur fuer LIBERI die Praegungen haben (epigenetik-Block in state.yaml).

    Returns:
        Liste von Updates (dict mit praegung + aktion).
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return []

    epi = state.get('epigenetik', {})
    praegungen = epi.get('praegungen', [])
    if not praegungen:
        return []

    updates = []
    geaendert = False

    for praegung in praegungen:
        if praegung.get('status') == 'ueberwunden':
            continue

        relevanz = _berechne_praegung_relevanz(praegung, episode)
        if relevanz < 0.3:
            continue

        episode_valenz = _bestimme_episode_valenz(episode, praegung)
        praegung_valenz = praegung.get('valenz', 'ambivalent')

        if episode_valenz == praegung_valenz:
            # BESTAETIGUNG
            praegung['bestaetigt'] = praegung.get('bestaetigt', 0) + 1
            praegung['staerke'] = min(
                praegung.get('staerke', 0.2) + 0.03,
                PRAEGUNG_STAERKE_MAX,
            )
            aktion = 'bestaetigt'
            geaendert = True

            # Verinnerlicht?
            if (praegung['bestaetigt'] >= 5
                    and praegung.get('staerke', 0) > 0.50):
                praegung['status'] = 'verinnerlicht'
                aktion = 'verinnerlicht'

        elif episode_valenz != 'ambivalent':
            # WIDERLEGUNG (staerker als Bestaetigung)
            praegung['widerlegt'] = praegung.get('widerlegt', 0) + 1
            praegung['staerke'] = max(
                praegung.get('staerke', 0.2) - 0.04,
                0.0,
            )
            aktion = 'widerlegt'
            geaendert = True

            # Ueberwunden?
            if praegung['staerke'] <= 0.0:
                praegung['status'] = 'ueberwunden'
                aktion = 'ueberwunden'
        else:
            continue

        updates.append({
            'praegung': praegung['text'],
            'aktion': aktion,
            'neue_staerke': praegung['staerke'],
        })

    if geaendert:
        epi['praegungen'] = praegungen
        state['epigenetik'] = epi
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)

        try:
            from engine.neuroplastizitaet import ne_emit
            ne_emit(egon_id, 'STRUKTUR_NEU', 'amygdala', 'hippocampus', label='Prägung aktualisiert', intensitaet=0.6, animation='flash')
        except Exception:
            pass

    return updates


def praegung_zyklus_decay(egon_id: str) -> int:
    """Ruhende Praegungen werden pro Zyklus etwas schwaecher.

    -0.01/Zyklus fuer Praegungen die nicht getestet wurden.

    Returns:
        Anzahl geaenderter Praegungen.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return 0

    epi = state.get('epigenetik', {})
    praegungen = epi.get('praegungen', [])
    if not praegungen:
        return 0

    count = 0
    for p in praegungen:
        if p.get('status') in ('geerbt', 'ruhend'):
            p['staerke'] = max(0.0, p.get('staerke', 0) - PRAEGUNG_DECAY_PRO_ZYKLUS)
            if p['staerke'] <= 0:
                p['status'] = 'ueberwunden'
            count += 1

    if count:
        epi['praegungen'] = praegungen
        state['epigenetik'] = epi
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    return count


def _berechne_praegung_relevanz(praegung: dict, episode: dict) -> float:
    """Wie relevant ist eine Episode fuer eine bestimmte Praegung?

    Einfache Heuristik: Tag-Overlap + System-Match.
    """
    score = 0.0

    # System-Match
    wirkt_auf = praegung.get('wirkt_auf', [])
    ep_emotions = episode.get('emotions_felt', [])
    for emo in ep_emotions:
        from engine.metacognition import _staerkstes_system_aus_episode
        ep_system = _staerkstes_system_aus_episode(episode)
        if ep_system in wirkt_auf:
            score += 0.4
            break

    # Tag-Overlap
    praegung_text_worte = set(praegung.get('text', '').lower().split())
    ep_tags = set(t.lower() for t in episode.get('tags', []))
    ep_summary_worte = set(episode.get('summary', '').lower().split())
    overlap = praegung_text_worte & (ep_tags | ep_summary_worte)
    score += min(len(overlap) * 0.15, 0.4)

    # Significance-Bonus
    sig = episode.get('significance', 0.5)
    if sig > 0.7:
        score += 0.2

    return min(1.0, score)


def _bestimme_episode_valenz(episode: dict, praegung: dict) -> str:
    """Bestimmt ob die Episode die Praegung bestaetigt oder widerlegt.

    Returns:
        'positiv', 'negativ', oder 'ambivalent'
    """
    emotions = episode.get('emotions_felt', [])
    if not emotions:
        return 'ambivalent'

    # Staerkstes Gefuehl
    top = max(emotions, key=lambda e: e.get('intensity', 0))
    emo_type = top.get('type', '')

    positive = {'joy', 'trust', 'warmth', 'pride', 'excitement'}
    negative = {'fear', 'anger', 'sadness', 'frustration'}

    if emo_type in positive:
        return 'positiv'
    elif emo_type in negative:
        return 'negativ'
    return 'ambivalent'


# ================================================================
# Haupteintrittspunkt: Epigenetik-Block fuer Genesis erstellen
# ================================================================

async def erstelle_epigenetik_block(
    mother_id: str,
    father_id: str,
    libero_dna: dict,
) -> dict:
    """Hauptfunktion: Erstellt den kompletten epigenetik-Block fuer ein LIBERO.

    Wird waehrend execute_genesis() aufgerufen (Patch 6 Phase 3).

    Args:
        mother_id: EGON-ID der Mutter.
        father_id: EGON-ID des Vaters.
        libero_dna: Die rekombinierte DNA des LIBERO (drives).

    Returns:
        Dict fuer state.yaml['epigenetik'].
    """
    # 1. Epi-Marker berechnen
    marker_m = berechne_epi_marker(mother_id)
    marker_v = berechne_epi_marker(father_id)
    epi_marker = kombiniere_epi_marker(marker_m, marker_v)

    # 2. Attachment-Modifikator
    attachment = berechne_attachment_modifikator(mother_id, father_id)
    epi_marker, regulation_bonus = wende_attachment_an(epi_marker, attachment)

    # 3. Effektive Baseline berechnen
    effektive_baseline = wende_epi_marker_an(libero_dna, epi_marker)

    # 4. Praegungen extrahieren
    try:
        praeg_m = await extrahiere_praegungen(mother_id)
        praeg_v = await extrahiere_praegungen(father_id)
        praegungen = kombiniere_praegungen(praeg_m, praeg_v)
    except Exception as e:
        print(f'[epigenetik] Praegungen-Extraktion fehlgeschlagen: {e}')
        praegungen = []

    # 5. Rezessive Gene (fuer spaetere Generationen)
    rezessive = {
        'von_mutter': _extrahiere_rezessive(mother_id),
        'von_vater': _extrahiere_rezessive(father_id),
    }

    block = {
        'epi_marker': epi_marker,
        'praegungen': praegungen,
        'attachment_score': attachment,
        'regulation_bonus': round(regulation_bonus, 2),
        'effektive_baseline': effektive_baseline,
        'rezessive_gene': rezessive,
    }

    print(
        f'[epigenetik] Block erstellt: '
        f'attachment={attachment:.2f}, '
        f'regulation_bonus={regulation_bonus:.2f}, '
        f'{len(praegungen)} Praegungen'
    )

    return block


def _extrahiere_rezessive(egon_id: str) -> dict:
    """Extrahiere rezessive Gene (Drives die nicht dominant sind).

    Fuer transgenerationale Vererbung (Gen3+).
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return {}

    drives = state.get('drives', {})
    from engine.state_validator import DNA_DEFAULTS
    dna_profile = state.get('dna_profile', 'DEFAULT')
    baselines = DNA_DEFAULTS.get(dna_profile, DNA_DEFAULTS.get('DEFAULT', {}))

    rezessive = {}
    for system in PANKSEPP_7:
        drive_val = drives.get(system, 0.3)
        baseline = baselines.get(system, 0.3)
        # Rezessiv = der "nicht-dominante" Wert
        if isinstance(drive_val, (int, float)) and isinstance(baseline, (int, float)):
            if abs(drive_val - baseline) < 0.1:
                rezessive[system] = round(drive_val, 3)

    return rezessive


# ================================================================
# Praegungen in Prompt einfuegen
# ================================================================

def praegungen_to_prompt(egon_id: str) -> str:
    """Generiert einen Prompt-Text aus aktiven Praegungen.

    Fuer Integration in prompt_builder_v2.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return ''

    epi = state.get('epigenetik', {})
    praegungen = epi.get('praegungen', [])
    if not praegungen:
        return ''

    aktive = [
        p for p in praegungen
        if p.get('status') in ('geerbt', 'ruhend', 'verinnerlicht')
        and p.get('staerke', 0) > 0.05
    ]
    if not aktive:
        return ''

    teile = []
    for p in aktive:
        staerke = p.get('staerke', 0)
        if staerke > 0.4:
            intensitaet = 'stark'
        elif staerke > 0.2:
            intensitaet = 'leicht'
        else:
            intensitaet = 'vage'
        text = p.get('text', '?')
        status = p.get('status', 'geerbt')

        if status == 'verinnerlicht':
            teile.append(f'- (eigene Ueberzeugung) {text}')
        else:
            teile.append(f'- ({intensitaet}) {text}')

    return '\n'.join(teile)
