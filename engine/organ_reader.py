"""Organ Reader — liest EGONs Organe aus der Schichten-Struktur.

v2-Struktur (alt):
  core/     → dna.md, ego.md, state.yaml
  social/   → bonds.yaml, network.yaml, owner.md, egon_self.md
  memory/   → episodes.yaml, inner_voice.md, experience.yaml
  contacts/ → active/*.yaml, resting/*.yaml
  capabilities/ → skills.yaml, wallet.yaml

v3-Struktur (neu, semantisch deutsch):
  kern/         → seele.md, ich.md
  innenwelt/    → innenwelt.yaml
  bindungen/    → naehe.yaml, gefuege.yaml, begleiter.md, selbstbild.md
  erinnerungen/ → erlebtes.yaml, erfahrungen.yaml
  innere_stimme/ → gedanken.yaml
  leib/         → leib.md
  begegnungen/  → active/*.yaml, resting/*.yaml
  faehigkeiten/ → koennen.yaml, wallet.yaml

Kompatibilitaets-Layer: Alias-System das v2-Pfade transparent auf v3 aufloest.
Engine-Code kann weiterhin read_organ(id, 'core', 'state.yaml') aufrufen —
der Alias-Layer resolved das automatisch auf innenwelt/innenwelt.yaml.

Patch 9: state.yaml/innenwelt.yaml wird beim Laden validiert und bei Bedarf
         automatisch repariert (Auto-Repair mit DNA-Baseline).
"""

import os
import yaml
from pathlib import Path
from config import EGON_DATA_DIR


# ================================================================
# v2 → v3 Alias-System
# ================================================================

# Layer-Aliase: v2-Layername → v3-Layername
LAYER_ALIASES = {
    'core':             'kern',
    'social':           'bindungen',
    'memory':           'erinnerungen',
    'capabilities':     'faehigkeiten',
    'contacts':         'begegnungen',
    'contacts/active':  'begegnungen/active',
    'contacts/resting': 'begegnungen/resting',
    'contacts/trash':   'begegnungen/trash',
    'config':           'einstellungen',
    'puffer':           'zwischenraum',
}

# Datei-Aliase: (v2-layer, v2-filename) → (v3-layer, v3-filename)
# Fuer Dateien die nicht nur den Layer wechseln sondern auch umbenannt werden
FILE_ALIASES = {
    ('core', 'state.yaml'):        ('innenwelt', 'innenwelt.yaml'),
    ('core', 'dna.md'):            ('kern', 'seele.md'),
    ('core', 'soul.md'):           ('kern', 'seele.md'),
    ('core', 'ego.md'):            ('kern', 'ich.md'),
    ('core', 'body.md'):           ('leib', 'leib.md'),
    ('social', 'bonds.yaml'):      ('bindungen', 'naehe.yaml'),
    ('social', 'network.yaml'):    ('bindungen', 'gefuege.yaml'),
    ('social', 'owner.md'):        ('bindungen', 'begleiter.md'),
    ('social', 'bezugsmensch.md'): ('bindungen', 'begleiter.md'),
    ('social', 'egon_self.md'):    ('bindungen', 'selbstbild.md'),
    ('social', 'self_diary.yaml'): ('tagebuch', 'selbst.yaml'),
    ('social', 'owner_diary.yaml'): ('tagebuch', 'begleiter.yaml'),
    ('memory', 'episodes.yaml'):   ('erinnerungen', 'erlebtes.yaml'),
    ('memory', 'experience.yaml'): ('erinnerungen', 'erfahrungen.yaml'),
    ('memory', 'inner_voice.md'):  ('innere_stimme', 'gedanken.yaml'),
    ('memory', 'dreams.md'):       ('erinnerungen', 'traeume.yaml'),
    ('memory', 'recent_memory.md'): ('erinnerungen', 'kurzzeitgedaechtnis.md'),
    ('capabilities', 'skills.yaml'): ('faehigkeiten', 'koennen.yaml'),
    # Non-standard skills/memory Pfade (recent_memory.py, genesis.py)
    ('skills', 'memory/recent_memory.md'): ('erinnerungen', 'kurzzeitgedaechtnis.md'),
    ('skills', 'memory/memory_cycle_current.md'): ('erinnerungen', 'zyklusgedaechtnis.md'),
    ('skills', 'memory/memory_archive.md'): ('erinnerungen', 'archiv.md'),
}

