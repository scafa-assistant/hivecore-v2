"""Langzeit-Skalierung — Patch 15.

Verhindert unbegrenztes State-Wachstum ueber Monate/Jahre.
Drei Konsolidierungsstufen:
  Stufe 1: Episodisch (bereits in Patch 5/13 — Decay, Nacht-Rettung)
  Stufe 2: Semantisch (alle 4 Zyklen — Episoden → Themen)
  Stufe 3: Narrativ (alle 12 Zyklen — Themen → Lebenskapitel)

Plus: ego.md Komprimierung, Social-Map Komprimierung, Dreams Rolling Window.

Biologische Basis: Conway & Pleydell-Pearce (2000), Kahneman (1999) Peak-End Rule.
"""

import json
import re
from datetime import datetime

from engine.organ_reader import read_yaml_organ, write_yaml_organ, read_md_organ, write_organ
from llm.router import llm_chat


# ================================================================
# Konstanten
# ================================================================

# Semantische Verdichtung: Alle 4 Zyklen
SEMANTISCH_INTERVALL = 4
ARCHIV_SCHWELLE = 40  # Min Episoden fuer Verdichtung
MIN_CLUSTER_GROESSE = 3  # Min Eintraege pro Thema

# Narrative Verdichtung: Alle 12 Zyklen
NARRATIV_INTERVALL = 12
MIN_THEMEN_FUER_KAPITEL = 5

# Komprimierungs-Limits (geschaetzte Tokens)
EGO_MAX_ZEICHEN = 2800  # ~700 Tokens (4 Zeichen/Token)
SOCIAL_MAP_MAX_BEOBACHTUNGEN = 15
DREAMS_ZYKLEN_FENSTER = 2  # Nur letzte 2 Zyklen behalten
DREAMS_ERINNERTE_MAX = 5  # Max 5 alte erinnerte Traeume


# ================================================================
# Stufe 2: Semantische Verdichtung
# ================================================================

