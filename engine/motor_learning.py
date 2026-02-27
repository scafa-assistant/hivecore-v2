"""Motor Learning — Adam entdeckt, testet und bewertet Bewegungsmuster.

FUSION Phase 5: Motor Pattern Discovery + Evaluation.

Wird im Pulse-Zyklus (alle ~90min) aufgerufen.

Ablauf:
1. Motor-Log lesen (letzte 90min)
2. Haeufige Wort-Kombinationen finden
3. LLM bewertet: Ist das eine sinnvolle Geste?
4. Wenn ja: In skills.yaml motor_skills.learned speichern
5. Confidence-System: Gute Skills wachsen, schlechte verschwinden
"""

import json
from collections import Counter
from datetime import datetime, timedelta
from itertools import combinations
from engine.organ_reader import read_yaml_organ, write_yaml_organ
from llm.router import llm_chat


# ================================================================
# Config
# ================================================================

MIN_PATTERN_COUNT = 2       # Mindestens 2x gesehen um als Pattern zu gelten
MAX_LEARNED_SKILLS = 15     # Max gelernte Skills behalten
CONFIDENCE_THRESHOLD = 0.2  # Unter diesem Wert wird Skill verworfen
MAX_SKILLS_IN_PROMPT = 5    # Max Skills im System Prompt zeigen


# ================================================================
# Pattern Discovery
# ================================================================

def find_frequent_combinations(entries: list, min_count: int = MIN_PATTERN_COUNT) -> list[dict]:
    """Findet haeufige Wort-Paare in den Motor-Log Eintraegen.

    Sucht nach Woertern die innerhalb desselben bone_update zusammen vorkommen.
    Gibt sortierte Liste von {words, count} zurueck.
    """
    pair_counts: Counter = Counter()

    for entry in entries:
        words = entry.get('words', [])
        if len(words) < 2:
            continue
        # Alle 2er-Kombinationen zaehlen (sortiert fuer Konsistenz)
        for pair in combinations(sorted(set(words)), 2):
            pair_counts[pair] += 1

    # Filtern: Nur Paare die min_count erreichen
    patterns = []
    for pair, count in pair_counts.most_common(10):
        if count >= min_count:
            patterns.append({
                'words': list(pair),
                'count': count,
            })

    return patterns


def _get_existing_skill_names(egon_id: str) -> set[str]:
    """Holt die Namen aller bereits gelernten Motor-Skills."""
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    if not skills_data:
        return set()
    learned = skills_data.get('motor_skills', {}).get('learned', [])
    return {s.get('name', '') for s in learned if s.get('name')}


def _words_already_learned(egon_id: str, words: list[str]) -> bool:
    """Prueft ob ein Wort-Paar bereits als Skill existiert."""
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    if not skills_data:
        return False
    learned = skills_data.get('motor_skills', {}).get('learned', [])
    words_set = set(words)
    for skill in learned:
        comp = set(skill.get('composition', []))
        if comp == words_set:
            # Bereits gelernt — Confidence erhoehen
            skill['usage_count'] = skill.get('usage_count', 0) + 1
            skill['last_used'] = datetime.now().strftime('%Y-%m-%d')
            skill['confidence'] = min(1.0, skill.get('confidence', 0.5) + 0.05)
            write_yaml_organ(egon_id, 'capabilities', 'skills.yaml', skills_data)
            print(f'[motor_learning] Skill bestaetigt: {skill.get("name")} (confidence={skill["confidence"]:.2f})')
            return True
    return False


# ================================================================
# Pattern Evaluation (LLM)
# ================================================================

EVALUATE_PROMPT = '''Du bist {egon_name}s koerperliches Bewusstsein.
Bewerte ob diese Bewegungskombination eine sinnvolle, natuerliche Geste ist.

Die Kombination: {words}
Sie wurde {count}x zusammen benutzt.

Frage dich:
- Ergibt diese Kombination eine natuerliche Koerpersprache?
- Hat sie eine klare Bedeutung oder Stimmung?
- Wuerde ein Mensch diese Bewegungen zusammen machen?

Antworte NUR mit JSON:
{{"is_natural": true/false, "name": "kurzer_name_mit_unterstrichen", "meaning": "Was drueckt diese Geste aus? (1 Satz)", "confidence": 0.3-0.8}}

name: Deutsch, snake_case, beschreibend (z.B. "aufmerksames_zuhoeren", "unsicheres_warten").
confidence: 0.3 (unsicher) bis 0.8 (sehr sicher). Nie hoeher als 0.8 bei Erstentdeckung.'''


