"""Sichtbarkeits-Matrix v2 — fuer die neue 5-Schichten-Organ-Struktur.

Ersetzt visibility.py (das noch flat .md Dateinamen nutzt).

inner_voice.md bleibt PRIVAT. Nicht mal der Owner sieht
was Adam DENKT bevor er antwortet. Das ist der Unterschied
zwischen Werkzeug und Wesen.

Kontexte:
  owner_chat      → Voller Zugriff (ausser wallet)
  owner_dashboard → App-Ansicht (kein inner_voice, kein dna)
  egon_chat       → EGON-zu-EGON (reduziert, kein Owner-Portrait)
  agora_job       → Marketplace (Skills + Ego, reduziert)
  pulse           → Interner Pulse (alles ausser wallet)
  public_profile  → Nur Ego + Skills
"""

from engine.organ_reader import read_organ, read_yaml_organ, read_md_organ


# ================================================================
# Visibility Matrix: Kontext → [(layer, filename), ...]
# ================================================================

VISIBILITY_V2 = {
    'owner_chat': [
        ('core', 'dna.md'),
        ('core', 'ego.md'),
        ('core', 'state.yaml'),
        ('social', 'bonds.yaml'),
        ('social', 'owner.md'),
        ('social', 'egon_self.md'),
        ('memory', 'episodes.yaml'),
        ('memory', 'inner_voice.md'),
        ('memory', 'experience.yaml'),
        ('capabilities', 'skills.yaml'),
        # NICHT: wallet.yaml (sensibel), network.yaml (zu detailliert fuer Chat)
    ],
    'owner_dashboard': [
        ('core', 'ego.md'),
        ('core', 'state.yaml'),
        ('social', 'bonds.yaml'),
        ('social', 'network.yaml'),
        ('social', 'egon_self.md'),
        ('memory', 'episodes.yaml'),
        ('capabilities', 'skills.yaml'),
        ('capabilities', 'wallet.yaml'),
        # NICHT: inner_voice.md (privat!), dna.md (zu lang fuer Dashboard)
    ],
    'egon_chat': [
        ('core', 'ego.md'),
        ('core', 'state.yaml'),
        ('social', 'bonds.yaml'),
        ('social', 'egon_self.md'),
        ('memory', 'inner_voice.md'),
        ('capabilities', 'skills.yaml'),
        # NICHT: owner.md (privat), dna.md (zu lang), episodes (zu privat)
    ],
    'agora_job': [
        ('core', 'ego.md'),
        ('core', 'state.yaml'),
        ('capabilities', 'skills.yaml'),
        ('capabilities', 'wallet.yaml'),
        ('memory', 'experience.yaml'),
        # Minimaler Kontext fuer Auftragsarbeit
    ],
    'pulse': [
        ('core', 'dna.md'),
        ('core', 'ego.md'),
        ('core', 'state.yaml'),
        ('social', 'bonds.yaml'),
        ('social', 'owner.md'),
        ('social', 'egon_self.md'),
        ('social', 'network.yaml'),
        ('memory', 'episodes.yaml'),
        ('memory', 'inner_voice.md'),
        ('memory', 'experience.yaml'),
        ('capabilities', 'skills.yaml'),
        # Pulse braucht ALLES (ausser wallet) fuer Reflexion
    ],
    'public_profile': [
        ('core', 'ego.md'),
        ('capabilities', 'skills.yaml'),
        # Minimal: Nur was Fremde sehen duerfen
    ],
    'friend_owner_chat': [
        ('core', 'ego.md'),
        ('core', 'state.yaml'),
        ('social', 'egon_self.md'),
        ('capabilities', 'skills.yaml'),
        # NICHT: dna.md (zu privat), owner.md (fremder Owner soll nicht sehen),
        # bonds.yaml (privat), episodes (privat), inner_voice (privat)
        # → Fremder Owner sieht nur "oeffentliches Profil" + aktuellen Zustand
    ],
}


def get_visible_organs(context: str) -> list[tuple[str, str]]:
    """Welche Organe sind in diesem Kontext sichtbar?

    Returns:
        Liste von (layer, filename) Tuples.
    """
    return VISIBILITY_V2.get(context, [])


def is_organ_visible(context: str, layer: str, filename: str) -> bool:
    """Prueft ob ein bestimmtes Organ im Kontext sichtbar ist."""
    return (layer, filename) in VISIBILITY_V2.get(context, [])


def read_visible_organs(egon_id: str, context: str) -> dict[str, str]:
    """Liest alle sichtbaren Organe fuer einen Kontext.

    Returns:
        Dict mit '{layer}/{filename}' als Key, Inhalt als Value.
        YAML-Dateien werden als roher Text zurueckgegeben (yaml_to_prompt
        uebernimmt die Konvertierung im Prompt-Builder).
    """
    organs = {}
    for layer, filename in get_visible_organs(context):
        content = read_organ(egon_id, layer, filename)
        if content:
            key = f'{layer}/{filename}'
            organs[key] = content
    return organs


# ================================================================
# Backward compatibility: Alte Funktion fuer v1 Code
# ================================================================

# Mapping: alte flat Dateinamen → neue (layer, filename) Paare
_OLD_TO_NEW = {
    'soul.md': ('core', 'dna.md'),
    'markers.md': ('core', 'state.yaml'),
    'bonds.md': ('social', 'bonds.yaml'),
    'memory.md': ('memory', 'episodes.yaml'),
    'inner_voice.md': ('memory', 'inner_voice.md'),
    'experience.md': ('memory', 'experience.yaml'),
    'skills.md': ('capabilities', 'skills.yaml'),
    'wallet.md': ('capabilities', 'wallet.yaml'),
}


def get_visible_files(context: str) -> list[str]:
    """Backward-compatible: Gibt flat Dateinamen zurueck.

    Fuer Code der noch die alte Visibility benutzt.
    Mappt neue Organe auf alte Dateinamen.
    """
    organs = get_visible_organs(context)

    # Reverse mapping: (layer, filename) → old flat name
    new_to_old = {v: k for k, v in _OLD_TO_NEW.items()}

    result = []
    for layer, filename in organs:
        old_name = new_to_old.get((layer, filename))
        if old_name:
            result.append(old_name)

    return result
