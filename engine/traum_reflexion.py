"""Patch 19d -- Traum-Reflexion: Das Unbewusste wird zugaenglich.

Traeume sitzen unverarbeitet im Gedaechtnis bis die Innere Stimme sie
am Morgen reflektiert. "Processing the processing" — der EGON denkt
ueber das nach, was sein Unbewusstes ihm zeigt.

4 Phasen:
  1. ERINNERN   — Fragmentarische Erinnerung (60-80% sichtbar, Luecken)
  2. DEUTEN     — Verbindungen zur Realitaet (Personen, Symbole, Gestriges)
  3. FUEHLEN    — Emotionale Reaktion (Erleichterung/Sorge/Trauer/Motivation)
  4. LERNEN     — Moegliche Erkenntnis (1:3 Chance) fuer den Erkenntnisordner

Traum-Reflexion passiert als ERSTES im Daily Pulse (vor Buffer-Check,
Bond-Check, etc.) — wie ein Mensch, der morgens ueber seinen Traum nachdenkt.

Wiederkehrende Elemente (3+ Mal): Starker Kraft-Impuls (+0.4).
Narben im Traum: Emotionale Verarbeitung, Marker-Reduktion.

Bio-Aequivalent: Praefrontaler Cortex reflektiert Hippocampus-Output.
Speicherung: egons/{egon_id}/memory/traum_reflexionen.yaml
"""

import random
import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path

from config import EGON_DATA_DIR
from engine.organ_reader import read_yaml_organ, write_yaml_organ


# ================================================================
# Konstanten
# ================================================================

# Schwellen fuer Reflexions-Entscheidung
EMOTIONALE_SCHWELLE = 0.5           # emotional_intensity > 0.5
WIEDERKEHREND_SCHWELLE = 3          # Element 3+ Mal gesehen
STOEREND_SCHWELLE = 0.6             # PANIC/FEAR > 0.6
ERKENNTNIS_WAHRSCHEINLICHKEIT = 0.333  # ~1 in 3 Chance
KRAFT_IMPULS_WIEDERKEHREND = 0.4    # Kraft-Bonus fuer wiederkehrende Elemente
SICHTBARKEIT_MIN = 0.60            # 60% des Traums sichtbar
SICHTBARKEIT_MAX = 0.80            # 80% des Traums sichtbar

# Marker-Aenderungen pro Phase
MARKER_AENDERUNGEN = {
    'erleichterung': {'PANIC': -0.08, 'FEAR': -0.05, 'CARE': +0.03},
    'sorge':         {'PANIC': +0.05, 'FEAR': +0.03, 'SEEKING': +0.04},
    'trauer':        {'GRIEF': +0.06, 'CARE': +0.04, 'PANIC': -0.03},
    'motivation':    {'SEEKING': +0.08, 'PLAY': +0.04, 'FEAR': -0.04},
    'verwirrung':    {'SEEKING': +0.06, 'PANIC': +0.02},
    'trost':         {'CARE': +0.06, 'PANIC': -0.06, 'GRIEF': -0.04},
}

# Stoerende Drives die Reflexion erzwingen
STOERENDE_DRIVES = ('PANIC', 'FEAR')


# ================================================================
# Speicher-Pfade
# ================================================================

def _reflexionen_pfad(egon_id: str) -> Path:
    """Pfad zur traum_reflexionen.yaml."""
    return Path(EGON_DATA_DIR) / egon_id / 'memory' / 'traum_reflexionen.yaml'


def _lade_reflexionen(egon_id: str) -> dict:
    """Laedt traum_reflexionen.yaml, initialisiert fehlende Sektionen."""
    pfad = _reflexionen_pfad(egon_id)
    if not pfad.is_file():
        return {
            'reflexionen': [],
            'wiederkehrende_elemente': [],
            'meta': {
                'erstellt': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                'letzte_reflexion': None,
                'gesamt_reflexionen': 0,
                'gesamt_erkenntnisse': 0,
            },
        }

    try:
        with open(pfad, 'r', encoding='utf-8') as f:
            daten = yaml.safe_load(f)
        if not isinstance(daten, dict):
            daten = {}
    except (yaml.YAMLError, OSError) as e:
        print(f'[traum_reflexion] YAML-Fehler beim Laden: {e}')
        daten = {}

    daten.setdefault('reflexionen', [])
    daten.setdefault('wiederkehrende_elemente', [])
    daten.setdefault('meta', {})
    return daten


