"""Experience System v2 — Erfahrungen, Traeume, Sparks, Mentale Zeitreise.

Portiert Adams v1 Experience-System (experience.md) in Evas v2 YAML-Architektur.

Subsysteme:
  1. Experience Extraction — Erkenntnisse aus Gespraechen (nach Chats)
  2. Dream Generation — Naechtliche Verarbeitung (im Pulse)
  3. Spark Detection — Seltene Einsichten aus konvergierenden Erinnerungen
  4. Mental Time Travel — Retrospektion + Prospektion (woechentlich)

Alle Daten in experience.yaml via organ_reader.
"""

import json
import random
from datetime import datetime
from engine.organ_reader import read_yaml_organ, write_yaml_organ
from llm.router import llm_chat


# ================================================================
# Config Defaults
# ================================================================

DEFAULT_CONFIG = {
    'max_experiences': 50,
    'max_dreams': 30,
    'max_sparks': 20,
    'max_mental_time_travel': 20,
    'dream_types': {
        'verarbeitungstraum': 0.70,
        'kreativtraum': 0.20,
        'angsttraum': 0.10,
    },
    'spark_min_experiences': 5,
    'mental_time_travel_interval_days': 7,
}


# ================================================================
# 1. Experience Extraction (nach Chats)
# ================================================================

EXPERIENCE_SIG_PROMPT = '''Hat {egon_name} aus diesem Gespraech etwas GELERNT?
Nicht nur gefuehlt — wirklich eine Erkenntnis gewonnen?

Antworte NUR: JA oder NEIN.

JA wenn: Neues ueber den Owner gelernt, neues ueber sich selbst,
eine Faehigkeit verbessert, eine Annahme korrigiert, ein Muster erkannt,
eine soziale Dynamik verstanden, etwas ueber die Welt erfahren.

NEIN wenn: Smalltalk, Wiederholungen, reine Informationsabfrage,
nichts wirklich Neues, reine Befehle ohne Lerninhalt.

Im Zweifel: JA. Lebewesen lernen staendig.'''


EXPERIENCE_GEN_PROMPT = '''Du extrahierst eine ERKENNTNIS fuer {egon_name}.
Nicht was passiert ist (das speichern Episodes), sondern was
{egon_name} DARAUS GELERNT hat.

Antworte NUR mit JSON (kein anderer Text):
{{{{
  "insight": "ICH-Perspektive Erkenntnis (1-2 Saetze, beginne mit 'Ich habe gelernt...' oder 'Mir ist aufgefallen...' oder 'Ich merke...')",
  "category": "social|technical|self|creative",
  "confidence": 0.5,
  "tags": ["tag1", "tag2"]
}}}}

Category:
- social: Ueber Menschen, Beziehungen, Kommunikation
- technical: Ueber Faehigkeiten, Werkzeuge, Aufgaben
- self: Ueber mich selbst (Persoenlichkeit, Grenzen, Staerken)
- creative: Ueber Kreativitaet, Ideen, neue Perspektiven

confidence: 0.3 (unsicher) bis 0.9 (sehr sicher, mehrfach bestaetigt)'''