# Reverse-Mapping: (v3-layer, v3-filename) → (v2-layer, v2-filename)
# Wird aufgebaut damit auch v3-Aufrufe auf v2-Dateien zurueckfallen koennen
_REVERSE_FILE_ALIASES = {}
for _v2_key, _v3_val in FILE_ALIASES.items():
    if _v3_val not in _REVERSE_FILE_ALIASES:
        _REVERSE_FILE_ALIASES[_v3_val] = _v2_key

_REVERSE_LAYER_ALIASES = {v: k for k, v in LAYER_ALIASES.items()}


# ================================================================
# v3 → v2 State-Normalisierung
# ================================================================
# Wenn innenwelt.yaml v3-Keys hat (ueberleben, entfaltung, empfindungen, lebenskraft),
# erzeugt diese Funktion v2-Alias-Keys (survive, thrive, express, drives).
# So funktioniert der gesamte Engine-Code ohne Aenderung.

# Drive-Mapping: v3 (deutsch) → v2 (Panksepp-English)
_DRIVE_V3_TO_V2 = {
    'neugier': 'SEEKING', 'tatendrang': 'ACTION', 'lerndrang': 'LEARNING',
    'fuersorge': 'CARE', 'spieltrieb': 'PLAY', 'furcht': 'FEAR',
    'zorn': 'RAGE', 'trauer': 'GRIEF', 'sehnsucht': 'LUST', 'panik': 'PANIC',
}
_DRIVE_V2_TO_V3 = {v: k for k, v in _DRIVE_V3_TO_V2.items()}

# Survive-Mapping: v3 → v2
_SURVIVE_MAP = {
    'lebenskraft': 'energy', 'geborgenheit': 'safety', 'innerer_zusammenhalt': 'coherence',
}

# Thrive-Mapping: v3 → v2
_THRIVE_MAP = {
    'zugehoerigkeit': 'belonging', 'vertrauen': 'trust_owner',
    'grundstimmung': 'mood', 'sinn': 'purpose',
}

# Emotion-Feld-Mapping: v3 → v2
_EMOTION_FIELD_MAP = {
    'art': 'type', 'staerke': 'intensity', 'ursache': 'cause',
    'beginn': 'onset', 'verblassklasse': 'decay_class', 'anker': 'verbal_anchor',
}

# Decay-Class Mapping: v3 → v2
_DECAY_V3_TO_V2 = {
    'blitz': 'flash', 'schnell': 'fast', 'langsam': 'slow', 'glazial': 'glacial',
}


