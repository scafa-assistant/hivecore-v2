"""Lebensfaeden — Langzeit-Erzaehlstraenge (Patch 5).

Lebensfaeden erfassen PROZESSE, nicht einzelne Events:
  - Ein Verlust und die Trauer die sich ueber Monate verwandelt
  - Ein Projekt das 3 Monate dauert mit wachsendem Vertrauen
  - Ein Konflikt der eskaliert, explodiert und heilt
  - Identitaetsfindung ueber das erste Lebensjahr

6 Faden-Typen mit jeweils eigenen Phasen-Verlaeufen.
Max 5 aktive Faeden, abgeschlossene werden archiviert.

Bio-Aequivalent: Hippocampus-Kortex Konsolidierung (langsame
Schema-Bildung ueber Tage/Wochen → stabile Narrative).

Daten:
  skills/memory/thread_index.yaml   — Uebersicht (~200 Tokens, immer geladen)
  skills/memory/threads/active/     — Max 5 aktive (je ~500 Tokens)
  skills/memory/threads/archived/   — Abgeschlossene (vollstaendig erhalten)
"""

from datetime import datetime
from engine.organ_reader import read_yaml_organ, write_yaml_organ


# ================================================================
# Faden-Typen + Phasen-Verlaeufe
# ================================================================

FADEN_TYPEN = {
    'verlust': ['schock', 'akut', 'verarbeitung', 'integration', 'narbe'],
    'projekt': ['beginn', 'aufbau', 'krise', 'durchbruch', 'abschluss'],
    'beziehung': ['kennenlernen', 'annaeherung', 'vertiefung', 'stabilitaet'],
    'konflikt': ['reibung', 'eskalation', 'explosion', 'klaerung', 'heilung'],
    'identitaet': ['frage', 'suche', 'krise', 'einsicht', 'annahme'],
    'entdeckung': ['ahnung', 'erforschung', 'vertiefung', 'meisterung'],
}

# Sofort-Faeden: Starten sofort bei bestimmten Triggern (nicht auf Zyklusende warten)
SOFORT_TRIGGER = {
    'tod':       {'typ': 'verlust',   'phase': 'schock'},
    'genesis':   {'typ': 'beziehung', 'phase': 'kennenlernen'},
    'stresstest': {'typ': 'identitaet', 'phase': 'krise'},
    'pairing':   {'typ': 'beziehung', 'phase': 'annaeherung'},
    'geburt':    {'typ': 'beziehung', 'phase': 'kennenlernen'},
}

MAX_AKTIVE_FAEDEN = 5

# Mindest-Intensitaet fuer Zyklusende-Erkennung
MIN_INTENSITAET = 0.6
MIN_PERSISTENZ_TAGE = 2  # Thema muss an mind. 2 Tagen auftauchen


# ================================================================
# Daten-Layer: thread_index.yaml
# ================================================================

def _load_index(egon_id: str) -> dict:
    """Laedt thread_index.yaml oder initialisiert."""
    data = read_yaml_organ(egon_id, 'skills', 'memory/thread_index.yaml')
    if not data or not isinstance(data, dict):
        data = {'aktive_faeden': [], 'archivierte_faeden': [], 'zaehler': 0}
    data.setdefault('aktive_faeden', [])
    data.setdefault('archivierte_faeden', [])
    data.setdefault('zaehler', 0)
    return data


def _save_index(egon_id: str, data: dict) -> None:
    write_yaml_organ(egon_id, 'skills', 'memory/thread_index.yaml', data)


def _load_faden(egon_id: str, faden_id: str, archiviert: bool = False) -> dict | None:
    """Laedt einen einzelnen Faden."""
    subdir = 'archived' if archiviert else 'active'
    return read_yaml_organ(
        egon_id, 'skills', f'memory/threads/{subdir}/{faden_id}.yaml',
    )


def _save_faden(egon_id: str, faden_id: str, data: dict, archiviert: bool = False) -> None:
    subdir = 'archived' if archiviert else 'active'
    write_yaml_organ(
        egon_id, 'skills', f'memory/threads/{subdir}/{faden_id}.yaml', data,
    )


# ================================================================
# Faden erstellen
# ================================================================

