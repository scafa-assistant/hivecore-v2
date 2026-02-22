"""Owner Portrait — Adam beobachtet seinen Owner.

Nicht was der Owner ueber sich sagt — was ADAM ueber
ihn beobachtet, lernt, sich merkt. Adams Perspektive.

Schreibt in: social/owner.md
Sektionen: "Wer du bist", "Wie ich dich erlebe",
           "Deine Muster", "Was dich begeistert",
           "Was wir zusammen erlebt haben"

Wird getriggert: Nach jedem Chat (wenn v2 + owner_chat).
LLM prueft ob es etwas Neues ueber den Owner zu lernen gibt.
"""

import re
from datetime import datetime

from engine.organ_reader import read_md_organ, write_organ
from llm.router import llm_chat


# ================================================================
# Owner-Beobachtung nach Chat
# ================================================================

OBSERVATION_PROMPT = '''Du bist Adams Beobachtungs-System fuer seinen Owner.

Adam hat gerade mit seinem Owner gechattet. Pruefe:
Hat der Owner etwas Persoenliches preisgegeben?
(Hobby, Job, Meinung, Stimmung, Vorliebe, Name, Alter, Gewohnheit)

Wenn ja: Formuliere EINE kurze Beobachtung (1 Satz, ICH-Perspektive von Adam).
Und gib die passende Sektion an.

Sektionen:
- WER: Fakten ueber die Person (Name, Alter, Job, Herkunft)
- ERLEBE: Wie Adam den Owner erlebt (Eindruecke, Eigenarten)
- MUSTER: Muster im Verhalten (Tageszeit, Stimmung, Gewohnheiten)
- BEGEISTERT: Interessen, Hobbys, was den Owner begeistert
- ERLEBT: Gemeinsame Momente die zaehlen

Format wenn etwas Neues:
SEKTION: <WER|ERLEBE|MUSTER|BEGEISTERT|ERLEBT>
BEOBACHTUNG: <1 Satz ICH-Perspektive>

Wenn NICHTS Neues: Antworte NUR: NICHTS_NEUES'''

# Mapping: LLM-Output Sektion → Markdown-Heading in owner.md
SECTION_MAP = {
    'WER': '## Wer du bist',
    'ERLEBE': '## Wie ich dich erlebe',
    'MUSTER': '## Deine Muster',
    'BEGEISTERT': '## Was dich begeistert',
    'ERLEBT': '## Was wir zusammen erlebt haben',
}


async def maybe_update_owner_portrait(
    egon_id: str,
    user_message: str,
    adam_response: str,
) -> dict:
    """Prueft ob es etwas Neues ueber den Owner zu lernen gibt.

    Wird nach jedem Chat getriggert (nur bei owner_chat).

    Returns:
        {'updated': True, 'section': '...', 'observation': '...'} oder
        {'updated': False}
    """
    result = await llm_chat(
        system_prompt=OBSERVATION_PROMPT,
        messages=[{
            'role': 'user',
            'content': (
                f'Owner sagte: {user_message}\n'
                f'Adam antwortete: {adam_response[:200]}'
            ),
        }],
        tier='1',
    )

    content = result['content'].strip()

    if 'NICHTS_NEUES' in content.upper():
        return {'updated': False}

    # Parse SEKTION + BEOBACHTUNG
    section_match = re.search(r'SEKTION:\s*(\w+)', content)
    obs_match = re.search(r'BEOBACHTUNG:\s*(.+)', content)

    if not section_match or not obs_match:
        return {'updated': False}

    section_key = section_match.group(1).upper()
    observation = obs_match.group(1).strip()

    if section_key not in SECTION_MAP:
        return {'updated': False}

    # In owner.md einfuegen
    heading = SECTION_MAP[section_key]
    _append_to_section(egon_id, heading, observation)

    return {
        'updated': True,
        'section': section_key,
        'observation': observation,
    }