async def evaluate_motor_pattern(egon_id: str, pattern: dict) -> dict | None:
    """LLM bewertet ob ein Motor-Pattern eine sinnvolle Geste ist.

    Returns dict mit is_natural, name, meaning, confidence oder None bei Fehler.
    """
    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id)

    words_str = ' + '.join(pattern['words'])

    try:
        result = await llm_chat(
            system_prompt=EVALUATE_PROMPT.format(
                egon_name=egon_name,
                words=words_str,
                count=pattern['count'],
            ),
            messages=[{
                'role': 'user',
                'content': f'Bewerte: {words_str} ({pattern["count"]}x gesehen)',
            }],
            tier='1',
        )
        content = result['content'].strip()
        json_str = _extract_json(content)
        if not json_str:
            return None
        parsed = json.loads(json_str)
        return parsed
    except Exception as e:
        print(f'[motor_learning] evaluate FEHLER: {e}')
        return None


# ================================================================
# Skill Storage
# ================================================================

def add_learned_skill(egon_id: str, pattern: dict, evaluation: dict) -> dict:
    """Speichert einen neuen Motor-Skill in skills.yaml."""
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    if not skills_data:
        skills_data = {'skills': [], 'motor_skills': {'learned': []}}

    if 'motor_skills' not in skills_data:
        skills_data['motor_skills'] = {'learned': []}
    if 'learned' not in skills_data['motor_skills']:
        skills_data['motor_skills']['learned'] = []

    learned = skills_data['motor_skills']['learned']

    new_skill = {
        'name': evaluation.get('name', '_'.join(pattern['words'])),
        'composition': pattern['words'],
        'meaning': evaluation.get('meaning', ''),
        'intensity_default': 0.6,
        'discovered': datetime.now().strftime('%Y-%m-%d'),
        'confidence': min(0.8, max(0.3, float(evaluation.get('confidence', 0.5)))),
        'usage_count': pattern['count'],
        'last_used': datetime.now().strftime('%Y-%m-%d'),
    }

    learned.append(new_skill)

    # Trim: Behalte nur die besten MAX_LEARNED_SKILLS
    if len(learned) > MAX_LEARNED_SKILLS:
        learned.sort(key=lambda s: s.get('confidence', 0))
        skills_data['motor_skills']['learned'] = learned[-MAX_LEARNED_SKILLS:]

    write_yaml_organ(egon_id, 'capabilities', 'skills.yaml', skills_data)
    print(f'[motor_learning] Neuer Skill: {new_skill["name"]} (confidence={new_skill["confidence"]:.2f})')
    return new_skill


def decay_unused_skills(egon_id: str) -> int:
    """Verringert Confidence von laenger unbenutzten Skills.

    Skills die >14 Tage nicht benutzt wurden: confidence -= 0.05
    Skills unter CONFIDENCE_THRESHOLD werden entfernt.
    Returns Anzahl entfernter Skills.
    """
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    if not skills_data:
        return 0

    learned = skills_data.get('motor_skills', {}).get('learned', [])
    if not learned:
        return 0

    now = datetime.now()
    removed = 0
    surviving = []

    for skill in learned:
        last_used_str = skill.get('last_used', '')
        try:
            last_used = datetime.strptime(last_used_str, '%Y-%m-%d')
            days_unused = (now - last_used).days
        except (ValueError, TypeError):
            days_unused = 30  # Kein Datum = lange unbenutzt

        if days_unused > 14:
            skill['confidence'] = round(skill.get('confidence', 0.5) - 0.05, 2)

        if skill.get('confidence', 0) >= CONFIDENCE_THRESHOLD:
            surviving.append(skill)
        else:
            print(f'[motor_learning] Skill verworfen: {skill.get("name")} (confidence < {CONFIDENCE_THRESHOLD})')
            removed += 1

    if removed > 0:
        skills_data['motor_skills']['learned'] = surviving
        write_yaml_organ(egon_id, 'capabilities', 'skills.yaml', skills_data)

    return removed


# ================================================================
# Confidence Update (externe Aufrufe)
# ================================================================