def _normalize_v3_state(state: dict) -> dict:
    """Erzeugt v2-Alias-Keys fuer v3-State.

    Wenn state v3-Keys hat (ueberleben, entfaltung, empfindungen, lebenskraft),
    werden die entsprechenden v2-Keys (survive, thrive, express, drives) hinzugefuegt.
    Originalwerte bleiben erhalten. Beide Key-Sets zeigen auf dieselben Daten.

    Wird automatisch nach dem Laden von innenwelt.yaml aufgerufen.
    """
    # Erkennung: Ist das ein v3-State?
    is_v3 = ('ueberleben' in state or 'empfindungen' in state
             or 'lebenskraft' in state or 'entfaltung' in state)
    if not is_v3:
        return state  # v2-State, nichts zu tun

    # --- dna_profil → dna_profile ---
    if 'dna_profil' in state and 'dna_profile' not in state:
        state['dna_profile'] = state['dna_profil']

    # --- lebenskraft → drives ---
    if 'lebenskraft' in state and 'drives' not in state:
        lk = state['lebenskraft']
        if isinstance(lk, dict):
            drives = {}
            for v3_key, v2_key in _DRIVE_V3_TO_V2.items():
                if v3_key in lk:
                    drives[v2_key] = lk[v3_key]
            # Fehlende Drives mit Default auffuellen
            for v2_key in ['SEEKING', 'ACTION', 'LEARNING', 'CARE', 'PLAY',
                           'FEAR', 'RAGE', 'GRIEF', 'LUST', 'PANIC']:
                if v2_key not in drives:
                    drives[v2_key] = 0.5
            state['drives'] = drives

    # --- ueberleben → survive ---
    if 'ueberleben' in state and 'survive' not in state:
        ub = state['ueberleben']
        if isinstance(ub, dict):
            survive = {}
            for v3_key, v2_key in _SURVIVE_MAP.items():
                if v3_key in ub:
                    sub = ub[v3_key]
                    if isinstance(sub, dict):
                        survive[v2_key] = {
                            'value': sub.get('wert', 0.5),
                            'verbal': sub.get('verbal', ''),
                        }
                    else:
                        survive[v2_key] = {'value': float(sub) if sub else 0.5, 'verbal': ''}
            # Fehlende Felder auffuellen
            for v2_key in ['energy', 'safety', 'coherence']:
                if v2_key not in survive:
                    survive[v2_key] = {'value': 0.5, 'verbal': ''}
            state['survive'] = survive

    # --- entfaltung → thrive ---
    if 'entfaltung' in state and 'thrive' not in state:
        ent = state['entfaltung']
        if isinstance(ent, dict):
            thrive = {}
            for v3_key, v2_key in _THRIVE_MAP.items():
                if v3_key in ent:
                    sub = ent[v3_key]
                    if isinstance(sub, dict):
                        thrive[v2_key] = {
                            'value': sub.get('wert', 0.5),
                            'verbal': sub.get('verbal', ''),
                        }
                    else:
                        thrive[v2_key] = {'value': float(sub) if sub else 0.5, 'verbal': ''}
            for v2_key in ['belonging', 'trust_owner', 'mood', 'purpose']:
                if v2_key not in thrive:
                    thrive[v2_key] = {'value': 0.5, 'verbal': ''}
            state['thrive'] = thrive

    # --- empfindungen → express ---
    if 'empfindungen' in state and 'express' not in state:
        emp = state['empfindungen']
        if isinstance(emp, dict):
            express = {}
            # aktive_gefuehle → active_emotions
            gefuehle = emp.get('aktive_gefuehle', [])
            if isinstance(gefuehle, list):
                emotions = []
                for g in gefuehle:
                    if isinstance(g, dict):
                        emo = {}
                        for v3_f, v2_f in _EMOTION_FIELD_MAP.items():
                            if v3_f in g:
                                val = g[v3_f]
                                # Decay-Class uebersetzen
                                if v3_f == 'verblassklasse' and val in _DECAY_V3_TO_V2:
                                    val = _DECAY_V3_TO_V2[val]
                                emo[v2_f] = val
                        # Felder die in v3 gleich heissen
                        for keep in ['type', 'intensity', 'cause', 'onset', 'decay_class']:
                            if keep in g and keep not in emo:
                                emo[keep] = g[keep]
                        emotions.append(emo)
                express['active_emotions'] = emotions
            else:
                express['active_emotions'] = []

            # schwerkraft → emotional_gravity
            schwerkraft = emp.get('schwerkraft', {})
            if isinstance(schwerkraft, dict) and schwerkraft:
                state.setdefault('emotional_gravity', {
                    'baseline_mood': schwerkraft.get('grundstimmung', 0.5),
                    'bias': schwerkraft.get('deutungstendenz', 'neutral'),
                })
            state['express'] = express

    # --- selbstbild → self_assessment ---
    if 'selbstbild' in state and 'self_assessment' not in state:
        sb = state['selbstbild']
        if isinstance(sb, dict):
            state['self_assessment'] = {'verbal': sb.get('verbal', '')}
        elif isinstance(sb, str):
            state['self_assessment'] = {'verbal': sb}

    return state


# ================================================================
# Hilfsfunktionen
# ================================================================

def _egon_path(egon_id: str) -> Path:
    """Basispfad fuer einen EGON."""
    return Path(EGON_DATA_DIR) / egon_id


def _is_v3(egon_id: str) -> bool:
    """Prueft ob ein EGON auf v3-Struktur migriert ist (kern/ existiert)."""
    return (_egon_path(egon_id) / 'kern').is_dir()


def _resolve_v3(layer: str, filename: str) -> tuple:
    """Loest v2-Pfad auf v3-Alias auf.

    Prueft zuerst exakte Datei-Aliase, dann Layer-Aliase.

    Returns:
        (v3_layer, v3_filename) oder (layer, filename) wenn kein Alias.
    """
    key = (layer, filename)
    if key in FILE_ALIASES:
        return FILE_ALIASES[key]
    if layer in LAYER_ALIASES:
        return (LAYER_ALIASES[layer], filename)
    return (layer, filename)