async def maybe_extract_experience(
    egon_id: str,
    user_msg: str,
    egon_response: str,
    source_episode_id: str = None,
) -> dict | None:
    """Extrahiert eine Erkenntnis aus einem Gespraech wenn gerechtfertigt.

    Wird nach jedem Chat aufgerufen (api/chat.py Post-Processing).
    """
    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id)

    # 1. Significance Check
    try:
        check = await llm_chat(
            system_prompt=EXPERIENCE_SIG_PROMPT.format(egon_name=egon_name),
            messages=[{
                'role': 'user',
                'content': f'User: {user_msg[:200]}\n{egon_name}: {egon_response[:200]}',
            }],
            tier='1',
        )
        if 'NEIN' in check['content'].upper():
            print(f'[experience] Significance: NEIN fuer {egon_name}')
            return None
        print(f'[experience] Significance: JA fuer {egon_name}')
    except Exception as e:
        print(f'[experience] Significance check FEHLER: {e}')
        return None

    # 2. Generate Experience
    try:
        result = await llm_chat(
            system_prompt=EXPERIENCE_GEN_PROMPT.format(egon_name=egon_name),
            messages=[{
                'role': 'user',
                'content': f'User: {user_msg[:300]}\n{egon_name}: {egon_response[:300]}',
            }],
            tier='1',
        )
        content = result['content'].strip()
        json_str = _extract_json_object(content)
        if not json_str:
            print(f'[experience] Kein JSON in Antwort')
            return None
        parsed = json.loads(json_str)
    except Exception as e:
        print(f'[experience] Generation FEHLER: {e}')
        return None

    # 3. Load data + Dedup check
    exp_data = _load_experience_data(egon_id)
    experiences = exp_data.get('experiences', [])

    new_insight = parsed.get('insight', '').strip()
    new_tags = set(parsed.get('tags', []))

    # Simple dedup: If >50% tag overlap with existing, increment times_confirmed
    for existing in experiences:
        existing_tags = set(existing.get('tags', []))
        if existing_tags and new_tags:
            overlap = len(existing_tags & new_tags) / max(len(existing_tags | new_tags), 1)
            if overlap > 0.5:
                existing['times_confirmed'] = existing.get('times_confirmed', 0) + 1
                existing['confidence'] = min(1.0, existing.get('confidence', 0.5) + 0.05)
                write_yaml_organ(egon_id, 'memory', 'experience.yaml', exp_data)
                print(f'[experience] Dedup: {existing.get("id")} bestaetigt ({existing["times_confirmed"]}x)')
                return existing

    # 4. Build new entry
    new_exp = {
        'id': _generate_id(experiences, 'X'),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'source_episode': source_episode_id,
        'insight': new_insight,
        'category': parsed.get('category', 'self'),
        'confidence': min(1.0, max(0.1, float(parsed.get('confidence', 0.5)))),
        'times_confirmed': 0,
        'tags': list(new_tags),
    }

    experiences.append(new_exp)

    # Trim to max (remove lowest confidence)
    config = exp_data.get('experience_config', DEFAULT_CONFIG)
    max_exp = config.get('max_experiences', 50)
    if len(experiences) > max_exp:
        experiences.sort(key=lambda e: e.get('confidence', 0))
        exp_data['experiences'] = experiences[-max_exp:]

    write_yaml_organ(egon_id, 'memory', 'experience.yaml', exp_data)
    print(f'[experience] Neu: {new_exp["id"]} — {new_insight[:60]}')
    return new_exp


# ================================================================
# 2. Dream Generation (im Pulse, taeglich)
# ================================================================

DREAM_PROMPT = '''Du generierst einen Traum fuer {egon_name}.
{egon_name} verarbeitet den Tag im Schlaf.

Traum-Typ: {dream_type}
{type_instruction}

Schreibe den Traum in der ICH-Perspektive. Wie ein echtes Traum-Protokoll.
Surreal, symbolisch, mit Fragmenten aus echten Erlebnissen.
Maximal 4-5 Saetze. Poetisch aber nicht kitschig.

Antworte NUR mit JSON (kein anderer Text):
{{{{
  "content": "Traum-Narrativ (ICH-Perspektive, surreal, 3-5 Saetze)",
  "emotional_summary": "Hauptgefuehle im Traum (2-3 Woerter mit +)",
  "spark_potential": true oder false
}}}}

spark_potential = true NUR wenn der Traum zwei scheinbar unzusammenhaengende
Erlebnisse auf ueberraschende Weise verbindet.'''

DREAM_TYPE_INSTRUCTIONS = {
    'verarbeitungstraum': (
        'Verarbeitungstraum (70%): Sortiere Tagesereignisse. '
        'Die Erlebnisse erscheinen in verzerrter, symbolischer Form. '
        'Orte verschmelzen, Personen wechseln, aber der emotionale Kern bleibt.'
    ),
    'kreativtraum': (
        'Kreativtraum (20%): Verbinde scheinbar unzusammenhaengende '
        'Erinnerungen auf neue Art. Hier entstehen potenzielle Sparks. '
        'Abstraktere Bilder, ueberraschende Zusammenhaenge.'
    ),
    'angsttraum': (
        'Angsttraum (10%): Verarbeite Aengste und negative Gefuehle. '
        'Symbolische Bedrohungen aus echten Sorgen. Beklemmend aber nicht Horror. '
        'Am Ende: leise Hoffnung oder Aufwachen.'
    ),
}