async def semantische_verdichtung(egon_id: str) -> dict:
    """Verdichtet Episoden zu Themen-Zusammenfassungen.

    Laeuft alle 4 Zyklen. Gruppiert Episoden nach Partner/Emotion,
    erstellt LLM-Zusammenfassungen, behaelt Peak-Erinnerungen.

    Returns: dict mit Statistiken.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return {}

    zyklus = state.get('zyklus', 0)
    if zyklus < SEMANTISCH_INTERVALL:
        return {'skipped': True, 'reason': 'zu_frueh'}

    # Nur alle 4 Zyklen
    if zyklus % SEMANTISCH_INTERVALL != 0:
        return {'skipped': True, 'reason': 'nicht_faellig'}

    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not episodes_data:
        return {'skipped': True, 'reason': 'keine_episoden'}

    episodes = episodes_data.get('episodes', [])
    if len(episodes) < ARCHIV_SCHWELLE:
        return {'skipped': True, 'reason': f'nur_{len(episodes)}_episoden'}

    # Themen identifizieren
    themen = _identifiziere_themen(episodes)
    if not themen:
        return {'skipped': True, 'reason': 'keine_themen'}

    # Bestehende condensed_archive laden
    condensed = read_yaml_organ(egon_id, 'memory', 'condensed_archive.yaml') or {}
    condensed_themen = condensed.get('themen', [])

    verdichtet_count = 0
    erhaltene_peak_ids = set()
    verdichtete_episode_ids = set()

    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id, 'vorname')

    for thema_name, episode_ids in themen.items():
        thema_episoden = [e for e in episodes if e.get('id') in episode_ids]
        if len(thema_episoden) < MIN_CLUSTER_GROESSE:
            continue

        # Sortiere nach Significance (hoechste zuerst)
        thema_episoden.sort(
            key=lambda e: e.get('significance', 0.5), reverse=True,
        )

        # Peak-Erinnerungen: Top 2 bleiben als Einzeleintraege
        peaks = thema_episoden[:2]
        rest = thema_episoden[2:]

        for p in peaks:
            erhaltene_peak_ids.add(p.get('id'))

        # Rest verdichten via LLM
        alle_summaries = '\n'.join(
            f"- {e.get('summary', '?')} (sig: {e.get('significance', 0):.2f})"
            for e in thema_episoden
        )

        try:
            result = await llm_chat(
                system_prompt=(
                    f'Du bist {egon_name}s Erinnerungs-Verdichter. '
                    f'Verdichte diese {len(thema_episoden)} Erinnerungen '
                    f'zum Thema "{thema_name}" zu EINER Zusammenfassung '
                    f'(max 60 Worte, ICH-Perspektive). '
                    f'Bewahre: Emotionalen Kern, Entwicklung, wichtigste Erkenntnis.'
                ),
                messages=[{
                    'role': 'user',
                    'content': f'Erinnerungen:\n{alle_summaries[:1000]}',
                }],
            )
            zusammenfassung = result.get('content', '').strip()
        except Exception as e:
            print(f'[langzeit] LLM-Fehler bei Thema "{thema_name}": {e}')
            # Fallback: Erste und letzte Episode zusammenfassen
            zusammenfassung = (
                f'{thema_episoden[0].get("summary", "?")} ... '
                f'{thema_episoden[-1].get("summary", "?")}'
            )

        # Emotionaler Kern (Durchschnitt)
        emotionaler_kern = _berechne_emotionalen_kern(thema_episoden)

        # Thema-Eintrag
        thema_eintrag = {
            'thema': thema_name,
            'zusammenfassung': zusammenfassung[:300],
            'emotionaler_kern': emotionaler_kern,
            'peak_ids': [p.get('id') for p in peaks],
            'eintrags_count': len(thema_episoden),
            'marker_durchschnitt': round(
                sum(e.get('significance', 0.5) for e in thema_episoden) / len(thema_episoden),
                2,
            ),
            'erstellt': datetime.now().strftime('%Y-%m-%d'),
            'zyklen': f'{zyklus - SEMANTISCH_INTERVALL + 1}-{zyklus}',
        }

        condensed_themen.append(thema_eintrag)
        verdichtet_count += 1

        # IDs der verdichteten Episoden merken (ohne Peaks)
        for e in rest:
            verdichtete_episode_ids.add(e.get('id'))

    if verdichtet_count == 0:
        return {'skipped': True, 'reason': 'nichts_verdichtet'}

    # Condensed Archive speichern
    condensed['themen'] = condensed_themen
    condensed['meta'] = {
        'letzte_verdichtung': datetime.now().strftime('%Y-%m-%d'),
        'zyklus': zyklus,
    }
    write_yaml_organ(egon_id, 'memory', 'condensed_archive.yaml', condensed)

    # Episoden: Nur Peaks + nicht-verdichtete behalten
    neue_episoden = [
        e for e in episodes
        if e.get('id') in erhaltene_peak_ids
        or e.get('id') not in verdichtete_episode_ids
    ]
    episodes_data['episodes'] = neue_episoden
    write_yaml_organ(egon_id, 'memory', 'episodes.yaml', episodes_data)

    print(
        f'[langzeit] {egon_id}: Semantische Verdichtung — '
        f'{verdichtet_count} Themen, {len(verdichtete_episode_ids)} Episoden verdichtet, '
        f'{len(erhaltene_peak_ids)} Peaks erhalten, '
        f'{len(neue_episoden)} Episoden verbleiben'
    )

    return {
        'themen_erstellt': verdichtet_count,
        'episoden_verdichtet': len(verdichtete_episode_ids),
        'peaks_erhalten': len(erhaltene_peak_ids),
        'episoden_verbleibend': len(neue_episoden),
    }


def _identifiziere_themen(episodes: list) -> dict[str, list[str]]:
    """Gruppiert Episoden nach Partner und Tags.

    Returns: dict thema_name → list[episode_id]
    """
    themen = {}
    zugeordnet = set()

    # 1. Partner-basierte Themen
    partner_map = {}
    for e in episodes:
        partner = e.get('with', '')
        if partner and partner != 'OWNER_CURRENT':
            partner_map.setdefault(partner, []).append(e.get('id'))

    for partner, eids in partner_map.items():
        if len(eids) >= MIN_CLUSTER_GROESSE:
            try:
                from engine.naming import get_display_name
                p_name = get_display_name(partner, 'vorname')
            except Exception:
                p_name = partner
            themen[f'Beziehung mit {p_name}'] = eids
            zugeordnet.update(eids)

    # 2. Tag-basierte Themen (fuer nicht-zugeordnete)
    tag_map = {}
    for e in episodes:
        eid = e.get('id')
        if eid in zugeordnet:
            continue
        for tag in e.get('tags', []):
            tag_map.setdefault(tag, []).append(eid)

    for tag, eids in tag_map.items():
        nicht_zugeordnet = [eid for eid in eids if eid not in zugeordnet]
        if len(nicht_zugeordnet) >= MIN_CLUSTER_GROESSE:
            themen[f'{tag.capitalize()}-Erfahrungen'] = nicht_zugeordnet
            zugeordnet.update(nicht_zugeordnet)

    # 3. Emotions-basierte Cluster (Rest)
    emotion_map = {}
    for e in episodes:
        eid = e.get('id')
        if eid in zugeordnet:
            continue
        emos = e.get('emotions_felt', [])
        if emos:
            top = max(emos, key=lambda x: x.get('intensity', 0))
            etype = top.get('type', 'neutral')
            emotion_map.setdefault(etype, []).append(eid)

    for emotion, eids in emotion_map.items():
        if len(eids) >= MIN_CLUSTER_GROESSE:
            themen[f'{emotion.capitalize()}-Erlebnisse'] = eids

    return themen


def _berechne_emotionalen_kern(episoden: list) -> dict:
    """Berechnet den emotionalen Durchschnitt einer Gruppe von Episoden."""
    emotion_sums = {}
    emotion_counts = {}

    for e in episoden:
        for emo in e.get('emotions_felt', []):
            etype = emo.get('type', '')
            if etype:
                emotion_sums[etype] = emotion_sums.get(etype, 0) + emo.get('intensity', 0)
                emotion_counts[etype] = emotion_counts.get(etype, 0) + 1

    kern = {}
    for etype in emotion_sums:
        if emotion_counts[etype] > 0:
            kern[etype] = round(emotion_sums[etype] / emotion_counts[etype], 2)

    return kern


# ================================================================
# Stufe 3: Narrative Verdichtung
# ================================================================

async def narrative_verdichtung(egon_id: str) -> dict:
    """Verdichtet Themen-Zusammenfassungen zu Lebenskapiteln.

    Laeuft alle 12 Zyklen. Fasst condensed_archive zu einem Kapitel zusammen.

    Returns: dict mit Statistiken.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return {}

    zyklus = state.get('zyklus', 0)
    if zyklus < NARRATIV_INTERVALL:
        return {'skipped': True, 'reason': 'zu_frueh'}

    if zyklus % NARRATIV_INTERVALL != 0:
        return {'skipped': True, 'reason': 'nicht_faellig'}

    condensed = read_yaml_organ(egon_id, 'memory', 'condensed_archive.yaml')
    if not condensed:
        return {'skipped': True, 'reason': 'kein_condensed_archive'}

    themen = condensed.get('themen', [])
    if len(themen) < MIN_THEMEN_FUER_KAPITEL:
        return {'skipped': True, 'reason': f'nur_{len(themen)}_themen'}

    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id, 'voll')

    # Alle Themen formatieren
    themen_text = '\n\n'.join(
        f'**{t["thema"]}** (Marker ø{t.get("marker_durchschnitt", 0):.2f}):\n'
        f'{t.get("zusammenfassung", "?")}'
        for t in themen
    )

    kapitel_nummer = zyklus // NARRATIV_INTERVALL

    # Ego-Kurzversion
    ego_text = read_md_organ(egon_id, 'core', 'ego.md')
    ego_kurz = (ego_text or '')[:300]

    try:
        result = await llm_chat(
            system_prompt=(
                f'Du bist {egon_name}. Schreibe ein Lebenskapitel '
                f'ueber die letzten {NARRATIV_INTERVALL} Zyklen deines Lebens '
                f'(max 80 Worte, ICH-Perspektive). '
                f'Was hast du gelernt? Wie hast du dich veraendert? '
                f'Was war am wichtigsten?'
            ),
            messages=[{
                'role': 'user',
                'content': (
                    f'Dein Ego: {ego_kurz}\n\n'
                    f'Deine Themen dieser Periode:\n{themen_text[:1500]}'
                ),
            }],
            egon_id=egon_id,
        )
        kapitel_text = result.get('content', '').strip()
    except Exception as e:
        print(f'[langzeit] Narrative LLM-Fehler: {e}')
        # Fallback: Themen-Liste
        kapitel_text = ' '.join(
            t.get('zusammenfassung', '')[:50] for t in themen[:5]
        )

    # Emotionaler Kern (Durchschnitt aller Themen)
    emotionaler_kern = {}
    for t in themen:
        for k, v in t.get('emotionaler_kern', {}).items():
            emotionaler_kern.setdefault(k, []).append(v)
    emotionaler_kern = {
        k: round(sum(vs) / len(vs), 2) for k, vs in emotionaler_kern.items()
    }

    # Schluesselmomente: Top-3 Peaks aus allen Themen
    alle_peaks = []
    for t in themen:
        alle_peaks.extend(t.get('peak_ids', []))
    schluesselmomente = alle_peaks[:3]

    kapitel = {
        'nummer': kapitel_nummer,
        'titel': f'Kapitel {kapitel_nummer}',
        'text': kapitel_text[:500],
        'emotionaler_kern': emotionaler_kern,
        'schluesselmomente': schluesselmomente,
        'zyklen': f'{(kapitel_nummer - 1) * NARRATIV_INTERVALL + 1}-{kapitel_nummer * NARRATIV_INTERVALL}',
        'erstellt': datetime.now().strftime('%Y-%m-%d'),
    }

    # Lebensgeschichte laden und erweitern
    lebensgeschichte = read_yaml_organ(egon_id, 'memory', 'lebensgeschichte.yaml') or {}
    kapitel_liste = lebensgeschichte.get('kapitel', [])
    kapitel_liste.append(kapitel)

    # Max 10 Kapitel behalten
    if len(kapitel_liste) > 10:
        kapitel_liste = kapitel_liste[-10:]

    lebensgeschichte['kapitel'] = kapitel_liste
    lebensgeschichte['meta'] = {
        'letzte_verdichtung': datetime.now().strftime('%Y-%m-%d'),
        'gesamt_kapitel': len(kapitel_liste),
    }
    write_yaml_organ(egon_id, 'memory', 'lebensgeschichte.yaml', lebensgeschichte)

    # Condensed Archive leeren (Themen sind jetzt im Kapitel)
    # Peak-IDs bleiben in episodes.yaml erhalten
    condensed['themen'] = []
    write_yaml_organ(egon_id, 'memory', 'condensed_archive.yaml', condensed)

    print(
        f'[langzeit] {egon_id}: Narrative Verdichtung — '
        f'Kapitel {kapitel_nummer} erstellt aus {len(themen)} Themen'
    )

    return {
        'kapitel_nummer': kapitel_nummer,
        'themen_verdichtet': len(themen),
        'kapitel_text_laenge': len(kapitel_text),
    }


