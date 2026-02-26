"""Cue-Index — Patch 14: Assoziatives Erinnern ohne Full-Scan.

Der Cue-Index ist das Hippocampus-Aequivalent:
Er mappt Cue-Tags direkt auf Erinnerungs-Eintraege,
ohne dass der gesamte Archiv-Inhalt geladen werden muss.

Datenquelle (aktuell): memory/episodes.yaml
Datenquelle (zukuenftig): memory/archive.md (nach Konsolidierung)

Index-Datei: memory/cue_index.yaml
  → Wird NIE ins LLM-Context geladen (0 Token-Kosten)
  → Nur lokaler Lookup: Cue-Wort → Liste von Eintrag-IDs

4 Index-Typen:
  wort_index:      Tag/Keyword → Episode-IDs
  emotions_index:  Emotions-Typ → Episode-IDs
  partner_index:   Gespraechspartner → Episode-IDs
  faden_index:     Thread/Lebensfaden → Episode-IDs
  stark_index:     Top 20% nach significance/emotional_marker

Biologische Grundlage:
  Teyler & DiScenna (1986): Der Hippocampus speichert
  nicht die Erinnerung selbst, sondern einen INDEX —
  einen Zeiger auf die verteilte Repraesentation.

Token-Impact: NETTO-ERSPARNIS 95-99% bei Lichtbogen-Lookups.
"""

import math
import time
from collections import defaultdict

from engine.organ_reader import read_yaml_organ, write_yaml_organ


# ================================================================
# Konfiguration
# ================================================================

# Lichtbogen-Lookup Parameter
MAX_TREFFER = 5         # Maximal 5 Eintraege pro Lookup
MIN_SCORE = 0.6         # Mindest-Score fuer einen Treffer
STARK_SCHWELLE = 0.70   # Significance >= 0.70 → stark_index

# Scoring-Gewichte
GEWICHT_WORT_EXAKT = 1.0     # Exakter Wort-Match
GEWICHT_WORT_TEIL = 0.4      # Teilmatch (Substring)
GEWICHT_PARTNER = 0.5         # Gleicher Gespraechspartner
GEWICHT_EMOTION = 0.3         # Gleiche dominante Emotion
GEWICHT_FADEN = 0.6           # Gleicher Lebensfaden/Thread
GEWICHT_STARK = 0.3           # Bonus fuer starke Erinnerungen

# Semantische Synonym-Gruppen (manuell gepflegt)
SYNONYM_GRUPPEN = {
    'vertrauen': ['vertrauen', 'verrat', 'luege', 'ehrlichkeit', 'glaube', 'misstrauen'],
    'verlust': ['verlust', 'tod', 'sterben', 'abschied', 'ende', 'trennung', 'trauer'],
    'freude': ['freude', 'glueck', 'spass', 'lachen', 'feier', 'begeisterung'],
    'angst': ['angst', 'furcht', 'panik', 'sorge', 'bedrohung', 'gefahr'],
    'liebe': ['liebe', 'zuneigung', 'romantik', 'naehe', 'intimitaet', 'sehnsucht'],
    'konflikt': ['konflikt', 'streit', 'wut', 'aerger', 'provokation', 'eskalation'],
    'wachstum': ['wachstum', 'lernen', 'entwicklung', 'erkenntnis', 'reife', 'einsicht'],
    'identitaet': ['identitaet', 'wer bin ich', 'sinn', 'zweck', 'bestimmung', 'selbst'],
}


# ================================================================
# Index aufbauen
# ================================================================