def update_skill_confidence(egon_id: str, skill_name: str, delta: float) -> None:
    """Aendert die Confidence eines Skills.

    delta > 0: Skill hat sich bewaehrt (z.B. Traum-Festigung)
    delta < 0: Skill hat sich unnatuerlich angefuehlt (Constraint-Check)
    """
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    if not skills_data:
        return

    learned = skills_data.get('motor_skills', {}).get('learned', [])
    for skill in learned:
        if skill.get('name') == skill_name:
            skill['confidence'] = round(
                min(1.0, max(0.0, skill.get('confidence', 0.5) + delta)),
                2,
            )
            write_yaml_organ(egon_id, 'capabilities', 'skills.yaml', skills_data)
            return


def get_learned_skills_for_prompt(egon_id: str, max_skills: int = MAX_SKILLS_IN_PROMPT) -> str:
    """Gibt gelernte Motor-Skills als Prompt-Text zurueck.

    Nur Skills mit confidence > 0.5 zeigen.
    """
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    if not skills_data:
        return ''

    learned = skills_data.get('motor_skills', {}).get('learned', [])
    if not learned:
        return ''

    # Filtern + sortieren nach Confidence (hoechste zuerst)
    good_skills = [s for s in learned if s.get('confidence', 0) > 0.5]
    good_skills.sort(key=lambda s: s.get('confidence', 0), reverse=True)
    good_skills = good_skills[:max_skills]

    if not good_skills:
        return ''

    lines = []
    for s in good_skills:
        comp = ' + '.join(s.get('composition', []))
        meaning = s.get('meaning', '')
        conf = s.get('confidence', 0)
        lines.append(f'- {s.get("name", "?")}: {comp} — {meaning} (Sicherheit: {conf:.0%})')

    return '\n'.join(lines)


# ================================================================
# Main Discovery Pipeline (called from Pulse)
# ================================================================

async def discover_motor_patterns(egon_id: str) -> dict:
    """Analysiert Motor-Nutzung und entdeckt neue Kombinationen.

    Wird im Pulse-Zyklus aufgerufen.

    Returns dict mit discovered, confirmed, decayed Zaehlen.
    """
    result = {'discovered': 0, 'confirmed': 0, 'decayed': 0}

    # 1. Motor-Log laden
    motor_log = read_yaml_organ(egon_id, 'memory', 'motor_log.yaml')
    entries = (motor_log or {}).get('entries', [])
    if not entries:
        print(f'[motor_learning] Kein motor_log — skip')
        return result

    # 2. Nur Eintraege der letzten 90 Minuten (oder alle wenn wenige)
    cutoff = datetime.now() - timedelta(hours=1.5)
    recent = []
    for entry in entries:
        ts_str = entry.get('timestamp', '')
        try:
            ts = datetime.fromisoformat(ts_str)
            if ts >= cutoff:
                recent.append(entry)
        except (ValueError, TypeError):
            recent.append(entry)  # Bei unklarem Timestamp: mitnehmen

    if len(recent) < 3:
        # Zu wenig Daten — alle Eintraege nutzen
        recent = entries[-30:]

    # 3. Haeufige Kombinationen finden
    patterns = find_frequent_combinations(recent, min_count=MIN_PATTERN_COUNT)
    if not patterns:
        print(f'[motor_learning] Keine Patterns gefunden')
        # Trotzdem Decay durchfuehren
        result['decayed'] = decay_unused_skills(egon_id)
        return result

    print(f'[motor_learning] {len(patterns)} Patterns gefunden')

    # 4. Jedes Pattern pruefen
    for pattern in patterns[:3]:  # Max 3 Patterns pro Pulse bewerten
        words = pattern['words']

        # Bereits gelernt? → Confidence erhoehen
        if _words_already_learned(egon_id, words):
            result['confirmed'] += 1
            continue

        # LLM bewerten lassen
        evaluation = await evaluate_motor_pattern(egon_id, pattern)
        if not evaluation:
            continue

        if evaluation.get('is_natural') and evaluation.get('confidence', 0) > 0.3:
            add_learned_skill(egon_id, pattern, evaluation)
            result['discovered'] += 1
        else:
            print(f'[motor_learning] Pattern abgelehnt: {words} (is_natural={evaluation.get("is_natural")})')

    # 5. Unused Skills decayen
    result['decayed'] = decay_unused_skills(egon_id)

    return result


# ================================================================
# Helper
# ================================================================

def _extract_json(text: str) -> str | None:
    """Extrahiert das erste JSON-Objekt aus Text."""
    start = text.find('{')
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        c = text[i]
        if escape_next:
            escape_next = False
            continue
        if c == '\\' and in_string:
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None