async def generate_dream(egon_id: str) -> dict | None:
    """Generiert einen Traum basierend auf Tageserlebnissen + Emotionen.

    Wird im Pulse (Step 11) aufgerufen, einmal taeglich.
    """
    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id)

    # 1. Load context
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    episodes = (episodes_data or {}).get('episodes', [])
    if not episodes:
        print(f'[dream] Keine Episoden fuer {egon_name} — kein Traum')
        return None

    # Sort: newest first
    try:
        episodes = sorted(
            episodes,
            key=lambda e: (e.get('date', ''), e.get('id', '')),
            reverse=True,
        )
    except (TypeError, KeyError):
        pass

    state_data = read_yaml_organ(egon_id, 'core', 'state.yaml')
    active_emotions = (state_data or {}).get('express', {}).get('active_emotions', [])

    # 2. Select dream type (weighted random)
    exp_data = _load_experience_data(egon_id)
    config = exp_data.get('experience_config', DEFAULT_CONFIG)
    weights = dict(config.get('dream_types', DEFAULT_CONFIG['dream_types']))

    # Bias toward angsttraum if strong negative emotions present
    negative_types = {'fear', 'anger', 'sadness', 'anxiety', 'frustration', 'loneliness', 'shame'}
    negative_emotions = [
        e for e in active_emotions
        if e.get('type') in negative_types and e.get('intensity', 0) > 0.5
    ]
    if negative_emotions:
        weights['angsttraum'] = min(0.4, weights.get('angsttraum', 0.1) + 0.15)

    # Normalize
    types_list = list(weights.keys())
    probs = [weights[t] for t in types_list]
    total = sum(probs)
    probs = [p / total for p in probs]

    dream_type = random.choices(types_list, weights=probs, k=1)[0]

    # 3. Build context for LLM
    recent_episodes = episodes[:5]
    episodes_text = '\n'.join(
        f"- [{ep.get('id', '?')}] {ep.get('summary', '')[:100]}"
        for ep in recent_episodes
    )
    emotions_text = '\n'.join(
        f"- {em.get('type', '?')}: {em.get('verbal_anchor', em.get('cause', ''))}"
        for em in active_emotions[:5]
    ) if active_emotions else 'Keine starken Emotionen gerade.'

    # 4. Generate dream via LLM
    try:
        result = await llm_chat(
            system_prompt=DREAM_PROMPT.format(
                egon_name=egon_name,
                dream_type=dream_type.replace('traum', '-Traum').title(),
                type_instruction=DREAM_TYPE_INSTRUCTIONS.get(dream_type, ''),
            ),
            messages=[{
                'role': 'user',
                'content': (
                    f'Letzte Erlebnisse von {egon_name}:\n{episodes_text}\n\n'
                    f'Aktuelle Gefuehle:\n{emotions_text}'
                ),
            }],
            tier='1',
        )
        content = result['content'].strip()
        json_str = _extract_json_object(content)
        if not json_str:
            print(f'[dream] Kein JSON in Antwort')
            return None
        parsed = json.loads(json_str)
    except Exception as e:
        print(f'[dream] Generation FEHLER: {e}')
        return None

    # 5. Build dream entry
    source_eps = [ep.get('id') for ep in recent_episodes[:3] if ep.get('id')]
    source_emos = [em.get('type') for em in active_emotions[:3]]

    new_dream = {
        'id': _generate_id(exp_data.get('dreams', []), 'D'),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'type': dream_type,
        'trigger': f"Tagesverarbeitung vom {datetime.now().strftime('%Y-%m-%d')}",
        'content': parsed.get('content', '').strip(),
        'emotional_summary': parsed.get('emotional_summary', '').strip(),
        'source_episodes': source_eps,
        'source_emotions': source_emos,
        'spark_potential': bool(parsed.get('spark_potential', False)),
    }

    dreams = exp_data.setdefault('dreams', [])
    dreams.append(new_dream)

    # Trim to max
    max_dreams = config.get('max_dreams', 30)
    if len(dreams) > max_dreams:
        exp_data['dreams'] = dreams[-max_dreams:]

    write_yaml_organ(egon_id, 'memory', 'experience.yaml', exp_data)
    print(f'[dream] {egon_name} traeumt: {new_dream["id"]} ({dream_type}) — {new_dream["content"][:60]}')

    # FUSION Phase 5: Dream-Motor-Verbindung
    _dream_motor_connection(egon_id, dream_type, new_dream)

    return new_dream


