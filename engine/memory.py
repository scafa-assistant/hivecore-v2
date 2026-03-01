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


# Marker-Typ → deutsches Mood-Wort (fuer v1 Fallback)
_MOOD_MAP = {
    'joy': 'freudig', 'curiosity': 'neugierig',
    'excitement': 'aufgeregt', 'trust': 'vertrauensvoll',
    'pride': 'stolz', 'gratitude': 'dankbar',
    'warmth': 'warm', 'relief': 'erleichtert',
    'fear': 'aengstlich', 'anxiety': 'nervoes',
    'anger': 'veraergert', 'sadness': 'traurig',
    'frustration': 'frustriert', 'loneliness': 'einsam',
    'shame': 'beschaemt', 'disgust': 'angewidert',
    'surprise': 'ueberrascht', 'nostalgia': 'nostalgisch',
}


def _get_current_mood(egon_id: str) -> str:
    """Leite aktuelle Stimmung ab — v2: state.yaml, v1: hoechster Marker."""
    from config import BRAIN_VERSION

    # v2: Mood aus state.yaml lesen (NDCF 3-Tier System)
    if BRAIN_VERSION == 'v2':
        state_path = os.path.join(EGON_DATA_DIR, egon_id, 'core', 'state.yaml')
        if os.path.isfile(state_path):
            try:
                import yaml
                with open(state_path, 'r', encoding='utf-8') as f:
                    state = yaml.safe_load(f)
                thrive = state.get('thrive', {})
                mood_data = thrive.get('mood', {})
                # Verbal-Anchor bevorzugen (z.B. "Neugierig und aufgeregt")
                verbal = mood_data.get('verbal', '')
                if verbal:
                    return verbal
                # Fallback: mood.value → Wort-Mapping
                value = mood_data.get('value', 0.5)
                if value >= 0.8:
                    return 'sehr gut'
                if value >= 0.6:
                    return 'gut'
                if value >= 0.4:
                    return 'okay'
                if value >= 0.2:
                    return 'gedrueckt'
                return 'schlecht'
            except Exception:
                pass

    # v1 (oder v2-Fallback): Hoechsten aktiven Marker als Mood verwenden
    markers_path = os.path.join(EGON_DATA_DIR, egon_id, 'markers.md')
    if os.path.isfile(markers_path):
        with open(markers_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Alle Marker-Typen + Intensitaeten finden
        types = re.findall(r'type:\s*(\w+)', content)
        intensities = re.findall(r'intensity:\s*([\d.]+)', content)
        if types and intensities:
            pairs = list(zip(types, [float(i) for i in intensities]))
            pairs.sort(key=lambda x: x[1], reverse=True)
            top_type = pairs[0][0]
            return _MOOD_MAP.get(top_type, top_type)

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