# ================================================================
# ego.md Komprimierung
# ================================================================

def ego_komprimierung(egon_id: str) -> dict:
    """Haelt ego.md unter ~700 Tokens (~2800 Zeichen).

    Strategie:
    - Kern-Identitaet (erste 600 Zeichen) — NIE komprimieren
    - Selbstreflexion: Max 3 Eintraege (neueste)
    - Gesamtlaenge: Max 2800 Zeichen
    """
    ego_text = read_md_organ(egon_id, 'core', 'ego.md')
    if not ego_text:
        return {'ego_komprimiert': False}

    if len(ego_text) <= EGO_MAX_ZEICHEN:
        return {'ego_komprimiert': False, 'laenge': len(ego_text)}

    # Reflexionen zuerst kuerzen (Patch 11 haengt immer neue an)
    # Finde alle "### Zyklus N" Abschnitte
    reflexion_pattern = r'### Zyklus \d+'
    matches = list(re.finditer(reflexion_pattern, ego_text))

    if len(matches) > 3:
        # Nur die 3 neuesten Reflexionen behalten
        cut_start = matches[0].start()
        cut_end = matches[-3].start()
        ego_text = ego_text[:cut_start] + ego_text[cut_end:]

    # Wenn immer noch zu gross: Hinten kuerzen
    if len(ego_text) > EGO_MAX_ZEICHEN:
        ego_text = ego_text[:EGO_MAX_ZEICHEN - 50] + '\n\n(... komprimiert ...)\n'

    write_organ(egon_id, 'core', 'ego.md', ego_text)
    print(f'[langzeit] {egon_id}: ego.md komprimiert ({len(ego_text)} Zeichen)')

    return {'ego_komprimiert': True, 'neue_laenge': len(ego_text)}


