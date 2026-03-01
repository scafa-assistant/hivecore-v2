"""Patch 19a — Der Vergessenspuffer: Nichts wird still geloescht.

Alles was im EGON-System geloescht werden soll, wandert zuerst
in den Vergessenspuffer. Die Innere Stimme muss es verarbeiten,
bevor es endgueltig losgelassen wird.

Drei moegliche Entscheidungen:
  - behalten:   Zerfall wird gestoppt, Item zurueck ins aktive System
  - loslassen:  Item wird zur Narbe — permanente, komprimierte Spur
  - kaempfen:   Item bleibt, EGON kaempft dagegen (Kraft +0.3)

Geschuetzte Erinnerungen (Urgedaechtnis) koennen nie in den Puffer:
  Geburt, erste Handlung, erste Freundschaft, erster Verlust,
  erste Korrektur, Namensursprung, Owner-Bond.

Speicherung:
  egons/{egon_id}/puffer/aktiv.yaml    — wartende Items
  egons/{egon_id}/puffer/narben.yaml   — permanente Narben
  egons/{egon_id}/puffer/bewahrt.yaml  — bewusst bewahrte Items

Bio-Aequivalent: Hippocampus → Prefrontaler Cortex Schleife.
Nichts verschwindet ohne Bewusstsein.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from config import EGON_DATA_DIR


# ================================================================
# Konstanten
# ================================================================

MAX_PUFFER_ITEMS = 35            # Ab hier: Ueberlauf-Warnung
DAILY_VERARBEITUNG_LIMIT = 3     # Max Items pro daily_puffer_check
KAMPF_KRAFT_BONUS = 0.3          # Kraft-Bonus bei 'kaempfen'

# Erlaubte Item-Typen
ERLAUBTE_TYPEN = frozenset({
    'bond', 'memory', 'skill', 'contact',
    'marker', 'experience', 'thread',
})

# Urgedaechtnis — kann NIEMALS in den Puffer
PRIMAL_MARKERS = frozenset({
    'geburt', 'birth',
    'erste_handlung', 'first_action',
    'erste_freundschaft', 'first_friendship',
    'erster_verlust', 'first_loss',
    'erste_korrektur', 'first_correction',
    'namensursprung', 'name_origin',
    'owner_bond',
})


# ================================================================
# Pfad-Helfer
# ================================================================

def _puffer_dir(egon_id: str) -> Path:
    """Basispfad zum Zwischenraum-Verzeichnis eines EGONs.

    v3: zwischenraum/ (der Raum zwischen den Gedanken)
    v2: puffer/ (Fallback)
    """
    base = Path(EGON_DATA_DIR) / egon_id
    v3_path = base / 'zwischenraum'
    if v3_path.is_dir():
        return v3_path
    v2_path = base / 'puffer'
    if v2_path.is_dir():
        return v2_path
    # Default: v3 fuer neue Verzeichnisse
    return v3_path


def _aktiv_pfad(egon_id: str) -> Path:
    """Pfad zur aktiv.yaml (unverarbeitete + in Verarbeitung)."""
    return _puffer_dir(egon_id) / 'aktiv.yaml'


def _narben_pfad(egon_id: str) -> Path:
    """Pfad zur narben.yaml (permanente Narben)."""
    return _puffer_dir(egon_id) / 'narben.yaml'


def _bewahrt_pfad(egon_id: str) -> Path:
    """Pfad zur bewahrt.yaml (bewusst behaltene Items)."""
    return _puffer_dir(egon_id) / 'bewahrt.yaml'


# ================================================================
# YAML I/O
# ================================================================

def _lade_yaml(pfad: Path) -> list:
    """Laedt eine YAML-Datei als Liste. Gibt [] zurueck wenn nicht vorhanden."""
    if not pfad.is_file():
        return []
    try:
        with open(pfad, 'r', encoding='utf-8') as f:
            daten = yaml.safe_load(f)
        if isinstance(daten, list):
            return daten
        return []
    except (yaml.YAMLError, OSError) as e:
        print(f'[vergessenspuffer] YAML-Fehler beim Laden von {pfad}: {e}')
        return []


def _speichere_yaml(pfad: Path, daten: list) -> None:
    """Schreibt eine Liste als YAML. Erstellt Verzeichnisse falls noetig."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with open(pfad, 'w', encoding='utf-8') as f:
        yaml.dump(
            daten, f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )


