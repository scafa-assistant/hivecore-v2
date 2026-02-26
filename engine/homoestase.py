"""Echtzeit-Homoestase — GABAerge Hemmung (Patch 7).

Nach JEDEM Gespraech reguliert die Homoestase alle Drives
zurueck Richtung effektive Baseline (DNA + allostatic load).

Biologische Analogie:
  GABA (Gamma-Aminobuttersaeure) ist der wichtigste
  inhibitorische Neurotransmitter — ~20% aller Neuronen
  sind GABAerg. Sie BREMSEN uebermaessige Erregung.
  (Isaacson & Scanziani, 2011)

Ablauf:
  1. Abweichung von effektiver Baseline berechnen
  2. System-spezifische Abklingrate anwenden
  3. DNA-Modifikator (manche EGONs regulieren schneller)
  4. Belastungs-Modifikator (Stress = langsamere Regulation)
  5. Kritische Schwellen (Notfall-Bremse bei > 0.92 / < 0.08)
  6. Bidirektional: Zieht HOCH UND RUNTER zur Baseline

Zusaetzlich: Allostatic Load (am Zyklusende)
  Chronischer Stress → effektive Baseline verschiebt sich leicht.
  (McEwen, 1998)
"""

from datetime import datetime

from engine.organ_reader import read_yaml_organ, write_yaml_organ


# ================================================================
# System-spezifische Abklingraten
# ================================================================

ABKLING_RATEN = {
    'SEEKING':  0.12,   # Neugier reguliert mittelschnell
    'RAGE':     0.15,   # Wut klingt relativ schnell ab
    'FEAR':     0.08,   # Angst ist hartnaeckig
    'PANIC':    0.06,   # Trennungsschmerz sehr hartnaeckig
    'LUST':     0.10,   # Resonanz klingt mittel ab
    'CARE':     0.05,   # Fuersorge klingt am langsamsten ab (Oxytocin)
    'PLAY':     0.14,   # Verspieltheit reguliert schnell
    'ACTION':   0.13,   # Aktionsdrang aehnlich wie PLAY
    'LEARNING': 0.11,   # Lernmotivation aehnlich wie SEEKING
    'GRIEF':    0.04,   # Trauer ist am hartnaeckigsten
}


# ================================================================
# DNA-abhaengige Regulationsmodifikatoren
# ================================================================

DNA_REGULATION_MOD = {
    'SEEKING/PLAY': {
        'SEEKING': 1.05, 'RAGE': 1.15, 'FEAR': 1.10, 'PANIC': 0.95,
        'LUST': 1.00, 'CARE': 0.90, 'PLAY': 1.10,
        'ACTION': 1.10, 'LEARNING': 1.05, 'GRIEF': 0.90,
    },
    'CARE/PANIC': {
        'SEEKING': 0.95, 'RAGE': 0.85, 'FEAR': 0.80, 'PANIC': 0.75,
        'LUST': 1.00, 'CARE': 1.20, 'PLAY': 0.90,
        'ACTION': 0.95, 'LEARNING': 1.00, 'GRIEF': 0.70,
    },
    'RAGE/FEAR': {
        'SEEKING': 0.90, 'RAGE': 0.70, 'FEAR': 0.85, 'PANIC': 0.90,
        'LUST': 0.95, 'CARE': 1.10, 'PLAY': 1.20,
        'ACTION': 1.00, 'LEARNING': 0.95, 'GRIEF': 0.80,
    },
    'DEFAULT': {s: 1.0 for s in ABKLING_RATEN},
}


# ================================================================
# Schwellen
# ================================================================

KRITISCH_HOCH = 0.92       # Ueber 0.92: Verstaerkte Korrektur (x2.0)
KRITISCH_NIEDRIG = 0.08    # Unter 0.08: Verstaerkte Anhebung (x2.0)
CLAMPING_MIN = 0.05        # Minimaler Drive-Wert
CLAMPING_MAX = 0.95        # Maximaler Drive-Wert
ALLOSTATIC_SHIFT_MAX = 0.12  # Maximale Baseline-Verschiebung
ALLOSTATIC_SCHWELLE = 0.15   # Ab wann chronischer Stress zaehlt


