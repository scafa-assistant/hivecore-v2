"""State Validator — Patch 9 Schicht 1: Validierung & Auto-Repair.

Prueft state.yaml gegen das erwartete Schema:
  - Pflichtfelder vorhanden?
  - Typen korrekt?
  - Wertebereiche eingehalten?
  - Logische Konsistenz zwischen Feldern?

Bei reparablen Fehlern: Auto-Repair mit DNA-Baseline als Fallback.
Bei nicht-reparablen Fehlern: StateValidationError → Checkpoint-Rollback.

Biologische Analogie:
  Wie die Blut-Hirn-Schranke fehlerhafte Signale filtert,
  prueft der Validator jeden State-Load auf Integritaet.
"""

import time
from datetime import datetime

# ================================================================
# Exceptions
# ================================================================

class StateValidationError(Exception):
    """State hat nicht-reparierbare Fehler."""
    def __init__(self, fehler_liste):
        self.fehler = fehler_liste
        super().__init__(f"{len(fehler_liste)} Validierungsfehler")


class StateCorruptionError(Exception):
    """State-Datei ist korrupt (YAML kaputt, leer, etc.)."""
    pass


# ================================================================
# Schema — angepasst an die ECHTE state.yaml Struktur
# ================================================================

# Die 10 Panksepp-Systeme (EGON-spezifisch)
DRIVE_SYSTEMS = [
    'SEEKING', 'ACTION', 'LEARNING', 'CARE', 'PLAY',
    'FEAR', 'RAGE', 'GRIEF', 'LUST', 'PANIC',
]

# Die 7 klassischen Panksepp-Systeme (fuer Homoestase/Epigenetik)
PANKSEPP_7 = ['SEEKING', 'RAGE', 'FEAR', 'PANIC', 'LUST', 'CARE', 'PLAY']

STATE_SCHEMA = {
    # --- Top-Level Felder ---
    'dna_profile': {
        'typ': str, 'pflicht': True,
        'werte': ['DEFAULT', 'SEEKING/PLAY', 'CARE/PANIC', 'RAGE/FEAR'],
    },
    'geschlecht': {
        'typ': str, 'pflicht': True,
        'werte': ['M', 'F'],
    },

    # --- Drives (10 Panksepp-Systeme) ---
    'drives': {
        'typ': dict, 'pflicht': True,
        'kinder': {
            system: {'typ': float, 'min': 0.0, 'max': 1.0, 'pflicht': True}
            for system in DRIVE_SYSTEMS
        },
    },

    # --- Survive (3 Grundbeduerfnisse) ---
    'survive': {
        'typ': dict, 'pflicht': True,
        'kinder': {
            'energy':    {'typ': dict, 'pflicht': True, 'hat_value': True},
            'safety':    {'typ': dict, 'pflicht': True, 'hat_value': True},
            'coherence': {'typ': dict, 'pflicht': True, 'hat_value': True},
        },
    },

    # --- Thrive (4 Wachstumsbeduerfnisse) ---
    'thrive': {
        'typ': dict, 'pflicht': True,
        'kinder': {
            'belonging':   {'typ': dict, 'pflicht': True, 'hat_value': True},
            'trust_owner': {'typ': dict, 'pflicht': True, 'hat_value': True},
            'mood':        {'typ': dict, 'pflicht': True, 'hat_value': True},
            'purpose':     {'typ': dict, 'pflicht': True, 'hat_value': True},
        },
    },

    # --- Express (aktive Emotionen) ---
    'express': {
        'typ': dict, 'pflicht': True,
        'kinder': {
            'active_emotions': {'typ': list, 'pflicht': True},
        },
    },

    # --- Self Assessment ---
    'self_assessment': {
        'typ': dict, 'pflicht': False,
    },

    # --- Emotional Gravity ---
    'emotional_gravity': {
        'typ': dict, 'pflicht': False,
        'kinder': {
            'baseline_mood': {'typ': float, 'min': 0.0, 'max': 1.0, 'pflicht': False},
        },
    },

    # --- Processing ---
    'processing': {
        'typ': dict, 'pflicht': False,
    },

    # --- Zirkadian (Patch 2) ---
    'zirkadian': {
        'typ': dict, 'pflicht': False,
    },

    # --- Somatic Gate (Patch 1) ---
    'somatic_gate': {
        'typ': dict, 'pflicht': False,
    },

    # --- Pairing (Patch 6) ---
    'pairing': {
        'typ': dict, 'pflicht': False,
    },

    # --- Identitaet (Patch 6 Naming) ---
    'identitaet': {
        'typ': dict, 'pflicht': False,
    },

    # --- Felder die durch spaetere Patches hinzukommen ---
    # Werden als optional markiert und erst nach Implementierung pflicht
    'homoestase': {'typ': dict, 'pflicht': False},   # Patch 7
    'thalamus':   {'typ': dict, 'pflicht': False},    # Patch 8
    'metacognition': {'typ': dict, 'pflicht': False},  # Patch 11
    'epigenetik': {'typ': dict, 'pflicht': False},     # Patch 10
    'interaktion': {'typ': dict, 'pflicht': False},    # Patch 12
    'neuroplastizitaet': {'typ': dict, 'pflicht': False},  # Patch 16
}


