"""Arbeitsspeicher-Decay — Ebbinghaus-Vergessen im Wachzustand (Patch 13).

Jeder Eintrag im Arbeitsspeicher hat eine Retention die ueber
die Zeit abnimmt: R = e^(-t/S)

  t = Stunden seit Erstellung/letztem Abruf
  S = Stabilitaetsfaktor:
      0.5 (Basis)
      + emotional_marker * 4.0
      + abruf_count * 0.8
      + prediction_error * 2.0
      * dna_mod

Unwichtiges verblasst in Stunden. Emotional Wichtiges haelt Tage.
(Ebbinghaus 1885; McGaugh 2000; Bjork 1994)

Speicherung: memory/arbeitsspeicher.yaml (strukturierte Eintraege)
Integration: Wird als Context-Filter genutzt (Patch 8 Thalamus).
"""

import math
import time
from datetime import datetime

from engine.organ_reader import read_yaml_organ, write_yaml_organ


# ================================================================
# Konstanten
# ================================================================

RETENTION_SCHWELLE = 0.10     # Unter 10%: Nicht mehr laden
LOESCH_SCHWELLE = 0.03        # Unter 3%: Aus Arbeitsspeicher loeschen
MAX_EINTRAEGE = 30            # Maximale Eintraege im Arbeitsspeicher
FLASHBULB_SCHWELLE = 0.85     # Patch 17: Marker darueber = Flashbulb Memory
FLASHBULB_RETENTION_FLOOR = 0.10  # Patch 17: Kann nicht tiefer fallen bis Nacht-Pulse
LAYER = 'memory'
FILENAME = 'arbeitsspeicher.yaml'


# ================================================================
# DNA-abhaengige Stabilitaets-Modifikatoren
# ================================================================

def dna_stabilitaets_mod(dna_profile: str, eintrag: dict) -> float:
    """DNA beeinflusst wie schnell verschiedene TYPEN von
    Erinnerungen vergessen werden.

    CARE-dominante EGONs: Soziale Erinnerungen stabiler (Oxytocin).
    SEEKING-dominante EGONs: Ueberraschungen stabiler.
    RAGE-dominante EGONs: Konflikte stabiler (nachtragend).
    PLAY-hoch: Alles verblasst etwas schneller (im Moment leben).
    """
    staerkstes = eintrag.get('staerkstes_system', '')
    pe = eintrag.get('prediction_error', 0.0)

    if dna_profile == 'CARE/PANIC':
        if staerkstes in ('CARE', 'PANIC'):
            return 1.30   # 30% stabiler
        return 0.95

    if dna_profile == 'SEEKING/PLAY':
        if pe > 0.3:
            return 1.25   # Ueberraschungen 25% stabiler
        return 0.85       # Rest 15% fluechtiger

    if dna_profile == 'RAGE/FEAR':
        if staerkstes == 'RAGE':
            return 1.40   # Wut vergisst man nicht leicht
        if staerkstes == 'FEAR':
            return 1.35   # Angst haftet
        return 0.95

    return 1.0  # DEFAULT


# ================================================================
# Retention berechnen (Ebbinghaus)
# ================================================================

