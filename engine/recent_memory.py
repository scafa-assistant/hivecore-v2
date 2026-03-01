"""Recent Memory — Kuerzliches Gedaechtnis (Patch 5).

Schicht 2 des 4-Schichten-Gedaechtnissystems.
Speichert Zusammenfassungen der letzten 7 Tage in skills/memory/recent_memory.md.
Wird IMMER in den System-Prompt geladen — loest das Chat-Key/Cross-Device Problem.

Erweitert um:
  - 28-Tage-Zyklus-Konsolidierung (cycle_memory → archive)
  - Mustertrennung (aehnliche Episoden mergen statt duplizieren)

Bio-Aequivalent: Hippocampus (frische Erinnerungen, noch nicht konsolidiert).
"""

import re
from datetime import datetime, timedelta

from engine.organ_reader import read_organ, write_organ, read_md_organ
from engine.organ_reader import read_yaml_organ, write_yaml_organ
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


# ================================================================
# 28-Tage-Zyklus-Konsolidierung (Patch 5)
# ================================================================

CONSOLIDATION_PROMPT = '''Du bist {egon_name}s Erinnerungs-Konsolidierer.
Verdichte diese {count} Tageseintraege zu einem Zyklusgedaechtnis.

{dna_focus}

Struktur (max 300 Worte, ICH-Perspektive):
1. Wichtigste Ereignisse (3-5 Saetze)
2. Beziehungsveraenderungen (Wer naeher? Wer entfernter?)
3. Was ich gelernt habe (Neue Erkenntnisse)
4. Offene Fragen (Was beschaeftigt mich noch?)

Kein Markdown. Natuerliche Sprache.'''

DNA_FOCUS = {
    'SEEKING/PLAY': 'Fokus: Was war NEU? Was habe ich gelernt? Was will ich noch entdecken?',
    'CARE/PANIC': 'Fokus: Wie haben sich Beziehungen veraendert? Wem bin ich naeher/ferner gekommen?',
    'DEFAULT': 'Ausgewogener Fokus: Ereignisse, Beziehungen, Erkenntnisse gleichgewichtet.',
}

ARCHIVE_PROMPT = '''Du bist {egon_name}s Langzeit-Archivar.
Komprimiere dieses Zyklusgedaechtnis zu einem Archiv-Eintrag.

Maximal 2-3 Saetze, ICH-Perspektive.
Was war der emotionale Kern dieses Zyklus?
Was muss ich mir fuer die Zukunft merken?

Am Ende: cue_tags: [tag1, tag2, tag3] (3-5 Tags die diesen Zyklus beschreiben)'''


async def zyklus_konsolidierung(egon_id: str) -> dict:
    """28-Tage-Zyklus-Konsolidierung.

    Tag 28: Sammelt pending_consolidation + aktive Eintraege aus recent_memory.md,
    komprimiert sie zu memory_cycle_current.md, archiviert den alten Zyklus.

    Wird aus langzeit_maintenance() aufgerufen.
    """
    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id, 'vorname')

    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    zyklus = state.get('zyklus', 0) if state else 0

    # DNA-Profil fuer fokussierte Konsolidierung
    dna_profile = state.get('dna_profile', 'DEFAULT') if state else 'DEFAULT'
    dna_focus = DNA_FOCUS.get(dna_profile, DNA_FOCUS['DEFAULT'])

    # Alle Eintraege aus recent_memory.md sammeln
    content = read_organ(egon_id, LAYER, FILENAME)
    if not content or not content.strip():
        return {'konsolidiert': False, 'reason': 'keine_eintraege'}

    blocks = content.split('\n---\n')
    all_summaries = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith('# '):
            if '## ' in block:
                block = block[block.index('## '):]
            else:
                continue
        # Datum + Text extrahieren
        date_match = re.search(r'## (\d{4}-\d{2}-\d{2})', block)
        date_str = date_match.group(1) if date_match else '?'
        # Status-Zeile entfernen
        text = re.sub(r'status: \w+', '', block).strip()
        text = re.sub(r'## \d{4}-\d{2}-\d{2} \d{2}:\d{2}', '', text).strip()
        if text:
            all_summaries.append(f'[{date_str}] {text}')

    if len(all_summaries) < 3:
        return {'konsolidiert': False, 'reason': 'zu_wenige_eintraege'}

    summaries_text = '\n'.join(all_summaries[-28:])  # Max 28 Tage

    # Altes Zyklusgedaechtnis → Archiv
    old_cycle = read_organ(egon_id, LAYER, 'memory/memory_cycle_current.md')
    if old_cycle and old_cycle.strip():
        await _archiviere_zyklus(egon_id, egon_name, old_cycle, zyklus - 1)

    # Neues Zyklusgedaechtnis generieren via LLM
    try:
        result = await llm_chat(
            system_prompt=CONSOLIDATION_PROMPT.format(
                egon_name=egon_name,
                count=len(all_summaries),
                dna_focus=dna_focus,
            ),
            messages=[{
                'role': 'user',
                'content': f'Meine Tageseintraege:\n{summaries_text[:2000]}',
            }],
            egon_id=egon_id,
        )
        cycle_text = result.get('content', '').strip()
    except Exception as e:
        print(f'[recent_memory] Konsolidierung LLM-Fehler: {e}')
        # Fallback: Erste und letzte 3 Eintraege
        cycle_text = '\n'.join(all_summaries[:3] + ['...'] + all_summaries[-3:])

    # Zyklusgedaechtnis schreiben
    header = f'# Zyklusgedaechtnis — Zyklus {zyklus}\n'
    header += f'Erstellt: {datetime.now().strftime("%Y-%m-%d")}\n\n'
    write_organ(egon_id, LAYER, 'memory/memory_cycle_current.md', header + cycle_text)

    # Recent Memory leeren (nur pending_consolidation entfernen, aktive behalten)
    _entferne_konsolidierte(egon_id)

    print(f'[recent_memory] {egon_id}: Zyklus {zyklus} konsolidiert '
          f'({len(all_summaries)} Eintraege → Zyklusgedaechtnis)')

    return {
        'konsolidiert': True,
        'eintraege': len(all_summaries),
        'zyklus': zyklus,
    }


