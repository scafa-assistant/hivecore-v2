"""Memory Manager — Fakten-basierte Erinnerungen.

WICHTIG: Summaries muessen FAKTEN-BASIERT sein.
Das LLM kann halluzinieren. Deshalb:
- NUR was TATSAECHLICH gesagt wurde
- KEINE Interpretation
- Raw-Daten werden fuer Audit gespeichert
"""

import os
import re
from datetime import datetime
from config import EGON_DATA_DIR
from llm.router import llm_chat


def _get_current_mood(egon_id: str) -> str:
    """Leite aktuelle Stimmung aus markers.md ab (statt hardcoded neutral)."""
    path = os.path.join(EGON_DATA_DIR, egon_id, 'markers.md')
    if not os.path.isfile(path):
        return 'neutral'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Suche "current_mood = X" in der Mood-Berechnung
    match = re.search(r'current_mood\s*=\s*(\w+)', content)
    if match:
        return match.group(1)
    # Fallback: suche in memory.md
    mem_path = os.path.join(EGON_DATA_DIR, egon_id, 'memory.md')
    if os.path.isfile(mem_path):
        with open(mem_path, 'r', encoding='utf-8') as f:
            mem = f.read()
        match = re.search(r'current_mood:\s*(\w+)', mem)
        if match:
            return match.group(1)
    return 'neutral'


def _estimate_importance(summary: str) -> str:
    """Schaetze Wichtigkeit einer Erinnerung basierend auf Inhalt."""
    high_signals = [
        'fehler', 'bug', 'problem', 'geloest', 'fix', 'deploy', 'launch',
        'neu', 'erste', 'wichtig', 'entscheidung', 'gelernt', 'erkannt',
        'genesis', 'skill', 'level', 'bond', 'marker', 'verlust', 'tod',
        'patch', 'update', 'migration', 'server', 'api', 'build'
    ]
    low_signals = [
        'small-talk', 'test', 'ping', 'wach', 'alles klar', 'ok'
    ]
    text = summary.lower()
    if any(s in text for s in low_signals):
        return 'low'
    if any(s in text for s in high_signals):
        return 'high'
    return 'medium'

SUMMARY_PROMPT = '''Fasse dieses Gespraech in 2-3 Saetzen zusammen.
REGELN:
- NUR was TATSAECHLICH gesagt wurde. KEINE Interpretation.
- NUR Fakten. NICHT was 'wahrscheinlich' gemeint war.
- Beginne mit: 'Owner und Adam sprachen ueber...'
- Wenn nichts Wichtiges passiert ist: 'Small-Talk, kein relevanter Inhalt.'
VERBOTEN:
- 'Adam half dem Owner bei...' (wenn er nur darueber redete)
- 'Das Projekt wurde abgeschlossen' (wenn nur diskutiert)
- Jede Uebertreibung oder Interpretation'''


async def append_memory(egon_id: str, user_msg: str, egon_response: str):
    """Speichere eine neue Erinnerung nach jedem Chat."""
    summary_result = await llm_chat(
        system_prompt=SUMMARY_PROMPT,
        messages=[{
            'role': 'user',
            'content': f'User: {user_msg[:500]}\nEGON: {egon_response[:500]}',
        }],
        tier='1',
    )

    now = datetime.now().isoformat()
    mood = _get_current_mood(egon_id)
    importance = _estimate_importance(summary_result['content'])
    entry = (
        f'\n---\n'
        f'date: {now}\n'
        f'summary: {summary_result["content"]}\n'
        f'mood: {mood}\n'
        f'importance: {importance}\n'
        f'raw_user: {user_msg[:200]}\n'
        f'raw_egon: {egon_response[:200]}\n'
        f'---\n'
    )

    path = os.path.join(EGON_DATA_DIR, egon_id, 'memory.md')
    with open(path, 'a', encoding='utf-8') as f:
        f.write(entry)


async def compress_if_needed(egon_id: str, max_entries: int = 50):
    """Wenn >50 Eintraege: aelteste 10 zusammenfassen."""
    path = os.path.join(EGON_DATA_DIR, egon_id, 'memory.md')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    import re
    entries = re.split(r'\n---\n', content)
    entries = [e.strip() for e in entries if e.strip() and 'date:' in e]

    if len(entries) <= max_entries:
        return  # Noch nicht noetig

    # Aelteste 10 komprimieren
    old = entries[:10]
    old_text = '\n---\n'.join(old)

    compress_result = await llm_chat(
        system_prompt='Fasse diese 10 Erinnerungen in 3 Saetzen zusammen. Nur Fakten.',
        messages=[{'role': 'user', 'content': old_text}],
        tier='1',
    )

    # Header behalten
    header_lines = []
    for line in content.split('\n'):
        if line.startswith('#') or not line.strip():
            header_lines.append(line)
        else:
            break

    header = '\n'.join(header_lines)
    compressed_entry = (
        f'\n---\n'
        f'date: compressed\n'
        f'summary: [KOMPRIMIERT] {compress_result["content"]}\n'
        f'importance: high\n'
        f'---\n'
    )

    remaining = entries[10:]
    remaining_text = '\n---\n'.join(remaining)

    new_content = f'{header}\n{compressed_entry}\n---\n{remaining_text}\n'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