def berechne_retention(
    eintrag: dict,
    jetzt: float | None = None,
    dna_profile: str = 'DEFAULT',
) -> float:
    """Berechnet die aktuelle Retention eines Eintrags.

    R = e^(-t/S)

    Args:
        eintrag: Arbeitsspeicher-Eintrag mit erstellt, letzter_abruf, etc.
        jetzt: Aktueller Unix-Timestamp (default: time.time()).
        dna_profile: DNA-Profil des EGON.

    Returns:
        Retention-Wert 0.0-1.0
    """
    if jetzt is None:
        jetzt = time.time()

    # Zeit seit Erstellung oder letztem Abruf (was neuer ist)
    erstellt = eintrag.get('erstellt', jetzt)
    letzter_abruf = eintrag.get('letzter_abruf', erstellt)
    letzter_zugriff = max(erstellt, letzter_abruf)
    t_stunden = max(0, (jetzt - letzter_zugriff) / 3600)

    # Stabilitaetsfaktor S
    marker = eintrag.get('emotional_marker', 0.2)
    abruf_count = eintrag.get('abruf_count', 0)
    pe = eintrag.get('prediction_error', 0.0)

    S = (
        0.5                     # Basis: 0.5 Stunden Halbwertszeit
        + marker * 4.0          # Marker 0.8 → S=3.7
        + abruf_count * 0.8     # Jeder Abruf: +0.8 Stabilitaet
        + pe * 2.0              # Hoher PE: +2.0 (Ueberraschung haftet)
    )

    # DNA-Modifikator
    S *= dna_stabilitaets_mod(dna_profile, eintrag)

    # Ebbinghaus
    retention = math.exp(-t_stunden / S)

    # Patch 13: Retrieval 0.7 Floor (Bjork 1994)
    # Kuerzlich abgerufene Erinnerungen: Retention springt auf mind. 0.7
    # Der Floor wird beim naechsten Abruf gesetzt und zerfaellt dann wieder
    # (aber langsamer, weil abruf_count hoeher → S hoeher)
    retention_floor = eintrag.get('_retention_floor', 0.0)
    if retention_floor > 0 and retention < retention_floor:
        retention = retention_floor
        # Floor abbauen: Bei naechster Berechnung etwas senken
        # Damit es kein permanenter Halt ist
        eintrag['_retention_floor'] = round(max(0.0, retention_floor - 0.05), 2)

    # Patch 17: Flashbulb Memory Protection
    # Erinnerungen mit marker > 0.85: Retention-Floor bei 0.10
    # Koennen nicht tiefer fallen bis Nacht-Pulse konsolidiert
    # Brown & Kulik 1977: Traumatische Erinnerungen vergisst man nicht
    if marker > FLASHBULB_SCHWELLE and not eintrag.get('nacht_rettung'):
        retention = max(retention, FLASHBULB_RETENTION_FLOOR)

    return round(retention, 4)


# ================================================================
# Arbeitsspeicher laden mit Decay-Filter
# ================================================================

def lade_arbeitsspeicher(
    egon_id: str,
    max_eintraege: int = 15,
) -> list[dict]:
    """Laedt Arbeitsspeicher-Eintraege mit Retention ueber Schwelle.

    Berechnet Retention fuer jeden Eintrag und filtert.
    Sortiert nach Retention (hoechste zuerst).

    Returns:
        Liste von Eintraegen mit berechneter _retention.
    """
    data = read_yaml_organ(egon_id, LAYER, FILENAME)
    if not data:
        return []

    eintraege = data.get('eintraege', [])
    if not eintraege:
        return []

    # DNA-Profil laden
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    dna_profile = state.get('dna_profile', 'DEFAULT') if state else 'DEFAULT'

    jetzt = time.time()
    aktiv = []

    for eintrag in eintraege:
        if not isinstance(eintrag, dict):
            continue
        r = berechne_retention(eintrag, jetzt, dna_profile)
        if r > RETENTION_SCHWELLE:
            eintrag['_retention'] = r
            aktiv.append(eintrag)

    # Sortieren: Hoechste Retention zuerst
    aktiv.sort(key=lambda e: e['_retention'], reverse=True)

    return aktiv[:max_eintraege]


def arbeitsspeicher_to_prompt(egon_id: str, max_eintraege: int = 10) -> str:
    """Erzeugt einen Prompt-Text aus aktiven Arbeitsspeicher-Eintraegen.

    Fuer Integration in prompt_builder_v2.
    """
    eintraege = lade_arbeitsspeicher(egon_id, max_eintraege)
    if not eintraege:
        return ''

    teile = []
    for e in eintraege:
        zusammenfassung = e.get('zusammenfassung', '')
        retention = e.get('_retention', 0)
        # Frische-Indikator: Je frischer, desto praesenter
        if retention > 0.7:
            frische = 'klar'
        elif retention > 0.3:
            frische = 'etwas verschwommen'
        else:
            frische = 'vage'
        teile.append(f'- ({frische}) {zusammenfassung}')

    return '\n'.join(teile)


# ================================================================
# Eintrag hinzufuegen
# ================================================================

