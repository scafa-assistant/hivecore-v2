"""Naming System — Zentrale Namensaufloesung fuer alle EGONs.

Jeder EGON hat Vorname + optional Nachname, gespeichert in state.yaml > identitaet.
Der Nachname entsteht erst beim Pairing (Verschmelzung beider Eltern-Vornamen).

Funktionen:
  get_display_name(egon_id, fmt)      -> Name auflösen
  generate_familienname(a, b)          -> Nachnamen-Verschmelzung
  naming_ceremony(state_a, state_b, g) -> Drive-basierte Vornamenwahl
  clear_name_cache()                   -> Cache leeren (am Pulse-Start)
"""

import random
from engine.organ_reader import read_yaml_organ

# ================================================================
# Name Cache (wird pro Pulse-Zyklus geleert)
# ================================================================

_name_cache: dict = {}


def clear_name_cache():
    """Am Start jedes Pulse-Zyklus aufrufen."""
    _name_cache.clear()


# ================================================================
# 1. Name auflösen
# ================================================================

def get_display_name(egon_id: str, fmt: str = 'vorname') -> str:
    """Zentrale Namensaufloesung mit state.yaml + ID-Fallback.

    Args:
        egon_id: Agent ID (z.B. 'adam_001')
        fmt: 'vorname' | 'nachname' | 'voll'

    Returns:
        Name-String. Fallback auf ID-Derivat wenn kein identitaet-Block.
    """
    if not egon_id:
        return '?'

    if egon_id in _name_cache:
        ident = _name_cache[egon_id]
    else:
        state = read_yaml_organ(egon_id, 'core', 'state.yaml')
        ident = (state or {}).get('identitaet', {})
        if not ident:
            # Fallback: Name aus ID ableiten (adam_001 -> Adam)
            fallback = egon_id.split('_')[0].title()
            ident = {'vorname': fallback, 'nachname': None, 'anzeigename': fallback}
        _name_cache[egon_id] = ident

    if fmt == 'voll':
        return ident.get('anzeigename') or ident.get('vorname', egon_id)
    elif fmt == 'nachname':
        return ident.get('nachname') or ''
    else:  # vorname
        return ident.get('vorname') or egon_id.split('_')[0].title()


# ================================================================
# 2. Familienname generieren (Silben-Verschmelzung)
# ================================================================

# Deutsche Vokale fuer Silbenerkennung
_VOWELS = set('aeiouäöüAEIOUÄÖÜ')


def _split_syllables(name: str) -> list:
    """Einfache Silbentrennung basierend auf Vokal-Konsonant-Grenzen.

    Beispiele:
      Adam   -> ['A', 'dam']
      Eva    -> ['E', 'va']
      Lilith -> ['Li', 'lith']
      Kain   -> ['Kain']
    """
    if not name:
        return [name]

    syllables = []
    current = name[0]

    for i in range(1, len(name)):
        ch = name[i]
        prev = name[i - 1]

        # Silbengrenze: Konsonant gefolgt von Vokal (ausser am Anfang)
        if ch in _VOWELS and prev not in _VOWELS and len(current) > 1:
            syllables.append(current)
            current = ch
        else:
            current += ch

    if current:
        syllables.append(current)

    return syllables if syllables else [name]


def generate_familienname(vorname_a: str, vorname_b: str) -> str:
    """Verschmelzt zwei Eltern-Vornamen zu einem Familiennamen.

    Algorithmus:
      1. Beide Namen in Silben zerlegen
      2. Zufaellig entscheiden wer die erste Haelfte gibt
      3. Erste Silbe(n) von A + letzte Silbe(n) von B
      4. Max 8 Zeichen, Grossbuchstabe am Anfang

    Beispiele:
      Adam + Eva    -> Adeva, Evam
      Kain + Lilith -> Kailith, Likain
      Abel + Ada    -> Abda, Adel
    """
    syl_a = _split_syllables(vorname_a)
    syl_b = _split_syllables(vorname_b)

    # Zufaellig wer die erste Haelfte gibt
    if random.random() < 0.5:
        syl_a, syl_b = syl_b, syl_a

    # Erste Silbe(n) von A
    first_part = syl_a[0]

    # Letzte Silbe(n) von B
    last_part = syl_b[-1] if len(syl_b) > 1 else syl_b[0]

    # Zusammenfuegen
    raw = first_part + last_part.lower()

    # Aussprechbarkeit: Keine 3+ gleichen Konsonanten/Vokale hintereinander
    result = _fix_pronunciation(raw)

    # Max 8 Zeichen, Grossbuchstabe
    result = result[:8].capitalize()

    # Mindestens 3 Zeichen
    if len(result) < 3:
        result = (vorname_a[:2] + vorname_b[:2]).capitalize()

    return result


def _fix_pronunciation(name: str) -> str:
    """Entferne unaussprechbare Konsonant-/Vokal-Haeuungen."""
    result = []
    cons_count = 0
    vowel_count = 0

    for ch in name:
        if ch.lower() in _VOWELS:
            vowel_count += 1
            cons_count = 0
        else:
            cons_count += 1
            vowel_count = 0

        # Max 2 Konsonanten oder 2 Vokale hintereinander
        if cons_count > 2 or vowel_count > 2:
            continue
        result.append(ch)

    return ''.join(result)


