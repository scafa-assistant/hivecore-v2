"""Recent Memory — Kuerzliches Gedaechtnis (Patch 5 Phase 1).

Schicht 2 des 4-Schichten-Gedaechtnissystems.
Speichert Zusammenfassungen der letzten 7 Tage in skills/memory/recent_memory.md.
Wird IMMER in den System-Prompt geladen — loest das Chat-Key/Cross-Device Problem.

Bio-Aequivalent: Hippocampus (frische Erinnerungen, noch nicht konsolidiert).
"""

import re
from datetime import datetime, timedelta

from engine.organ_reader import read_organ, write_organ, read_md_organ
from llm.router import llm_chat

LAYER = 'skills'
FILENAME = 'memory/recent_memory.md'

SUMMARY_PROMPT = (
    'Fasse dieses Gespraech in 2-3 Saetzen zusammen. '
    'Schreibe aus der Ich-Perspektive von {egon_name}. '
    'Fokus: Was war emotional wichtig? Was hat sich veraendert? '
    'Maximal 100 Tokens. Kein Markdown. Keine Aufzaehlungen.'
)


async def generate_chat_summary(
    egon_id: str, user_msg: str, egon_response: str,
) -> str:
    """Generiert eine ~100 Token Zusammenfassung eines Gespraechs.

    Nutzt Tier 1 (Moonshot) — guenstigster LLM-Call.
    """
    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id)

    result = await llm_chat(
        system_prompt=SUMMARY_PROMPT.format(egon_name=egon_name),
        messages=[{
            'role': 'user',
            'content': f'User: {user_msg[:500]}\n{egon_name}: {egon_response[:500]}',
        }],
        tier='1',
        egon_id=egon_id,
    )
    return result.get('content', '').strip()


def append_to_recent_memory(egon_id: str, summary: str) -> None:
    """Haengt eine Zusammenfassung an recent_memory.md an.

    Fuehrt vorher cleanup_old_entries() aus (7-Tage Bereinigung).
    """
    cleanup_old_entries(egon_id)

    existing = read_organ(egon_id, LAYER, FILENAME)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    entry = f'\n## {timestamp}\n{summary}\nstatus: active\n---\n'

    write_organ(egon_id, LAYER, FILENAME, existing + entry)
    print(f'[recent_memory] Eintrag fuer {egon_id}: {summary[:60]}')


def load_recent_memory(egon_id: str) -> str:
    """Laedt recent_memory.md und filtert nur aktive Eintraege.

    Returns:
        Gefilterter Markdown-Text (nur status: active), oder '' wenn leer.
    """
    content = read_md_organ(egon_id, LAYER, FILENAME)
    if not content or not content.strip():
        return ''

    # Parse Eintraege (getrennt durch ---)
    blocks = re.split(r'\n---\n', content)
    active = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Header-Zeile entfernen (z.B. "# Kuerzliches Gedaechtnis")
        if block.startswith('# ') and '## ' in block:
            block = block[block.index('## '):].strip()
        elif block.startswith('# '):
            continue
        if 'status: pending_consolidation' in block:
            continue
        # Aktive Eintraege (status: active oder kein expliziter Status)
        active.append(block)

    if not active:
        return ''

    return '\n---\n'.join(active)


def cleanup_old_entries(egon_id: str, max_days: int = 7) -> None:
    """Markiert Eintraege aelter als max_days als pending_consolidation.

    Eintraege mit status: active und Datum > 7 Tage
    werden zu status: pending_consolidation geaendert.
    """
    content = read_organ(egon_id, LAYER, FILENAME)
    if not content or not content.strip():
        return

    cutoff = datetime.now() - timedelta(days=max_days)
    blocks = content.split('\n---\n')
    changed = False
    new_blocks = []

    for block in blocks:
        if 'status: active' not in block:
            new_blocks.append(block)
            continue

        # Datum aus ## YYYY-MM-DD HH:MM Header extrahieren
        date_match = re.search(r'## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})', block)
        if date_match:
            try:
                entry_date = datetime.strptime(date_match.group(1), '%Y-%m-%d %H:%M')
                if entry_date < cutoff:
                    block = block.replace('status: active', 'status: pending_consolidation')
                    changed = True
            except ValueError:
                pass

        new_blocks.append(block)

    if changed:
        write_organ(egon_id, LAYER, FILENAME, '\n---\n'.join(new_blocks))
        print(f'[recent_memory] Cleanup fuer {egon_id}: alte Eintraege markiert')