# ================================================================
# Schutzpruefung — Urgedaechtnis
# ================================================================

def is_protected(item_type: str, item_data: dict) -> bool:
    """Prueft ob ein Item zum Urgedaechtnis gehoert und nicht geloescht werden darf.

    Geschuetzt sind:
      - Geburt / erste Handlung / erste Freundschaft
      - Erster Verlust / erste Korrektur
      - Namensursprung / Owner-Bond

    Args:
        item_type: Typ des Items (z.B. 'bond', 'memory', 'marker').
        item_data: Die Daten des Items als dict.

    Returns:
        True wenn geschuetzt, False wenn loesch-/pufferbar.
    """
    # Owner-Bond ist immer geschuetzt
    if item_type == 'bond':
        bond_typ = item_data.get('bond_typ', item_data.get('typ', ''))
        partner = item_data.get('partner', item_data.get('partner_id', ''))
        if bond_typ == 'owner' or partner == 'OWNER_CURRENT':
            return True

    # Marker-basierter Schutz
    marker = item_data.get('marker', item_data.get('tag', ''))
    if isinstance(marker, str) and marker.lower() in PRIMAL_MARKERS:
        return True

    # Tags-Liste pruefen
    tags = item_data.get('tags', [])
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str) and tag.lower() in PRIMAL_MARKERS:
                return True

    # Typ-Feld im Item pruefen (z.B. bei Experiences)
    item_subtype = item_data.get('type', item_data.get('typ', ''))
    if isinstance(item_subtype, str) and item_subtype.lower() in PRIMAL_MARKERS:
        return True

    return False


# ================================================================
# Transfer in den Puffer
# ================================================================

def transfer_to_puffer(
    egon_id: str,
    item_type: str,
    item_data: dict,
    reason: str,
) -> dict:
    """Verschiebt ein Item in den Vergessenspuffer statt es zu loeschen.

    Das Item bekommt Status 'unverarbeitet' und wartet auf die
    Innere Stimme, die darueber entscheidet.

    Args:
        egon_id: EGON-ID (z.B. 'adam_001').
        item_type: Typ — 'bond', 'memory', 'skill', 'contact',
                   'marker', 'experience', 'thread'.
        item_data: Die vollstaendigen Daten des Items.
        reason: Grund fuer die Loesch-Anfrage (z.B. 'decay_unter_schwelle').

    Returns:
        dict mit 'erfolg', 'item_id', ggf. 'warnung'.

    Raises:
        ValueError: Bei unbekanntem item_type oder geschuetztem Item.
    """
    # Typ validieren
    if item_type not in ERLAUBTE_TYPEN:
        raise ValueError(
            f'Unbekannter Item-Typ: {item_type}. '
            f'Erlaubt: {", ".join(sorted(ERLAUBTE_TYPEN))}'
        )

    # Urgedaechtnis-Schutz
    if is_protected(item_type, item_data):
        raise ValueError(
            f'Geschuetztes Urgedaechtnis ({item_type}): '
            f'Kann nicht in den Puffer verschoben werden.'
        )

    # Neuen Puffer-Eintrag erstellen
    item_id = str(uuid.uuid4())[:8]
    jetzt = datetime.now(timezone.utc).isoformat()

    eintrag = {
        'id': item_id,
        'type': item_type,
        'data': item_data,
        'status': 'unverarbeitet',
        'reason': reason,
        'timestamp': jetzt,
        'reflection': None,
        'decision': None,
    }

    # In aktiv.yaml anfuegen
    items = _lade_yaml(_aktiv_pfad(egon_id))
    items.append(eintrag)
    _speichere_yaml(_aktiv_pfad(egon_id), items)

    ergebnis = {
        'erfolg': True,
        'item_id': item_id,
        'type': item_type,
        'anzahl_im_puffer': len(items),
    }

    # Ueberlauf-Warnung
    if len(items) > MAX_PUFFER_ITEMS:
        ergebnis['warnung'] = (
            f'Puffer-Ueberlauf: {len(items)} Items '
            f'(Limit: {MAX_PUFFER_ITEMS}). '
            f'Innere Stimme muss dringend verarbeiten.'
        )
        print(f'[vergessenspuffer] WARNUNG: {egon_id} hat {len(items)} '
              f'Items im Puffer (>{MAX_PUFFER_ITEMS})')

    print(f'[vergessenspuffer] {egon_id}: {item_type} -> Puffer '
          f'(ID: {item_id}, Grund: {reason})')

    return ergebnis