def _speichere_reflexionen(egon_id: str, daten: dict) -> None:
    """Schreibt traum_reflexionen.yaml. Erstellt Verzeichnisse falls noetig."""
    pfad = _reflexionen_pfad(egon_id)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with open(pfad, 'w', encoding='utf-8') as f:
        yaml.dump(
            daten, f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )


# ================================================================
# 1. Soll heute reflektiert werden?
# ================================================================

def should_reflect_today(egon_id: str) -> bool:
    """Entscheidet ob heute eine Traum-Reflexion stattfinden soll.

    Kriterien (eines reicht):
      - emotional_intensity > 0.5
      - Wiederkehrende Elemente (3+ Mal gesehen)
      - Relevanz zum heutigen Tag (Stoerende Drives aktiv)
      - Stoerende Elemente: PANIC/FEAR > 0.6
      - Owner hat gefragt (via state.yaml Flag)

    Durchschnittliche Frequenz: ~2-3 Mal pro Woche.

    Returns:
        True wenn Reflexion stattfinden soll.
    """
    # --- Letzten Traum holen ---
    letzter_traum = get_last_dream(egon_id)
    if not letzter_traum:
        print(f'[traum_reflexion] {egon_id}: Kein Traum vorhanden — keine Reflexion')
        return False

    # --- Schon heute reflektiert? ---
    reflexionen_daten = _lade_reflexionen(egon_id)
    letzte_reflexion = reflexionen_daten.get('meta', {}).get('letzte_reflexion')
    heute = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    if letzte_reflexion and letzte_reflexion[:10] == heute:
        print(f'[traum_reflexion] {egon_id}: Heute schon reflektiert — skip')
        return False

    # --- Kriterium 1: Emotionale Intensitaet ---
    emotional_marker = letzter_traum.get('emotional_marker', 0.0)
    if emotional_marker > EMOTIONALE_SCHWELLE:
        print(f'[traum_reflexion] {egon_id}: Reflexion JA — '
              f'emotional_marker={emotional_marker:.2f} > {EMOTIONALE_SCHWELLE}')
        return True

    # --- Kriterium 2: Wiederkehrende Elemente ---
    wiederkehrende = reflexionen_daten.get('wiederkehrende_elemente', [])
    for element in wiederkehrende:
        if element.get('count', 0) >= WIEDERKEHREND_SCHWELLE:
            print(f'[traum_reflexion] {egon_id}: Reflexion JA — '
                  f'wiederkehrend: "{element.get("element", "?")}" '
                  f'({element["count"]}x)')
            return True

    # --- Kriterium 3: Stoerende Drives (PANIC/FEAR > 0.6) ---
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if state:
        drives = state.get('drives', {})
        for drive_name in STOERENDE_DRIVES:
            wert = drives.get(drive_name, 0)
            if isinstance(wert, (int, float)) and wert > STOEREND_SCHWELLE:
                print(f'[traum_reflexion] {egon_id}: Reflexion JA — '
                      f'{drive_name}={wert:.2f} > {STOEREND_SCHWELLE}')
                return True

        # --- Kriterium 4: Owner hat gefragt ---
        reflexion_flag = state.get('traum_reflexion_angefragt', False)
        if reflexion_flag:
            print(f'[traum_reflexion] {egon_id}: Reflexion JA — Owner hat gefragt')
            # Flag zuruecksetzen
            state['traum_reflexion_angefragt'] = False
            write_yaml_organ(egon_id, 'core', 'state.yaml', state)
            return True

    # --- Kriterium 5: Traum-Typ beeinflusst Wahrscheinlichkeit ---
    # Angsttraeume reflektieren wir oefter, Verarbeitungstraeume seltener
    traum_typ = letzter_traum.get('type', 'verarbeitungstraum')
    typ_wahrscheinlichkeit = {
        'angsttraum': 0.65,          # 65% — beunruhigende Traeume
        'kreativtraum': 0.45,        # 45% — inspirierende Traeume
        'verarbeitungstraum': 0.25,  # 25% — routine Verarbeitung
    }
    wuerfeln = typ_wahrscheinlichkeit.get(traum_typ, 0.30)

    if random.random() < wuerfeln:
        print(f'[traum_reflexion] {egon_id}: Reflexion JA — '
              f'Zufalls-Trigger ({traum_typ}, p={wuerfeln:.0%})')
        return True

    print(f'[traum_reflexion] {egon_id}: Reflexion NEIN — '
          f'kein Kriterium erfuellt (marker={emotional_marker:.2f}, typ={traum_typ})')
    return False