async def _archiviere_zyklus(
    egon_id: str, egon_name: str, cycle_text: str, zyklus: int,
) -> None:
    """Komprimiert ein Zyklusgedaechtnis zu einem Archiv-Eintrag (~150 Tokens)."""
    try:
        result = await llm_chat(
            system_prompt=ARCHIVE_PROMPT.format(egon_name=egon_name),
            messages=[{
                'role': 'user',
                'content': f'Zyklusgedaechtnis:\n{cycle_text[:1000]}',
            }],
            egon_id=egon_id,
        )
        archive_text = result.get('content', '').strip()
    except Exception:
        archive_text = cycle_text[:200] + '...'

    # An memory_archive.md anhaengen
    existing_archive = read_organ(egon_id, LAYER, 'memory/memory_archive.md')
    if not existing_archive:
        existing_archive = '# Lebensarchiv\n\n'

    entry = f'\n## Zyklus {zyklus}\n{archive_text}\n---\n'
    write_organ(egon_id, LAYER, 'memory/memory_archive.md', existing_archive + entry)
    print(f'[recent_memory] {egon_id}: Zyklus {zyklus} archiviert')


def _entferne_konsolidierte(egon_id: str) -> None:
    """Entfernt pending_consolidation Eintraege aus recent_memory.md."""
    content = read_organ(egon_id, LAYER, FILENAME)
    if not content:
        return

    blocks = content.split('\n---\n')
    kept = [b for b in blocks if 'status: pending_consolidation' not in b]
    if len(kept) < len(blocks):
        write_organ(egon_id, LAYER, FILENAME, '\n---\n'.join(kept))


# ================================================================
# Mustertrennung — Pattern Separation (Patch 5)
# ================================================================

# DNA-abhaengige Merge-Schwellen
MERGE_SCHWELLE = {
    'SEEKING/PLAY': 0.80,   # Mergt leichter → "alles Routine"
    'CARE/PANIC': 0.70,     # Mergt weniger → "jedes Gespraech zaehlt"
    'DEFAULT': 0.75,
}