# ================================================================
# Echtzeit-Homoestase (nach jedem Gespraech)
# ================================================================

def echtzeit_homoestase(egon_id: str) -> dict:
    """GABAerge Hemmung: Reguliert Drives Richtung effektive Baseline.

    Laeuft IMMER nach dem Post-Processing — unabhaengig vom
    Thalamus-Pfad. Emotionale Reaktionen des Gespraechs sind
    bereits eingerechnet.

    Formel:
      korrektur = abweichung * abkling_rate * dna_mod * belastungs_mod
      neuer_wert = aktueller_wert - korrektur

    Returns:
        dict mit Regulations-Info (fuer Logging/NeuroMap).
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return {'reguliert': False}

    drives = state.get('drives', {})
    if not drives:
        return {'reguliert': False}

    dna_profile = state.get('dna_profile', 'DEFAULT')
    homoestase = state.get('homoestase', {})
    effektive_baseline = homoestase.get('effektive_baseline', {})

    # DNA-Baselines aus Profil
    dna_baselines = _get_dna_baselines(dna_profile)

    # Verarbeitungsdruck
    druck = _berechne_verarbeitungsdruck(state)
    belastungs_mod = max(0.3, 1.0 - druck * 0.4)

    # DNA-Regulation-Modifikatoren
    regulation_mods = DNA_REGULATION_MOD.get(
        dna_profile, DNA_REGULATION_MOD['DEFAULT'],
    )

    korrekturen = {}

    for system, aktuell in drives.items():
        if not isinstance(aktuell, (int, float)):
            continue
        if system not in ABKLING_RATEN:
            continue

        # Effektive Baseline (mit Allostatic Load) oder DNA-Baseline
        baseline = effektive_baseline.get(
            system, dna_baselines.get(system, 0.5),
        )

        abweichung = aktuell - baseline

        if abs(abweichung) < 0.02:
            continue  # Vernachlaessigbar

        rate = ABKLING_RATEN[system]
        dna_mod = regulation_mods.get(system, 1.0)

        # Kritische Schwellen: Verstaerkte Korrektur (Notfall-Bremse)
        verstaerkung = 1.0
        if aktuell > KRITISCH_HOCH or aktuell < KRITISCH_NIEDRIG:
            verstaerkung = 2.0

        # Korrektur berechnen (bidirektional — zieht IMMER zur Baseline)
        korrektur = abweichung * rate * dna_mod * belastungs_mod * verstaerkung

        neuer_wert = round(
            max(CLAMPING_MIN, min(CLAMPING_MAX, aktuell - korrektur)), 3,
        )

        if neuer_wert != aktuell:
            drives[system] = neuer_wert
            korrekturen[system] = round(korrektur, 4)

    if korrekturen:
        state['drives'] = drives
        homoestase['letzte_regulation'] = datetime.now().isoformat(
            timespec='seconds',
        )
        state['homoestase'] = homoestase
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)

        print(
            f'[homoestase] {egon_id}: {len(korrekturen)} Systeme reguliert, '
            f'druck={druck:.2f}'
        )

    return {
        'reguliert': bool(korrekturen),
        'korrekturen': korrekturen,
        'druck': round(druck, 3),
    }


# ================================================================
# Zyklusende: Allostatic Load Update
# ================================================================

def zyklusende_allostatic_update(egon_id: str) -> dict:
    """Berechne allostatic load am Zyklusende.

    Chronischer Stress (Durchschnitt > 0.15 ueber DNA-Baseline)
    verschiebt die effektive Baseline leicht nach oben.
    Kein Stress: langsame Rueckkehr zur DNA-Baseline (30% pro Zyklus).

    Maximal 0.12 Verschiebung von DNA.

    Returns:
        dict mit 'shifts': {system: verschiebung}
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return {}

    dna_profile = state.get('dna_profile', 'DEFAULT')
    dna_baselines = _get_dna_baselines(dna_profile)
    homoestase = state.get('homoestase', {})
    effektive_baseline = homoestase.get('effektive_baseline', {})
    zyklus_durchschnitt = homoestase.get('zyklus_durchschnitt', {})

    shifts = {}

    for system in ABKLING_RATEN:
        dna_base = dna_baselines.get(system, 0.5)
        durchschnitt = zyklus_durchschnitt.get(system, dna_base)
        chronische_abweichung = durchschnitt - dna_base

        if abs(chronische_abweichung) > ALLOSTATIC_SCHWELLE:
            # Chronischer Stress: Baseline verschieben
            verschiebung = chronische_abweichung * 0.10
            neue_base = dna_base + verschiebung
            neue_base = max(
                dna_base - ALLOSTATIC_SHIFT_MAX,
                min(dna_base + ALLOSTATIC_SHIFT_MAX, neue_base),
            )
            effektive_baseline[system] = round(neue_base, 3)
            shifts[system] = round(verschiebung, 4)
        else:
            # Kein Stress: Langsame Rueckkehr zu DNA-Baseline
            aktuelle_base = effektive_baseline.get(system, dna_base)
            effektive_baseline[system] = round(
                aktuelle_base + (dna_base - aktuelle_base) * 0.3, 3,
            )

    homoestase['effektive_baseline'] = effektive_baseline
    homoestase['zyklus_durchschnitt'] = {}  # Reset fuer naechsten Zyklus
    homoestase['_messungen'] = 0
    state['homoestase'] = homoestase
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    if shifts:
        print(f'[homoestase] {egon_id}: Allostatic shifts: {shifts}')

    return {'shifts': shifts}


