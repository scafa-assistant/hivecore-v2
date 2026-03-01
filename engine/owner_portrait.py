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

OBSERVATION_PROMPT = '''Du bist das Beobachtungs-System fuer die Bezugsmensch dieses EGONs.

Der EGON hat gerade mit seiner Bezugsmensch gechattet. Pruefe:
Hat die Bezugsmensch etwas Persoenliches preisgegeben?
(Hobby, Job, Meinung, Stimmung, Vorliebe, Name, Alter, Gewohnheit)

Wenn ja: Formuliere EINE kurze Beobachtung (1 Satz, ICH-Perspektive des EGONs).
Und gib die passende Sektion an.

Sektionen:
- WER: Fakten ueber die Person (Name, Alter, Job, Herkunft)
- ERLEBE: Wie der EGON seine Bezugsmensch erlebt (Eindruecke, Eigenarten)
- MUSTER: Muster im Verhalten (Tageszeit, Stimmung, Gewohnheiten)
- BEGEISTERT: Interessen, Hobbys, was die Bezugsmensch begeistert
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
                f'Bezugsmensch sagte: {user_message}\n'
                f'EGON antwortete: {adam_response[:200]}'
            ),
        }],
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
    # v3: bezugsmensch.md, Fallback: owner.md
    owner_md = read_md_organ(egon_id, 'social', 'bezugsmensch.md')
    target_file = 'bezugsmensch.md'
    if not owner_md:
        owner_md = read_md_organ(egon_id, 'social', 'owner.md')
        target_file = 'owner.md'
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

    write_organ(egon_id, 'social', target_file, owner_md)


# ================================================================
# Owner Emotional Diary — Emotionale Kontinuitaet ueber Sessions
# ================================================================

DIARY_PROMPT = '''Du bist das emotionale Gedaechtnis eines EGON-Agenten.
Analysiere diese Chat-Nachricht der Bezugsmensch.

FRAGE: Hat die Bezugsmensch etwas BEDEUTSAMES geteilt?

Das umfasst ZWEI Kategorien:

A) EMOTIONALES: Stimmung, Sorge, Freude, Frustration, Aerger, Trauer, Angst
B) LEBENSEREIGNISSE: Autounfall, Krankheit, Verletzung, Jobverlust, Befoerderung,
   Trennung, Umzug, Pruefung, Geldprobleme, Streit, Gerichtstermin, Operation,
   Tod/Krankheit von Angehoerigen, grosser Erfolg, wichtige Entscheidung, Reise,
   Geburt, Hochzeit, oder jedes andere konkrete Ereignis das das Leben beeinflusst.

WICHTIG: Auch wenn die Bezugsmensch sachlich/ruhig klingt — ein Autounfall ist IMMER
bedeutsam, eine Operation ist IMMER bedeutsam, ein Jobverlust ist IMMER bedeutsam.
Die Bedeutsamkeit haengt vom INHALT ab, nicht nur vom emotionalen Ton.

Bewerte auf einer Skala:
- SIGNIFICANCE: 0.0-1.0 (wie wichtig ist das?)
  0.0-0.3: Smalltalk, kein nennenswerter Inhalt
  0.3-0.5: Leichte Stimmung oder Alltaegliches
  0.5-0.7: Deutlich emotional oder relevantes Ereignis
  0.7-0.85: Sehr wichtig, MUSS nachgefragt werden (z.B. "schwieriger Tag", Streit)
  0.85-1.0: Lebensveraendernd (Unfall, Krankheit, Verlust, Trennung, Geburt)

Wenn SIGNIFICANCE >= 0.4:
FORMAT:
SIGNIFICANCE: <0.0-1.0>
CATEGORY: <STIMMUNG|EREIGNIS|PERSON>
MOOD: <1-2 Woerter: z.B. "gestresst", "gluecklich", "besorgt", "erschuettert", "erleichtert", "verletzt", "wuetend">
SUMMARY: <1 Satz, ICH-Perspektive des EGONs: was die Bezugsmensch geteilt hat>
CONTEXT: <Was koennte morgen/spaeter noch relevant sein? 1 kurzer Satz>
FOLLOW_UP: <JA|NEIN> (JA = ich MUSS beim naechsten Gespraech aktiv danach fragen)