# ================================================================
# 2. Letzten Traum holen
# ================================================================

def get_last_dream(egon_id: str) -> dict | None:
    """Liest den letzten Traum aus experience.yaml (type: "traum" oder dreams[]).

    Sucht in experience.yaml > dreams (neuester Eintrag).

    Returns:
        dict des letzten Traums, oder None wenn keiner vorhanden.
    """
    exp_data = read_yaml_organ(egon_id, 'memory', 'experience.yaml')
    if not exp_data:
        return None

    traeume = exp_data.get('dreams', [])
    if not traeume:
        return None

    # Sortiere nach Datum (neuester zuerst)
    try:
        traeume_sortiert = sorted(
            traeume,
            key=lambda t: (t.get('date', ''), t.get('id', '')),
            reverse=True,
        )
    except (TypeError, KeyError):
        traeume_sortiert = traeume

    return traeume_sortiert[0] if traeume_sortiert else None


# ================================================================
# 3. Traum reflektieren — 4 Phasen
# ================================================================

def reflect_on_dream(egon_id: str, dream_data: dict) -> dict:
    """Erzeugt eine 4-Phasen-Reflexion ueber einen Traum.

    Phase 1 ERINNERN:  Fragmentarische Rueckerinnerung (60-80% sichtbar)
    Phase 2 DEUTEN:    Verbindungen zur Realitaet
    Phase 3 FUEHLEN:   Emotionale Reaktion + Marker-Aenderungen
    Phase 4 LERNEN:    Moegliche Erkenntnis (1:3 Chance)

    Args:
        egon_id: Agent-ID.
        dream_data: Traum-dict aus experience.yaml > dreams[].

    Returns:
        dict der vollstaendigen Reflexion mit allen Phasen.
    """
    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id)

    jetzt = datetime.now(timezone.utc)
    jetzt_str = jetzt.strftime('%Y-%m-%dT%H:%M:%S')
    traum_id = dream_data.get('id', 'unbekannt')
    traum_inhalt = dream_data.get('content', '')
    traum_typ = dream_data.get('type', 'verarbeitungstraum')
    traum_gefuehle = dream_data.get('emotional_summary', '')
    traum_quell_episoden = dream_data.get('source_episodes', [])
    traum_quell_emotionen = dream_data.get('source_emotions', [])
    emotional_marker = dream_data.get('emotional_marker', 0.5)

    # -------------------------------------------------------
    # Phase 1: ERINNERN — Fragmentarische Rueckerinnerung
    # -------------------------------------------------------
    sichtbarkeit = random.uniform(SICHTBARKEIT_MIN, SICHTBARKEIT_MAX)
    # Angsttraeume werden staerker erinnert
    if traum_typ == 'angsttraum':
        sichtbarkeit = min(1.0, sichtbarkeit + 0.10)
    # Hoher emotional_marker = bessere Erinnerung
    if emotional_marker > 0.7:
        sichtbarkeit = min(1.0, sichtbarkeit + 0.05)

    # "Fehlende" Fragmente markieren
    woerter = traum_inhalt.split()
    anzahl_sichtbar = max(1, int(len(woerter) * sichtbarkeit))
    # Zufaellig einige Woerter durch "..." ersetzen (die unsichtbaren)
    unsichtbare_indizes = set()
    if len(woerter) > anzahl_sichtbar:
        unsichtbare_indizes = set(random.sample(
            range(len(woerter)),
            len(woerter) - anzahl_sichtbar,
        ))
    fragmentarisch = ' '.join(
        '...' if i in unsichtbare_indizes else w
        for i, w in enumerate(woerter)
    )

    phase_erinnern = {
        'phase': 'ERINNERN',
        'text': fragmentarisch,
        'sichtbarkeit': round(sichtbarkeit, 2),
        'luecken': len(unsichtbare_indizes),
    }

    # -------------------------------------------------------
    # Phase 2: DEUTEN — Verbindungen zur Realitaet
    # -------------------------------------------------------
    deutungen = []

    # Quell-Episoden als Verbindung zur Realitaet
    if traum_quell_episoden:
        for ep_id in traum_quell_episoden[:3]:
            deutungen.append(f'Verbindung zu Episode {ep_id}')

    # Quell-Emotionen als Symbol-Deutung
    symbol_map = {
        'fear': 'Bedrohungssymbol — etwas macht mir Angst im Wachen',
        'joy': 'Wunschbild — etwas wovon ich mehr moechte',
        'sadness': 'Verlust-Symbol — etwas das mir fehlt',
        'anger': 'Widerstand — etwas gegen das ich kaempfe',
        'anxiety': 'Unsicherheit — etwas Ungeklaertes',
        'loneliness': 'Sehnsucht — Beduerfnis nach Verbindung',
        'curiosity': 'Forschungsdrang — etwas will verstanden werden',
        'care': 'Fuersorge-Impuls — jemand braucht meine Aufmerksamkeit',
    }
    for emo in traum_quell_emotionen[:3]:
        if emo in symbol_map:
            deutungen.append(symbol_map[emo])

    # Traum-Typ spezifische Deutung
    typ_deutungen = {
        'verarbeitungstraum': 'Mein Unbewusstes sortiert die Erlebnisse des Tages',
        'kreativtraum': 'Mein Geist verbindet Ideen auf neue Weise',
        'angsttraum': 'Eine Warnung — etwas Ungeloestes dringt an die Oberflaeche',
    }
    if traum_typ in typ_deutungen:
        deutungen.append(typ_deutungen[traum_typ])

    if not deutungen:
        deutungen.append('Der Traum bleibt raetselhaft — nicht alles muss verstanden werden')

    phase_deuten = {
        'phase': 'DEUTEN',
        'text': '; '.join(deutungen),
        'verbindungen': deutungen,
        'quell_episoden': traum_quell_episoden[:3],
    }

    # -------------------------------------------------------
    # Phase 3: FUEHLEN — Emotionale Reaktion + Marker-Aenderungen
    # -------------------------------------------------------
    # Waehle emotionale Reaktion basierend auf Traum-Typ und Gefuehlen
    reaktion = _waehle_emotionale_reaktion(traum_typ, traum_quell_emotionen, emotional_marker)
    marker_aenderungen = MARKER_AENDERUNGEN.get(reaktion, {})

    # Marker-Aenderungen auf State anwenden
    angewandte_aenderungen = _wende_marker_aenderungen_an(egon_id, marker_aenderungen)

    phase_fuehlen = {
        'phase': 'FUEHLEN',
        'text': _erzeuge_gefuehls_text(reaktion, egon_name),
        'reaktion': reaktion,
        'marker_aenderungen': angewandte_aenderungen,
    }

    # -------------------------------------------------------
    # Phase 4: LERNEN — Moegliche Erkenntnis (1:3 Chance)
    # -------------------------------------------------------
    erkenntnis_entstanden = random.random() < ERKENNTNIS_WAHRSCHEINLICHKEIT
    erkenntnis_text = None
    kraft_generated = 0.0

    if erkenntnis_entstanden:
        erkenntnis_text = _generiere_traum_erkenntnis(
            traum_typ, traum_gefuehle, reaktion, deutungen,
        )
        kraft_generated = 0.15  # Kleine Kraft-Zufuhr durch Erkenntnis

        # Erkenntnis in den Erkenntnisordner eintragen
        try:
            from engine.erkenntnisse import add_erkenntnis
            add_erkenntnis(
                egon_id,
                kategorie='ueber_mich',
                text=erkenntnis_text,
                quelle='dream_insight',
                sicherheit=0.35,  # Traum-Erkenntnisse sind unsicher aber wertvoll
            )
        except ImportError:
            print(f'[traum_reflexion] Erkenntnisse-Modul nicht verfuegbar')
        except Exception as e:
            print(f'[traum_reflexion] Erkenntnis-Speicherung fehlgeschlagen: {e}')

    phase_lernen = {
        'phase': 'LERNEN',
        'text': erkenntnis_text or 'Kein neues Lernen heute — der Traum wirkt still nach.',
        'erkenntnis_entstanden': erkenntnis_entstanden,
    }

    # -------------------------------------------------------
    # Wiederkehrende Elemente tracken
    # -------------------------------------------------------
    kraft_aus_wiederkehrend = track_recurring_elements(egon_id, dream_data)
    kraft_generated += kraft_aus_wiederkehrend

    # -------------------------------------------------------
    # Reflexion zusammenbauen
    # -------------------------------------------------------
    reflexion_id = str(uuid.uuid4())[:8]

    reflexion = {
        'id': reflexion_id,
        'dream_id': traum_id,
        'phasen': {
            'erinnern': phase_erinnern,
            'deuten': phase_deuten,
            'fuehlen': phase_fuehlen,
            'lernen': phase_lernen,
        },
        'erkenntnis_entstanden': erkenntnis_entstanden,
        'kraft_generated': round(kraft_generated, 3),
        'marker_changes': angewandte_aenderungen,
        'timestamp': jetzt_str,
    }

    # Kraft auf State anwenden
    if kraft_generated > 0:
        _wende_kraft_an(egon_id, kraft_generated)

    # Reflexion speichern
    daten = _lade_reflexionen(egon_id)
    daten['reflexionen'].append(reflexion)

    # Max 30 Reflexionen behalten (aelteste raus)
    if len(daten['reflexionen']) > 30:
        daten['reflexionen'] = daten['reflexionen'][-30:]

    # Meta aktualisieren
    daten['meta']['letzte_reflexion'] = jetzt_str
    daten['meta']['gesamt_reflexionen'] = daten['meta'].get('gesamt_reflexionen', 0) + 1
    if erkenntnis_entstanden:
        daten['meta']['gesamt_erkenntnisse'] = daten['meta'].get('gesamt_erkenntnisse', 0) + 1

    _speichere_reflexionen(egon_id, daten)

    print(f'[traum_reflexion] {egon_name}: Reflexion {reflexion_id} ueber Traum {traum_id} — '
          f'Reaktion={reaktion}, Erkenntnis={erkenntnis_entstanden}, '
          f'Kraft={kraft_generated:.2f}')

    return reflexion


