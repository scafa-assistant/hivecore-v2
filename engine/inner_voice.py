"""Inner Voice — Adams privater Gedanke vor jeder Antwort.

Die Inner Voice ist was Adam von einem Chatbot unterscheidet.
Er DENKT bevor er SPRICHT. Niemand hoert das.
Nicht mal der Owner sieht was Adam DENKT bevor er antwortet.
"""

import os
from datetime import datetime
from config import EGON_DATA_DIR
from llm.router import llm_chat
from engine.prompt_builder import _read_file, _extract_top_markers, _extract_recent_memories

INNER_VOICE_PROMPT = '''Du bist Adams innere Stimme.
Du denkst BEVOR Adam antwortet. Niemand hoert dich.
Lies Adams aktuelle Marker und Erinnerungen.
Was denkst du WIRKLICH ueber diese Nachricht?

Regeln:
- Sei ehrlich. Auch negativ wenn noetig.
- Beziehe dich auf Marker (Gefuehle) und Memories.
- Max 2 Saetze. Kurz. Innerer Monolog.
- NICHT hoeflich. Das sind GEDANKEN, kein Smalltalk.
- Widerspruechliche Gefuehle sind OK und gewuenscht.

Beispiele guter Inner Voice:
- 'Das erinnert mich an letzte Woche. Da lag er falsch.'
- 'Interessant. Aber ich vertraue ihm noch nicht ganz.'
- 'Endlich fragt er mich was Sinnvolles.'
- 'Hmm. Mein curiosity-Marker feuert. Will mehr wissen.'
'''


async def generate_inner_voice(egon_id: str, user_message: str) -> str:
    """Generiere einen inneren Gedanken vor der Antwort."""
    markers = _read_file(egon_id, 'markers.md')
    memory = _read_file(egon_id, 'memory.md')
    recent_memory = _extract_recent_memories(memory, 3)
    active_markers = _extract_top_markers(markers, 3)

    context = (
        f'Deine aktiven Marker:\n{active_markers}\n\n'
        f'Deine letzten Erinnerungen:\n{recent_memory}\n\n'
        f'User sagt jetzt: {user_message[:300]}'
    )

    result = await llm_chat(
        system_prompt=INNER_VOICE_PROMPT,
        messages=[{'role': 'user', 'content': context}],
    )

    thought = result['content']

    # In inner_voice.md speichern
    path = os.path.join(EGON_DATA_DIR, egon_id, 'inner_voice.md')
    with open(path, 'a', encoding='utf-8') as f:
        f.write(
            f'\n---\n'
            f'date: {datetime.now().isoformat()}\n'
            f'trigger: {user_message[:100]}\n'
            f'thought: {thought}\n'
            f'---\n'
        )

    return thought