def starte_lebensfaden(
    egon_id: str,
    typ: str,
    titel: str,
    ausloeser: str,
    start_phase: str | None = None,
    emotionen: dict | None = None,
) -> dict | None:
    """Startet einen neuen Lebensfaden.

    Args:
        egon_id: Agent-ID.
        typ: Einer der 6 Faden-Typen.
        titel: Kurztitel des Fadens (z.B. "Trauer um Eva").
        ausloeser: Was den Faden ausgeloest hat.
        start_phase: Optionale Start-Phase (default: erste Phase des Typs).
        emotionen: Dict {emotion: intensitaet} des Ausloeser-Moments.

    Returns:
        dict mit Faden-Info oder None wenn Max erreicht.
    """
    if typ not in FADEN_TYPEN:
        print(f'[lebensfaeden] Unbekannter Typ: {typ}')
        return None

    index = _load_index(egon_id)
    aktive = index['aktive_faeden']

    # Max pruefen
    if len(aktive) >= MAX_AKTIVE_FAEDEN:
        print(f'[lebensfaeden] {egon_id}: Max {MAX_AKTIVE_FAEDEN} aktive Faeden — '
              f'kann "{titel}" nicht starten')
        return None

    # Duplikat-Check: Gleicher Titel bereits aktiv?
    for af in aktive:
        if af.get('titel', '').lower() == titel.lower():
            print(f'[lebensfaeden] {egon_id}: Faden "{titel}" bereits aktiv')
            return None

    phasen = FADEN_TYPEN[typ]
    phase = start_phase if start_phase in phasen else phasen[0]

    index['zaehler'] += 1
    faden_id = f'LF{index["zaehler"]:04d}'
    heute = datetime.now().strftime('%Y-%m-%d')

    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    zyklus = state.get('zyklus', 0) if state else 0

    # Index-Eintrag (leichtgewichtig, ~40 Tokens)
    index_eintrag = {
        'id': faden_id,
        'typ': typ,
        'titel': titel,
        'phase': phase,
        'gestartet': heute,
        'letztes_update': heute,
    }
    aktive.append(index_eintrag)
    _save_index(egon_id, index)

    # Vollstaendiger Faden (detailliert, ~500 Tokens)
    faden = {
        'id': faden_id,
        'typ': typ,
        'titel': titel,
        'phasen': phasen,
        'aktuelle_phase': phase,
        'gestartet': heute,
        'ausloeser': ausloeser,
        'verlauf': [
            {
                'zyklus': zyklus,
                'tag': heute,
                'phase': phase,
                'eintrag': ausloeser[:200],
                'emotionen': emotionen or {},
            }
        ],
    }
    _save_faden(egon_id, faden_id, faden)

    print(f'[lebensfaeden] {egon_id}: Faden "{titel}" ({typ}) gestartet — Phase: {phase}')
    return {'id': faden_id, 'typ': typ, 'titel': titel, 'phase': phase}


# ================================================================
# Sofort-Faden bei bestimmten Events
# ================================================================

def sofort_faden(egon_id: str, trigger: str, details: str, emotionen: dict | None = None) -> dict | None:
    """Startet einen Sofort-Faden bei kritischen Events.

    Args:
        trigger: Einer von 'tod', 'genesis', 'stresstest', 'pairing', 'geburt'.
        details: Kurzbeschreibung des Events.
        emotionen: Emotionale Intensitaeten.
    """
    if trigger not in SOFORT_TRIGGER:
        return None

    config = SOFORT_TRIGGER[trigger]
    return starte_lebensfaden(
        egon_id=egon_id,
        typ=config['typ'],
        titel=details[:80],
        ausloeser=details,
        start_phase=config['phase'],
        emotionen=emotionen,
    )


# ================================================================
# Faden aktualisieren (Verlaufs-Eintrag + Phase-Progression)
# ================================================================

def aktualisiere_faden(
    egon_id: str,
    faden_id: str,
    eintrag: str,
    emotionen: dict | None = None,
    phase_weiter: bool = False,
) -> dict | None:
    """Fuegt einen Verlaufs-Eintrag zu einem aktiven Faden hinzu.

    Args:
        faden_id: ID des Fadens.
        eintrag: Zusammenfassung (100-120 Woerter).
        emotionen: Aktuelle emotionale Bilanz.
        phase_weiter: Ob die Phase vordruecken soll.

    Returns:
        dict mit Update-Info oder None.
    """
    faden = _load_faden(egon_id, faden_id)
    if not faden:
        return None

    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    zyklus = state.get('zyklus', 0) if state else 0
    heute = datetime.now().strftime('%Y-%m-%d')

    faden['verlauf'].append({
        'zyklus': zyklus,
        'tag': heute,
        'phase': faden['aktuelle_phase'],
        'eintrag': eintrag[:300],
        'emotionen': emotionen or {},
    })

    # Phase-Progression
    alte_phase = faden['aktuelle_phase']
    if phase_weiter:
        phasen = faden.get('phasen', [])
        idx = phasen.index(alte_phase) if alte_phase in phasen else -1
        if idx >= 0 and idx < len(phasen) - 1:
            faden['aktuelle_phase'] = phasen[idx + 1]
            print(f'[lebensfaeden] {egon_id}: Faden "{faden["titel"]}" '
                  f'Phase {alte_phase} -> {faden["aktuelle_phase"]}')

    # Komprimierung: Mitte verdichten wenn > 10 Eintraege
    if len(faden['verlauf']) > 10:
        faden['verlauf'] = _komprimiere_verlauf(faden['verlauf'])

    _save_faden(egon_id, faden_id, faden)

    # Index updaten
    index = _load_index(egon_id)
    for af in index['aktive_faeden']:
        if af['id'] == faden_id:
            af['phase'] = faden['aktuelle_phase']
            af['letztes_update'] = heute
            break
    _save_index(egon_id, index)

    return {
        'id': faden_id,
        'phase': faden['aktuelle_phase'],
        'eintraege': len(faden['verlauf']),
    }