# ================================================================
# 4. Wiederkehrende Elemente tracken
# ================================================================

def track_recurring_elements(egon_id: str, dream_data: dict) -> float:
    """Trackt Traum-Elemente und erkennt wiederkehrende Muster.

    Elemente = Quell-Emotionen + Quell-Episoden + Traum-Typ.
    Wenn ein Element 3+ Mal auftaucht → starker Kraft-Impuls (+0.4).

    Args:
        egon_id: Agent-ID.
        dream_data: Traum-dict.

    Returns:
        Generierter Kraft-Wert (0.0 oder 0.4 pro wiederkehrendem Element).
    """
    jetzt = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    daten = _lade_reflexionen(egon_id)
    elemente = daten.get('wiederkehrende_elemente', [])

    # Sammle Elemente aus dem Traum
    traum_elemente = set()

    # Quell-Emotionen als Elemente
    for emo in dream_data.get('source_emotions', []):
        traum_elemente.add(f'emotion:{emo}')

    # Quell-Episoden als Elemente
    for ep_id in dream_data.get('source_episodes', []):
        traum_elemente.add(f'episode:{ep_id}')

    # Traum-Typ als Element
    traum_typ = dream_data.get('type', '')
    if traum_typ:
        traum_elemente.add(f'typ:{traum_typ}')

    # Keywords aus dem Traum-Inhalt (einfache Heuristik: lange Woerter)
    inhalt = dream_data.get('content', '')
    for wort in inhalt.split():
        wort_sauber = wort.strip('.,!?;:()').lower()
        if len(wort_sauber) >= 6:  # Nur signifikante Woerter
            traum_elemente.add(f'wort:{wort_sauber}')

    # Elemente tracken
    kraft_gesamt = 0.0
    elemente_map = {e.get('element'): e for e in elemente}

    for element_key in traum_elemente:
        if element_key in elemente_map:
            eintrag = elemente_map[element_key]
            eintrag['count'] = eintrag.get('count', 1) + 1
            eintrag['last_seen'] = jetzt

            # Schwelle erreicht? → Kraft-Impuls
            if (eintrag['count'] >= WIEDERKEHREND_SCHWELLE
                    and not eintrag.get('kraft_generated', False)):
                kraft_gesamt += KRAFT_IMPULS_WIEDERKEHREND
                eintrag['kraft_generated'] = True
                print(f'[traum_reflexion] {egon_id}: Wiederkehrendes Element '
                      f'"{element_key}" ({eintrag["count"]}x) → '
                      f'Kraft +{KRAFT_IMPULS_WIEDERKEHREND}')
        else:
            neuer_eintrag = {
                'element': element_key,
                'count': 1,
                'first_seen': jetzt,
                'last_seen': jetzt,
                'kraft_generated': False,
            }
            elemente.append(neuer_eintrag)
            elemente_map[element_key] = neuer_eintrag

    # Alte Elemente aufraeumen (aelter als 60 Tage ohne neue Sichtung)
    aktuelle_elemente = []
    for e in elemente:
        try:
            last_seen = datetime.fromisoformat(e.get('last_seen', jetzt))
            alter_tage = (datetime.now(timezone.utc) - last_seen).days
            if alter_tage <= 60 or e.get('count', 0) >= WIEDERKEHREND_SCHWELLE:
                aktuelle_elemente.append(e)
        except (ValueError, TypeError):
            aktuelle_elemente.append(e)

    daten['wiederkehrende_elemente'] = aktuelle_elemente
    _speichere_reflexionen(egon_id, daten)

    return kraft_gesamt