# ================================================================
# Validierung
# ================================================================

def validiere_state(state_dict, schema=None):
    """Pruefe state.yaml gegen das Schema.

    Args:
        state_dict: Geparstes state.yaml als dict.
        schema: Optionales Custom-Schema (Default: STATE_SCHEMA).

    Returns:
        Liste von Fehler-Strings (leer = alles ok).
    """
    if schema is None:
        schema = STATE_SCHEMA

    fehler = []

    if not isinstance(state_dict, dict):
        return ['STATE ist kein dict']

    for feld, regeln in schema.items():
        wert = state_dict.get(feld)

        # Pflichtfeld fehlt
        if regeln.get('pflicht') and wert is None:
            fehler.append(f'FEHLT: {feld}')
            continue

        if wert is None:
            continue  # Optionales Feld, nicht vorhanden

        # Typ-Pruefung
        erwartet = regeln['typ']
        if erwartet == float and isinstance(wert, int):
            wert = float(wert)
            state_dict[feld] = wert
        elif not isinstance(wert, erwartet):
            fehler.append(
                f'TYP: {feld} ist {type(wert).__name__}, '
                f'erwartet {erwartet.__name__}'
            )
            continue

        # Wertebereich (numerisch)
        if 'min' in regeln and isinstance(wert, (int, float)):
            if wert < regeln['min']:
                fehler.append(f'RANGE: {feld}={wert} < min={regeln["min"]}')
        if 'max' in regeln and isinstance(wert, (int, float)):
            if wert > regeln['max']:
                fehler.append(f'RANGE: {feld}={wert} > max={regeln["max"]}')

        # Erlaubte Werte
        if 'werte' in regeln and wert not in regeln['werte']:
            fehler.append(f'WERT: {feld}={wert}, erlaubt: {regeln["werte"]}')

        # Verschachtelte Objekte
        if 'kinder' in regeln and isinstance(wert, dict):
            for k_feld, k_regeln in regeln['kinder'].items():
                k_wert = wert.get(k_feld)

                if k_regeln.get('pflicht') and k_wert is None:
                    fehler.append(f'FEHLT: {feld}.{k_feld}')
                    continue

                if k_wert is None:
                    continue

                # hat_value: Survive/Thrive Sub-Dicts mit {value: float, verbal: str}
                if k_regeln.get('hat_value'):
                    if isinstance(k_wert, dict):
                        v = k_wert.get('value')
                        if v is None:
                            fehler.append(f'FEHLT: {feld}.{k_feld}.value')
                        elif isinstance(v, int):
                            k_wert['value'] = float(v)
                        elif not isinstance(v, float):
                            fehler.append(
                                f'TYP: {feld}.{k_feld}.value ist '
                                f'{type(v).__name__}, erwartet float'
                            )
                        elif v < 0.0 or v > 1.0:
                            fehler.append(
                                f'RANGE: {feld}.{k_feld}.value={v} '
                                f'nicht in [0.0, 1.0]'
                            )
                    else:
                        fehler.append(
                            f'TYP: {feld}.{k_feld} ist '
                            f'{type(k_wert).__name__}, erwartet dict'
                        )
                    continue

                # Normale Typ/Range-Pruefung fuer Kinder
                k_typ = k_regeln.get('typ')
                if k_typ:
                    if k_typ == float and isinstance(k_wert, int):
                        k_wert = float(k_wert)
                        wert[k_feld] = k_wert
                    elif not isinstance(k_wert, k_typ):
                        fehler.append(
                            f'TYP: {feld}.{k_feld} ist '
                            f'{type(k_wert).__name__}, erwartet {k_typ.__name__}'
                        )
                        continue

                if 'min' in k_regeln and isinstance(k_wert, (int, float)):
                    if k_wert < k_regeln['min']:
                        fehler.append(
                            f'RANGE: {feld}.{k_feld}={k_wert} < {k_regeln["min"]}'
                        )
                if 'max' in k_regeln and isinstance(k_wert, (int, float)):
                    if k_wert > k_regeln['max']:
                        fehler.append(
                            f'RANGE: {feld}.{k_feld}={k_wert} > {k_regeln["max"]}'
                        )

    return fehler