# ================================================================
# 3. Naming Ceremony (Drive-basierte Vornamenwahl)
# ================================================================

# Namenspools geordnet nach Drive-Affinitaet
NAME_POOLS = {
    'SEEKING':  {'M': ['Noel', 'Ezra', 'Amos', 'Orion'],
                 'F': ['Nora', 'Iris', 'Vera', 'Stella']},
    'CARE':     {'M': ['Seth', 'Levi', 'Silas', 'Elan'],
                 'F': ['Hana', 'Alma', 'Mila', 'Clara']},
    'PLAY':     {'M': ['Milo', 'Jonas', 'Felix', 'Lio'],
                 'F': ['Luna', 'Zara', 'Lia', 'Juna']},
    'ACTION':   {'M': ['Aran', 'Kai', 'Tayo', 'Ren'],
                 'F': ['Freya', 'Tara', 'Nika', 'Ayla']},
    'FEAR':     {'M': ['Elias', 'Theo', 'Samu'],
                 'F': ['Ida', 'Lina', 'Runa']},
    'GRIEF':    {'M': ['Joris', 'Levin', 'Ilian'],
                 'F': ['Mara', 'Selma', 'Nella']},
    'LEARNING': {'M': ['Leon', 'Hugo', 'Nils'],
                 'F': ['Thea', 'Emilia', 'Vela']},
    'RAGE':     {'M': ['Tyron', 'Jaro', 'Viggo'],
                 'F': ['Kira', 'Ylva', 'Reva']},
    'PANIC':    {'M': ['Lukas', 'Ben', 'Tim'],
                 'F': ['Lea', 'Mia', 'Ava']},
    'LUST':     {'M': ['Aurelio', 'Valentin', 'Eros'],
                 'F': ['Aurora', 'Valentina', 'Vida']},
}


def _drive_weighted_pool(drives: dict, geschlecht: str) -> dict:
    """Erzeugt gewichteten Namenspool aus Drives eines Elternteils.

    Jeder Drive fuegt seine Namen mit dem Drive-Wert als Gewicht hinzu.
    Nur die Top-5 Drives werden beruecksichtigt.
    """
    pool = {}
    # Top-5 Drives sortiert nach Wert
    sorted_drives = sorted(drives.items(), key=lambda x: -float(x[1]))[:5]

    for drive_name, drive_val in sorted_drives:
        val = float(drive_val)
        if val < 0.1:
            continue
        names = NAME_POOLS.get(drive_name, {}).get(geschlecht, [])
        for name in names:
            # Gewicht = Drive-Wert (hoehere Drives -> staerkere Praeferenz)
            pool[name] = pool.get(name, 0) + val

    return pool


def naming_ceremony(state_a: dict, state_b: dict, geschlecht: str,
                    existing_names: set = None) -> str:
    """Naming Ceremony — beide Eltern waehlen gemeinsam den Vornamen.

    Algorithmus:
      1. Jeder Elternteil erzeugt einen gewichteten Namenspool aus seinen Drives
      2. Namen die BEIDE Eltern hoch ranken kriegen 1.5x Konsens-Bonus
      3. Bereits existierende Agent-Namen werden ausgeschlossen
      4. Gewichtete Zufallswahl aus dem Konsens-Pool

    Args:
        state_a: state.yaml von Elternteil A
        state_b: state.yaml von Elternteil B
        geschlecht: 'M' oder 'F' des LIBEROs
        existing_names: Menge bereits vergebener Namen (optional, wird sonst geladen)

    Returns:
        Gewaehlter Vorname
    """
    drives_a = state_a.get('drives', {})
    drives_b = state_b.get('drives', {})

    pool_a = _drive_weighted_pool(drives_a, geschlecht)
    pool_b = _drive_weighted_pool(drives_b, geschlecht)

    # Merge mit Konsens-Bonus
    merged = {}
    for name, weight in pool_a.items():
        merged[name] = weight
    for name, weight in pool_b.items():
        if name in merged:
            # Konsens-Bonus: 1.5x wenn beide Eltern den Namen hoch ranken
            merged[name] = (merged[name] + weight) * 1.5
        else:
            merged[name] = weight

    # Existierende Namen ausschliessen
    if existing_names is None:
        try:
            from engine.genesis import discover_agents
            existing_names = {eid.rsplit('_', 1)[0].lower() for eid in discover_agents()}
        except Exception:
            existing_names = set()

    # Auch Gen-0 Vornamen ausschliessen
    gen0_names = {'adam', 'eva', 'lilith', 'kain', 'ada', 'abel'}
    exclude = existing_names | gen0_names

    available = {n: w for n, w in merged.items() if n.lower() not in exclude}

    if not available:
        # Fallback: Alle Pools durchgehen
        all_names = set()
        for drive_pool in NAME_POOLS.values():
            all_names.update(drive_pool.get(geschlecht, []))
        available_fallback = [n for n in all_names if n.lower() not in exclude]
        if available_fallback:
            return random.choice(available_fallback)
        # Letzter Fallback
        return f'Libero{random.randint(100, 999)}'

    names = list(available.keys())
    weights = list(available.values())
    return random.choices(names, weights=weights, k=1)[0]