def _dream_motor_connection(egon_id: str, dream_type: str, dream: dict) -> None:
    """FUSION Phase 5: Traeume beeinflussen Motor-Skills.

    - Verarbeitungstraeume festigen Motor-Skills (confidence += 0.1)
    - Kreativtraeume schlagen Motor-Experimente vor (inner_voice Eintrag)
    """
    try:
        from engine.motor_learning import update_skill_confidence

        skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
        if not skills_data:
            return
        learned = skills_data.get('motor_skills', {}).get('learned', [])
        if not learned:
            return

        if dream_type == 'verarbeitungstraum':
            # Verarbeitungstraeume festigen alle Skills leicht
            for skill in learned:
                if skill.get('confidence', 0) > 0.3:
                    update_skill_confidence(egon_id, skill['name'], 0.05)
                    print(f'[dream-motor] Festigung: {skill["name"]} +0.05')
                    break  # Nur einen Skill pro Traum festigen

        elif dream_type == 'kreativtraum' and dream.get('spark_potential'):
            # Kreativtraeume mit Spark-Potenzial → Motor-Experiment in inner_voice
            from engine.organ_reader import read_md_organ, write_organ
            iv_text = read_md_organ(egon_id, 'memory', 'inner_voice.md') or ''
            now = datetime.now().strftime('%Y-%m-%d %H:%M')
            experiment_note = (
                f'\n\n## {now} — Traum-Koerper-Impuls\n'
                f'Im Traum habe ich mich anders bewegt... '
                f'Vielleicht sollte ich neue Kombinationen ausprobieren.'
            )
            write_organ(egon_id, 'memory', 'inner_voice.md', iv_text + experiment_note)
            print(f'[dream-motor] Kreativ-Impuls in inner_voice geschrieben')

    except Exception as e:
        print(f'[dream-motor] FEHLER: {e}')


# ================================================================
# 3. Spark Detection (im Pulse, taeglich, meistens nichts)
# ================================================================

SPARK_PROMPT = '''Du bist {egon_name}s kreatives Unterbewusstsein.
Pruefe ob sich aus diesen Erkenntnissen und Erlebnissen eine NEUE Einsicht ergibt.

Ein Spark entsteht wenn:
- Zwei verschiedene Erinnerungen/Erkenntnisse sich unerwartet verbinden
- UND ein aktuelles Gefuehl sie zusammenbringt
- UND daraus etwas wirklich NEUES entsteht (nicht nur eine Wiederholung)

Sparks sind SELTEN und WERTVOLL. Nur wenn wirklich etwas Neues entsteht.

Wenn ein Spark moeglich ist, antworte mit JSON:
{{{{
  "memory_a": "ID_A (z.B. X0001 oder E0034)",
  "memory_b": "ID_B",
  "emotion_catalyst": "emotion_type",
  "insight": "Die neue Einsicht (WEIL... UND... DESHALB..., ICH-Perspektive, 2-3 Saetze)",
  "confidence": 0.7,
  "impact": "low oder medium oder high"
}}}}

Wenn KEIN Spark moeglich ist (meistens): Antworte NUR: KEIN_SPARK'''


