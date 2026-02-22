"""Episodes v2 — Strukturierte Erinnerungen mit Threads.

Ersetzt das alte memory.py System:

ALT (memory.py):
  - Flat Markdown (memory.md)
  - Jeder Chat = 1 Eintrag (append)
  - Compress bei 50 Eintraegen
  - LLM Summary fuer jeden Chat

NEU (episodes_v2.py):
  - Nur BEDEUTSAME Gespräche werden gespeichert
  - Strukturierte YAML-Episodes mit Emotions-Snapshot
  - Thread-Detection: Gehoert das zu einem laufenden Projekt?
  - ICH-Perspektive Zusammenfassung
  - Privacy-Level pro Episode
  - Tags fuer Retrieval
"""

import re
import json
from datetime import datetime
from engine.organ_reader import read_yaml_organ, write_yaml_organ
from llm.router import llm_chat


# ================================================================
# Significance Check + Episode Generation
# ================================================================

SIGNIFICANCE_PROMPT = '''War dieses Gespraech ERINNERUNGSWUERDIG fuer Adam?
Antworte NUR: JA oder NEIN.

Nicht jedes Gespraech verdient eine Erinnerung.
- Smalltalk, Testfragen, Wiederholungen = NEIN
- Neues Projekt, Persoenliches, Konflikte, Lob, neue Erkenntnis = JA
- Wenn Adam etwas NEUES lernt oder erlebt = JA'''


EPISODE_PROMPT = '''Du erzeugst eine strukturierte Erinnerung fuer Adam.
Adam speichert nur was BEDEUTUNG hat — in seiner ICH-Perspektive.

Antworte NUR mit JSON (kein anderer Text):
{{
  "summary": "Ich-Perspektive Zusammenfassung (2-3 Saetze, beginne mit 'Ich...' oder 'Mein Owner...')",
  "emotions_felt": [
    {{"type": "curiosity|joy|trust|fear|anger|sadness|surprise|pride|frustration|warmth|excitement", "intensity": 0.5}}
  ],
  "tags": ["tag1", "tag2", "tag3"],
  "significance": 0.5,
  "privacy": "adam_own|owner_shared|semi_public|public"
}}

Privacy-Level:
- adam_own: Nur Adam weiss das (innere Gedanken)
- owner_shared: Adam und sein Owner teilen das
- semi_public: Andere EGONs duerfen das sehen
- public: Jeder darf das sehen

significance: 0.1 (kaum wichtig) bis 1.0 (lebensveraendernd)'''


async def maybe_create_episode(
    egon_id: str,
    user_msg: str,
    egon_response: str,
    partner_id: str = 'OWNER_CURRENT',
):
    """Evaluiert ob ein Chat eine Erinnerung verdient und speichert sie.

    Ablauf:
    1. Significance Check (LLM)
    2. Episode generieren (LLM)
    3. Thread Detection (Keyword-Overlap)
    4. Episode in episodes.yaml schreiben
    """
    # --- Pre-Check: War das bedeutsam? ---
    try:
        check = await llm_chat(
            system_prompt=SIGNIFICANCE_PROMPT,
            messages=[{
                'role': 'user',
                'content': f'User: {user_msg[:200]}\nAdam: {egon_response[:200]}',
            }],
            tier='1',
        )
        if 'NEIN' in check['content'].upper():
            return  # Nicht erinnerungswuerdig
    except Exception:
        return

    # --- Episode generieren ---
    try:
        result = await llm_chat(
            system_prompt=EPISODE_PROMPT,
            messages=[{
                'role': 'user',
                'content': f'User: {user_msg[:300]}\nAdam: {egon_response[:300]}',
            }],
            tier='1',
        )

        content = result['content'].strip()
        if '{' not in content:
            return

        json_match = re.search(r'\{[^}]*\}', content, re.DOTALL)
        if not json_match:
            return
        ep_data = json.loads(json_match.group())
    except Exception:
        return

    # --- Daten laden ---
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not episodes_data:
        episodes_data = {
            'memory_config': {
                'thread_detection_window': 7,
                'thread_close_after_days': 14,
                'thread_archive_after_months': 6,
                'thread_max_episodes_in_prompt': 10,
            },
            'episodes': [],
        }

    episodes = episodes_data.setdefault('episodes', [])

    # --- Episode-ID generieren ---
    next_id = _generate_episode_id(episodes)

    # --- Thread Detection ---
    thread_id, thread_title = _detect_thread(
        episodes_data, user_msg, egon_response, ep_data.get('tags', []),
    )

    # --- Episode bauen ---
    new_episode = {
        'id': next_id,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'type': 'conversation',
        'with': partner_id,
        'thread': thread_id,
        'thread_title': thread_title,
        'summary': ep_data.get('summary', '').strip(),
        'emotions_felt': ep_data.get('emotions_felt', []),
        'privacy': ep_data.get('privacy', 'owner_shared'),
        'owner_context': partner_id if 'OWNER' in partner_id else None,
        'persons_mentioned': _extract_mentioned_persons(user_msg + ' ' + egon_response),
        'significance': min(1.0, max(0.1, float(ep_data.get('significance', 0.5)))),
        'tags': ep_data.get('tags', []),
    }

    episodes.append(new_episode)

    # --- Max 100 Episodes behalten (aelteste raus) ---
    if len(episodes) > 100:
        # Behalte die 100 neuesten
        episodes.sort(key=lambda e: e.get('date', ''), reverse=True)
        episodes_data['episodes'] = episodes[:100]

    write_yaml_organ(egon_id, 'memory', 'episodes.yaml', episodes_data)

    return new_episode