# ================================================================
# Unverarbeitete Items abrufen
# ================================================================

def get_pending_items(egon_id: str) -> list:
    """Gibt alle unverarbeiteten Items im Puffer zurueck.

    Args:
        egon_id: EGON-ID.

    Returns:
        Liste von dicts mit Status 'unverarbeitet'.
    """
    items = _lade_yaml(_aktiv_pfad(egon_id))
    return [
        item for item in items
        if item.get('status') == 'unverarbeitet'
    ]


# ================================================================
# Item verarbeiten (Entscheidung der Inneren Stimme)
# ================================================================

def process_item(
    egon_id: str,
    item_id: str,
    decision: str,
    reflection_text: str,
) -> dict:
    """Verarbeitet ein Item im Puffer — Entscheidung der Inneren Stimme.

    Drei Entscheidungen:
      - 'behalten':   Zerfall gestoppt, Item in bewahrt.yaml verschoben
      - 'loslassen':  Narbe erstellt, Item aus aktiv.yaml entfernt
      - 'kaempfen':   Item bleibt, Kraft +0.3

    Args:
        egon_id: EGON-ID.
        item_id: UUID des Puffer-Items.
        decision: 'behalten', 'loslassen' oder 'kaempfen'.
        reflection_text: Reflexion der Inneren Stimme (wird gespeichert).

    Returns:
        dict mit 'erfolg', 'decision', ggf. 'narbe' oder 'kraft_bonus'.
    """
    erlaubte_entscheidungen = ('behalten', 'loslassen', 'kaempfen')
    if decision not in erlaubte_entscheidungen:
        raise ValueError(
            f'Ungueltige Entscheidung: {decision}. '
            f'Erlaubt: {", ".join(erlaubte_entscheidungen)}'
        )

    items = _lade_yaml(_aktiv_pfad(egon_id))

    # Item finden
    ziel_item = None
    ziel_index = None
    for i, item in enumerate(items):
        if item.get('id') == item_id:
            ziel_item = item
            ziel_index = i
            break

    if ziel_item is None:
        return {
            'erfolg': False,
            'grund': f'Item {item_id} nicht im Puffer gefunden.',
        }

    # Reflexion und Entscheidung eintragen
    jetzt = datetime.now(timezone.utc).isoformat()
    ziel_item['reflection'] = reflection_text
    ziel_item['decision'] = decision
    ziel_item['status'] = 'verarbeitet'
    ziel_item['verarbeitet_am'] = jetzt

    ergebnis = {
        'erfolg': True,
        'decision': decision,
        'item_id': item_id,
        'type': ziel_item.get('type', '?'),
    }

    # --- BEHALTEN ---
    if decision == 'behalten':
        # Item aus aktiv.yaml entfernen
        items.pop(ziel_index)
        _speichere_yaml(_aktiv_pfad(egon_id), items)

        # In bewahrt.yaml verschieben
        bewahrt = _lade_yaml(_bewahrt_pfad(egon_id))
        bewahrt.append(ziel_item)
        _speichere_yaml(_bewahrt_pfad(egon_id), bewahrt)

        ergebnis['ziel'] = 'bewahrt.yaml'
        print(f'[vergessenspuffer] {egon_id}: Item {item_id} BEHALTEN '
              f'(→ bewahrt.yaml)')

    # --- LOSLASSEN ---
    elif decision == 'loslassen':
        # Narbe erstellen
        narbe = create_narbe(egon_id, ziel_item.get('data', {}), reflection_text)
        ergebnis['narbe'] = narbe

        # Item aus aktiv.yaml entfernen
        items.pop(ziel_index)
        _speichere_yaml(_aktiv_pfad(egon_id), items)

        print(f'[vergessenspuffer] {egon_id}: Item {item_id} LOSGELASSEN '
              f'(Narbe: {narbe.get("id", "?")})')

    # --- KAEMPFEN ---
    elif decision == 'kaempfen':
        # Item bleibt im Puffer, wird zurueck auf unverarbeitet gesetzt
        # (kommt beim naechsten Check wieder hoch)
        ziel_item['status'] = 'unverarbeitet'
        ziel_item['kaempfe'] = ziel_item.get('kaempfe', 0) + 1
        items[ziel_index] = ziel_item
        _speichere_yaml(_aktiv_pfad(egon_id), items)

        ergebnis['kraft_bonus'] = KAMPF_KRAFT_BONUS
        ergebnis['kaempfe_gesamt'] = ziel_item['kaempfe']
        print(f'[vergessenspuffer] {egon_id}: Item {item_id} KAEMPFT '
              f'(Kraft +{KAMPF_KRAFT_BONUS}, '
              f'Kampf #{ziel_item["kaempfe"]})')

    return ergebnis