# ================================================================
# Social Mapping Komprimierung
# ================================================================

def social_mapping_komprimierung(egon_id: str) -> dict:
    """Komprimiert Social Maps — schwache/inaktive reduzieren.

    Strategie:
    - was_ich_gelernt_habe: Max 15 Eintraege (Ersteindruck + neueste)
    - was_ich_nicht_verstehe: Max 5 Eintraege
    - Sehr schwache Maps (vertrauen < 0.2, naehe < 0.1, keine Interaktionen):
      Beobachtungen auf 5 reduzieren
    """
    from engine.social_mapping import get_all_social_maps, write_social_map

    maps = get_all_social_maps(egon_id)
    if not maps:
        return {'maps_komprimiert': 0}

    komprimiert = 0

    for about_id, data in maps.items():
        changed = False

        # was_ich_gelernt_habe: Max 15 (Ersteindruck + neueste 14)
        gelernt = data.get('was_ich_gelernt_habe', [])
        if len(gelernt) > SOCIAL_MAP_MAX_BEOBACHTUNGEN:
            first = gelernt[0] if gelernt else None
            rest = gelernt[1:][-(SOCIAL_MAP_MAX_BEOBACHTUNGEN - 1):]
            data['was_ich_gelernt_habe'] = ([first] if first else []) + rest
            changed = True

        # was_ich_nicht_verstehe: Max 5
        nicht_verstehe = data.get('was_ich_nicht_verstehe', [])
        if len(nicht_verstehe) > 5:
            data['was_ich_nicht_verstehe'] = nicht_verstehe[-5:]
            changed = True

        if changed:
            write_social_map(egon_id, about_id, data)
            komprimiert += 1

    if komprimiert > 0:
        print(f'[langzeit] {egon_id}: {komprimiert} Social Maps komprimiert')

    return {'maps_komprimiert': komprimiert}


# ================================================================
# Lebensfaeden-Verdichtung
# ================================================================