# ================================================================
# Faden abschliessen
# ================================================================

def schliesse_faden(egon_id: str, faden_id: str, abschluss_eintrag: str = '') -> bool:
    """Schliesst einen Faden ab und archiviert ihn.

    Der Faden bleibt vollstaendig erhalten, wird nur von aktiv → archiviert verschoben.
    """
    faden = _load_faden(egon_id, faden_id)
    if not faden:
        return False

    heute = datetime.now().strftime('%Y-%m-%d')

    # Abschluss-Eintrag
    if abschluss_eintrag:
        state = read_yaml_organ(egon_id, 'core', 'state.yaml')
        zyklus = state.get('zyklus', 0) if state else 0
        faden['verlauf'].append({
            'zyklus': zyklus,
            'tag': heute,
            'phase': faden['aktuelle_phase'],
            'eintrag': abschluss_eintrag[:300],
            'emotionen': {},
        })

    faden['abgeschlossen'] = heute

    # In archiviert verschieben
    _save_faden(egon_id, faden_id, faden, archiviert=True)

    # Aus Index entfernen
    index = _load_index(egon_id)
    index['aktive_faeden'] = [
        af for af in index['aktive_faeden'] if af['id'] != faden_id
    ]
    index['archivierte_faeden'].append({
        'id': faden_id,
        'typ': faden['typ'],
        'titel': faden['titel'],
        'phase': faden['aktuelle_phase'],
        'gestartet': faden['gestartet'],
        'abgeschlossen': heute,
    })
    _save_index(egon_id, index)

    print(f'[lebensfaeden] {egon_id}: Faden "{faden["titel"]}" abgeschlossen')
    return True


# ================================================================
# Komprimierung (Anfang + Ende detailliert, Mitte verdichtet)
# ================================================================