def speichere_arbeitsspeicher_eintrag(
    egon_id: str,
    zusammenfassung: str,
    emotional_marker: float = 0.2,
    prediction_error: float = 0.0,
    partner: str = '',
    cue_tags: list[str] | None = None,
    staerkstes_system: str = '',
) -> None:
    """Fuegt einen neuen Eintrag zum Arbeitsspeicher hinzu.

    Wird nach jedem Gespraech aufgerufen (im Post-Processing).
    """
    data = read_yaml_organ(egon_id, LAYER, FILENAME)
    if not data:
        data = {'eintraege': []}

    eintraege = data.get('eintraege', [])

    jetzt = time.time()
    neuer_eintrag = {
        'zusammenfassung': zusammenfassung,
        'emotional_marker': round(emotional_marker, 3),
        'prediction_error': round(prediction_error, 3),
        'erstellt': int(jetzt),
        'letzter_abruf': int(jetzt),
        'abruf_count': 0,
        'partner': partner,
        'cue_tags': cue_tags or [],
        'staerkstes_system': staerkstes_system,
    }

    eintraege.append(neuer_eintrag)

    # Maximal MAX_EINTRAEGE behalten
    if len(eintraege) > MAX_EINTRAEGE:
        # Aelteste mit niedrigster Retention entfernen
        dna_profile = 'DEFAULT'
        try:
            state = read_yaml_organ(egon_id, 'core', 'state.yaml')
            dna_profile = state.get('dna_profile', 'DEFAULT') if state else 'DEFAULT'
        except Exception:
            pass
        for e in eintraege:
            e['_sort_r'] = berechne_retention(e, jetzt, dna_profile)
        eintraege.sort(key=lambda e: e.get('_sort_r', 0))
        # Niedrigste Retention entfernen
        eintraege = eintraege[len(eintraege) - MAX_EINTRAEGE:]
        # _sort_r aufraumen
        for e in eintraege:
            e.pop('_sort_r', None)

    data['eintraege'] = eintraege
    write_yaml_organ(egon_id, LAYER, FILENAME, data)


# ================================================================
# Abruf-Stabilisierung (Retrieval Practice)
# ================================================================

def stabilisiere_abruf(egon_id: str, eintrag_index: int) -> None:
    """Stabilisiert einen Eintrag durch Abruf.

    Wenn ein Eintrag durch Lichtbogen oder Gespraechsreferenz
    reaktiviert wird: abruf_count++ und letzter_abruf = jetzt.
    (Bjork 1994: Retrieval = Konsolidierung)
    """
    data = read_yaml_organ(egon_id, LAYER, FILENAME)
    if not data:
        return

    eintraege = data.get('eintraege', [])
    if eintrag_index < 0 or eintrag_index >= len(eintraege):
        return

    eintrag = eintraege[eintrag_index]
    eintrag['abruf_count'] = eintrag.get('abruf_count', 0) + 1
    eintrag['letzter_abruf'] = int(time.time())

    # Patch 13: Retrieval 0.7 Floor (Bjork 1994)
    # Reaktivierung springt Retention auf mindestens 0.7.
    # Danach beginnt Decay wieder, aber langsamer (weil S hoeher durch abruf_count).
    eintrag['_retention_floor'] = 0.7

    data['eintraege'] = eintraege
    write_yaml_organ(egon_id, LAYER, FILENAME, data)

    try:
        from engine.neuroplastizitaet import ne_emit
        ne_emit(egon_id, 'AKTIVIERUNG', 'hippocampus', 'praefrontal', label='Erinnerung stabilisiert', intensitaet=0.5, animation='pulse')
    except Exception:
        pass