def validiere_konsistenz(state_dict):
    """Pruefe logische Konsistenz ZWISCHEN Feldern.

    Returns:
        Liste von Fehler-Strings (leer = alles konsistent).
    """
    fehler = []

    drives = state_dict.get('drives', {})

    # Drives muessen alle vorhanden sein
    for system in DRIVE_SYSTEMS:
        if system not in drives:
            fehler.append(f'KONSISTENZ: drives.{system} fehlt')

    # Survive/Thrive Values muessen plausibel sein
    survive = state_dict.get('survive', {})
    for key in ['energy', 'safety', 'coherence']:
        sub = survive.get(key, {})
        if isinstance(sub, dict):
            v = sub.get('value')
            if v is not None and isinstance(v, (int, float)):
                if v == 0.0:
                    # Energy/Safety/Coherence bei exakt 0.0 ist verdaechtig
                    fehler.append(
                        f'KONSISTENZ: survive.{key}.value=0.0 '
                        f'(verdaechtig niedrig)'
                    )

    # Homoestase-Konsistenz (wenn vorhanden, Patch 7)
    homoestase = state_dict.get('homoestase', {})
    if homoestase:
        eff_base = homoestase.get('effektive_baseline', {})
        for system in PANKSEPP_7:
            base_wert = eff_base.get(system)
            drive_wert = drives.get(system)
            if base_wert is not None and drive_wert is not None:
                # Effektive Baseline darf max 0.15 von DNA abweichen
                # (DNA-Proxy: dna_profile Defaults)
                if abs(base_wert - drive_wert) > 0.40:
                    fehler.append(
                        f'KONSISTENZ: homoestase.{system}={base_wert:.3f} '
                        f'weicht stark von drives.{system}={drive_wert:.3f} ab'
                    )

    # Express: Emotionen muessen gueltige Struktur haben
    express = state_dict.get('express', {})
    emotions = express.get('active_emotions', [])
    if isinstance(emotions, list):
        for i, emo in enumerate(emotions):
            if not isinstance(emo, dict):
                fehler.append(f'KONSISTENZ: express.active_emotions[{i}] ist kein dict')
                continue
            if 'type' not in emo:
                fehler.append(f'KONSISTENZ: express.active_emotions[{i}].type fehlt')
            intensity = emo.get('intensity')
            if intensity is not None:
                if not isinstance(intensity, (int, float)):
                    fehler.append(
                        f'KONSISTENZ: express.active_emotions[{i}].intensity '
                        f'ist {type(intensity).__name__}'
                    )
                elif intensity < 0.0 or intensity > 1.0:
                    fehler.append(
                        f'KONSISTENZ: express.active_emotions[{i}].intensity='
                        f'{intensity} nicht in [0.0, 1.0]'
                    )

    return fehler


# ================================================================
# Auto-Repair
# ================================================================