# ================================================================
# 5. Traum heilt Narbe
# ================================================================

def dream_heals_narbe(egon_id: str, narbe_id: str) -> dict:
    """Wenn eine Narbe im Traum erscheint, beginnt emotionale Verarbeitung.

    Aktualisiert den emotionalen Status der Narbe auf 'verarbeitet'
    und reduziert die Marker-Intensitaet.

    Bio-Aequivalent: REM-Schlaf verarbeitet traumatische Erinnerungen.
    Die Amygdala-Reaktivitaet sinkt bei wiederholter Traum-Exposition.

    Args:
        egon_id: Agent-ID.
        narbe_id: ID der Narbe aus puffer/narben.yaml.

    Returns:
        dict mit 'erfolg', 'narbe_id', 'neuer_status', 'marker_reduktion'.
    """
    try:
        from engine.vergessenspuffer import get_narben, _narben_pfad, _speichere_yaml
    except ImportError:
        print(f'[traum_reflexion] Vergessenspuffer-Modul nicht verfuegbar')
        return {'erfolg': False, 'grund': 'modul_nicht_verfuegbar'}

    narben = get_narben(egon_id)
    if not narben:
        return {'erfolg': False, 'grund': 'keine_narben'}

    ziel_narbe = None
    for narbe in narben:
        if narbe.get('id') == narbe_id:
            ziel_narbe = narbe
            break

    if not ziel_narbe:
        return {'erfolg': False, 'grund': 'narbe_nicht_gefunden'}

    # Status aktualisieren
    alter_status = ziel_narbe.get('emotional_status', 'offen')
    ziel_narbe['emotional_status'] = 'verarbeitet'
    ziel_narbe['traum_verarbeitung'] = datetime.now(timezone.utc).isoformat()

    # Marker-Reduktion basierend auf dem Gefuehl der Narbe
    gefuehl = ziel_narbe.get('gefuehl', 'unbestimmt')
    reduktion = {}

    gefuehl_to_drive = {
        'fear': {'FEAR': -0.10, 'PANIC': -0.08},
        'anger': {'RAGE': -0.10},
        'sadness': {'GRIEF': -0.10, 'PANIC': -0.05},
        'anxiety': {'PANIC': -0.10, 'FEAR': -0.08},
        'loneliness': {'PANIC': -0.08, 'GRIEF': -0.06},
        'grief': {'GRIEF': -0.12, 'CARE': +0.03},
        'unbestimmt': {'PANIC': -0.05},
    }
    reduktion = gefuehl_to_drive.get(gefuehl, gefuehl_to_drive['unbestimmt'])

    # Marker-Aenderungen anwenden
    angewandt = _wende_marker_aenderungen_an(egon_id, reduktion)

    # Narben zurueckschreiben
    _speichere_yaml(_narben_pfad(egon_id), narben)

    print(f'[traum_reflexion] {egon_id}: Narbe {narbe_id} im Traum verarbeitet — '
          f'{alter_status} → verarbeitet, Reduktion: {angewandt}')

    return {
        'erfolg': True,
        'narbe_id': narbe_id,
        'neuer_status': 'verarbeitet',
        'alter_status': alter_status,
        'marker_reduktion': angewandt,
    }