def _resolve_v2(layer: str, filename: str) -> tuple:
    """Loest v3-Pfad zurueck auf v2-Original auf (Reverse-Alias).

    Returns:
        (v2_layer, v2_filename) oder (layer, filename) wenn kein Reverse-Alias.
    """
    key = (layer, filename)
    if key in _REVERSE_FILE_ALIASES:
        return _REVERSE_FILE_ALIASES[key]
    if layer in _REVERSE_LAYER_ALIASES:
        return (_REVERSE_LAYER_ALIASES[layer], filename)
    return (layer, filename)


def _is_state_file(layer: str, filename: str) -> bool:
    """Prueft ob das Organ die zentrale State-Datei ist (v2 oder v3)."""
    return ((layer == 'core' and filename == 'state.yaml') or
            (layer == 'innenwelt' and filename == 'innenwelt.yaml'))


# ================================================================
# Lese-Operationen
# ================================================================

def read_organ(egon_id: str, layer: str, filename: str) -> str:
    """Liest ein Organ als Text.

    Suchstrategie (erste Treffer gewinnt):
      1. v3-Alias-Pfad (forward resolution: core/state.yaml → innenwelt/innenwelt.yaml)
      2. Original-Pfad wie angegeben (layer/filename)
      3. Reverse-Alias (v3→v2 Fallback: kern/seele.md → core/dna.md)
      4. Flat-Fallback (v1: nur filename im Root)

    Returns:
        Dateiinhalt als String, oder '' wenn nicht gefunden.
    """
    base = _egon_path(egon_id)

    # 1. v3-Alias-Pfad
    v3_layer, v3_file = _resolve_v3(layer, filename)
    v3_path = base / v3_layer / v3_file
    if v3_path.is_file():
        return v3_path.read_text(encoding='utf-8')

    # 2. Original-Pfad wie angegeben
    orig_path = base / layer / filename
    if orig_path != v3_path and orig_path.is_file():
        return orig_path.read_text(encoding='utf-8')

    # 3. Reverse-Alias (v3-Aufruf findet v2-Datei)
    v2_layer, v2_file = _resolve_v2(layer, filename)
    v2_path = base / v2_layer / v2_file
    if v2_path != orig_path and v2_path != v3_path and v2_path.is_file():
        return v2_path.read_text(encoding='utf-8')

    # 4. Flat-Fallback (v1: egons/adam/{filename})
    flat_path = base / filename
    if flat_path.is_file():
        return flat_path.read_text(encoding='utf-8')

    return ''


def read_yaml_organ(egon_id: str, layer: str, filename: str) -> dict:
    """Liest ein YAML-Organ und parsed es.

    Patch 9: Fuer die State-Datei (core/state.yaml oder innenwelt/innenwelt.yaml)
    wird nach dem Laden validiert und bei Bedarf automatisch repariert.

    Returns:
        Parsed YAML als dict, oder {} bei Fehler/nicht gefunden.
    """
    text = read_organ(egon_id, layer, filename)
    if not text:
        return {}

    try:
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            return {}
    except yaml.YAMLError as e:
        print(f'[organ_reader] YAML Parse Error in {layer}/{filename}: {e}')
        if _is_state_file(layer, filename):
            try:
                from engine.checkpoint import kaskaden_rollback
                print(f'[organ_reader] state korrupt — starte Kaskaden-Rollback')
                if kaskaden_rollback(egon_id):
                    text2 = read_organ(egon_id, layer, filename)
                    if text2:
                        data2 = yaml.safe_load(text2)
                        if isinstance(data2, dict):
                            return data2
            except Exception as e2:
                print(f'[organ_reader] Kaskaden-Rollback fehlgeschlagen: {e2}')
        return {}

    # v3→v2 Normalisierung: Erzeugt v2-Alias-Keys aus v3-State
    # MUSS vor dem Validator laufen, damit der v2-Schema-Check greift
    if _is_state_file(layer, filename) and data:
        data = _normalize_v3_state(data)

    # Patch 9: State-Validierung
    if _is_state_file(layer, filename) and data:
        try:
            from engine.state_validator import lade_und_validiere
            data = lade_und_validiere(data, egon_id)
        except ImportError:
            pass
        except Exception as e:
            print(f'[organ_reader] State-Validierung fehlgeschlagen fuer {egon_id}: {e}')
            try:
                from engine.checkpoint import kaskaden_rollback
                if kaskaden_rollback(egon_id):
                    text2 = read_organ(egon_id, layer, filename)
                    if text2:
                        data2 = yaml.safe_load(text2)
                        if isinstance(data2, dict):
                            return data2
            except Exception as e2:
                print(f'[organ_reader] Kaskaden-Rollback fehlgeschlagen: {e2}')
            return {}

    return data