# DNA-Defaults pro Profil (Drives-Baselines)
DNA_DEFAULTS = {
    'DEFAULT': {
        'SEEKING': 0.60, 'ACTION': 0.50, 'LEARNING': 0.55,
        'CARE': 0.50, 'PLAY': 0.55, 'FEAR': 0.40,
        'RAGE': 0.30, 'GRIEF': 0.35, 'LUST': 0.40, 'PANIC': 0.30,
    },
    'SEEKING/PLAY': {
        'SEEKING': 0.75, 'ACTION': 0.60, 'LEARNING': 0.65,
        'CARE': 0.45, 'PLAY': 0.70, 'FEAR': 0.35,
        'RAGE': 0.30, 'GRIEF': 0.30, 'LUST': 0.45, 'PANIC': 0.25,
    },
    'CARE/PANIC': {
        'SEEKING': 0.50, 'ACTION': 0.45, 'LEARNING': 0.50,
        'CARE': 0.75, 'PLAY': 0.45, 'FEAR': 0.50,
        'RAGE': 0.25, 'GRIEF': 0.45, 'LUST': 0.35, 'PANIC': 0.55,
    },
    'RAGE/FEAR': {
        'SEEKING': 0.55, 'ACTION': 0.55, 'LEARNING': 0.50,
        'CARE': 0.40, 'PLAY': 0.40, 'FEAR': 0.65,
        'RAGE': 0.60, 'GRIEF': 0.40, 'LUST': 0.35, 'PANIC': 0.45,
    },
}


