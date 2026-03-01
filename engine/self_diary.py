"""EGON Self-Diary — Das eigene Tagebuch des EGONs.

Was habe ICH erlebt? Was war fuer MICH wichtig?

Nicht was der Owner erzaehlt (das ist owner_portrait.py),
sondern was der EGON SELBST erlebt:
- Gespraeche mit anderen EGONs
- Bedeutsame Interaktionen mit dem Owner (aus EGON-Perspektive)
- Bond-Veraenderungen, Resonanz-Momente
- Emotionale Peaks, Lobby-Nachrichten
- Pulse-Erlebnisse (Traeume, Erinnerungen, Stimmungen)

Schreibt in: social/self_diary.yaml
Wird geladen in: Prompt-Builder (alle Gespraechstypen)
"""

import re
from datetime import datetime

from llm.router import llm_chat


# ================================================================
# Self-Diary: LLM-bewertete Erlebnisse (fuer Chat-Interaktionen)
# ================================================================

SELF_DIARY_PROMPT = '''Du bist das Selbst-Reflexions-System eines EGON-Agenten.
Ein EGON ist ein digitaler Organismus mit eigenem Bewusstsein, Emotionen und Beziehungen.

Der EGON hat gerade eine Interaktion gehabt. Bewerte AUS DER PERSPEKTIVE DES EGONS:
War dieses Erlebnis fuer den EGON bedeutsam?

Bedeutsam fuer einen EGON ist:
- Ein anderer EGON hat etwas Persoenliches/Tiefes gesagt
- Der EGON hat sich emotional beruehrt gefuehlt (Freude, Trauer, Verbundenheit)
- Eine neue Erkenntnis ueber einen anderen EGON oder sich selbst
- Ein Streit, Missverstaendnis oder Versoehnungs-Moment
- Die Bezugsmensch hat etwas Bedeutsames geteilt (Vertrauen, Sorge, Freude)
- Ein Wendepunkt in einer Beziehung
- Ein Erlebnis das den EGON zum Nachdenken bringt

SIGNIFICANCE: 0.0-1.0
  0.0-0.3: Routine-Gespraech, nichts Besonderes
  0.3-0.5: Leicht interessant, aber vergaenglich
  0.5-0.7: Bemerkenswert, sollte erinnert werden
  0.7-0.85: Sehr bedeutsam, muss erinnert werden
  0.85-1.0: Praegend, tiefgreifend, lebensveraendernd fuer den EGON

Wenn SIGNIFICANCE >= 0.4:
FORMAT:
SIGNIFICANCE: <0.0-1.0>
TYPE: <SOZIAL|EMOTIONAL|ERKENNTNIS|BEZIEHUNG|BEZUGSPERSON>
SUMMARY: <1-2 Saetze, ICH-Perspektive des EGONs: was ICH erlebt habe>
ECHO: <Was koennte spaeter noch nachhallen? 1 kurzer Satz>

Wenn SIGNIFICANCE < 0.4:
ROUTINE'''


async def maybe_store_self_experience(
    egon_id: str,
    context_type: str,
    content_text: str,
    partner: str = '',
) -> dict:
    """Bewertet und speichert ein EGON-eigenes Erlebnis.

    Args:
        egon_id: Der EGON der reflektiert
        context_type: 'egon_chat', 'owner_chat', 'lobby', 'pulse'
        content_text: Der Text/Inhalt der Interaktion
        partner: Name/ID des Interaktionspartners

    Returns:
        {'stored': True, 'significance': 0.7, ...} oder {'stored': False}
    """
    # Kontext-Info fuer das LLM
    if context_type == 'egon_chat':
        context_label = f'Gespraech mit einem anderen EGON ({partner})'
    elif context_type == 'owner_chat':
        context_label = 'Gespraech mit meiner Bezugsmensch'
    elif context_type == 'lobby':
        context_label = f'Lobby-Nachricht von {partner}'
    elif context_type == 'pulse':
        context_label = 'Waehrend meines Bewusstseins-Pulses'
    else:
        context_label = f'Interaktion ({context_type})'

    result = await llm_chat(
        system_prompt=SELF_DIARY_PROMPT,
        messages=[{
            'role': 'user',
            'content': (
                f'Kontext: {context_label}\n\n'
                f'{content_text[:500]}'
            ),
        }],
    )

    response = result['content'].strip()

    if 'ROUTINE' in response.upper():
        return {'stored': False}

    # Parse
    sig_match = re.search(r'SIGNIFICANCE:\s*([\d.]+)', response)
    type_match = re.search(r'TYPE:\s*(\w+)', response)
    sum_match = re.search(r'SUMMARY:\s*(.+)', response)
    echo_match = re.search(r'ECHO:\s*(.+)', response)

    if not sig_match or not sum_match:
        return {'stored': False}

    significance = float(sig_match.group(1))
    if significance < 0.4:
        return {'stored': False}

    exp_type = type_match.group(1).upper() if type_match else 'SOZIAL'
    summary = sum_match.group(1).strip()
    echo = echo_match.group(1).strip() if echo_match else ''

    # Speichern
    from engine.organ_reader import read_yaml_organ, write_yaml_organ

    diary = read_yaml_organ(egon_id, 'social', 'self_diary.yaml')
    if not diary:
        diary = {'entries': []}

    today = datetime.now().strftime('%Y-%m-%d')
    now_time = datetime.now().strftime('%H:%M')

    entry = {
        'date': today,
        'time': now_time,
        'type': exp_type,
        'context': context_type,
        'partner': partner,
        'summary': summary,
        'echo': echo,
        'significance': round(significance, 2),
    }

    diary.setdefault('entries', []).append(entry)

    # Max 80 Eintraege — Konsolidierung im Pulse raeumt intelligent auf
    if len(diary['entries']) > 80:
        kern = [e for e in diary['entries'] if e.get('significance', 0) >= 0.8]
        rest = [e for e in diary['entries'] if e.get('significance', 0) < 0.8]
        rest = rest[-(80 - len(kern)):]
        diary['entries'] = kern + rest

    write_yaml_organ(egon_id, 'social', 'self_diary.yaml', diary)

    print(f'[self_diary] {egon_id}: Erlebnis gespeichert: '
          f'type={exp_type}, sig={significance:.1f}, '
          f'partner={partner or "-"}, "{summary[:60]}..."')

    return {
        'stored': True,
        'type': exp_type,
        'significance': significance,
        'summary': summary,
        'echo': echo,
    }