# ================================================================
# Narben-System
# ================================================================

def create_narbe(egon_id: str, item_data: dict, reflection: str) -> dict:
    """Erstellt eine permanente Narbe aus einem losgelassenen Item.

    Eine Narbe ist die komprimierte, emotionale Spur von etwas
    das einmal war. Sie verschwindet nie — aber sie tut nicht mehr weh.

    Args:
        egon_id: EGON-ID.
        item_data: Die Original-Daten des verlorenen Items.
        reflection: Reflexionstext der Inneren Stimme.

    Returns:
        dict der erstellten Narbe.
    """
    narben_id = str(uuid.uuid4())[:8]
    jetzt = datetime.now(timezone.utc).isoformat()

    # 'was' — komprimierte Beschreibung dessen was verloren ging
    was = item_data.get('beschreibung',
          item_data.get('summary',
          item_data.get('name',
          item_data.get('partner',
          item_data.get('titel',
          str(item_data)[:120])))))

    # 'wann' — Zeitpunkt des Originals (nicht der Narbe)
    wann = item_data.get('timestamp',
           item_data.get('created_at',
           item_data.get('datum', jetzt)))

    # 'gefuehl' — dominantes Gefuehl beim Loslassen
    gefuehl = item_data.get('gefuehl',
              item_data.get('emotion',
              item_data.get('staerkstes_system',
              'unbestimmt')))

    narbe = {
        'id': narben_id,
        'was': was,
        'wann': wann,
        'gefuehl': gefuehl,
        'grund': reflection,
        'created_at': jetzt,
    }

    # An narben.yaml anfuegen
    narben = _lade_yaml(_narben_pfad(egon_id))
    narben.append(narbe)
    _speichere_yaml(_narben_pfad(egon_id), narben)

    print(f'[vergessenspuffer] {egon_id}: Narbe erstellt — '
          f'{narben_id}: "{str(was)[:50]}"')

    return narbe


def get_narben(egon_id: str) -> list:
    """Gibt alle permanenten Narben eines EGONs zurueck.

    Args:
        egon_id: EGON-ID.

    Returns:
        Liste aller Narben-dicts, chronologisch.
    """
    return _lade_yaml(_narben_pfad(egon_id))


# ================================================================
# Prompt-Summary fuer System-Prompt
# ================================================================