def auto_repair(state_dict, fehler_liste):
    """Versuche automatische Reparatur fuer bekannte Fehler-Typen.

    Repariert:
      - Fehlende Drive-Werte → DNA-Baseline einsetzen
      - Werte ausserhalb Range → Clamping
      - Fehlende Survive/Thrive Sub-Dicts → Defaults
      - Fehlende active_emotions → leere Liste

    Args:
        state_dict: Der (moeglicherweise defekte) State.
        fehler_liste: Liste von Fehler-Strings aus validiere_state().

    Returns:
        (reparierter_state, liste_der_reparaturen)
    """
    reparaturen = []
    profil = state_dict.get('dna_profile', 'DEFAULT')
    defaults = DNA_DEFAULTS.get(profil, DNA_DEFAULTS['DEFAULT'])

    for fehler in fehler_liste:

        # --- Fehlende Drives → DNA-Baseline ---
        if fehler.startswith('FEHLT: drives.'):
            system = fehler.split('.')[-1]
            baseline = defaults.get(system, 0.50)
            state_dict.setdefault('drives', {})[system] = baseline
            reparaturen.append(f'REPARIERT: drives.{system} = DNA-Baseline {baseline}')

        # --- Fehlende Drives (ganzes dict) ---
        elif fehler == 'FEHLT: drives':
            # v3: Nicht reparieren wenn lebenskraft vorhanden (Normalisierung fehlt)
            if 'lebenskraft' in state_dict:
                reparaturen.append('SKIP: drives fehlt aber lebenskraft vorhanden (v3)')
            else:
                state_dict['drives'] = dict(defaults)
                reparaturen.append('REPARIERT: drives komplett aus DNA-Baseline')

        # --- Drive-Werte ausserhalb Range → Clamping ---
        elif fehler.startswith('RANGE: drives.'):
            teile = fehler.split()
            pfad_wert = teile[1]  # z.B. "drives.SEEKING=1.2"
            pfad = pfad_wert.split('=')[0]
            system = pfad.split('.')[-1]
            if system in state_dict.get('drives', {}):
                wert = state_dict['drives'][system]
                state_dict['drives'][system] = max(0.0, min(1.0, float(wert)))
                reparaturen.append(f'REPARIERT: {pfad} geclampt auf [0.0, 1.0]')

        # --- Fehlende Survive-Felder → Defaults ---
        elif 'survive.' in fehler and 'FEHLT' in fehler:
            feld = fehler.split('.')[-1]
            survive_defaults = {
                'energy':    {'value': 0.50, 'verbal': 'neutral'},
                'safety':    {'value': 0.60, 'verbal': 'stabil'},
                'coherence': {'value': 0.50, 'verbal': 'neutral'},
            }
            if feld in survive_defaults:
                state_dict.setdefault('survive', {})[feld] = survive_defaults[feld]
                reparaturen.append(f'REPARIERT: survive.{feld} = Default')
            elif feld == 'value':
                # z.B. FEHLT: survive.energy.value — repariere den value-Key
                parent_feld = fehler.split('.')[1]
                if parent_feld in survive_defaults:
                    state_dict.setdefault('survive', {}).setdefault(
                        parent_feld, {}
                    )['value'] = survive_defaults[parent_feld]['value']
                    reparaturen.append(
                        f'REPARIERT: survive.{parent_feld}.value = Default'
                    )

        # --- Fehlende Thrive-Felder → Defaults ---
        elif 'thrive.' in fehler and 'FEHLT' in fehler:
            feld = fehler.split('.')[-1]
            thrive_defaults = {
                'belonging':   {'value': 0.40, 'verbal': 'suchend'},
                'trust_owner': {'value': 0.50, 'verbal': 'neutral'},
                'mood':        {'value': 0.50, 'verbal': 'neutral'},
                'purpose':     {'value': 0.50, 'verbal': 'unklar'},
            }
            if feld in thrive_defaults:
                state_dict.setdefault('thrive', {})[feld] = thrive_defaults[feld]
                reparaturen.append(f'REPARIERT: thrive.{feld} = Default')
            elif feld == 'value':
                parent_feld = fehler.split('.')[1]
                if parent_feld in thrive_defaults:
                    state_dict.setdefault('thrive', {}).setdefault(
                        parent_feld, {}
                    )['value'] = thrive_defaults[parent_feld]['value']
                    reparaturen.append(
                        f'REPARIERT: thrive.{parent_feld}.value = Default'
                    )

        # --- Fehlende Survive/Thrive als ganzes dict ---
        elif fehler == 'FEHLT: survive':
            if 'ueberleben' in state_dict:
                reparaturen.append('SKIP: survive fehlt aber ueberleben vorhanden (v3)')
            else:
                state_dict['survive'] = {
                    'energy':    {'value': 0.50, 'verbal': 'neutral'},
                    'safety':    {'value': 0.60, 'verbal': 'stabil'},
                    'coherence': {'value': 0.50, 'verbal': 'neutral'},
                }
                reparaturen.append('REPARIERT: survive komplett aus Defaults')

        elif fehler == 'FEHLT: thrive':
            if 'entfaltung' in state_dict:
                reparaturen.append('SKIP: thrive fehlt aber entfaltung vorhanden (v3)')
            else:
                state_dict['thrive'] = {
                    'belonging':   {'value': 0.40, 'verbal': 'suchend'},
                    'trust_owner': {'value': 0.50, 'verbal': 'neutral'},
                    'mood':        {'value': 0.50, 'verbal': 'neutral'},
                    'purpose':     {'value': 0.50, 'verbal': 'unklar'},
                }
                reparaturen.append('REPARIERT: thrive komplett aus Defaults')

        # --- Fehlende Express → leere Emotionsliste ---
        elif fehler == 'FEHLT: express':
            if 'empfindungen' in state_dict:
                reparaturen.append('SKIP: express fehlt aber empfindungen vorhanden (v3)')
            else:
                state_dict['express'] = {'active_emotions': []}
                reparaturen.append('REPARIERT: express = leere Emotionsliste')

        elif 'active_emotions' in fehler and 'FEHLT' in fehler:
            state_dict.setdefault('express', {})['active_emotions'] = []
            reparaturen.append('REPARIERT: express.active_emotions = []')

        # --- Fehlender dna_profile → DEFAULT (oder v3-Alias) ---
        elif fehler == 'FEHLT: dna_profile':
            if 'dna_profil' in state_dict:
                state_dict['dna_profile'] = state_dict['dna_profil']
                reparaturen.append(
                    f'REPARIERT: dna_profile = dna_profil ({state_dict["dna_profil"]})')
            else:
                state_dict['dna_profile'] = 'DEFAULT'
                reparaturen.append('REPARIERT: dna_profile = DEFAULT')

        # --- Fehlender geschlecht → kann nicht repariert werden ---
        # (bleibt in der Fehlerliste)

        # --- Survive/Thrive value ausserhalb Range → Clamping ---
        elif 'RANGE:' in fehler and '.value=' in fehler:
            # z.B. "RANGE: survive.energy.value=1.5 nicht in [0.0, 1.0]"
            teile = fehler.split()
            pfad = teile[1].split('=')[0]  # survive.energy.value
            parts = pfad.split('.')
            if len(parts) == 3:
                top, sub, _ = parts
                container = state_dict.get(top, {}).get(sub, {})
                if isinstance(container, dict) and 'value' in container:
                    container['value'] = max(0.0, min(1.0, float(container['value'])))
                    reparaturen.append(f'REPARIERT: {pfad} geclampt auf [0.0, 1.0]')

        # --- Emotions-Intensity ausserhalb Range → Clamping ---
        elif 'active_emotions' in fehler and 'intensity' in fehler and 'KONSISTENZ' in fehler:
            # Finde den Index
            try:
                idx = int(fehler.split('[')[1].split(']')[0])
                emotions = state_dict.get('express', {}).get('active_emotions', [])
                if idx < len(emotions) and isinstance(emotions[idx], dict):
                    v = emotions[idx].get('intensity', 0.5)
                    if isinstance(v, (int, float)):
                        emotions[idx]['intensity'] = max(0.0, min(1.0, float(v)))
                        reparaturen.append(
                            f'REPARIERT: active_emotions[{idx}].intensity geclampt'
                        )
            except (ValueError, IndexError):
                pass

    return state_dict, reparaturen