def read_md_organ(egon_id: str, layer: str, filename: str) -> str:
    """Liest ein Markdown-Organ. Convenience-Alias fuer read_organ."""
    return read_organ(egon_id, layer, filename)


# ================================================================
# Schreib-Operationen
# ================================================================

def write_organ(egon_id: str, layer: str, filename: str, content: str) -> None:
    """Schreibt ein Organ zurueck.

    Bei migrierten EGONs (v3): Schreibt auf den v3-Alias-Pfad.
    Bei nicht-migrierten EGONs (v2): Schreibt auf den Original-Pfad.
    """
    if _is_v3(egon_id):
        layer, filename = _resolve_v3(layer, filename)

    path = _egon_path(egon_id) / layer / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def write_yaml_organ(egon_id: str, layer: str, filename: str, data: dict) -> None:
    """Schreibt ein YAML-Organ zurueck.

    Bei migrierten EGONs: Pfad wird auf v3-Alias aufgeloest.
    Patch 9: Fuer State-Dateien wird vor dem Schreiben validiert.
    Schreibt ueber Temp-Datei + Rename fuer Atomaritaet.
    """
    if _is_v3(egon_id):
        layer, filename = _resolve_v3(layer, filename)

    path = _egon_path(egon_id) / layer / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    # Patch 9: Validierung vor dem Schreiben (State-Datei)
    if _is_state_file(layer, filename):
        try:
            from engine.state_validator import quick_validate
            fehler = quick_validate(data)
            if fehler:
                fatale = [f for f in fehler if not f.startswith('KONSISTENZ:')]
                if fatale:
                    print(f'[organ_reader] BLOCKIERT: state Write fuer {egon_id} '
                          f'hat {len(fatale)} fatale Fehler: {fatale}')
                    return
        except ImportError:
            pass

    # Atomarer Write via Temp-Datei + Rename
    temp_path = path.with_suffix('.yaml.tmp')
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                data,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                width=120,
            )
        temp_path.replace(path)
    except Exception as e:
        print(f'[organ_reader] Write-Fehler {layer}/{filename}: {e}')
        if temp_path.exists():
            temp_path.unlink()
        raise


# ================================================================
# Kontakt- und Existenz-Operationen
# ================================================================

def list_contact_cards(egon_id: str, folder: str = 'active') -> list[dict]:
    """Liest alle Kontaktkarten aus begegnungen/{folder}/ (v3) oder contacts/{folder}/ (v2).

    Returns:
        Liste von parsed YAML-Dicts.
    """
    base = _egon_path(egon_id)

    # v3 zuerst
    contacts_dir = base / 'begegnungen' / folder
    if not contacts_dir.is_dir():
        # v2 Fallback
        contacts_dir = base / 'contacts' / folder
    if not contacts_dir.is_dir():
        return []

    cards = []
    for card_file in sorted(contacts_dir.glob('*.yaml')):
        try:
            data = yaml.safe_load(card_file.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                cards.append(data)
        except yaml.YAMLError as e:
            print(f'[organ_reader] Contact card parse error {card_file}: {e}')

    return cards


def organ_exists(egon_id: str, layer: str, filename: str) -> bool:
    """Prueft ob ein Organ existiert (v3-Alias, v2, oder flat)."""
    base = _egon_path(egon_id)

    # v3-Alias
    v3_layer, v3_file = _resolve_v3(layer, filename)
    if (base / v3_layer / v3_file).is_file():
        return True

    # v2-Original
    if (base / layer / filename).is_file():
        return True

    # Flat-Fallback
    if (base / filename).is_file():
        return True

    return False