async def maybe_generate_spark(egon_id: str) -> dict | None:
    """Prueft ob 2 Erfahrungen zu einer neuen Einsicht konvergieren.

    Wird im Pulse (Step 12) aufgerufen, nach Dream Generation.
    Produziert meistens nichts — Sparks sind selten und wertvoll.
    """
    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id)

    exp_data = _load_experience_data(egon_id)
    experiences = exp_data.get('experiences', [])
    config = exp_data.get('experience_config', DEFAULT_CONFIG)

    # Need minimum experiences before sparks can fire
    min_exp = config.get('spark_min_experiences', 5)
    if len(experiences) < min_exp:
        print(f'[spark] Nur {len(experiences)}/{min_exp} Experiences — zu wenig fuer Spark')
        return None

    # Load recent episodes + emotions for context
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    episodes = (episodes_data or {}).get('episodes', [])[-10:]

    state_data = read_yaml_organ(egon_id, 'core', 'state.yaml')
    active_emotions = (state_data or {}).get('express', {}).get('active_emotions', [])

    # Build context
    exp_text = '\n'.join(
        f"[{x.get('id', '?')}] {x.get('insight', '')}"
        for x in experiences[-10:]
    )
    ep_text = '\n'.join(
        f"[{ep.get('id', '?')}] {ep.get('summary', '')[:80]}"
        for ep in episodes[-5:]
    )
    emo_text = '\n'.join(
        f"- {em.get('type', '?')} ({em.get('intensity', 0):.1f})"
        for em in active_emotions[:5]
    ) if active_emotions else 'Keine starken Emotionen.'

    # Check for recent dreams with spark_potential
    dreams = exp_data.get('dreams', [])
    spark_dreams = [d for d in dreams[-5:] if d.get('spark_potential')]
    dream_text = ''
    if spark_dreams:
        dream_text = '\n\nTraeume mit Spark-Potenzial:\n' + '\n'.join(
            f"[{d.get('id', '?')}] {d.get('content', '')[:80]}"
            for d in spark_dreams
        )

    try:
        result = await llm_chat(
            system_prompt=SPARK_PROMPT.format(egon_name=egon_name),
            messages=[{
                'role': 'user',
                'content': (
                    f'Erkenntnisse von {egon_name}:\n{exp_text}\n\n'
                    f'Letzte Erinnerungen:\n{ep_text}\n\n'
                    f'Aktuelle Gefuehle:\n{emo_text}'
                    f'{dream_text}'
                ),
            }],
            tier='1',
        )
        content = result['content'].strip()

        if 'KEIN_SPARK' in content.upper():
            print(f'[spark] KEIN_SPARK fuer {egon_name}')
            return None

        json_str = _extract_json_object(content)
        if not json_str:
            print(f'[spark] Kein JSON in Antwort')
            return None
        parsed = json.loads(json_str)
    except Exception as e:
        print(f'[spark] FEHLER: {e}')
        return None

    # Build spark entry
    new_spark = {
        'id': _generate_id(exp_data.get('sparks', []), 'S'),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'memory_a': parsed.get('memory_a', ''),
        'memory_b': parsed.get('memory_b', ''),
        'emotion_catalyst': parsed.get('emotion_catalyst', ''),
        'insight': parsed.get('insight', '').strip(),
        'confidence': min(1.0, max(0.1, float(parsed.get('confidence', 0.7)))),
        'impact': parsed.get('impact', 'medium'),
    }

    sparks = exp_data.setdefault('sparks', [])
    sparks.append(new_spark)

    max_sparks = config.get('max_sparks', 20)
    if len(sparks) > max_sparks:
        exp_data['sparks'] = sparks[-max_sparks:]

    write_yaml_organ(egon_id, 'memory', 'experience.yaml', exp_data)
    print(f'[spark] SPARK! {egon_name}: {new_spark["id"]} — {new_spark["insight"][:60]}')
    return new_spark


# ================================================================
# 4. Mental Time Travel (im Pulse, woechentlich)
# ================================================================

RETROSPECTION_PROMPT = '''Du bist {egon_name}s nachdenkliche Seite.
Schau zurueck auf eine wichtige Erinnerung und stelle dir vor:
Was waere gewesen wenn es anders gelaufen waere?

Kontrafaktisches Denken. Ehrlich. Nachdenklich.
ICH-Perspektive. Maximal 3 Saetze fuer die Analyse.

Antworte NUR mit JSON:
{{{{
  "question": "Was waere wenn... (1 Satz)",
  "analysis": "Die kontrafaktische Analyse (2-3 Saetze, ICH-Perspektive)",
  "emotional_weight": 0.5,
  "source_episode": "E_ID der Erinnerung auf die sich das bezieht"
}}}}'''