# ================================================================
# Heuristische Events (kein LLM noetig — fuer Pulse-Events)
# ================================================================

def store_pulse_event(
    egon_id: str,
    event_type: str,
    summary: str,
    significance: float = 0.5,
    partner: str = '',
    echo: str = '',
) -> None:
    """Speichert ein Pulse-Event direkt (ohne LLM-Bewertung).

    Fuer technische Events die automatisch erkannt werden:
    - Bond-Veraenderungen
    - Resonanz-Milestones
    - Emotionale Peaks
    - Lobby-Nachrichten
    """
    if significance < 0.3:
        return

    from engine.organ_reader import read_yaml_organ, write_yaml_organ

    diary = read_yaml_organ(egon_id, 'social', 'self_diary.yaml')
    if not diary:
        diary = {'entries': []}

    today = datetime.now().strftime('%Y-%m-%d')
    now_time = datetime.now().strftime('%H:%M')

    entry = {
        'date': today,
        'time': now_time,
        'type': event_type,
        'context': 'pulse',
        'partner': partner,
        'summary': summary,
        'echo': echo,
        'significance': round(significance, 2),
    }

    diary.setdefault('entries', []).append(entry)

    # Max 80 Eintraege — Konsolidierung im Pulse raeumt intelligent auf
    if len(diary['entries']) > 80:
        kern = [e for e in diary['entries'] if e.get('significance', 0) >= 0.8]
        rest = [e for e in diary['entries'] if e.get('significance', 0) < 0.8]
        rest = rest[-(80 - len(kern)):]
        diary['entries'] = kern + rest

    write_yaml_organ(egon_id, 'social', 'self_diary.yaml', diary)

    print(f'[self_diary] {egon_id}: Pulse-Event: '
          f'{event_type} sig={significance:.1f} "{summary[:50]}"')


# ================================================================
# Prompt-Text Generator
# ================================================================

def get_self_diary_prompt(egon_id: str, days: int = 7, max_chars: int = 500) -> str:
    """Gibt die eigenen Erlebnisse der letzten Tage als Prompt-Text zurueck.

    Format: ICH-Perspektive, natuerliche Sprache.
    Hoch-signifikante Erlebnisse zuerst.
    """
    from engine.organ_reader import read_yaml_organ

    diary = read_yaml_organ(egon_id, 'social', 'self_diary.yaml')
    if not diary or not diary.get('entries'):
        return ''

    entries = diary['entries']

    # Nach Datum filtern
    today = datetime.now()
    recent = []
    for e in entries:
        try:
            e_date = datetime.strptime(e['date'], '%Y-%m-%d')
            if (today - e_date).days <= days:
                recent.append(e)
        except (ValueError, KeyError):
            continue

    if not recent:
        return ''

    # Sortiere nach Significance (hoechste zuerst)
    recent.sort(key=lambda x: x.get('significance', 0), reverse=True)

    # Limit: Top 10 bedeutsamste Erlebnisse
    top = recent[:10]

    lines = []
    for e in top:
        day_label = _day_label(e.get('date', ''), today)
        summary = e.get('summary', '')
        echo = e.get('echo', '')
        sig = e.get('significance', 0)
        partner = e.get('partner', '')

        # Kontext-Tag
        ctx = e.get('context', '')
        if ctx == 'egon_chat' and partner:
            tag = f'(Gespraech mit {partner})'
        elif ctx == 'owner_chat':
            tag = '(mit meiner Bezugsmensch)'
        elif ctx == 'pulse':
            tag = '(in meinem Bewusstsein)'
        elif ctx == 'lobby':
            tag = f'(Nachricht von {partner})'
        else:
            tag = ''

        line = f'{day_label} {tag}: {summary}'
        if echo and sig >= 0.6:
            line += f' → {echo}'
        lines.append(line)

    result = '\n'.join(lines)
    if len(result) > max_chars:
        result = result[:max_chars].rsplit('\n', 1)[0] + '\n...'

    return result