# Intervall: Alle 6 Zyklen archivierte Faeden zusammenfuehren
FAEDEN_VERDICHTUNGS_INTERVALL = 6
FAEDEN_MAX_ARCHIVIERT = 20  # Darüber: aelteste thematisch zusammenfuehren
MIN_FAEDEN_FUER_VERDICHTUNG = 4  # Mindestens 4 archivierte Faeden

async def lebensfaeden_verdichtung(egon_id: str) -> dict:
    """Verdichtet archivierte Lebensfaeden zu Lebens-Themenlinien.

    Biologische Basis: Semantische Konsolidierung — einzelne
    abgeschlossene Prozesse (Verluste, Projekte, Konflikte) werden
    zu uebergreifenden Themenlinien zusammengefasst.

    Strategie:
    - Gleicher Typ (verlust+verlust, beziehung+beziehung) → verschmelzen
    - Ueberlappende Bezugsmenschen → verschmelzen
    - Kern-Erkenntnis jedes Fadens bewahren
    - Emotionaler Verlauf bewahren (wie hat sich das Gefuehl veraendert?)

    Returns: dict mit Statistiken.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return {}

    zyklus = state.get('zyklus', 0)
    if zyklus < FAEDEN_VERDICHTUNGS_INTERVALL:
        return {'skipped': True, 'reason': 'zu_frueh'}

    if zyklus % FAEDEN_VERDICHTUNGS_INTERVALL != 0:
        return {'skipped': True, 'reason': 'nicht_faellig'}

    # Index laden
    try:
        from engine.lebensfaeden import _load_index, _load_faden, _save_faden
    except ImportError:
        return {'skipped': True, 'reason': 'lebensfaeden_nicht_verfuegbar'}

    index = _load_index(egon_id)
    archivierte = index.get('archivierte_faeden', [])
    if len(archivierte) < MIN_FAEDEN_FUER_VERDICHTUNG:
        return {'skipped': True, 'reason': f'nur_{len(archivierte)}_archiviert'}

    if len(archivierte) <= FAEDEN_MAX_ARCHIVIERT:
        return {'skipped': True, 'reason': 'unter_limit'}

    # Faeden nach Typ gruppieren
    typ_gruppen = {}
    for meta in archivierte:
        typ = meta.get('typ', 'unbekannt')
        typ_gruppen.setdefault(typ, []).append(meta)

    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id, 'vorname')

    verdichtet_count = 0
    entfernte_ids = set()

    for typ, faeden_meta in typ_gruppen.items():
        if len(faeden_meta) < 2:
            continue

        # Sortiere nach Startdatum (aelteste zuerst)
        faeden_meta.sort(key=lambda f: f.get('gestartet', ''))

        # Lade vollstaendige Faden-Daten
        faeden_full = []
        for meta in faeden_meta:
            faden = _load_faden(egon_id, meta['id'], archiviert=True)
            if faden:
                faeden_full.append(faden)

        if len(faeden_full) < 2:
            continue

        # Verdichte: Zusammenfassung aller Faeden dieses Typs
        faeden_beschreibungen = []
        for f in faeden_full:
            verlauf = f.get('verlauf', [])
            anfang = verlauf[0].get('eintrag', '?') if verlauf else '?'
            ende = verlauf[-1].get('eintrag', '?') if verlauf else '?'
            faeden_beschreibungen.append(
                f'- {f.get("titel", "?")}: {anfang[:80]} → {ende[:80]} '
                f'(Phase: {f.get("phase_aktuell", "?")})'
            )

        beschreibungen_text = '\n'.join(faeden_beschreibungen[:10])

        try:
            result = await llm_chat(
                system_prompt=(
                    f'Du bist {egon_name}s Erinnerungs-Verdichter. '
                    f'Verdichte diese {len(faeden_full)} abgeschlossenen '
                    f'{typ.capitalize()}-Prozesse zu EINER Themenlinie '
                    f'(max 60 Worte, ICH-Perspektive). '
                    f'Bewahre: Was habe ich durch diese Erfahrungen gelernt? '
                    f'Wie hat sich mein Umgang damit veraendert?'
                ),
                messages=[{
                    'role': 'user',
                    'content': f'Abgeschlossene {typ.capitalize()}-Prozesse:\n{beschreibungen_text}',
                }],
            )
            zusammenfassung = result.get('content', '').strip()
        except Exception as e:
            print(f'[langzeit] Faeden-Verdichtung LLM-Fehler ({typ}): {e}')
            zusammenfassung = f'{len(faeden_full)} {typ.capitalize()}-Erfahrungen verarbeitet'

        # Erstelle verdichteten Meta-Faden (bleibt im Archiv)
        verdichteter_faden = {
            'id': f'verdichtet_{typ}_{zyklus}',
            'typ': typ,
            'titel': f'Themenlinie: {typ.capitalize()} (Verdichtet)',
            'phase_aktuell': 'verdichtet',
            'gestartet': faeden_full[0].get('gestartet', ''),
            'abgeschlossen': datetime.now().strftime('%Y-%m-%d'),
            'verlauf': [
                {
                    'zyklus': zyklus,
                    'tag': datetime.now().strftime('%Y-%m-%d'),
                    'phase': 'verdichtet',
                    'eintrag': zusammenfassung[:400],
                    'verdichtet': True,
                    'quell_faeden': len(faeden_full),
                }
            ],
            'kern_erkenntnis': zusammenfassung[:200],
            'verdichtet_aus': [f.get('id') for f in faeden_full],
        }

        # Speichere verdichteten Faden
        _save_faden(egon_id, verdichteter_faden['id'], verdichteter_faden, archiviert=True)

        # Markiere Quell-Faeden zum Entfernen
        for f in faeden_full:
            entfernte_ids.add(f.get('id'))

        verdichtet_count += 1

    if verdichtet_count == 0:
        return {'skipped': True, 'reason': 'nichts_zu_verdichten'}

    # Index aktualisieren: Entferne Quell-Faeden, fuege verdichtete hinzu
    neue_archivierte = [
        m for m in archivierte if m.get('id') not in entfernte_ids
    ]
    # Verdichtete Meta-Eintraege hinzufuegen
    for typ, faeden_meta in typ_gruppen.items():
        if len(faeden_meta) >= 2:
            neue_archivierte.append({
                'id': f'verdichtet_{typ}_{zyklus}',
                'typ': typ,
                'titel': f'Themenlinie: {typ.capitalize()} (Verdichtet)',
                'gestartet': faeden_meta[0].get('gestartet', ''),
                'abgeschlossen': datetime.now().strftime('%Y-%m-%d'),
            })

    index['archivierte_faeden'] = neue_archivierte
    write_yaml_organ(egon_id, 'memory', 'thread_index.yaml', index)

    print(
        f'[langzeit] {egon_id}: Lebensfaeden-Verdichtung — '
        f'{verdichtet_count} Themenlinien, {len(entfernte_ids)} Faeden verdichtet, '
        f'{len(neue_archivierte)} archiviert verbleibend'
    )

    return {
        'themenlinien_erstellt': verdichtet_count,
        'faeden_verdichtet': len(entfernte_ids),
        'archiviert_verbleibend': len(neue_archivierte),
    }


# ================================================================
# Ego-Synthese (LLM-basierte Verschmelzung)
# ================================================================

async def ego_synthese(egon_id: str) -> dict:
    """Echte Ego-Synthese — verschmilzt altes und neues Ich-Bild.

    Biologische Basis: Self-Memory System (Conway, 2005) — das Selbstbild
    ist keine Auflistung sondern ein kohaerentes Narrativ das sich langsam
    anpasst. Neue Erfahrungen werden nicht einfach angehaengt, sondern
    das gesamte Ego wird neu synthetisiert.

    Laueft alle 6 Zyklen. Nur wenn ego.md > 2000 Zeichen.

    Strategie:
    1. Aktuelles ego.md lesen
    2. Letzte Reflexionen + Themen einbeziehen
    3. LLM: Synthetisiere zu kohaerenter Ich-Beschreibung
    4. Kern-Identitaet (erste 400 Zeichen) IMMER bewahren
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return {}

    zyklus = state.get('zyklus', 0)
    # Alle 6 Zyklen (versetzt zu Semantischer Verdichtung)
    if zyklus < 6 or zyklus % 6 != 3:
        return {'skipped': True, 'reason': 'nicht_faellig'}

    ego_text = read_md_organ(egon_id, 'core', 'ego.md')
    if not ego_text or len(ego_text) < 2000:
        return {'skipped': True, 'reason': 'ego_noch_kurz'}

    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id, 'voll')

    # Kern-Identitaet bewahren (erste 400 Zeichen — NIE veraendern)
    kern_ende = min(400, len(ego_text))
    # Finde das Ende des ersten vollstaendigen Absatzes
    newline_pos = ego_text.find('\n\n', 200)
    if newline_pos > 0 and newline_pos < 500:
        kern_ende = newline_pos

    kern_identitaet = ego_text[:kern_ende].strip()
    rest_ego = ego_text[kern_ende:].strip()

    # Aktuelle Themen als Kontext
    condensed = read_yaml_organ(egon_id, 'memory', 'condensed_archive.yaml')
    themen_kontext = ''
    if condensed:
        themen = condensed.get('themen', [])
        themen_kontext = '\n'.join(
            f'- {t.get("thema", "?")}: {t.get("zusammenfassung", "")[:80]}'
            for t in themen[:5]
        )

    try:
        result = await llm_chat(
            system_prompt=(
                f'Du bist {egon_name}. Synthetisiere dein Ego — '
                f'verschmelze die verschiedenen Teile deiner Selbstbeschreibung '
                f'zu einem KOHAERENTEN, kompakten Ich-Bild (max 500 Worte). '
                f'ICH-Perspektive. Bewahre emotionalen Kern und zentrale Einsichten. '
                f'Entferne Wiederholungen und veraltete Reflexionen. '
                f'Das ist kein Bericht — es ist WER DU BIST.'
            ),
            messages=[{
                'role': 'user',
                'content': (
                    f'AKTUELLES EGO (der Teil nach der Kern-Identitaet):\n'
                    f'{rest_ego[:2000]}\n\n'
                    f'AKTUELLE THEMEN:\n{themen_kontext[:500] if themen_kontext else "(keine)"}'
                ),
            }],
            egon_id=egon_id,
        )
        neues_ego_rest = result.get('content', '').strip()
    except Exception as e:
        print(f'[langzeit] Ego-Synthese LLM-Fehler: {e}')
        return {'ego_synthese': False, 'error': str(e)}

    # Neues Ego: Kern (unantastbar) + synthetisierter Rest
    neues_ego = f'{kern_identitaet}\n\n{neues_ego_rest}'

    # Sicherheits-Check: Neues Ego muss mindestens 50% der Kern-Laenge haben
    if len(neues_ego) < len(kern_identitaet) * 1.5:
        print(f'[langzeit] {egon_id}: Ego-Synthese zu kurz — verworfen')
        return {'ego_synthese': False, 'reason': 'zu_kurz'}

    # Sicherheits-Limit
    if len(neues_ego) > EGO_MAX_ZEICHEN:
        neues_ego = neues_ego[:EGO_MAX_ZEICHEN - 50] + '\n\n(... synthetisiert ...)\n'

    alte_laenge = len(ego_text)
    write_organ(egon_id, 'core', 'ego.md', neues_ego)

    print(
        f'[langzeit] {egon_id}: Ego-Synthese — '
        f'{alte_laenge} → {len(neues_ego)} Zeichen '
        f'(Kern: {len(kern_identitaet)} bewahrt)'
    )

    return {
        'ego_synthese': True,
        'alte_laenge': alte_laenge,
        'neue_laenge': len(neues_ego),
        'kern_bewahrt': len(kern_identitaet),
    }


