"""Interaction Log — Lueckenloses wissenschaftliches Protokoll jeder Interaktion.

Jede Chat-Interaktion wird als eine JSONL-Zeile gespeichert mit:
- Timestamp, EGON-ID, User-Input, LLM-Output
- Inner Voice (vor dem Chat)
- Thalamus-Entscheidung (Pfad, Relevanz)
- Body/Bones/Motor-Daten
- Emotionen + Drives (vorher/nachher)
- Episode, Experience, Diary (falls erzeugt)
- Bond-Aenderungen
- LLM-Tier, Model, Verarbeitungszeit

Format: JSONL (eine JSON-Zeile pro Interaktion)
Pfad: egons/shared/interaction_log/YYYY-MM-DD.jsonl
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import EGON_DATA_DIR

# Log-Verzeichnis
_LOG_DIR = Path(EGON_DATA_DIR) / 'shared' / 'interaction_log'
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Aktuelle Interaktion (wird waehrend des Chat-Flows befuellt)
_current: dict = {}


def begin_interaction(egon_id: str, user_message: str, user_name: str = 'owner',
                      conversation_type: str = 'owner_chat') -> None:
    """Startet eine neue Interaktion — rufe das AM ANFANG des Chat-Handlers auf."""
    global _current
    _current = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'unix_ts': time.time(),
        'egon_id': egon_id,
        'user_name': user_name,
        'user_message': user_message,
        'conversation_type': conversation_type,

        # Pre-Chat State (wird spaeter befuellt)
        'pre_state': None,
        'inner_voice': None,
        'thalamus': None,

        # LLM
        'llm_raw_response': None,
        'llm_model': None,

        # Parsed Response
        'display_text': None,
        'body_data': None,
        'action_data': None,
        'bone_update': None,

        # Post-Processing
        'post_state': None,
        'emotion_change': None,
        'drive_changes': None,
        'bond_changes': None,
        'episode_created': None,
        'experience_created': None,
        'diary_entry': None,
        'self_diary_entry': None,

        # Meta
        'processing_time_ms': None,
        'errors': [],
    }


def log_pre_state(state_data: Optional[dict]) -> None:
    """Loggt den emotionalen Zustand VOR dem Chat."""
    if not _current or not state_data:
        return
    try:
        emotions = state_data.get('express', {}).get('active_emotions', [])
        drives = state_data.get('drives', {})
        _current['pre_state'] = {
            'emotions': emotions[:5] if emotions else [],
            'drives': {k: round(v, 3) if isinstance(v, float) else v
                       for k, v in drives.items()} if drives else {},
        }
    except Exception as e:
        _current['errors'].append(f'pre_state: {e}')


def log_inner_voice(inner_text: str) -> None:
    """Loggt den inneren Gedanken (vor dem Chat generiert)."""
    if not _current:
        return
    _current['inner_voice'] = inner_text


def log_thalamus(gate: Optional[dict]) -> None:
    """Loggt die Thalamus-Entscheidung."""
    if not _current or not gate:
        return
    _current['thalamus'] = {
        'pfad': gate.get('pfad'),
        'relevanz': round(gate.get('relevanz', 0), 3),
        'schritte': gate.get('aktive_schritte', []),
    }


def log_llm_response(raw_content: str, model: str = 'moonshot') -> None:
    """Loggt die rohe LLM-Antwort."""
    if not _current:
        return
    _current['llm_raw_response'] = raw_content
    _current['llm_model'] = model


def log_parsed_response(display_text: str, body_data: Optional[dict],
                        action_data: Optional[dict]) -> None:
    """Loggt das Ergebnis des Response-Parsers."""
    if not _current:
        return
    _current['display_text'] = display_text
    _current['body_data'] = body_data
    _current['action_data'] = action_data


def log_bone_update(bone_update: Optional[dict]) -> None:
    """Loggt das Motor-Translator Ergebnis."""
    if not _current:
        return
    _current['bone_update'] = bone_update


def log_post_state(state_data: Optional[dict]) -> None:
    """Loggt den emotionalen Zustand NACH dem Chat."""
    if not _current or not state_data:
        return
    try:
        emotions = state_data.get('express', {}).get('active_emotions', [])
        drives = state_data.get('drives', {})
        _current['post_state'] = {
            'emotions': emotions[:5] if emotions else [],
            'drives': {k: round(v, 3) if isinstance(v, float) else v
                       for k, v in drives.items()} if drives else {},
        }

        # Delta berechnen
        if _current.get('pre_state'):
            pre_drives = _current['pre_state'].get('drives', {})
            post_drives = _current['post_state'].get('drives', {})
            delta = {}
            for k in set(list(pre_drives.keys()) + list(post_drives.keys())):
                pre_v = pre_drives.get(k, 0)
                post_v = post_drives.get(k, 0)
                if isinstance(pre_v, (int, float)) and isinstance(post_v, (int, float)):
                    d = round(post_v - pre_v, 4)
                    if abs(d) > 0.001:
                        delta[k] = d
            _current['drive_changes'] = delta if delta else None

            # Emotion-Aenderung
            pre_emo = _current['pre_state'].get('emotions', [])
            post_emo = _current['post_state'].get('emotions', [])
            if pre_emo and post_emo:
                pre_top = max(pre_emo, key=lambda e: e.get('intensity', 0))
                post_top = max(post_emo, key=lambda e: e.get('intensity', 0))
                _current['emotion_change'] = {
                    'before': f"{pre_top.get('type', '?')}({pre_top.get('intensity', 0):.2f})",
                    'after': f"{post_top.get('type', '?')}({post_top.get('intensity', 0):.2f})",
                }

    except Exception as e:
        _current['errors'].append(f'post_state: {e}')


def log_episode(episode: Optional[dict]) -> None:
    """Loggt die erzeugte Episode (falls vorhanden)."""
    if not _current or not episode:
        return
    _current['episode_created'] = {
        'id': episode.get('id', ''),
        'summary': episode.get('summary', ''),
        'significance': episode.get('significance', 0),
        'emotions_felt': episode.get('emotions_felt', []),
    }


def log_experience(experience: Optional[dict]) -> None:
    """Loggt die erzeugte Erfahrung (falls vorhanden)."""
    if not _current or not experience:
        return
    _current['experience_created'] = {
        'insight': experience.get('insight', ''),
        'category': experience.get('category', ''),
        'confidence': experience.get('confidence', 0),
    }


def log_diary(diary_entry: Optional[dict]) -> None:
    """Loggt den Owner-Diary Eintrag."""
    if not _current or not diary_entry:
        return
    _current['diary_entry'] = diary_entry


def log_self_diary(entry: Optional[dict]) -> None:
    """Loggt den Self-Diary Eintrag."""
    if not _current or not entry:
        return
    _current['self_diary_entry'] = entry


def log_bond_change(bond_info: Optional[dict]) -> None:
    """Loggt Bond-Aenderungen."""
    if not _current or not bond_info:
        return
    _current['bond_changes'] = bond_info


def log_error(context: str, error: str) -> None:
    """Loggt einen Fehler waehrend der Verarbeitung."""
    if not _current:
        return
    _current['errors'].append(f'{context}: {error}')


def end_interaction() -> Optional[dict]:
    """Beendet die Interaktion und schreibt sie in die JSONL-Datei.

    Returns:
        Das komplette Interaktions-Dict (fuer eventuelle weitere Nutzung).
    """
    global _current
    if not _current or not _current.get('egon_id'):
        return None

    # Verarbeitungszeit berechnen
    if _current.get('unix_ts'):
        _current['processing_time_ms'] = round(
            (time.time() - _current['unix_ts']) * 1000
        )
    # unix_ts nicht in die Datei schreiben (redundant mit timestamp)
    _current.pop('unix_ts', None)

    # Leere Felder entfernen fuer kompaktere Logs
    record = {k: v for k, v in _current.items()
              if v is not None and v != [] and v != {}}

    # In Tages-JSONL schreiben
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    log_file = _LOG_DIR / f'{today}.jsonl'

    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
        print(f'[interaction_log] Gespeichert: {_current["egon_id"]} '
              f'({_current.get("processing_time_ms", 0)}ms) → {log_file.name}')
    except Exception as e:
        print(f'[interaction_log] FEHLER beim Schreiben: {e}')

    result = _current.copy()
    _current = {}
    return result


# ================================================================
# Statistik-Funktionen (fuer Paper-Analyse)
# ================================================================

def get_log_files() -> list[str]:
    """Gibt alle vorhandenen Log-Dateien zurueck."""
    return sorted([f.name for f in _LOG_DIR.glob('*.jsonl')])


def count_interactions(date: Optional[str] = None) -> dict:
    """Zaehlt Interaktionen pro EGON (optional fuer ein Datum)."""
    counts: dict = {}
    files = [_LOG_DIR / f'{date}.jsonl'] if date else list(_LOG_DIR.glob('*.jsonl'))

    for log_file in files:
        if not log_file.exists():
            continue
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        eid = record.get('egon_id', 'unknown')
                        counts[eid] = counts.get(eid, 0) + 1
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue

    return counts


def log_heartbeat(egon_id: str, drives: Optional[dict] = None,
                  emotions: Optional[list] = None,
                  phase: str = 'unknown') -> None:
    """Loggt einen Heartbeat — auch wenn der EGON schweigt.

    Wird vom Scheduler aufgerufen. Schweigen IST ein Datenpunkt.
    """
    record = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'egon_id': egon_id,
        'conversation_type': 'heartbeat',
        'phase': phase,
    }

    if drives:
        record['drives'] = {k: round(v, 3) if isinstance(v, (int, float)) else v
                            for k, v in drives.items()}
    if emotions:
        record['emotions'] = emotions[:3]

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    log_file = _LOG_DIR / f'{today}.jsonl'

    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
    except Exception as e:
        print(f'[interaction_log] Heartbeat-FEHLER: {e}')


def read_interactions(date: str, egon_id: Optional[str] = None,
                      limit: int = 100) -> list[dict]:
    """Liest Interaktionen fuer ein Datum (optional gefiltert nach EGON)."""
    log_file = _LOG_DIR / f'{date}.jsonl'
    if not log_file.exists():
        return []

    results = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if egon_id and record.get('egon_id') != egon_id:
                        continue
                    results.append(record)
                    if len(results) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return results