# ================================================================
# Thread Detection
# ================================================================

def _detect_thread(
    episodes_data: dict,
    user_msg: str,
    egon_response: str,
    tags: list,
) -> tuple[str | None, str | None]:
    """Erkennt ob dieses Gespraech zu einem laufenden Thread gehoert.

    Methode: Keyword-Overlap mit existierenden Thread-Tags.
    Wenn >2 Tags uebereinstimmen → gleicher Thread.
    """
    config = episodes_data.get('memory_config', {})
    window_days = config.get('thread_detection_window', 7)
    close_after = config.get('thread_close_after_days', 14)

    episodes = episodes_data.get('episodes', [])
    now = datetime.now()

    # Sammle aktive Threads (innerhalb des Fensters)
    active_threads = {}  # thread_id -> (title, tag_set, last_date)
    for ep in episodes:
        thread_id = ep.get('thread')
        if not thread_id:
            continue

        try:
            ep_date = datetime.strptime(ep.get('date', ''), '%Y-%m-%d')
            days_ago = (now - ep_date).days
        except ValueError:
            continue

        if days_ago > close_after:
            continue  # Thread ist abgelaufen

        ep_tags = set(ep.get('tags', []))
        if thread_id in active_threads:
            _, existing_tags, _ = active_threads[thread_id]
            active_threads[thread_id] = (
                ep.get('thread_title', ''),
                existing_tags | ep_tags,
                ep.get('date', ''),
            )
        else:
            active_threads[thread_id] = (
                ep.get('thread_title', ''),
                ep_tags,
                ep.get('date', ''),
            )

    # Pruefe Overlap mit neuen Tags
    tag_set = set(tags)
    best_match = None
    best_overlap = 0

    for tid, (title, thread_tags, _) in active_threads.items():
        overlap = len(tag_set & thread_tags)
        if overlap >= 2 and overlap > best_overlap:
            best_match = (tid, title)
            best_overlap = overlap

    if best_match:
        return best_match

    # Kein Match → kein Thread (wird spaeter ggf. vom thread_manager erstellt)
    return None, None


# ================================================================
# Helper Functions
# ================================================================

def _generate_episode_id(episodes: list) -> str:
    """Generiert die naechste Episode-ID (E0001, E0002, ...)."""
    max_num = 0
    for ep in episodes:
        eid = ep.get('id', '')
        if eid.startswith('E') and eid[1:].isdigit():
            num = int(eid[1:])
            if num > max_num:
                max_num = num
    return f'E{max_num + 1:04d}'


def _extract_mentioned_persons(text: str) -> list[str]:
    """Extrahiert erwaehnte Personen aus dem Text.

    Einfache Heuristik: Grossgeschriebene Woerter die nicht am Satzanfang stehen
    und keine deutschen Nomen sind.
    """
    # Erstmal leer — wird spaeter durch contact_manager ersetzt
    return []


# ================================================================
# Episode Retrieval — fuer Prompt Builder
# ================================================================

def get_recent_episodes(egon_id: str, max_count: int = 8) -> list[dict]:
    """Holt die neuesten Episoden fuer den Prompt."""
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not episodes_data:
        return []

    episodes = episodes_data.get('episodes', [])
    try:
        episodes = sorted(episodes, key=lambda e: e.get('date', ''), reverse=True)
    except (TypeError, KeyError):
        pass

    return episodes[:max_count]


def get_thread_episodes(egon_id: str, thread_id: str) -> list[dict]:
    """Holt alle Episoden eines Threads."""
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not episodes_data:
        return []

    episodes = episodes_data.get('episodes', [])
    return [ep for ep in episodes if ep.get('thread') == thread_id]


def get_episodes_by_partner(egon_id: str, partner_id: str, max_count: int = 5) -> list[dict]:
    """Holt Episoden mit einem bestimmten Partner."""
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not episodes_data:
        return []

    episodes = episodes_data.get('episodes', [])
    partner_episodes = [ep for ep in episodes if ep.get('with') == partner_id]

    try:
        partner_episodes = sorted(
            partner_episodes, key=lambda e: e.get('date', ''), reverse=True,
        )
    except (TypeError, KeyError):
        pass

    return partner_episodes[:max_count]