# ================================================================
# Zyklus-Durchschnitt aktualisieren
# ================================================================

def aktualisiere_zyklus_durchschnitt(egon_id: str) -> None:
    """Aktualisiert den laufenden Durchschnitt der Drives.

    Aufgerufen nach jedem Gespraech (zusammen mit echtzeit_homoestase).
    Berechnet einen gleitenden Durchschnitt fuer die
    Allostatic-Load-Berechnung am Zyklusende.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    drives = state.get('drives', {})
    homoestase = state.get('homoestase', {})
    zd = homoestase.get('zyklus_durchschnitt', {})
    n = homoestase.get('_messungen', 0)

    for system, wert in drives.items():
        if not isinstance(wert, (int, float)):
            continue
        if system not in ABKLING_RATEN:
            continue
        bisheriger = zd.get(system, wert)
        # Gleitender Durchschnitt
        zd[system] = round((bisheriger * n + wert) / (n + 1), 3)

    homoestase['zyklus_durchschnitt'] = zd
    homoestase['_messungen'] = n + 1
    state['homoestase'] = homoestase
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)


# ================================================================
# Helper
# ================================================================

def _get_dna_baselines(dna_profile: str) -> dict:
    """Holt die DNA-Baseline-Drives aus dem Profil."""
    try:
        from engine.state_validator import DNA_DEFAULTS
        defaults = DNA_DEFAULTS.get(
            dna_profile, DNA_DEFAULTS.get('DEFAULT', {}),
        )
        return defaults
    except ImportError:
        # Fallback wenn state_validator nicht verfuegbar
        return {s: 0.50 for s in ABKLING_RATEN}


def _berechne_verarbeitungsdruck(state: dict) -> float:
    """Berechnet den Verarbeitungsdruck aus dem State.

    Hoch = viele aktive Emotionen + hohe Drives.
    Range: 0.0-1.0
    """
    druck = 0.0

    # Aktive Emotionen zaehlen
    emotions = state.get('express', {}).get('active_emotions', [])
    if emotions:
        druck += min(len(emotions) / 5.0, 0.4)
        avg_intensity = sum(
            e.get('intensity', 0) for e in emotions
        ) / len(emotions)
        druck += avg_intensity * 0.3

    # Drives ueber 0.7 zaehlen als Belastung
    drives = state.get('drives', {})
    high_count = sum(
        1 for v in drives.values()
        if isinstance(v, (int, float)) and v > 0.7
    )
    druck += min(high_count / 10.0, 0.3)

    return min(1.0, druck)