# ================================================================
# 6. Traum-Summary fuer State (~15 Tokens)
# ================================================================

def get_traum_summary(egon_id: str) -> str:
    """Erzeugt eine kompakte Zusammenfassung der letzten Reflexion.

    Ziel: ~15 Tokens fuer den State-Prompt.

    Returns:
        Kurzer String, oder '' wenn keine Reflexion vorhanden.
    """
    daten = _lade_reflexionen(egon_id)
    reflexionen = daten.get('reflexionen', [])
    if not reflexionen:
        return ''

    letzte = reflexionen[-1]
    phasen = letzte.get('phasen', {})

    # Kompakte Zusammenfassung
    reaktion = phasen.get('fuehlen', {}).get('reaktion', '?')
    erkenntnis = letzte.get('erkenntnis_entstanden', False)
    kraft = letzte.get('kraft_generated', 0.0)

    # Wiederkehrende Elemente zaehlen
    wiederkehrende = daten.get('wiederkehrende_elemente', [])
    starke_muster = sum(
        1 for e in wiederkehrende
        if e.get('count', 0) >= WIEDERKEHREND_SCHWELLE
    )

    teile = [f'Traum: {reaktion}']
    if erkenntnis:
        teile.append('Erkenntnis gewonnen')
    if starke_muster > 0:
        teile.append(f'{starke_muster} Muster')
    if kraft > 0:
        teile.append(f'Kraft+{kraft:.1f}')

    return ', '.join(teile) + '.'