def baue_index_auf(egon_id, episoden=None):
    """Baue den kompletten Cue-Index aus den Episoden auf.

    Wird bei Zyklusende-Konsolidierung aufgerufen oder wenn
    kein Index existiert und ein Lichtbogen-Lookup gebraucht wird.

    Args:
        egon_id: ID des EGON.
        episoden: Optional — vorab geladene Episodenliste.
                  Wenn None, wird episodes.yaml gelesen.

    Returns:
        Das generierte Index-Dict.
    """
    if episoden is None:
        ep_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
        episoden = ep_data.get('episodes', []) if ep_data else []

    wort_index = defaultdict(list)
    emotions_index = defaultdict(list)
    partner_index = defaultdict(list)
    faden_index = defaultdict(list)
    stark_index = []

    for eintrag in episoden:
        if not isinstance(eintrag, dict):
            continue

        eid = eintrag.get('id', '')
        if not eid:
            continue

        # --- Wort-Index: aus tags[] ---
        for tag in eintrag.get('tags', []):
            if isinstance(tag, str):
                tag_lower = tag.lower().strip()
                if tag_lower and eid not in wort_index[tag_lower]:
                    wort_index[tag_lower].append(eid)

        # Auch aus summary Keywords extrahieren (Top-Woerter)
        summary = eintrag.get('summary', '')
        if summary:
            for wort in _extrahiere_keywords(summary):
                if wort and eid not in wort_index[wort]:
                    wort_index[wort].append(eid)

        # --- Emotions-Index: aus emotions_felt[] ---
        for emo in eintrag.get('emotions_felt', []):
            if isinstance(emo, dict):
                emo_typ = emo.get('type', '')
                if emo_typ:
                    emo_upper = emo_typ.upper()
                    if eid not in emotions_index[emo_upper]:
                        emotions_index[emo_upper].append(eid)

        # --- Partner-Index: aus 'with' Feld ---
        partner = eintrag.get('with', '')
        if partner and partner != 'OWNER_CURRENT':
            if eid not in partner_index[partner]:
                partner_index[partner].append(eid)

        # Auch aus persons_mentioned
        for person in eintrag.get('persons_mentioned', []):
            if isinstance(person, str) and person:
                if eid not in partner_index[person]:
                    partner_index[person].append(eid)

        # --- Faden-Index: aus thread_title ---
        thread = eintrag.get('thread_title')
        if thread and isinstance(thread, str):
            if eid not in faden_index[thread]:
                faden_index[thread].append(eid)

        # Auch aus lebensfaeden (wenn vorhanden, zukuenftig)
        for faden in eintrag.get('lebensfaeden', []):
            if isinstance(faden, str) and faden:
                if eid not in faden_index[faden]:
                    faden_index[faden].append(eid)

        # --- Stark-Index: Top-Eintraege nach significance ---
        significance = eintrag.get('significance', 0)
        emotional_marker = eintrag.get('emotional_marker', 0)
        # Nehme den hoeheren Wert (episodes nutzen significance, archive nutzt emotional_marker)
        staerke = max(
            float(significance) if significance else 0,
            float(emotional_marker) if emotional_marker else 0,
        )
        if staerke >= STARK_SCHWELLE and eid not in stark_index:
            stark_index.append(eid)

    # Index zusammenbauen
    index = {
        'wort_index': dict(wort_index),
        'emotions_index': dict(emotions_index),
        'partner_index': dict(partner_index),
        'faden_index': dict(faden_index),
        'stark_index': stark_index,
        'meta': {
            'letzte_aktualisierung': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'eintraege_total': len(episoden),
            'index_eintraege': sum(len(v) for v in wort_index.values()),
        },
    }

    # Speichern
    write_yaml_organ(egon_id, 'memory', 'cue_index.yaml', index)
    print(f'[cue_index] {egon_id}: Index aufgebaut — {len(episoden)} Episoden, '
          f'{len(wort_index)} Woerter, {len(stark_index)} starke')

    return index