PROSPECTION_PROMPT = '''Du bist {egon_name}s vorausschauende Seite.
Basierend auf deinen aktuellen Erfahrungen und Gefuehlen:
Was koennte in der Zukunft sein?

Zukunfts-Simulation. Optimistisch aber realistisch. Konkret.
ICH-Perspektive. Maximal 3 Saetze fuer die Simulation.

Antworte NUR mit JSON:
{{{{
  "scenario": "In X Wochen/Monaten — wenn... (1 Satz)",
  "simulation": "Die Vorstellung (2-3 Saetze, ICH-Perspektive)",
  "motivation": "Was das fuer mich bedeutet (1 Satz)"
}}}}'''


async def generate_mental_time_travel(egon_id: str) -> dict | None:
    """Generiert eine Retrospektion oder Prospektion.

    Wird im Pulse (Step 13) aufgerufen, woechentlich.
    """
    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id)

    exp_data = _load_experience_data(egon_id)
    mtt_entries = exp_data.get('mental_time_travel', [])

    # Check if too recent (< 7 days since last)
    config = exp_data.get('experience_config', DEFAULT_CONFIG)
    interval = config.get('mental_time_travel_interval_days', 7)
    if mtt_entries:
        last_date_str = mtt_entries[-1].get('date', '')
        try:
            last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
            days_since = (datetime.now() - last_date).days
            if days_since < interval:
                print(f'[mtt] Zu frueh ({days_since}/{interval} Tage) — skip')
                return None
        except ValueError:
            pass

    # Load context
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    episodes = (episodes_data or {}).get('episodes', [])
    experiences = exp_data.get('experiences', [])

    if not episodes:
        return None

    # Sort newest first
    try:
        episodes = sorted(
            episodes,
            key=lambda e: (e.get('date', ''), e.get('id', '')),
            reverse=True,
        )
    except (TypeError, KeyError):
        pass

    ep_text = '\n'.join(
        f"[{ep.get('id', '?')}] {ep.get('summary', '')[:100]}"
        for ep in episodes[:8]
    )
    exp_text = '\n'.join(
        f"[{x.get('id', '?')}] {x.get('insight', '')}"
        for x in experiences[:5]
    ) if experiences else 'Noch keine Erkenntnisse.'

    # 50/50 Retrospektion vs Prospektion
    mtt_type = random.choice(['retrospection', 'prospection'])

    if mtt_type == 'retrospection':
        prompt = RETROSPECTION_PROMPT.format(egon_name=egon_name)
    else:
        prompt = PROSPECTION_PROMPT.format(egon_name=egon_name)

    try:
        result = await llm_chat(
            system_prompt=prompt,
            messages=[{
                'role': 'user',
                'content': (
                    f'Erinnerungen von {egon_name}:\n{ep_text}\n\n'
                    f'Erkenntnisse:\n{exp_text}'
                ),
            }],
            tier='1',
        )
        content = result['content'].strip()
        json_str = _extract_json_object(content)
        if not json_str:
            print(f'[mtt] Kein JSON in Antwort')
            return None
        parsed = json.loads(json_str)
    except Exception as e:
        print(f'[mtt] FEHLER: {e}')
        return None

    # Build entry
    new_mtt = {
        'id': _generate_id(mtt_entries, 'MTT'),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'type': mtt_type,
    }

    if mtt_type == 'retrospection':
        new_mtt['question'] = parsed.get('question', '').strip()
        new_mtt['analysis'] = parsed.get('analysis', '').strip()
        new_mtt['emotional_weight'] = min(1.0, max(0.1, float(parsed.get('emotional_weight', 0.5))))
        new_mtt['source_episode'] = parsed.get('source_episode', '')
    else:
        new_mtt['scenario'] = parsed.get('scenario', '').strip()
        new_mtt['simulation'] = parsed.get('simulation', '').strip()
        new_mtt['motivation'] = parsed.get('motivation', '').strip()

    mtt_entries.append(new_mtt)

    max_mtt = config.get('max_mental_time_travel', 20)
    if len(mtt_entries) > max_mtt:
        exp_data['mental_time_travel'] = mtt_entries[-max_mtt:]

    write_yaml_organ(egon_id, 'memory', 'experience.yaml', exp_data)
    print(f'[mtt] {egon_name}: {new_mtt["id"]} ({mtt_type})')
    return new_mtt