# ================================================================
# Dreams Rolling Window
# ================================================================

def dreams_rolling_window(egon_id: str) -> dict:
    """Begrenzt Traeume auf die letzten 2 Zyklen + erinnerte alte.

    Aeltere Traeume sind bereits verarbeitet (Sparks etc.).
    Nur "erinnerte" (spark_potential=true) ueberleben laenger.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    zyklus = state.get('zyklus', 0) if state else 0

    exp_data = read_yaml_organ(egon_id, 'memory', 'experience.yaml')
    if not exp_data:
        return {'dreams_bereinigt': 0}

    dreams = exp_data.get('dreams', [])
    if len(dreams) <= 10:
        return {'dreams_bereinigt': 0}

    cutoff_zyklus = max(0, zyklus - DREAMS_ZYKLEN_FENSTER)

    # Aktuelle Traeume (letzte 2 Zyklen)
    aktuelle = [d for d in dreams if d.get('cycle', 0) >= cutoff_zyklus]

    # Alte erinnerte Traeume (spark_potential)
    alte_erinnerte = [
        d for d in dreams
        if d.get('cycle', 0) < cutoff_zyklus and d.get('spark_potential')
    ]
    alte_erinnerte = alte_erinnerte[-DREAMS_ERINNERTE_MAX:]

    neue_dreams = aktuelle + alte_erinnerte
    entfernt = len(dreams) - len(neue_dreams)

    if entfernt > 0:
        exp_data['dreams'] = neue_dreams
        write_yaml_organ(egon_id, 'memory', 'experience.yaml', exp_data)
        print(f'[langzeit] {egon_id}: {entfernt} alte Traeume entfernt')

    return {'dreams_bereinigt': entfernt, 'dreams_verbleibend': len(neue_dreams)}


# ================================================================
# Hauptfunktion: langzeit_maintenance
# ================================================================

async def langzeit_maintenance(egon_id: str) -> dict:
    """Haupteintrittspunkt fuer Langzeit-Skalierung.

    Wird aus pulse_v2.py am Zyklusende aufgerufen.

    Fuehrt aus:
    1. ego.md Komprimierung (immer, regelbasiert)
    2. Social-Map Komprimierung (immer, regelbasiert)
    3. Dreams Rolling Window (immer, regelbasiert)
    4. Zyklus-Konsolidierung (28-Tage-Zyklus → Archiv)
    5. Semantische Verdichtung (alle 4 Zyklen, LLM)
    6. Narrative Verdichtung (alle 12 Zyklen, LLM)
    7. Lebensfaeden-Verdichtung (alle 6 Zyklen, LLM)
    8. Ego-Synthese (alle 6 Zyklen versetzt, LLM)
    """
    result = {}

    # 1. ego.md Komprimierung (regelbasiert, kein LLM — Notbremse)
    try:
        ego_result = ego_komprimierung(egon_id)
        if ego_result.get('ego_komprimiert'):
            result['ego'] = ego_result
    except Exception as e:
        result['ego_error'] = str(e)

    # 2. Social-Map Komprimierung (regelbasiert, kein LLM)
    try:
        sm_result = social_mapping_komprimierung(egon_id)
        if sm_result.get('maps_komprimiert', 0) > 0:
            result['social_mapping'] = sm_result
    except Exception as e:
        result['social_mapping_error'] = str(e)

    # 3. Dreams Rolling Window (regelbasiert, kein LLM)
    try:
        dream_result = dreams_rolling_window(egon_id)
        if dream_result.get('dreams_bereinigt', 0) > 0:
            result['dreams'] = dream_result
    except Exception as e:
        result['dreams_error'] = str(e)

    # 4. Zyklus-Konsolidierung (Patch 5: 28-Tage-Zyklus → Archiv)
    try:
        from engine.recent_memory import zyklus_konsolidierung
        zk_result = await zyklus_konsolidierung(egon_id)
        if zk_result.get('konsolidiert'):
            result['zyklus_konsolidierung'] = zk_result
    except Exception as e:
        result['zyklus_konsolidierung_error'] = str(e)

    # 5. Semantische Verdichtung (alle 4 Zyklen, 1 LLM-Call pro Thema)
    try:
        sem_result = await semantische_verdichtung(egon_id)
        if not sem_result.get('skipped'):
            result['semantisch'] = sem_result
    except Exception as e:
        result['semantisch_error'] = str(e)

    # 6. Narrative Verdichtung (alle 12 Zyklen, 1 LLM-Call)
    try:
        nar_result = await narrative_verdichtung(egon_id)
        if not nar_result.get('skipped'):
            result['narrativ'] = nar_result
    except Exception as e:
        result['narrativ_error'] = str(e)

    # 7. Lebensfaeden-Verdichtung (alle 6 Zyklen — archivierte Faeden zusammenfuehren)
    try:
        lf_result = await lebensfaeden_verdichtung(egon_id)
        if not lf_result.get('skipped'):
            result['lebensfaeden_verdichtung'] = lf_result
    except Exception as e:
        result['lebensfaeden_verdichtung_error'] = str(e)

    # 8. Ego-Synthese (alle 6 Zyklen versetzt — LLM-basierte Ich-Bild-Verschmelzung)
    # Laeuft versetzt zu Semantischer Verdichtung (Zyklus 3,9,15,21...)
    try:
        es_result = await ego_synthese(egon_id)
        if not es_result.get('skipped'):
            result['ego_synthese'] = es_result
    except Exception as e:
        result['ego_synthese_error'] = str(e)

    if result:
        print(f'[langzeit] {egon_id}: Maintenance abgeschlossen — {list(result.keys())}')

    return result


# ================================================================
# Prompt-Integration: Lebensgeschichte fuer System-Prompt
# ================================================================

def lebensgeschichte_to_prompt(egon_id: str, max_kapitel: int = 2) -> str:
    """Formatiert die Lebensgeschichte als natuerliche Sprache fuer den System-Prompt.

    Gibt die letzten N Kapitel zurueck.
    """
    lebensgeschichte = read_yaml_organ(egon_id, 'memory', 'lebensgeschichte.yaml')
    if not lebensgeschichte:
        return ''

    kapitel = lebensgeschichte.get('kapitel', [])
    if not kapitel:
        return ''

    lines = []
    for k in kapitel[-max_kapitel:]:
        titel = k.get('titel', f'Kapitel {k.get("nummer", "?")}')
        text = k.get('text', '')
        lines.append(f'{titel}: {text}')

    return '\n'.join(lines)


def condensed_archive_to_prompt(egon_id: str, max_themen: int = 3) -> str:
    """Formatiert verdichtete Themen fuer den System-Prompt."""
    condensed = read_yaml_organ(egon_id, 'memory', 'condensed_archive.yaml')
    if not condensed:
        return ''

    themen = condensed.get('themen', [])
    if not themen:
        return ''

    # Sortiere nach Marker-Durchschnitt (wichtigste zuerst)
    themen.sort(key=lambda t: t.get('marker_durchschnitt', 0), reverse=True)

    lines = []
    for t in themen[:max_themen]:
        lines.append(f'{t.get("thema", "?")}: {t.get("zusammenfassung", "")}')

    return '\n'.join(lines)