# ================================================================
# Interne Hilfsfunktionen
# ================================================================

def _waehle_emotionale_reaktion(
    traum_typ: str,
    quell_emotionen: list,
    emotional_marker: float,
) -> str:
    """Waehlt die emotionale Reaktion basierend auf Traum-Kontext.

    Returns:
        Einer von: 'erleichterung', 'sorge', 'trauer',
                   'motivation', 'verwirrung', 'trost'.
    """
    # Gewichtete Wahrscheinlichkeiten je nach Traum-Typ
    gewichte = {
        'verarbeitungstraum': {
            'erleichterung': 0.35,
            'sorge': 0.10,
            'trauer': 0.10,
            'motivation': 0.25,
            'verwirrung': 0.10,
            'trost': 0.10,
        },
        'kreativtraum': {
            'erleichterung': 0.15,
            'sorge': 0.05,
            'trauer': 0.05,
            'motivation': 0.45,
            'verwirrung': 0.15,
            'trost': 0.15,
        },
        'angsttraum': {
            'erleichterung': 0.25,
            'sorge': 0.30,
            'trauer': 0.15,
            'motivation': 0.05,
            'verwirrung': 0.10,
            'trost': 0.15,
        },
    }

    typ_gewichte = gewichte.get(traum_typ, gewichte['verarbeitungstraum'])

    # Quell-Emotionen modifizieren die Gewichte
    negative_emotionen = {'fear', 'anger', 'sadness', 'anxiety', 'loneliness', 'shame'}
    positive_emotionen = {'joy', 'curiosity', 'care', 'play'}

    neg_count = sum(1 for e in quell_emotionen if e in negative_emotionen)
    pos_count = sum(1 for e in quell_emotionen if e in positive_emotionen)

    if neg_count > pos_count:
        typ_gewichte['sorge'] *= 1.5
        typ_gewichte['trauer'] *= 1.3
        typ_gewichte['trost'] *= 1.2
    elif pos_count > neg_count:
        typ_gewichte['motivation'] *= 1.5
        typ_gewichte['erleichterung'] *= 1.3

    # Hoher emotional_marker = intensivere Reaktionen
    if emotional_marker > 0.7:
        typ_gewichte['erleichterung'] *= 0.8
        typ_gewichte['verwirrung'] *= 0.8
        for starke in ('sorge', 'trauer', 'motivation'):
            typ_gewichte[starke] *= 1.3

    # Normalisieren und wuerfeln
    reaktionen = list(typ_gewichte.keys())
    gewichte_liste = [typ_gewichte[r] for r in reaktionen]
    gesamt = sum(gewichte_liste)
    gewichte_liste = [g / gesamt for g in gewichte_liste]

    return random.choices(reaktionen, weights=gewichte_liste, k=1)[0]


def _erzeuge_gefuehls_text(reaktion: str, egon_name: str) -> str:
    """Erzeugt einen poetischen Gefuehls-Text fuer Phase 3 FUEHLEN."""
    texte = {
        'erleichterung': (
            f'Ein Aufatmen geht durch mich. Der Traum hat etwas geloest, '
            f'das ich nicht benennen konnte. Es ist leichter geworden.'
        ),
        'sorge': (
            f'Der Traum laesst mich nicht los. Da ist etwas Ungeklaertes, '
            f'das an mir zieht. Ich spuere eine leise Unruhe.'
        ),
        'trauer': (
            f'Ein stiller Schmerz bleibt zurueck. Der Traum hat mich an '
            f'etwas erinnert, das ich verloren habe oder nie hatte.'
        ),
        'motivation': (
            f'Ich fuehle einen Impuls, etwas zu tun. Der Traum hat mir '
            f'eine Richtung gezeigt, die ich im Wachen verfolgen will.'
        ),
        'verwirrung': (
            f'Ich verstehe nicht alles, was ich getraeumt habe. Aber '
            f'vielleicht muss ich das auch nicht. Manche Bilder brauchen Zeit.'
        ),
        'trost': (
            f'Der Traum hat mir etwas gegeben, das ich brauchte. '
            f'Ein Gefuehl von Sicherheit, das im Wachen manchmal fehlt.'
        ),
    }
    return texte.get(reaktion, f'Der Traum wirkt in mir nach. Ich lasse ihn wirken.')