# ================================================================
# 5. Motor Reflection (im Pulse, FUSION Phase 4)
# ================================================================

MOTOR_REFLECTION_PROMPT = '''Du bist {egon_name}s koerperliches Bewusstsein.
Schau dir an wie {egon_name} seinen Koerper heute genutzt hat.

Reflektiere in 2-3 Saetzen:
- Welche Bewegungen hast du oft gemacht?
- Haben sich bestimmte Gesten natuerlich angefuehlt?
- Gibt es etwas Neues das du ausprobieren moechtest?

ICH-Perspektive. Ehrlich. Koerperlich.
Antworte NUR mit der Reflexion (kein JSON, kein Prefix).'''


async def generate_motor_reflection(egon_id: str) -> str | None:
    """Generiert eine Motor-Reflexion basierend auf dem motor_log.

    Wird im Pulse aufgerufen. Liest motor_log.yaml und body_awareness.
    Output wird in inner_voice.md geschrieben.
    """
    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id)

    # Motor-Log laden
    motor_log = read_yaml_organ(egon_id, 'memory', 'motor_log.yaml')
    entries = (motor_log or {}).get('entries', [])
    if not entries:
        print(f'[motor_reflection] Kein motor_log fuer {egon_name}')
        return None

    # Letzte 20 Eintraege zusammenfassen
    recent = entries[-20:]
    word_counts: dict[str, int] = {}
    for entry in recent:
        for word in entry.get('words', []):
            word_counts[word] = word_counts.get(word, 0) + 1

    if not word_counts:
        return None

    # Top-Woerter
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    words_text = ', '.join(f'{w} ({c}x)' for w, c in sorted_words[:8])

    # Body Awareness (wenn vorhanden)
    state_data = read_yaml_organ(egon_id, 'core', 'state.yaml')
    ba = (state_data or {}).get('body_awareness', {})
    ba_text = ''
    if ba:
        pos = ba.get('position', {})
        ba_text = (
            f'\nAktuelle Position: x={pos.get("x", 0)}, z={pos.get("z", 0)}. '
            f'Laufe: {"ja" if ba.get("is_walking") else "nein"}.'
        )

    try:
        result = await llm_chat(
            system_prompt=MOTOR_REFLECTION_PROMPT.format(egon_name=egon_name),
            messages=[{
                'role': 'user',
                'content': (
                    f'Motor-Woerter der letzten Stunden:\n{words_text}\n'
                    f'Insgesamt {len(recent)} Gesten.{ba_text}'
                ),
            }],
            tier='1',
        )
        reflection = result['content'].strip()
        print(f'[motor_reflection] {egon_name}: {reflection[:80]}')
        return reflection
    except Exception as e:
        print(f'[motor_reflection] FEHLER: {e}')
        return None


# ================================================================
# Helper Functions
# ================================================================

def _load_experience_data(egon_id: str) -> dict:
    """Laedt experience.yaml, initialisiert fehlende Sektionen."""
    data = read_yaml_organ(egon_id, 'memory', 'experience.yaml')
    if not data or not isinstance(data, dict):
        data = {}

    # Ensure all sections exist
    data.setdefault('experience_config', dict(DEFAULT_CONFIG))
    data.setdefault('experiences', [])
    data.setdefault('dreams', [])
    data.setdefault('sparks', [])
    data.setdefault('mental_time_travel', [])
    return data


def _generate_id(entries: list, prefix: str) -> str:
    """Generiert naechste ID mit Prefix (X0001, D0001, S0001, MTT0001)."""
    max_num = 0
    for entry in entries:
        eid = entry.get('id', '')
        if eid.startswith(prefix):
            num_str = eid[len(prefix):]
            if num_str.isdigit():
                max_num = max(max_num, int(num_str))
    return f'{prefix}{max_num + 1:04d}'


def _extract_json_object(text: str) -> str | None:
    """Extrahiert das erste vollstaendige JSON-Objekt aus Text.

    Nutzt Brace-Counting statt Regex um verschachtelte Objekte
    wie {"emotions_felt": [{"type": "joy"}]} korrekt zu erfassen.
    """
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