def mustertrennung(
    egon_id: str,
    neue_zusammenfassung: str,
    partner: str = '',
    cue_tags: list | None = None,
    emotional_delta: float = 0.0,
    prediction_error: float = 0.0,
) -> dict:
    """Prueft ob eine neue Erinnerung mit einer bestehenden gemerged werden sollte.

    Bio-Aequivalent: Dentate Gyrus — verhindert Interferenz aehnlicher Erinnerungen.

    Args:
        egon_id: Agent-ID.
        neue_zusammenfassung: Text der neuen Zusammenfassung.
        partner: Gespraechspartner-ID.
        cue_tags: Tags der neuen Zusammenfassung.
        emotional_delta: Emotionale Veraenderung (-1 bis +1).
        prediction_error: Ueberraschungs-Score (0.0-1.0).

    Returns:
        dict mit 'aktion': 'merge'|'append', 'merge_target': ID wenn merge.
    """
    if cue_tags is None:
        cue_tags = []

    # Sicherheitscheck: Hoher Prediction Error → NIEMALS mergen
    if prediction_error > 0.3:
        return {'aktion': 'append', 'grund': 'prediction_error_hoch'}

    # DNA-abhaengige Schwelle
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    dna_profile = state.get('dna_profile', 'DEFAULT') if state else 'DEFAULT'
    schwelle = MERGE_SCHWELLE.get(dna_profile, 0.75)

    # Recent Memory Eintraege der letzten 3 Tage laden
    content = read_organ(egon_id, LAYER, FILENAME)
    if not content:
        return {'aktion': 'append', 'grund': 'kein_recent_memory'}

    cutoff = datetime.now() - timedelta(days=3)
    blocks = content.split('\n---\n')
    neue_cues = set(cue_tags)

    for i, block in enumerate(blocks):
        if 'status: active' not in block:
            continue

        # Datum pruefen
        date_match = re.search(r'## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})', block)
        if date_match:
            try:
                entry_date = datetime.strptime(date_match.group(1), '%Y-%m-%d %H:%M')
                if entry_date < cutoff:
                    continue
            except ValueError:
                continue

        # 1. Gleicher Partner? (40%)
        gleicher_partner = 0.0
        if partner:
            if partner in block:
                gleicher_partner = 1.0

        # 2. Themen-Overlap (35%)
        # Einfacher Wort-Overlap als Proxy fuer cue_tags
        block_words = set(block.lower().split())
        if neue_cues:
            cue_overlap = len(neue_cues & block_words) / max(len(neue_cues), 1)
        else:
            # Wort-basierter Overlap
            neue_words = set(neue_zusammenfassung.lower().split())
            gemeinsam = neue_words & block_words
            cue_overlap = len(gemeinsam) / max(len(neue_words), 1)

        # 3. Aehnliche emotionale Bilanz (25%)
        emo_aehnlichkeit = max(0.0, 1.0 - abs(emotional_delta))

        # Gesamt-Aehnlichkeit
        aehnlichkeit = (
            gleicher_partner * 0.4
            + cue_overlap * 0.35
            + emo_aehnlichkeit * 0.25
        )

        if aehnlichkeit > schwelle:
            # MERGE: Bestehenden Eintrag erweitern
            # Anzahl Gespraeche tracken
            gespraeche_match = re.search(r'\((\d+) Gespraeche\)', block)
            count = int(gespraeche_match.group(1)) + 1 if gespraeche_match else 2

            # Block aktualisieren
            old_text = re.sub(r'status: active', '', block).strip()
            old_text = re.sub(r'## \d{4}-\d{2}-\d{2} \d{2}:\d{2}', '', old_text).strip()
            old_text = re.sub(r'\(\d+ Gespraeche\)', '', old_text).strip()

            merged_text = f'{old_text} + {neue_zusammenfassung[:100]} ({count} Gespraeche)'
            # Max ~300 Zeichen
            if len(merged_text) > 300:
                merged_text = merged_text[:280] + f'... ({count} Gespraeche)'

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            blocks[i] = f'## {timestamp}\n{merged_text}\nstatus: active'

            write_organ(egon_id, LAYER, FILENAME, '\n---\n'.join(blocks))
            print(f'[mustertrennung] {egon_id}: Merge (Aehnlichkeit {aehnlichkeit:.2f} > {schwelle})')

            return {
                'aktion': 'merge',
                'aehnlichkeit': round(aehnlichkeit, 2),
                'schwelle': schwelle,
                'gespraeche': count,
            }

    return {'aktion': 'append', 'grund': 'keine_aehnliche_erinnerung'}


def append_with_mustertrennung(
    egon_id: str,
    summary: str,
    partner: str = '',
    cue_tags: list | None = None,
    emotional_delta: float = 0.0,
    prediction_error: float = 0.0,
) -> dict:
    """Wrapper: Prueft Mustertrennung und appendet oder mergt.

    Ersetzt direkten Aufruf von append_to_recent_memory() in chat.py.
    """
    result = mustertrennung(
        egon_id, summary, partner, cue_tags, emotional_delta, prediction_error,
    )

    if result['aktion'] == 'append':
        append_to_recent_memory(egon_id, summary)

    return result