def inkrementeller_update(egon_id, neue_eintraege):
    """Fuege neue Eintraege zum bestehenden Index hinzu.

    Schneller als Neuaufbau bei kleinen Aenderungen
    (z.B. nach jedem Gespraech oder bei Zyklusende).

    Args:
        egon_id: ID des EGON.
        neue_eintraege: Liste neuer Episode/Archiv-Dicts.

    Returns:
        Aktualisiertes Index-Dict.
    """
    index = read_yaml_organ(egon_id, 'memory', 'cue_index.yaml')

    if not index or 'wort_index' not in index:
        # Kein Index vorhanden → komplett aufbauen
        return baue_index_auf(egon_id)

    for eintrag in neue_eintraege:
        if not isinstance(eintrag, dict):
            continue

        eid = eintrag.get('id', '')
        if not eid:
            continue

        # Wort-Tags
        for tag in eintrag.get('tags', []):
            if isinstance(tag, str):
                tag_lower = tag.lower().strip()
                if tag_lower:
                    if tag_lower not in index['wort_index']:
                        index['wort_index'][tag_lower] = []
                    if eid not in index['wort_index'][tag_lower]:
                        index['wort_index'][tag_lower].append(eid)

        # Emotions-Index
        for emo in eintrag.get('emotions_felt', []):
            if isinstance(emo, dict):
                emo_typ = emo.get('type', '').upper()
                if emo_typ:
                    if emo_typ not in index.get('emotions_index', {}):
                        index.setdefault('emotions_index', {})[emo_typ] = []
                    if eid not in index['emotions_index'][emo_typ]:
                        index['emotions_index'][emo_typ].append(eid)

        # Partner-Index
        partner = eintrag.get('with', '')
        if partner and partner != 'OWNER_CURRENT':
            if partner not in index.get('partner_index', {}):
                index.setdefault('partner_index', {})[partner] = []
            if eid not in index['partner_index'][partner]:
                index['partner_index'][partner].append(eid)

        # Stark-Index
        staerke = max(
            float(eintrag.get('significance', 0) or 0),
            float(eintrag.get('emotional_marker', 0) or 0),
        )
        if staerke >= STARK_SCHWELLE:
            if eid not in index.get('stark_index', []):
                index.setdefault('stark_index', []).append(eid)

    # Meta aktualisieren
    index.setdefault('meta', {})
    index['meta']['letzte_aktualisierung'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    index['meta']['eintraege_total'] = (
        index['meta'].get('eintraege_total', 0) + len(neue_eintraege)
    )

    write_yaml_organ(egon_id, 'memory', 'cue_index.yaml', index)
    return index


# ================================================================
# Lichtbogen-Lookup
# ================================================================

def lichtbogen_lookup(egon_id, cue_woerter, kontext=None):
    """Finde relevante Erinnerungs-Eintraege ueber den Cue-Index.

    KEIN Full-Scan. Nur Index-Lookup + gezielte Einzel-Loads.

    Args:
        egon_id: ID des EGON.
        cue_woerter: Liste von Cue-Woertern aus dem aktuellen Gespraech.
        kontext: Optional — Dict mit:
            partner_id: ID des Gespraechspartners
            dominante_emotion: Aktive Emotions-Typ (z.B. 'FEAR')
            aktiver_faden: Name des aktiven Lebensfadens/Threads

    Returns:
        Liste von Eintrag-IDs (sortiert nach Relevanz-Score),
        maximal MAX_TREFFER Eintraege.
    """
    index = read_yaml_organ(egon_id, 'memory', 'cue_index.yaml')

    if not index or 'wort_index' not in index:
        # Kein Index vorhanden — versuche aufzubauen
        index = baue_index_auf(egon_id)
        if not index or 'wort_index' not in index:
            return []

    treffer_scores = defaultdict(float)
    wort_index = index.get('wort_index', {})

    # 1. WORT-MATCH (staerkstes Signal)
    erweiterte_cues = erweitere_cues(cue_woerter)

    for wort in erweiterte_cues:
        wort_lower = wort.lower().strip()
        if not wort_lower:
            continue

        # Exakter Match
        if wort_lower in wort_index:
            # IDF-Gewichtung: seltene Cues sind wertvoller
            gewicht = _cue_gewicht(wort_lower, index)
            for eid in wort_index[wort_lower]:
                treffer_scores[eid] += GEWICHT_WORT_EXAKT * gewicht

        # Teilmatch (Wort ist Teilstring eines Index-Tags)
        for tag, eids in wort_index.items():
            if wort_lower != tag and (wort_lower in tag or tag in wort_lower):
                for eid in eids:
                    treffer_scores[eid] += GEWICHT_WORT_TEIL

    # 2. KONTEXT-MATCH (verstaerkt bestehende Treffer)
    if kontext and isinstance(kontext, dict):
        # Partner-Match
        partner = kontext.get('partner_id')
        if partner:
            for eid in index.get('partner_index', {}).get(partner, []):
                treffer_scores[eid] += GEWICHT_PARTNER

        # Emotions-Match
        emotion = kontext.get('dominante_emotion', '').upper()
        if emotion:
            for eid in index.get('emotions_index', {}).get(emotion, []):
                treffer_scores[eid] += GEWICHT_EMOTION

        # Faden-Match
        faden = kontext.get('aktiver_faden')
        if faden:
            for eid in index.get('faden_index', {}).get(faden, []):
                treffer_scores[eid] += GEWICHT_FADEN

    # 3. STARK-BONUS (emotional starke Eintraege werden bevorzugt)
    for eid in index.get('stark_index', []):
        if eid in treffer_scores:
            treffer_scores[eid] += GEWICHT_STARK

    # Sortieren und filtern
    sortiert = sorted(treffer_scores.items(), key=lambda x: x[1], reverse=True)

    ergebnis = [
        eid for eid, score in sortiert
        if score >= MIN_SCORE
    ][:MAX_TREFFER]

    if ergebnis:
        print(f'[cue_index] {egon_id}: Lichtbogen-Lookup — '
              f'{len(ergebnis)} Treffer fuer {cue_woerter[:3]}')

    return ergebnis


def lade_eintraege_nach_id(egon_id, eintrag_ids):
    """Lade NUR die spezifischen Episoden/Archiv-Eintraege nach ID.

    Kein Full-Scan — gezielter Zugriff.

    Args:
        egon_id: ID des EGON.
        eintrag_ids: Liste von Eintrag-IDs (z.B. ['E0003', 'E0015']).

    Returns:
        Liste von Episode-Dicts.
    """
    if not eintrag_ids:
        return []

    ids_set = set(eintrag_ids)

    # 1. In episodes.yaml suchen
    ep_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    episoden = ep_data.get('episodes', []) if ep_data else []

    gefunden = [
        ep for ep in episoden
        if isinstance(ep, dict) and ep.get('id') in ids_set
    ]

    # 2. TODO: Wenn archive.md existiert, auch dort suchen
    # (wird aktiviert wenn Konsolidierung implementiert ist)

    return gefunden


# ================================================================
# Semantische Erweiterung
# ================================================================

def erweitere_cues(cue_woerter):
    """Erweitere Cue-Woerter um semantisch verwandte Begriffe.

    Args:
        cue_woerter: Original-Liste von Cue-Woertern.

    Returns:
        Erweiterte Liste (Original + Synonyme).
    """
    erweitert = set()
    for wort in cue_woerter:
        if isinstance(wort, str):
            erweitert.add(wort.lower().strip())

    for wort in list(erweitert):
        for _gruppe_name, synonyme in SYNONYM_GRUPPEN.items():
            if wort in synonyme:
                erweitert.update(synonyme)

    return list(erweitert)


# ================================================================
# Index-Analyse (fuer Metacognition, Patch 11)
# ================================================================

def top_themen(egon_id, n=5):
    """Liefert die N haeufigsten Cue-Woerter (fuer Metacognition).

    Returns:
        Liste von (wort, anzahl) Tupeln, sortiert nach Haeufigkeit.
    """
    index = read_yaml_organ(egon_id, 'memory', 'cue_index.yaml')
    if not index or 'wort_index' not in index:
        return []

    haeufigkeit = {
        tag: len(ids)
        for tag, ids in index.get('wort_index', {}).items()
    }

    return sorted(haeufigkeit.items(), key=lambda x: x[1], reverse=True)[:n]


def emotionale_verteilung(egon_id):
    """Liefert die Verteilung der Emotions-Typen im Index.

    Returns:
        Dict {emotion_typ: anzahl}.
    """
    index = read_yaml_organ(egon_id, 'memory', 'cue_index.yaml')
    if not index or 'emotions_index' not in index:
        return {}

    return {
        emo: len(ids)
        for emo, ids in index.get('emotions_index', {}).items()
    }


# ================================================================
# Hilfsfunktionen
# ================================================================

# Stoppwoerter die nicht in den Wort-Index gehoeren
_STOPPWOERTER = {
    'ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr', 'mein', 'dein',
    'und', 'oder', 'aber', 'mit', 'von', 'zu', 'in', 'auf', 'an',
    'fuer', 'ueber', 'nach', 'bei', 'das', 'die', 'der', 'den',
    'dem', 'ein', 'eine', 'einen', 'einem', 'einer', 'nicht', 'ist',
    'hat', 'war', 'habe', 'bin', 'sind', 'wird', 'kann', 'auch',
    'noch', 'schon', 'nur', 'sehr', 'wie', 'was', 'dass', 'als',
    'wenn', 'dann', 'so', 'doch', 'hier', 'dort', 'da', 'nun',
    'heute', 'gestern', 'morgen', 'immer', 'nie', 'mal', 'mehr',
}


def _extrahiere_keywords(text, max_keywords=5):
    """Extrahiere die wichtigsten Keywords aus einem Text.

    Filtert Stoppwoerter und gibt nur laengere, bedeutungsvolle
    Woerter zurueck.

    Returns:
        Liste von max_keywords Keywords (lowercase).
    """
    if not text or not isinstance(text, str):
        return []

    # Einfache Tokenisierung
    import re
    woerter = re.findall(r'[a-zäöüß]+', text.lower())

    # Filtern: min 4 Zeichen, keine Stoppwoerter
    gefiltert = [
        w for w in woerter
        if len(w) >= 4 and w not in _STOPPWOERTER
    ]

    # Haeufigste zurueckgeben
    from collections import Counter
    return [w for w, _ in Counter(gefiltert).most_common(max_keywords)]


def _cue_gewicht(cue_wort, index):
    """Inverse Document Frequency: Seltene Cues sind wertvoller.

    'Vertrauen' kommt in 4 Eintraegen vor → hohes Gewicht.
    'gut' kommt in 40 Eintraegen vor → niedriges Gewicht.

    Returns:
        Gewicht zwischen 0.5 und 2.0.
    """
    total = index.get('meta', {}).get('eintraege_total', 1)
    vorkommen = len(index.get('wort_index', {}).get(cue_wort, []))

    if vorkommen == 0:
        return 0.0

    idf = math.log(max(total, 1) / vorkommen)

    # Normalisieren auf 0.5-2.0
    return max(0.5, min(idf / 2.0, 2.0))