def _komprimiere_verlauf(verlauf: list) -> list:
    """Komprimiert den Verlauf: Anfang (2) + Ende (3) detailliert, Mitte zusammengefasst.

    Bio-Analogie: Primacy-Recency Effekt — Anfang und Ende werden
    besser erinnert als die Mitte.
    """
    if len(verlauf) <= 7:
        return verlauf

    anfang = verlauf[:2]
    ende = verlauf[-3:]
    mitte = verlauf[2:-3]

    # Mitte in 2-3er Gruppen zusammenfassen
    komprimierte_mitte = []
    gruppe_groesse = max(2, len(mitte) // 3)
    for i in range(0, len(mitte), gruppe_groesse):
        gruppe = mitte[i:i + gruppe_groesse]
        if not gruppe:
            continue
        # Zusammenfassung: Kombiniere Eintraege, behalte emotionalsten Eintrag
        beste = max(
            gruppe,
            key=lambda g: sum(g.get('emotionen', {}).values()) if g.get('emotionen') else 0,
        )
        eintraege_texte = '; '.join(
            g.get('eintrag', '')[:50] for g in gruppe
        )
        komprimierte_mitte.append({
            'zyklus': beste.get('zyklus'),
            'tag': f"{gruppe[0].get('tag', '?')} – {gruppe[-1].get('tag', '?')}",
            'phase': beste.get('phase'),
            'eintrag': f'[Verdichtet: {len(gruppe)} Eintr.] {eintraege_texte[:200]}',
            'emotionen': beste.get('emotionen', {}),
            'verdichtet': True,
        })

    return anfang + komprimierte_mitte + ende


# ================================================================
# Zyklusende-Erkennung: Neue Faeden aus Episoden erkennen
# ================================================================

def zyklusende_faden_erkennung(egon_id: str) -> list:
    """Prueft ob aus den aktuellen Episoden neue Lebensfaeden entstehen sollten.

    Kriterien:
    1. Thema taucht an mehreren Tagen auf (Persistenz >= 2 Tage)
    2. Emotionale Intensitaet >= 0.6
    3. Noch nicht durch bestehenden Faden abgedeckt

    Wird am Zyklusende aus pulse_v2.py aufgerufen.
    """
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not episodes_data:
        return []

    episodes = episodes_data.get('episodes', [])
    if len(episodes) < 3:
        return []

    # Aktive Faeden-Titel sammeln
    index = _load_index(egon_id)
    aktive_titel = {af.get('titel', '').lower() for af in index['aktive_faeden']}

    # Partner-Persistenz pruefen: Gleicher Partner an mehreren Tagen mit hoher Emotion
    partner_tage = {}
    partner_emotionen = {}
    for ep in episodes[-20:]:  # Letzte 20 Episoden
        partner = ep.get('with', '')
        if not partner or partner == 'OWNER_CURRENT':
            continue
        tag = ep.get('date', '')
        if tag:
            partner_tage.setdefault(partner, set()).add(tag)

        # Emotionen sammeln
        for emo in ep.get('emotions_felt', []):
            intensity = emo.get('intensity', 0)
            if intensity >= MIN_INTENSITAET:
                partner_emotionen.setdefault(partner, []).append(intensity)

    neue_faeden = []

    for partner, tage in partner_tage.items():
        if len(tage) < MIN_PERSISTENZ_TAGE:
            continue
        emos = partner_emotionen.get(partner, [])
        if not emos:
            continue
        avg_intensitaet = sum(emos) / len(emos)
        if avg_intensitaet < MIN_INTENSITAET:
            continue

        # Nicht schon abgedeckt?
        try:
            from engine.naming import get_display_name
            p_name = get_display_name(partner, 'vorname')
        except Exception:
            p_name = partner
        potential_titel = f'Beziehung mit {p_name}'
        if potential_titel.lower() in aktive_titel:
            continue

        faden = starte_lebensfaden(
            egon_id, 'beziehung', potential_titel,
            f'Wiederholte Begegnungen mit {p_name} — {len(tage)} Tage, '
            f'ø Intensitaet {avg_intensitaet:.2f}',
        )
        if faden:
            neue_faeden.append(faden)

    # Tag-basierte Themen (Konflikte, Projekte)
    tag_tage = {}
    tag_emotionen = {}
    for ep in episodes[-20:]:
        for tag in ep.get('tags', []):
            tag_key = tag.lower()
            tag_date = ep.get('date', '')
            if tag_date:
                tag_tage.setdefault(tag_key, set()).add(tag_date)
            for emo in ep.get('emotions_felt', []):
                if emo.get('intensity', 0) >= MIN_INTENSITAET:
                    tag_emotionen.setdefault(tag_key, []).append(emo.get('intensity', 0))

    KONFLIKT_TAGS = {'konflikt', 'streit', 'wut', 'enttaeuschung', 'frustration'}
    PROJEKT_TAGS = {'lernen', 'projekt', 'bauen', 'entwickeln', 'code'}
    IDENTITAET_TAGS = {'ich', 'selbst', 'identitaet', 'wer_bin_ich', 'zweifel'}

    for tag_key, tage in tag_tage.items():
        if len(tage) < MIN_PERSISTENZ_TAGE:
            continue
        emos = tag_emotionen.get(tag_key, [])
        if not emos or sum(emos) / len(emos) < MIN_INTENSITAET:
            continue

        # Typ bestimmen
        if tag_key in KONFLIKT_TAGS:
            typ = 'konflikt'
        elif tag_key in PROJEKT_TAGS:
            typ = 'projekt'
        elif tag_key in IDENTITAET_TAGS:
            typ = 'identitaet'
        else:
            typ = 'entdeckung'

        titel = f'{tag_key.capitalize()}-Phase'
        if titel.lower() in aktive_titel:
            continue

        if len(index['aktive_faeden']) + len(neue_faeden) >= MAX_AKTIVE_FAEDEN:
            break

        faden = starte_lebensfaden(
            egon_id, typ, titel,
            f'Thema "{tag_key}" taucht persistent auf ({len(tage)} Tage)',
        )
        if faden:
            neue_faeden.append(faden)

    if neue_faeden:
        print(f'[lebensfaeden] {egon_id}: {len(neue_faeden)} neue Faeden erkannt')

    return neue_faeden


# ================================================================
# Auto-Phase-Progression (heuristisch, kein LLM)
# ================================================================

def auto_phase_check(egon_id: str) -> list:
    """Prueft ob aktive Faeden die naechste Phase erreicht haben.

    Heuristik basierend auf:
    - Anzahl Eintraege in aktueller Phase (>= 3 → weiter)
    - Emotionaler Trend (sinkende Intensitaet bei verlust → naechste Phase)
    - Zeitdauer (> 2 Zyklen in gleicher Phase → weiter)

    Returns: Liste von Phase-Aenderungen.
    """
    index = _load_index(egon_id)
    aenderungen = []

    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    zyklus = state.get('zyklus', 0) if state else 0

    for af in index['aktive_faeden']:
        faden_id = af['id']
        faden = _load_faden(egon_id, faden_id)
        if not faden:
            continue

        phasen = faden.get('phasen', [])
        aktuelle_phase = faden.get('aktuelle_phase', '')
        idx = phasen.index(aktuelle_phase) if aktuelle_phase in phasen else -1

        if idx < 0 or idx >= len(phasen) - 1:
            continue  # Bereits in letzter Phase oder unbekannt

        # Eintraege in aktueller Phase zaehlen
        eintraege_in_phase = [
            v for v in faden.get('verlauf', [])
            if v.get('phase') == aktuelle_phase and not v.get('verdichtet')
        ]

        # Heuristik 1: >= 3 Eintraege → Phase kann weiterruecken
        if len(eintraege_in_phase) >= 3:
            result = aktualisiere_faden(
                egon_id, faden_id,
                f'Phase "{aktuelle_phase}" abgeschlossen nach {len(eintraege_in_phase)} Eintraegen.',
                phase_weiter=True,
            )
            if result:
                aenderungen.append(result)
                continue

        # Heuristik 2: > 2 Zyklen in gleicher Phase
        if eintraege_in_phase:
            erster_eintrag_zyklus = eintraege_in_phase[0].get('zyklus', zyklus)
            if zyklus - erster_eintrag_zyklus >= 2:
                result = aktualisiere_faden(
                    egon_id, faden_id,
                    f'Phase "{aktuelle_phase}" nach 2+ Zyklen weitergeruckt.',
                    phase_weiter=True,
                )
                if result:
                    aenderungen.append(result)

    # Letzte Phase erreicht → Abschluss-Check
    for af in index['aktive_faeden']:
        faden = _load_faden(egon_id, af['id'])
        if not faden:
            continue
        phasen = faden.get('phasen', [])
        if faden.get('aktuelle_phase') == phasen[-1] if phasen else False:
            eintraege = [
                v for v in faden.get('verlauf', [])
                if v.get('phase') == phasen[-1] and not v.get('verdichtet')
            ]
            if len(eintraege) >= 2:
                schliesse_faden(
                    egon_id, af['id'],
                    f'Faden "{faden["titel"]}" hat letzte Phase erreicht und abgeschlossen.',
                )

    return aenderungen


# ================================================================
# Prompt-Integration: Faeden fuer System-Prompt
# ================================================================

def lebensfaeden_to_prompt(egon_id: str) -> str:
    """Formatiert aktive Lebensfaeden fuer den System-Prompt.

    Maximal ~200 Tokens (Index + aktuelle Phase).
    """
    index = _load_index(egon_id)
    aktive = index.get('aktive_faeden', [])
    if not aktive:
        return ''

    lines = []
    for af in aktive:
        typ = af.get('typ', '?')
        titel = af.get('titel', '?')
        phase = af.get('phase', '?')
        lines.append(f'- {titel} ({typ}): Phase "{phase}"')

    return 'Aktive Lebensfaeden:\n' + '\n'.join(lines)


# ================================================================
# Pulse-Integration: Zyklusende-Check
# ================================================================

def lebensfaeden_pulse(egon_id: str) -> dict:
    """Wird am Zyklusende aus pulse_v2.py aufgerufen.

    1. Zyklusende-Erkennung: Neue Faeden aus Episoden
    2. Auto-Phase-Check: Bestehende Faeden updaten
    """
    result = {}

    try:
        neue = zyklusende_faden_erkennung(egon_id)
        if neue:
            result['neue_faeden'] = [f['titel'] for f in neue]
    except Exception as e:
        result['erkennung_error'] = str(e)

    try:
        aenderungen = auto_phase_check(egon_id)
        if aenderungen:
            result['phase_aenderungen'] = aenderungen
    except Exception as e:
        result['phase_error'] = str(e)

    if result:
        print(f'[lebensfaeden] {egon_id}: Pulse — {result}')

    return result