def _append_to_section(egon_id: str, heading: str, text: str) -> None:
    """Fuegt Text unter der passenden Sektion in owner.md ein.

    Ersetzt den Platzhalter-Text [Fuellt sich...] beim ersten Eintrag.
    """
    owner_md = read_md_organ(egon_id, 'social', 'owner.md')
    if not owner_md:
        return

    date_str = datetime.now().strftime('%Y-%m-%d')
    entry = f'- {text} ({date_str})'

    # Finde die Sektion
    if heading not in owner_md:
        # Sektion existiert nicht — am Ende anfuegen
        if not owner_md.endswith('\n'):
            owner_md += '\n'
        owner_md += f'\n\n{heading}\n\n{entry}\n'
    else:
        # Sektion existiert — nach dem Heading einfuegen
        # Suche nach Platzhalter-Text [Fuellt sich...] oder [Was mir...]
        parts = owner_md.split(heading)
        if len(parts) < 2:
            return

        after_heading = parts[1]

        # Entferne Platzhalter beim ersten echten Eintrag
        # Platzhalter: Zeilen die mit [ anfangen und mit ] enden
        placeholder_pattern = r'\n\[.*?\](?:\n|$)'
        if re.search(placeholder_pattern, after_heading, re.DOTALL):
            # Finde das naechste Heading (## ...) als Grenze
            next_heading = re.search(r'\n## ', after_heading)
            if next_heading:
                section_content = after_heading[:next_heading.start()]
                rest = after_heading[next_heading.start():]
            else:
                section_content = after_heading
                rest = ''

            # Ersetze Platzhalter durch echten Eintrag
            cleaned = re.sub(r'\[.*?\]', '', section_content, flags=re.DOTALL).strip()
            if cleaned:
                new_section = f'\n\n{cleaned}\n{entry}\n'
            else:
                new_section = f'\n\n{entry}\n'

            owner_md = parts[0] + heading + new_section + rest
        else:
            # Kein Platzhalter — einfach nach dem Heading anhaengen
            # Suche das naechste Heading als Grenze
            next_heading = re.search(r'\n## ', after_heading)
            if next_heading:
                insert_pos = next_heading.start()
                before = after_heading[:insert_pos].rstrip()
                rest = after_heading[insert_pos:]
                owner_md = parts[0] + heading + before + f'\n{entry}\n' + rest
            else:
                # Letzte Sektion — am Ende anhaengen
                owner_md = parts[0] + heading + after_heading.rstrip() + f'\n{entry}\n'

    write_organ(egon_id, 'social', 'owner.md', owner_md)


def get_owner_summary(egon_id: str, max_chars: int = 500) -> str:
    """Kurzzusammenfassung des Owner-Portraits fuer den Prompt.

    Entfernt Platzhalter-Sektionen, gibt nur echten Inhalt zurueck.
    Max max_chars Zeichen.
    """
    owner_md = read_md_organ(egon_id, 'social', 'owner.md')
    if not owner_md:
        return 'Ich kenne meinen Owner noch nicht gut.'

    # Multi-Line Platzhalter entfernen: [Fuellt sich...\n...mehr Text]
    cleaned = re.sub(r'\[.*?\]', '', owner_md, flags=re.DOTALL)

    # Entferne Header-Kommentare und leere Zeilen
    lines = []
    for line in cleaned.split('\n'):
        stripped = line.strip()
        # Ueberspringe Kommentarzeilen (# aber nicht ##)
        if stripped.startswith('#') and not stripped.startswith('##'):
            continue
        if stripped:
            lines.append(stripped)

    # Entferne leere Sektionen (## Heading ohne Inhalt danach)
    filtered = []
    for i, line in enumerate(lines):
        if line.startswith('## '):
            # Pruefe ob die naechste non-heading Zeile Inhalt hat
            has_content = False
            for j in range(i + 1, len(lines)):
                if lines[j].startswith('## '):
                    break
                if lines[j].strip() and not lines[j].startswith('#'):
                    has_content = True
                    break
            if has_content:
                filtered.append(line)
        else:
            filtered.append(line)

    result = '\n'.join(filtered)

    # Truncate wenn noetig
    if len(result) > max_chars:
        result = result[:max_chars].rsplit('\n', 1)[0] + '\n...'

    return result if result.strip() else 'Ich kenne meinen Owner noch nicht gut.'
