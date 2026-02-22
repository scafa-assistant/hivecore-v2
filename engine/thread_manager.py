"""Thread Manager — Multi-Day Project Tracking.

Threads sind zusammenhaengende Gespraeche ueber mehrere Tage.
Z.B. "Wir bauen eine Webapp" oder "Adams neues Gehirn einpflanzen".

Ein Thread verbindet Episoden die thematisch zusammengehoeren,
damit Adam bei der naechsten Interaktion den Kontext hat:
"Ach ja, wir arbeiten ja noch an dem Projekt..."

Lifecycle:
  1. Thread wird erkannt wenn >= 2 Episoden aehnliche Tags haben
  2. Thread bleibt aktiv solange Episoden reinkommen
  3. Thread wird geschlossen nach 14 Tagen Inaktivitaet
  4. Thread wird archiviert nach 6 Monaten
"""

from datetime import datetime
from engine.organ_reader import read_yaml_organ, write_yaml_organ


# ================================================================
# Thread Lifecycle
# ================================================================

def maybe_create_thread(egon_id: str):
    """Prueft ob neue Threads erstellt werden sollten.

    Methode: Suche Episoden ohne Thread die aehnliche Tags haben.
    Wenn >= 2 Episoden mit >= 2 gemeinsamen Tags → neuen Thread erstellen.

    Wird im Pulse aufgerufen (nicht bei jedem Chat).
    """
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not episodes_data:
        return

    episodes = episodes_data.get('episodes', [])
    config = episodes_data.get('memory_config', {})
    window = config.get('thread_detection_window', 7)

    now = datetime.now()

    # Sammle unthreaded Episoden der letzten N Tage
    unthreaded = []
    for ep in episodes:
        if ep.get('thread'):
            continue  # Bereits in einem Thread

        try:
            ep_date = datetime.strptime(ep.get('date', ''), '%Y-%m-%d')
            if (now - ep_date).days <= window:
                unthreaded.append(ep)
        except ValueError:
            continue

    if len(unthreaded) < 2:
        return  # Nicht genug Episoden

    # Suche Paare mit Tag-Overlap >= 2
    changed = False
    for i, ep1 in enumerate(unthreaded):
        tags1 = set(ep1.get('tags', []))
        if not tags1:
            continue

        for ep2 in unthreaded[i + 1:]:
            tags2 = set(ep2.get('tags', []))
            overlap = tags1 & tags2

            if len(overlap) >= 2:
                # Neuen Thread erstellen
                thread_id = _generate_thread_id(episodes)
                thread_title = _generate_thread_title(overlap)

                # Beide Episoden dem Thread zuweisen
                ep1['thread'] = thread_id
                ep1['thread_title'] = thread_title
                ep2['thread'] = thread_id
                ep2['thread_title'] = thread_title
                changed = True
                break  # Ein Thread pro Durchlauf reicht

        if changed:
            break

    if changed:
        write_yaml_organ(egon_id, 'memory', 'episodes.yaml', episodes_data)


def close_stale_threads(egon_id: str):
    """Schliesst Threads die zu lange inaktiv sind.

    Ein Thread ist "stale" wenn die letzte Episode aelter als
    thread_close_after_days ist (default: 14 Tage).

    Geschlossene Threads werden nicht geloescht — die Episoden
    behalten ihren Thread-Link. Aber im Prompt werden sie nicht
    mehr als "aktiv" geladen.

    Wird im Pulse aufgerufen.
    """
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not episodes_data:
        return

    config = episodes_data.get('memory_config', {})
    close_after = config.get('thread_close_after_days', 14)

    episodes = episodes_data.get('episodes', [])
    now = datetime.now()

    # Finde die letzte Aktivitaet pro Thread
    thread_last_activity = {}
    for ep in episodes:
        thread_id = ep.get('thread')
        if not thread_id:
            continue

        ep_date = ep.get('date', '')
        if thread_id not in thread_last_activity or ep_date > thread_last_activity[thread_id]:
            thread_last_activity[thread_id] = ep_date

    # Stale Threads markieren (setze thread_status auf 'closed')
    # Wir tracken Thread-Status in memory_config
    closed_threads = set(config.get('closed_threads', []))
    changed = False

    for thread_id, last_date_str in thread_last_activity.items():
        if thread_id in closed_threads:
            continue  # Bereits geschlossen

        try:
            last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
            if (now - last_date).days > close_after:
                closed_threads.add(thread_id)
                changed = True
        except ValueError:
            continue

    if changed:
        config['closed_threads'] = list(closed_threads)
        episodes_data['memory_config'] = config
        write_yaml_organ(egon_id, 'memory', 'episodes.yaml', episodes_data)


# ================================================================
# Thread Context fuer Prompt
# ================================================================

def get_active_threads(egon_id: str) -> list[dict]:
    """Holt alle aktiven (nicht geschlossenen) Threads mit ihren Episoden.

    Returns:
        Liste von Dicts: [{'thread_id': ..., 'title': ..., 'episodes': [...]}]
    """
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not episodes_data:
        return []

    config = episodes_data.get('memory_config', {})
    closed = set(config.get('closed_threads', []))
    episodes = episodes_data.get('episodes', [])

    # Sammle aktive Threads
    threads = {}
    for ep in episodes:
        thread_id = ep.get('thread')
        if not thread_id or thread_id in closed:
            continue

        if thread_id not in threads:
            threads[thread_id] = {
                'thread_id': thread_id,
                'title': ep.get('thread_title', 'Unbenannt'),
                'episodes': [],
            }
        threads[thread_id]['episodes'].append(ep)

    # Sortiere Threads nach letzter Aktivitaet
    result = list(threads.values())
    result.sort(
        key=lambda t: max(
            (e.get('date', '') for e in t['episodes']),
            default='',
        ),
        reverse=True,
    )

    return result


def get_thread_summary(thread: dict) -> str:
    """Erstellt eine kompakte Zusammenfassung eines Threads fuer den Prompt.

    Args:
        thread: Dict mit 'thread_id', 'title', 'episodes'

    Returns:
        Kompakter String: "Projekt: X (3 Episoden, zuletzt: ...)"
    """
    episodes = thread.get('episodes', [])
    title = thread.get('title', 'Unbenannt')
    count = len(episodes)

    if not episodes:
        return f'Projekt: {title} (leer)'

    # Sortiere nach Datum
    episodes.sort(key=lambda e: e.get('date', ''))

    last_ep = episodes[-1]
    last_date = last_ep.get('date', '?')
    last_summary = last_ep.get('summary', '').strip()

    # Kuerze Summary
    if len(last_summary) > 100:
        last_summary = last_summary[:100] + '...'

    return f'Projekt: {title} ({count} Episoden, zuletzt {last_date}): {last_summary}'


# ================================================================
# Helper
# ================================================================

def _generate_thread_id(episodes: list) -> str:
    """Generiert eine neue Thread-ID (T001, T002, ...)."""
    max_num = 0
    for ep in episodes:
        tid = ep.get('thread', '') or ''
        if tid.startswith('T') and tid[1:].isdigit():
            num = int(tid[1:])
            if num > max_num:
                max_num = num
    return f'T{max_num + 1:03d}'


def _generate_thread_title(common_tags: set) -> str:
    """Generiert einen Thread-Titel aus gemeinsamen Tags.

    Z.B. {'webapp', 'react', 'frontend'} → 'webapp-react-frontend'
    """
    tags = sorted(common_tags)[:3]  # Max 3 Tags im Titel
    return '-'.join(tags) if tags else 'Unbenanntes Projekt'