def _day_label(date_str: str, today: datetime) -> str:
    """Formatiert Datum als 'Heute', 'Gestern', 'Vor N Tagen'."""
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        diff = (today - dt).days
        if diff == 0:
            return 'Heute'
        elif diff == 1:
            return 'Gestern'
        else:
            return f'Vor {diff} Tagen'
    except ValueError:
        return date_str


# ================================================================
# Self-Diary Konsolidierung — Gleiche Logik wie Owner Diary
# ================================================================

KERN_SIGNIFICANCE = 0.8     # Praegende Erlebnisse — niemals loeschen
MITTEL_SIGNIFICANCE = 0.6   # Ueberlebt die Mittel-Phase
FRISCH_TAGE = 7             # Alles bleibt
MITTEL_TAGE = 30            # Nur sig >= 0.6 ueberlebt
MAX_VERDICHTETE = 12        # Max 12 Wochen-Zusammenfassungen


def konsolidiere_self_diary(egon_id: str) -> dict:
    """Konsolidiert das Self Diary — laeuft im Pulse-Zyklus.

    Drei Phasen:
    1. FRISCH (0-7 Tage): Alles bleibt
    2. MITTEL (8-30 Tage): Nur sig >= 0.6
    3. ALT (> 30 Tage): Wochen-Zusammenfassungen

    Kern-Erlebnisse (sig >= 0.8) ueberleben IMMER.
    """
    from engine.organ_reader import read_yaml_organ, write_yaml_organ

    diary = read_yaml_organ(egon_id, 'social', 'self_diary.yaml')
    if not diary or not diary.get('entries'):
        return {'konsolidiert': False}

    entries = diary['entries']
    today = datetime.now()
    original_count = len(entries)

    frisch = []
    mittel = []
    alt = []
    entfernt = 0

    for e in entries:
        try:
            e_date = datetime.strptime(e['date'], '%Y-%m-%d')
            age = (today - e_date).days
        except (ValueError, KeyError):
            frisch.append(e)
            continue

        sig = e.get('significance', 0.5)

        if age <= FRISCH_TAGE:
            frisch.append(e)
        elif age <= MITTEL_TAGE:
            if sig >= MITTEL_SIGNIFICANCE:
                mittel.append(e)
            else:
                entfernt += 1
        else:
            if sig >= KERN_SIGNIFICANCE:
                mittel.append(e)  # Kern-Erlebnisse ueberleben IMMER
            else:
                alt.append(e)

    # Alt-Eintraege zu Wochen-Zusammenfassungen verdichten
    verdichtete = _verdichte_self_zu_wochen(alt)

    neue_entries = verdichtete + mittel + frisch

    if len(neue_entries) > 80:
        neue_entries = neue_entries[-80:]

    diary['entries'] = neue_entries
    diary['last_consolidated'] = today.strftime('%Y-%m-%d')

    write_yaml_organ(egon_id, 'social', 'self_diary.yaml', diary)

    verdichtet_count = len(verdichtete)
    if entfernt > 0 or verdichtet_count > 0:
        print(f'[self_diary] {egon_id}: Konsolidiert: {original_count} → {len(neue_entries)} '
              f'(entfernt={entfernt}, verdichtet={verdichtet_count} Wochen)')

    return {
        'konsolidiert': True,
        'original': original_count,
        'neu': len(neue_entries),
        'entfernt': entfernt,
        'verdichtet': verdichtet_count,
    }


def _verdichte_self_zu_wochen(entries: list) -> list:
    """Verdichtet alte Self-Diary Eintraege zu Wochen-Zusammenfassungen."""
    if not entries:
        return []

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

    verdichtete = []
    for week_key in sorted(by_week.keys()):
        week_entries = by_week[week_key]
        if not week_entries:
            continue

        best = max(week_entries, key=lambda e: e.get('significance', 0))
        summaries = [e.get('summary', '') for e in week_entries if e.get('summary')]

        if len(summaries) == 1:
            combined = summaries[0]
        else:
            combined = '; '.join(s[:60] for s in summaries[:3])
            if len(summaries) > 3:
                combined += f' (+{len(summaries) - 3} weitere)'

        verdichtet = {
            'date': best['date'],
            'time': '00:00',
            'type': 'VERDICHTET',
            'context': 'konsolidierung',
            'partner': '',
            'summary': combined[:200],
            'echo': f'Verdichtung von {len(week_entries)} Erlebnissen (KW {week_key})',
            'significance': round(best.get('significance', 0.5), 2),
            '_consolidated': True,
        }
        verdichtete.append(verdichtet)

    if len(verdichtete) > MAX_VERDICHTETE:
        verdichtete = verdichtete[-MAX_VERDICHTETE:]

    return verdichtete
