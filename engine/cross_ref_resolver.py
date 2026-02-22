"""Cross-Reference Resolver — loest Verweise in inner_voice.md auf.

Inner Voice ist der Hub — sie verbindet alle Organe durch Referenzen:
  (-> ep:E0034)     = Episode aus episodes.yaml
  (-> bond:OWNER)   = Bond aus bonds.yaml
  (-> exp:X0003)    = Erkenntnis aus experience.yaml
  (-> thread:T001)  = Thread aus episodes.yaml
  (-> skill:Python) = Skill aus skills.yaml

Dieser Resolver parst die Referenzen und laedt die Eintraege.
Max 5 aufgeloeste Referenzen pro Prompt.
"""

import re
from engine.organ_reader import read_yaml_organ


# ================================================================
# Reference Pattern
# ================================================================

# Matches: (-> ep:E0034), (-> bond:OWNER_CURRENT), (-> exp:X0003), etc.
REF_PATTERN = re.compile(r'\(->\s*(\w+):([^)]+)\)')


# ================================================================
# Main Resolver
# ================================================================

def resolve_cross_refs(
    egon_id: str,
    text: str,
    max_refs: int = 5,
) -> list[dict]:
    """Parst Cross-References aus Text und laedt die Eintraege.

    Args:
        egon_id: EGON-ID
        text: Text mit Cross-References (z.B. inner_voice Eintraege)
        max_refs: Maximale Anzahl aufzuloesender Referenzen

    Returns:
        Liste von Dicts: [{'type': 'ep', 'id': 'E0034', 'content': '...'}]
    """
    matches = REF_PATTERN.findall(text)
    if not matches:
        return []

    resolved = []
    seen = set()

    for ref_type, ref_id in matches:
        ref_id = ref_id.strip()
        key = f'{ref_type}:{ref_id}'

        if key in seen:
            continue  # Duplikate ueberspringen
        seen.add(key)

        if len(resolved) >= max_refs:
            break

        content = _resolve_single(egon_id, ref_type, ref_id)
        if content:
            resolved.append({
                'type': ref_type,
                'id': ref_id,
                'content': content,
            })

    return resolved


def resolve_and_format(
    egon_id: str,
    text: str,
    max_refs: int = 5,
) -> str:
    """Loest Cross-Refs auf und formatiert als Kontext-Block.

    Returns:
        Formatierter String fuer den Prompt, oder '' wenn keine Refs.
    """
    refs = resolve_cross_refs(egon_id, text, max_refs)
    if not refs:
        return ''

    lines = ['--- Referenzierter Kontext ---']
    for ref in refs:
        lines.append(f'[{ref["type"]}:{ref["id"]}] {ref["content"]}')

    return '\n'.join(lines)


# ================================================================
# Single Reference Resolver
# ================================================================

def _resolve_single(egon_id: str, ref_type: str, ref_id: str) -> str | None:
    """Loest eine einzelne Referenz auf.

    Returns:
        Kurze Zusammenfassung des Eintrags, oder None wenn nicht gefunden.
    """
    resolvers = {
        'ep': _resolve_episode,
        'bond': _resolve_bond,
        'exp': _resolve_experience,
        'thread': _resolve_thread,
        'skill': _resolve_skill,
    }

    resolver = resolvers.get(ref_type)
    if not resolver:
        return None

    try:
        return resolver(egon_id, ref_id)
    except Exception:
        return None


def _resolve_episode(egon_id: str, episode_id: str) -> str | None:
    """Loest eine Episode-Referenz auf."""
    data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not data:
        return None

    for ep in data.get('episodes', []):
        if ep.get('id') == episode_id:
            date = ep.get('date', '?')
            summary = ep.get('summary', '').strip()
            # Kuerze auf 100 Zeichen
            if len(summary) > 100:
                summary = summary[:100] + '...'
            return f'{date}: {summary}'

    return None  # Episode nicht gefunden


def _resolve_bond(egon_id: str, bond_id: str) -> str | None:
    """Loest eine Bond-Referenz auf."""
    data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not data:
        return None

    for bond in data.get('bonds', []):
        if bond.get('id') == bond_id:
            score = bond.get('score', 0)
            trust = bond.get('trust', 0)
            style = bond.get('attachment_style', '?')
            return f'Score {score}, Trust {trust:.2f}, Stil: {style}'

    # Auch in former_owner_bonds suchen
    for bond in data.get('former_owner_bonds', []):
        if bond.get('id') == bond_id:
            score = bond.get('score', 0)
            return f'Ex-Owner, Score {score}'

    return None


def _resolve_experience(egon_id: str, exp_id: str) -> str | None:
    """Loest eine Experience-Referenz auf."""
    data = read_yaml_organ(egon_id, 'memory', 'experience.yaml')
    if not data:
        return None

    for xp in data.get('experiences', []):
        if xp.get('id') == exp_id:
            insight = xp.get('insight', '').strip()
            confidence = xp.get('confidence', 0)
            if len(insight) > 100:
                insight = insight[:100] + '...'
            return f'{insight} (Confidence: {confidence:.0%})'

    return None


def _resolve_thread(egon_id: str, thread_id: str) -> str | None:
    """Loest eine Thread-Referenz auf."""
    data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not data:
        return None

    # Sammle alle Episoden dieses Threads
    thread_episodes = [
        ep for ep in data.get('episodes', [])
        if ep.get('thread') == thread_id
    ]

    if not thread_episodes:
        return None

    title = thread_episodes[0].get('thread_title', 'Unbenannt')
    count = len(thread_episodes)

    # Letzte Episode
    thread_episodes.sort(key=lambda e: e.get('date', ''))
    last = thread_episodes[-1]
    last_date = last.get('date', '?')
    last_summary = last.get('summary', '').strip()
    if len(last_summary) > 80:
        last_summary = last_summary[:80] + '...'

    return f'Projekt "{title}" ({count} Episoden, zuletzt {last_date}): {last_summary}'


def _resolve_skill(egon_id: str, skill_name: str) -> str | None:
    """Loest eine Skill-Referenz auf."""
    data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    if not data:
        return None

    for sk in data.get('skills', []):
        name = sk.get('name', '')
        if name.lower() == skill_name.lower():
            level = sk.get('level', 0)
            max_level = sk.get('max_level', 5)
            confidence = sk.get('confidence', 0)
            return f'{name}: Level {level}/{max_level}, Confidence {confidence:.0%}'

    return None