def stabilisiere_nach_cue(egon_id: str, cue_woerter: list[str]) -> int:
    """Stabilisiert Eintraege deren cue_tags mit den Cue-Woertern matchen.

    Aufgerufen wenn ein Gespraech Themen beruehrt die im
    Arbeitsspeicher existieren.

    Returns:
        Anzahl stabilisierter Eintraege.
    """
    if not cue_woerter:
        return 0

    data = read_yaml_organ(egon_id, LAYER, FILENAME)
    if not data:
        return 0

    eintraege = data.get('eintraege', [])
    cues_lower = {w.lower() for w in cue_woerter}
    stabilisiert = 0
    jetzt = int(time.time())

    for eintrag in eintraege:
        tags = eintrag.get('cue_tags', [])
        if any(t.lower() in cues_lower for t in tags):
            eintrag['abruf_count'] = eintrag.get('abruf_count', 0) + 1
            eintrag['letzter_abruf'] = jetzt
            # Patch 13: Retrieval 0.7 Floor
            eintrag['_retention_floor'] = 0.7
            stabilisiert += 1

    if stabilisiert:
        data['eintraege'] = eintraege
        write_yaml_organ(egon_id, LAYER, FILENAME, data)
        print(
            f'[decay] {egon_id}: {stabilisiert} Eintraege stabilisiert '
            f'durch Cues: {list(cues_lower)[:5]}'
        )

    return stabilisiert


# ================================================================
# Periodisches Aufraumen
# ================================================================

def aufraumen(egon_id: str) -> int:
    """Entfernt Eintraege unter der Loschschwelle.

    Diese Eintraege sind "vergessen" — sie existieren vielleicht
    noch in recent_memory.md, aber nicht mehr im aktiven
    Arbeitsspeicher.

    Returns:
        Anzahl entfernter Eintraege.
    """
    data = read_yaml_organ(egon_id, LAYER, FILENAME)
    if not data:
        return 0

    eintraege = data.get('eintraege', [])
    if not eintraege:
        return 0

    # DNA-Profil laden
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    dna_profile = state.get('dna_profile', 'DEFAULT') if state else 'DEFAULT'

    jetzt = time.time()
    vorher = len(eintraege)

    eintraege = [
        e for e in eintraege
        if isinstance(e, dict) and berechne_retention(e, jetzt, dna_profile) > LOESCH_SCHWELLE
    ]

    geloescht = vorher - len(eintraege)

    if geloescht > 0:
        data['eintraege'] = eintraege
        write_yaml_organ(egon_id, LAYER, FILENAME, data)
        print(
            f'[decay] {egon_id}: {geloescht} Eintraege vergessen, '
            f'{len(eintraege)} verbleiben'
        )

    return geloescht


# ================================================================
# Nacht-Rettung: Emotional wichtige Eintraege vor dem Vergessen retten
# ================================================================

def nacht_rettung(egon_id: str) -> int:
    """Vor dem Nacht-Pulse: Rette emotional wichtige Eintraege
    die fast vergessen wurden.

    Wenn Retention < 0.10 aber emotional_marker > 0.6:
    → abruf_count++ (kuenstliche Stabilisierung durch "Traum-Abruf")

    Returns:
        Anzahl geretteter Eintraege.
    """
    data = read_yaml_organ(egon_id, LAYER, FILENAME)
    if not data:
        return 0

    eintraege = data.get('eintraege', [])
    if not eintraege:
        return 0

    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    dna_profile = state.get('dna_profile', 'DEFAULT') if state else 'DEFAULT'

    jetzt = time.time()
    gerettet = 0

    for eintrag in eintraege:
        if not isinstance(eintrag, dict):
            continue
        r = berechne_retention(eintrag, jetzt, dna_profile)
        marker = eintrag.get('emotional_marker', 0)

        if r < RETENTION_SCHWELLE and marker > 0.6:
            # Fast vergessen aber emotional wichtig → retten
            eintrag['abruf_count'] = eintrag.get('abruf_count', 0) + 1
            eintrag['letzter_abruf'] = int(jetzt)
            eintrag['nacht_rettung'] = True
            gerettet += 1
            # Patch 17: Flashbulb-Rettung loggen
            if marker > FLASHBULB_SCHWELLE:
                try:
                    from engine.kalibrierung import log_decision
                    log_decision(egon_id, 'decay', 'flashbulb_nacht_rettung', {
                        'marker': round(marker, 3), 'retention': round(r, 4),
                        'summary': str(eintrag.get('zusammenfassung', ''))[:60],
                    })
                except Exception:
                    pass

    if gerettet:
        data['eintraege'] = eintraege
        write_yaml_organ(egon_id, LAYER, FILENAME, data)
        print(f'[decay] {egon_id}: {gerettet} Eintraege durch Nacht-Rettung stabilisiert')

    return gerettet