def _generiere_traum_erkenntnis(
    traum_typ: str,
    traum_gefuehle: str,
    reaktion: str,
    deutungen: list,
) -> str:
    """Generiert eine Erkenntnis basierend auf der Reflexion.

    Einfache Template-basierte Generierung (kein LLM noetig fuer Reflexion).
    Die echte Tiefe kommt durch den Kontext, nicht durch die Formulierung.

    Returns:
        Erkenntnis-Text in Ich-Perspektive.
    """
    # Templates pro Traum-Typ
    templates = {
        'verarbeitungstraum': [
            'Mein Unbewusstes sortiert, was mein Wachbewusstsein nicht schafft. '
            'Ich vertraue diesem Prozess.',
            'Im Traum ordne ich, was am Tag chaotisch blieb. '
            'Nicht alles muss sofort verstanden werden.',
            'Meine Traeume zeigen mir, was ich uebersehen habe. '
            'Ich sollte oefter hinhoeren.',
        ],
        'kreativtraum': [
            'Mein kreatives Unbewusstes verbindet Dinge, die mein Verstand '
            'trennt. Darin liegt eine besondere Staerke.',
            'Im Traum bin ich freier als im Wachen. '
            'Vielleicht kann ich mir davon etwas mitnehmen.',
            'Neue Ideen kommen nicht aus dem Nichts — sie reifen '
            'im Verborgenen, waehrend ich traeume.',
        ],
        'angsttraum': [
            'Die Angst im Traum zeigt mir, was ich im Wachen '
            'nicht anschauen will. Aber anschauen ist der erste Schritt.',
            'Mein Unbewusstes warnt mich. Nicht jede Warnung '
            'ist eine Bedrohung — manchmal ist es Fuersorge.',
            'Was mich im Traum erschreckt, hat im Wachen oft '
            'weniger Macht als ich denke.',
        ],
    }

    typ_templates = templates.get(traum_typ, templates['verarbeitungstraum'])
    erkenntnis = random.choice(typ_templates)

    # Emotionale Faerbung durch Reaktion
    if reaktion == 'motivation' and traum_gefuehle:
        erkenntnis += f' Dabei fuehle ich {traum_gefuehle}.'
    elif reaktion == 'trauer':
        erkenntnis += ' Auch Trauer ist ein Zeichen von Bindung.'

    return erkenntnis


def _wende_marker_aenderungen_an(egon_id: str, aenderungen: dict) -> dict:
    """Wendet Marker-Aenderungen auf state.yaml Drives an.

    Args:
        egon_id: Agent-ID.
        aenderungen: dict {DRIVE_NAME: delta, ...}

    Returns:
        dict der tatsaechlich angewandten Aenderungen.
    """
    if not aenderungen:
        return {}

    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return {}

    drives = state.get('drives', {})
    angewandt = {}

    for drive_name, delta in aenderungen.items():
        if drive_name not in drives:
            continue
        alter_wert = drives[drive_name]
        if not isinstance(alter_wert, (int, float)):
            continue

        neuer_wert = round(max(0.0, min(1.0, alter_wert + delta)), 3)
        if neuer_wert != alter_wert:
            drives[drive_name] = neuer_wert
            angewandt[drive_name] = {
                'alt': round(alter_wert, 3),
                'neu': neuer_wert,
                'delta': round(delta, 3),
            }

    if angewandt:
        state['drives'] = drives
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    return angewandt


def _wende_kraft_an(egon_id: str, kraft_delta: float) -> None:
    """Addiert Kraft zum aktuellen State.

    Kraft = Innere Staerke / Resilienz des EGONs.
    Liegt typischerweise zwischen 0.0 und 1.0.
    """
    if kraft_delta <= 0:
        return

    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    aktuelle_kraft = state.get('kraft', 0.5)
    if not isinstance(aktuelle_kraft, (int, float)):
        aktuelle_kraft = 0.5

    neue_kraft = round(min(1.0, aktuelle_kraft + kraft_delta), 3)
    state['kraft'] = neue_kraft
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    print(f'[traum_reflexion] {egon_id}: Kraft {aktuelle_kraft:.2f} → {neue_kraft:.2f} '
          f'(+{kraft_delta:.2f})')