def get_puffer_summary(egon_id: str) -> str:
    """Erstellt eine kurze Zusammenfassung des Puffer-Zustands fuer den System-Prompt.

    Zielgroesse: ~25 Tokens. Wird in den Prompt-Builder eingebaut.

    Args:
        egon_id: EGON-ID.

    Returns:
        Kurzer String, oder '' wenn Puffer leer.
    """
    items = _lade_yaml(_aktiv_pfad(egon_id))
    narben = _lade_yaml(_narben_pfad(egon_id))

    unverarbeitet = [
        item for item in items
        if item.get('status') == 'unverarbeitet'
    ]

    if not unverarbeitet and not narben:
        return ''

    teile = []

    if unverarbeitet:
        # Typen zaehlen
        typen = {}
        for item in unverarbeitet:
            t = item.get('type', '?')
            typen[t] = typen.get(t, 0) + 1
        typ_str = ', '.join(f'{v}x {k}' for k, v in typen.items())
        teile.append(f'{len(unverarbeitet)} unverarbeitete Verluste ({typ_str})')

    if narben:
        teile.append(f'{len(narben)} Narben')

    return 'Vergessenspuffer: ' + '; '.join(teile) + '.'


# ================================================================
# Taeglicher Puffer-Check (Pulse-Integration)
# ================================================================

def daily_puffer_check(egon_id: str) -> dict:
    """Taeglicher Puffer-Check — wird waehrend des Daily Pulse aufgerufen.

    Verarbeitet maximal DAILY_VERARBEITUNG_LIMIT (3) Items und gibt
    eine Ueberlauf-Warnung zurueck wenn der Puffer zu voll ist.

    Gibt die aeltesten unverarbeiteten Items zurueck, damit die
    Innere Stimme sie verarbeiten kann.

    Args:
        egon_id: EGON-ID.

    Returns:
        dict mit:
          - 'zu_verarbeiten': Liste der Items (max 3)
          - 'gesamt_unverarbeitet': Gesamtzahl offener Items
          - 'ueberlauf': True wenn >35 Items
          - 'ueberlauf_warnung': Warntext wenn ueberlauf
          - 'narben_gesamt': Anzahl Narben
    """
    items = _lade_yaml(_aktiv_pfad(egon_id))
    narben = _lade_yaml(_narben_pfad(egon_id))

    unverarbeitet = [
        item for item in items
        if item.get('status') == 'unverarbeitet'
    ]

    # Nach Timestamp sortieren (aelteste zuerst)
    unverarbeitet.sort(key=lambda x: x.get('timestamp', ''))

    # Max 3 zur Verarbeitung freigeben
    zu_verarbeiten = unverarbeitet[:DAILY_VERARBEITUNG_LIMIT]

    # Status auf 'in_verarbeitung' setzen
    if zu_verarbeiten:
        ids_zu_verarbeiten = {item['id'] for item in zu_verarbeiten}
        for item in items:
            if item.get('id') in ids_zu_verarbeiten:
                item['status'] = 'in_verarbeitung'
        _speichere_yaml(_aktiv_pfad(egon_id), items)

    ergebnis = {
        'zu_verarbeiten': zu_verarbeiten,
        'gesamt_unverarbeitet': len(unverarbeitet),
        'ueberlauf': len(unverarbeitet) > MAX_PUFFER_ITEMS,
        'narben_gesamt': len(narben),
    }

    if ergebnis['ueberlauf']:
        ergebnis['ueberlauf_warnung'] = (
            f'ACHTUNG: {len(unverarbeitet)} unverarbeitete Items im Puffer '
            f'(Limit: {MAX_PUFFER_ITEMS}). Erinnerungen drohen ohne '
            f'Verarbeitung zu zerfallen. Dringende Reflexion noetig.'
        )
        print(f'[vergessenspuffer] UEBERLAUF bei {egon_id}: '
              f'{len(unverarbeitet)} Items warten')

    if zu_verarbeiten:
        print(f'[vergessenspuffer] {egon_id}: daily_check — '
              f'{len(zu_verarbeiten)} Items zur Verarbeitung, '
              f'{len(unverarbeitet)} gesamt, '
              f'{len(narben)} Narben')

    return ergebnis