# ================================================================
# Lade & Validiere (Hauptfunktion)
# ================================================================

def lade_und_validiere(state_dict, egon_id='unknown'):
    """Hauptfunktion: Validiere einen geladenen State, repariere wenn moeglich.

    Wird von organ_reader.read_yaml_organ() aufgerufen wenn
    layer='core' und filename='state.yaml'.

    Args:
        state_dict: Bereits geparstes state.yaml dict.
        egon_id: ID des EGON (fuer Logging).

    Returns:
        Validierter (und ggf. reparierter) State-Dict.

    Raises:
        StateValidationError: Wenn nicht reparierbar.
        StateCorruptionError: Wenn State leer oder kein dict.
    """
    if state_dict is None or not isinstance(state_dict, dict):
        raise StateCorruptionError(f'[{egon_id}] State ist leer oder kein dict')

    if not state_dict:
        raise StateCorruptionError(f'[{egon_id}] State-Dict ist leer')

    # Phase 1: Schema-Validierung
    fehler = validiere_state(state_dict)

    # Phase 2: Konsistenz-Pruefung
    fehler += validiere_konsistenz(state_dict)

    if not fehler:
        return state_dict  # Alles ok

    # Phase 3: Auto-Repair
    state_dict, reparaturen = auto_repair(state_dict, fehler)

    if reparaturen:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'[state_validator] [{egon_id}] {ts} — {len(reparaturen)} Reparaturen:')
        for r in reparaturen:
            print(f'  {r}')

    # Phase 4: Erneute Validierung
    verbleibende = validiere_state(state_dict)
    verbleibende += validiere_konsistenz(state_dict)

    # Konsistenz-Warnungen (KONSISTENZ:) sind nicht fatal
    fatale_fehler = [f for f in verbleibende if not f.startswith('KONSISTENZ:')]

    if fatale_fehler:
        raise StateValidationError(fatale_fehler)

    # Nur Konsistenz-Warnungen uebrig → loggen aber nicht blocken
    if verbleibende:
        print(f'[state_validator] [{egon_id}] Warnungen: {verbleibende}')

    return state_dict


def quick_validate(state_dict):
    """Schnelle Validierung ohne Auto-Repair.

    Fuer Transaktionen: Prueft ob ein State geschrieben werden darf.

    Returns:
        Liste von Fehler-Strings (leer = ok).
    """
    if not isinstance(state_dict, dict) or not state_dict:
        return ['State ist leer oder kein dict']
    return validiere_state(state_dict)