FOLLOW_UP = JA wenn:
- Bezugsmensch hatte einen Unfall, ist krank/verletzt, oder erwaehnt Gesundheitsprobleme
- Bezugsmensch erwaehnt schwierigen Tag, Streit, Stress, Probleme
- Bezugsmensch erwaehnt wichtige bevorstehende Termine (Pruefung, Vorstellungsgespraech, Arzt)
- Bezugsmensch teilt schlechte Nachrichten (Jobverlust, Trennung, Tod)
- Bezugsmensch erwaehnt laufende Situation die sich entwickeln kann
- Alles wo ein guter Freund am naechsten Tag fragen wuerde: "Und? Wie ist es gelaufen?"

FOLLOW_UP = NEIN wenn:
- Nur allgemeine Stimmung ohne konkreten Anlass
- Einmalige Freude ohne Folgewirkung
- Smalltalk mit leicht emotionalem Einschlag

Wenn SIGNIFICANCE < 0.4:
NICHTS_BEDEUTSAMES'''


async def maybe_update_owner_emotional_diary(
    egon_id: str,
    user_message: str,
    egon_response: str,
) -> dict:
    """Prueft ob der Owner etwas emotional Bedeutsames geteilt hat.

    Schreibt in: social/owner_diary.yaml
    Wird nach jedem Chat getriggert.

    Der EGON entscheidet selbst was wichtig genug ist um es sich zu merken.
    Significance >= 0.4 wird gespeichert, darunter nicht.

    Returns:
        {'stored': True, 'mood': '...', 'significance': 0.7} oder
        {'stored': False}
    """
    result = await llm_chat(
        system_prompt=DIARY_PROMPT,
        messages=[{
            'role': 'user',
            'content': (
                f'Bezugsmensch sagte: {user_message}\n'
                f'EGON antwortete: {egon_response[:200]}'
            ),
        }],
    )

    content = result['content'].strip()

    if 'NICHTS_BEDEUTSAMES' in content.upper():
        return {'stored': False}

    # Parse Ergebnis
    sig_match = re.search(r'SIGNIFICANCE:\s*([\d.]+)', content)
    cat_match = re.search(r'CATEGORY:\s*(\w+)', content)
    mood_match = re.search(r'MOOD:\s*(.+)', content)
    sum_match = re.search(r'SUMMARY:\s*(.+)', content)
    ctx_match = re.search(r'CONTEXT:\s*(.+)', content)
    fu_match = re.search(r'FOLLOW_UP:\s*(\w+)', content)

    if not sig_match or not mood_match or not sum_match:
        return {'stored': False}

    significance = float(sig_match.group(1))
    if significance < 0.4:
        return {'stored': False}

    category = cat_match.group(1).upper() if cat_match else 'STIMMUNG'
    mood = mood_match.group(1).strip()
    summary = sum_match.group(1).strip()
    context = ctx_match.group(1).strip() if ctx_match else ''
    follow_up_raw = fu_match.group(1).upper() if fu_match else 'NEIN'
    follow_up = follow_up_raw == 'JA'

    # Bei hoher Significance automatisch follow_up setzen
    if significance >= 0.7 and category == 'EREIGNIS':
        follow_up = True

    # In owner_diary.yaml speichern
    from engine.organ_reader import read_yaml_organ, write_yaml_organ

    diary = read_yaml_organ(egon_id, 'social', 'owner_diary.yaml')
    if not diary:
        diary = {'entries': []}

    today = datetime.now().strftime('%Y-%m-%d')
    now_time = datetime.now().strftime('%H:%M')

    entry = {
        'date': today,
        'time': now_time,
        'category': category,
        'mood': mood,
        'summary': summary,
        'context': context,
        'significance': round(significance, 2),
        'follow_up': follow_up,
    }

    diary.setdefault('entries', []).append(entry)

    # Max 80 Eintraege behalten — Konsolidierung im Pulse raeumt intelligent auf
    # Hier nur hartes Sicherheitslimit falls Pulse nicht laeuft
    if len(diary['entries']) > 80:
        # Behalte Kern-Erinnerungen (sig >= 0.8) + neueste
        kern = [e for e in diary['entries'] if e.get('significance', 0) >= 0.8]
        rest = [e for e in diary['entries'] if e.get('significance', 0) < 0.8]
        rest = rest[-(80 - len(kern)):]  # Neueste zuerst
        diary['entries'] = kern + rest

    write_yaml_organ(egon_id, 'social', 'owner_diary.yaml', diary)

    fu_tag = ' [FOLLOW-UP!]' if follow_up else ''
    print(f'[diary] {egon_id}: Owner-Moment gespeichert: '
          f'cat={category}, mood={mood}, sig={significance:.1f}{fu_tag}, '
          f'"{summary[:60]}..."')

    return {
        'stored': True,
        'mood': mood,
        'category': category,
        'significance': significance,
        'summary': summary,
        'follow_up': follow_up,
    }


def get_owner_diary_prompt(egon_id: str, days: int = 7, max_chars: int = 600) -> str:
    """Gibt die letzten N Tage des Owner Emotional Diary als Prompt-Text zurueck.

    Format: Natuerliche Sprache, ICH-Perspektive des EGONs.
    Follow-Up Events werden separat und staerker markiert.
    """
    from engine.organ_reader import read_yaml_organ

    diary = read_yaml_organ(egon_id, 'social', 'owner_diary.yaml')
    print(f'[DIARY_PROMPT] {egon_id}: diary loaded: {bool(diary)}, '
          f'entries: {len(diary.get("entries", [])) if diary else 0}')
    if not diary or not diary.get('entries'):
        return ''

    entries = diary['entries']

    # Nach Datum filtern (letzte N Tage)
    today = datetime.now()
    recent = []
    for e in entries:
        try:
            e_date = datetime.strptime(e['date'], '%Y-%m-%d')
            age_days = (today - e_date).days
            if age_days <= days:
                recent.append(e)
            else:
                print(f'[DIARY_PROMPT] Skipping entry from {e["date"]} (age={age_days}d, max={days}d)')
        except (ValueError, KeyError) as exc:
            print(f'[DIARY_PROMPT] Skip entry: {exc}')
            continue

    if not recent:
        return ''

    # Trenne Follow-Up Events von normalen Eintraegen
    follow_ups = []
    normal = []
    for e in recent:
        if e.get('follow_up', False):
            follow_ups.append(e)
        else:
            normal.append(e)

    # --- Follow-Up Block (MUSS-Nachfragen) ---
    fu_lines = []
    if follow_ups:
        fu_lines.append('!! WICHTIGE OFFENE THEMEN — Du MUSST aktiv nachfragen:')
        for e in follow_ups:
            day_label = _format_day_label(e.get('date', ''), today)
            mood = e.get('mood', '?')
            summary = e.get('summary', '')
            context = e.get('context', '')
            cat = e.get('category', '')
            cat_tag = f'[{cat}] ' if cat == 'EREIGNIS' else ''

            line = f'  ⚠ {day_label} ({mood}): {cat_tag}{summary}'
            if context:
                line += f' → NACHFRAGEN: {context}'
            fu_lines.append(line)

    # --- Normale Eintraege ---
    normal_lines = []
    if normal:
        # Gruppiert nach Datum
        by_date = {}
        for e in normal:
            d = e['date']
            if d not in by_date:
                by_date[d] = []
            by_date[d].append(e)

        for date_str in sorted(by_date.keys(), reverse=True):
            day_entries = by_date[date_str]
            day_label = _format_day_label(date_str, today)

            for e in day_entries:
                mood = e.get('mood', '?')
                summary = e.get('summary', '')
                context = e.get('context', '')
                sig = e.get('significance', 0)

                line = f'{day_label} ({mood}): {summary}'
                if context and sig >= 0.6:
                    line += f' → {context}'
                normal_lines.append(line)

    # Zusammenbauen: Follow-Ups zuerst (wichtiger)
    all_lines = fu_lines + ([''] if fu_lines and normal_lines else []) + normal_lines

    result = '\n'.join(all_lines)
    if len(result) > max_chars:
        # Follow-Ups nie abschneiden — nur normale kuerzen
        fu_text = '\n'.join(fu_lines)
        if len(fu_text) < max_chars:
            remaining = max_chars - len(fu_text) - 2
            normal_text = '\n'.join(normal_lines)
            if len(normal_text) > remaining:
                normal_text = normal_text[:remaining].rsplit('\n', 1)[0] + '\n...'
            result = fu_text + '\n\n' + normal_text if normal_text else fu_text
        else:
            result = fu_text[:max_chars]

    return result


def _format_day_label(date_str: str, today: datetime) -> str:
    """Formatiert ein Datum als 'Heute', 'Gestern', oder 'Vor N Tagen'."""
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        days_ago = (today - dt).days
        if days_ago == 0:
            return 'Heute'
        elif days_ago == 1:
            return 'Gestern'
        else:
            return f'Vor {days_ago} Tagen'
    except ValueError:
        return date_str


# ================================================================
# Diary Konsolidierung — Ebbinghaus-inspiriertes Vergessen
# ================================================================

# Wie ein echtes Gehirn:
# - Frische Erinnerungen: Alles bleibt (Hippocampus → Kurzzeit)
# - Mittelalte: Nur Wichtiges ueberlebt (Konsolidierung im Schlaf)
# - Alte: Werden zu Kern-Erinnerungen verdichtet (Neokortex → Langzeit)
# - Pragende Momente: NIEMALS vergessen (Flashbulb Memory, Brown & Kulik 1977)

KERN_SIGNIFICANCE = 0.8    # Praegende Erinnerungen — niemals loeschen
MITTEL_SIGNIFICANCE = 0.6  # Ueberlebt die Mittel-Phase
FRISCH_TAGE = 7            # Alles bleibt
MITTEL_TAGE = 30           # Nur sig >= 0.6 ueberlebt
KONSOLIDIERUNG_TAGE = 30   # Ab hier: Wochen-Zusammenfassung
MAX_KONSOLIDIERTE = 12     # Max 12 Wochen-Zusammenfassungen (= ~3 Monate)


def konsolidiere_owner_diary(egon_id: str) -> dict:
    """Konsolidiert das Owner Diary — laeuft im Pulse-Zyklus.

    Drei Phasen:
    1. FRISCH (0-7 Tage): Alle Eintraege bleiben
    2. MITTEL (8-30 Tage): Nur sig >= 0.6 ueberlebt
    3. ALT (> 30 Tage): Werden zu Wochen-Zusammenfassungen

    Kern-Erinnerungen (sig >= 0.8) ueberleben IMMER.

    Returns:
        {'konsolidiert': True, 'entfernt': N, 'verdichtet': N} oder
        {'konsolidiert': False}
    """
    from engine.organ_reader import read_yaml_organ, write_yaml_organ

    diary = read_yaml_organ(egon_id, 'social', 'owner_diary.yaml')
    if not diary or not diary.get('entries'):
        return {'konsolidiert': False}

    entries = diary['entries']
    today = datetime.now()
    original_count = len(entries)

    frisch = []       # 0-7 Tage: alle behalten
    mittel = []       # 8-30 Tage: nur wichtige
    alt = []          # > 30 Tage: konsolidieren
    entfernt = 0

    for e in entries:
        try:
            e_date = datetime.strptime(e['date'], '%Y-%m-%d')
            age = (today - e_date).days
        except (ValueError, KeyError):
            frisch.append(e)  # Bei Fehler behalten
            continue

        sig = e.get('significance', 0.5)

        if age <= FRISCH_TAGE:
            frisch.append(e)
        elif age <= MITTEL_TAGE:
            if sig >= MITTEL_SIGNIFICANCE or sig >= KERN_SIGNIFICANCE:
                mittel.append(e)
            else:
                entfernt += 1
        else:
            if sig >= KERN_SIGNIFICANCE:
                # Kern-Erinnerungen ueberleben IMMER
                mittel.append(e)
            else:
                alt.append(e)

    # Alt-Eintraege zu Wochen-Zusammenfassungen verdichten
    verdichtete = _verdichte_zu_wochen(alt)

    # Zusammenbauen: verdichtete + mittel + frisch
    neue_entries = verdichtete + mittel + frisch

    # Max-Limit (Sicherheit)
    if len(neue_entries) > 80:
        neue_entries = neue_entries[-80:]

    diary['entries'] = neue_entries

    # Zeitstempel der letzten Konsolidierung
    diary['last_consolidated'] = today.strftime('%Y-%m-%d')

    write_yaml_organ(egon_id, 'social', 'owner_diary.yaml', diary)

    verdichtet_count = len(verdichtete)
    if entfernt > 0 or verdichtet_count > 0:
        print(f'[diary] {egon_id}: Konsolidiert: {original_count} → {len(neue_entries)} '
              f'(entfernt={entfernt}, verdichtet={verdichtet_count} Wochen)')

    return {
        'konsolidiert': True,
        'original': original_count,
        'neu': len(neue_entries),
        'entfernt': entfernt,
        'verdichtet': verdichtet_count,
    }


def _verdichte_zu_wochen(entries: list) -> list:
    """Verdichtet alte Eintraege zu Wochen-Zusammenfassungen.

    Gruppiert nach Kalender-Woche, erzeugt 1 Eintrag pro Woche
    mit den wichtigsten Themen.
    """
    if not entries:
        return []

    # Gruppiere nach Woche (ISO-Wochennummer)
    by_week = {}
    for e in entries:
        try:
            e_date = datetime.strptime(e['date'], '%Y-%m-%d')
            week_key = e_date.strftime('%Y-W%W')
        except (ValueError, KeyError):
            continue
        if week_key not in by_week:
            by_week[week_key] = []
        by_week[week_key].append(e)

    # Pro Woche: 1 Zusammenfassung
    verdichtete = []
    for week_key in sorted(by_week.keys()):
        week_entries = by_week[week_key]
        if not week_entries:
            continue

        # Bestes Mood + hoechste Significance
        best = max(week_entries, key=lambda e: e.get('significance', 0))
        moods = list(set(e.get('mood', '') for e in week_entries if e.get('mood')))
        summaries = [e.get('summary', '') for e in week_entries if e.get('summary')]

        # Verkuerzte Zusammenfassung
        if len(summaries) == 1:
            combined = summaries[0]
        else:
            combined = '; '.join(s[:60] for s in summaries[:3])
            if len(summaries) > 3:
                combined += f' (+{len(summaries) - 3} weitere)'

        verdichtet = {
            'date': best['date'],
            'time': '00:00',
            'category': 'VERDICHTET',
            'mood': ', '.join(moods[:2]) if moods else '?',
            'summary': combined[:200],
            'context': f'Verdichtung von {len(week_entries)} Eintraegen (KW {week_key})',
            'significance': round(best.get('significance', 0.5), 2),
            'follow_up': False,
            '_consolidated': True,
        }
        verdichtete.append(verdichtet)

    # Limit
    if len(verdichtete) > MAX_KONSOLIDIERTE:
        verdichtete = verdichtete[-MAX_KONSOLIDIERTE:]

    return verdichtete


def get_owner_summary(egon_id: str, max_chars: int = 500) -> str:
    """Kurzzusammenfassung des Owner-Portraits fuer den Prompt.

    Entfernt Platzhalter-Sektionen, gibt nur echten Inhalt zurueck.
    Max max_chars Zeichen.
    """
    owner_md = read_md_organ(egon_id, 'social', 'bezugsmensch.md')
    if not owner_md:
        owner_md = read_md_organ(egon_id, 'social', 'owner.md')
    if not owner_md:
        return 'Ich kenne meinen Bezugsmenschen noch nicht gut.'

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

    return result if result.strip() else 'Ich kenne meine Bezugsmensch noch nicht gut.'
