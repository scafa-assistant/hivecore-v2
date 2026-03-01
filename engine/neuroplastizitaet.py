"""engine/neuroplastizitaet.py — Patch 16: Strukturelle Brain-Events.

Das Gehirn waechst mit seinen Erfahrungen. Neue Faeden (Verbindungen
zwischen Hirnregionen) entstehen, staerken sich, verblassen oder
hinterlassen Narben — genau wie synaptische Plastizitaet beim Menschen.

Hebbsche Regel: "Neurons that fire together wire together."
Synaptisches Pruning: Ungenutzte Verbindungen werden abgebaut.
LTP/LTD: Wiederholte Aktivierung staerkt/schwaecht Verbindungen.

Backend-Only: Definiert Struktur und Events.
Frontend rendert (Dicke, Farbe, Animation).

Bio-Quellen: Hebb 1949, Huttenlocher 1979, Bliss & Lomo 1973, Fields 2008
"""

import time
from collections import defaultdict

from engine.organ_reader import read_yaml_organ, write_yaml_organ


# ================================================================
# KONSTANTEN
# ================================================================

# 14 anatomische Grundfaeden — bei Geburt vorhanden, immer da
ANATOMISCHE_GRUNDFAEDEN = [
    # Sensorischer Input → Verarbeitung
    {'von': 'thalamus',     'nach': 'praefrontal',  'dicke': 0.5, 'farbe': '#78909c'},
    {'von': 'thalamus',     'nach': 'amygdala',     'dicke': 0.5, 'farbe': '#78909c'},
    # Emotionale Verarbeitung
    {'von': 'amygdala',     'nach': 'praefrontal',  'dicke': 0.4, 'farbe': '#ef5350'},
    {'von': 'amygdala',     'nach': 'insula',       'dicke': 0.4, 'farbe': '#ef5350'},
    {'von': 'amygdala',     'nach': 'hypothalamus', 'dicke': 0.3, 'farbe': '#ef5350'},
    {'von': 'insula',       'nach': 'praefrontal',  'dicke': 0.3, 'farbe': '#ab47bc'},
    # Gedaechtnis
    {'von': 'hippocampus',  'nach': 'praefrontal',  'dicke': 0.4, 'farbe': '#66bb6a'},
    {'von': 'hippocampus',  'nach': 'neokortex',    'dicke': 0.3, 'farbe': '#66bb6a'},
    {'von': 'hippocampus',  'nach': 'amygdala',     'dicke': 0.3, 'farbe': '#66bb6a'},
    # Koerper-Regulation
    {'von': 'hypothalamus', 'nach': 'hirnstamm',    'dicke': 0.3, 'farbe': '#8d6e63'},
    # Hoehere Kognition
    {'von': 'praefrontal',  'nach': 'neokortex',    'dicke': 0.4, 'farbe': '#42a5f5'},
    {'von': 'neokortex',    'nach': 'hippocampus',  'dicke': 0.3, 'farbe': '#42a5f5'},
    # Cerebellum (Mustererkennung)
    {'von': 'cerebellum',   'nach': 'praefrontal',  'dicke': 0.2, 'farbe': '#78909c'},
    {'von': 'cerebellum',   'nach': 'neokortex',    'dicke': 0.2, 'farbe': '#78909c'},
]

BOND_FARBEN = {
    'neu':           '#b0bec5',   # Grau-Blau — unbekannt
    'bekannt':       '#81d4fa',   # Hell-Blau — oberflaechlich
    'freundschaft':  '#4fc3f7',   # Blau — vertraut
    'tiefe_bindung': '#0288d1',   # Dunkel-Blau — tief
    'romantisch':    '#f48fb1',   # Rosa
    'paar':          '#e91e63',   # Pink — Resonanz (Patch 6)
    'elternteil':    '#ffb74d',   # Orange — familiaer
    'kind':          '#ff8a65',   # Orange-Rot — eigenes Kind
    'owner':         '#ffd54f',   # Gold — besondere Bindung
    'konflikt':      '#e53935',   # Rot — aktiver Konflikt
    'gebrochen':     '#455a64',   # Dunkel-Grau — Narbe
}

LEBENSFADEN_FARBEN = {
    'keimend':        '#c8e6c9',   # Zartes Gruen
    'wachsend':       '#ffd54f',   # Gold
    'eskalation':     '#ff9800',   # Orange
    'explosion':      '#f44336',   # Rot
    'integration':    '#7e57c2',   # Lila
    'ruhend':         '#9e9e9e',   # Grau
    'abgeschlossen':  '#546e7a',   # Blau-Grau
}

PRAEGUNG_STATUS_RENDERING = {
    'geerbt': {
        'opacity': 0.05,
        'dicke': 0.15,
        'farbe': '#880e4f',
        'bei_aktivierung': {
            'opacity': 0.6,
            'animation': 'deep_pulse',
            'dauer_ms': 3000,
            'zurueck_zu': 0.05,
        },
    },
    'verinnerlicht': {
        'opacity': 0.4,
        'dicke': 0.30,
        'farbe': '#ad1457',
    },
    'ueberwunden': {
        'opacity': 0.02,
        'dicke': 0.05,
        'farbe': '#616161',
    },
    'ruhend': {
        'opacity': 0.03,
        'dicke': 0.10,
        'farbe': '#880e4f',
    },
}

TEMPORAERE_TYPEN = {
    'lichtbogen': {
        'von': 'hippocampus',
        'nach': 'neokortex',
        'dicke': 0.3,
        'farbe': '#fff176',
        'lebensdauer_ms': 5000,
        'animation': 'flash_fade',
    },
    'arbeitsspeicher_abruf': {
        'von': 'hippocampus',
        'nach': 'praefrontal',
        'dicke': 0.2,
        'farbe': '#a5d6a7',
        'lebensdauer_ms': 3000,
        'animation': 'pulse_fade',
    },
    'konsolidierung': {
        'von': 'hippocampus',
        'nach': 'neokortex',
        'dicke': 0.4,
        'farbe': '#ce93d8',
        'lebensdauer_ms': 8000,
        'animation': 'wave',
    },
}

MAX_DYNAMISCHE_FAEDEN = 50  # Ohne anatomische Grundfaeden

ALLE_REGIONEN = [
    'thalamus', 'praefrontal', 'amygdala', 'insula',
    'hypothalamus', 'hippocampus', 'neokortex',
    'hirnstamm', 'cerebellum',
]


# ================================================================
# EVENT-BUFFER (in-memory, pro EGON, fuer Frontend-Polling)
# ================================================================

_event_buffer: dict = defaultdict(list)
_MAX_BUFFER = 200


def event_buffer_push(egon_id: str, events: list) -> None:
    """Events in den Buffer schreiben (fuer Frontend-Polling/SSE)."""
    buf = _event_buffer[egon_id]
    buf.extend(events)
    if len(buf) > _MAX_BUFFER:
        _event_buffer[egon_id] = buf[-_MAX_BUFFER:]


def ne_emit(egon_id: str, typ: str, von: str, nach: str = '',
            label: str = '', intensitaet: float = 0.5,
            animation: str = 'pulse', dauer: float = 2.0,
            extra: dict | None = None) -> None:
    """Universelle NeuroMap-Event-Emission fuer alle Module.

    Einfach aus jedem Modul aufrufbar:
        from engine.neuroplastizitaet import ne_emit
        ne_emit(egon_id, 'AKTIVIERUNG', 'hippocampus', 'praefrontal',
                label='Episoden-Abruf', intensitaet=0.7)

    Args:
        egon_id: Welcher EGON.
        typ: Event-Typ (AKTIVIERUNG, SIGNAL, IMPULS, STRUKTUR_NEU, etc.)
        von: Quell-Region (z.B. 'hippocampus', 'amygdala', 'thalamus').
        nach: Ziel-Region (optional, leer fuer lokale Aktivierung).
        label: Menschenlesbarer Text fuers Frontend.
        intensitaet: 0.0-1.0 — steuert Helligkeit/Groesse im Frontend.
        animation: Frontend-Animation ('pulse', 'flow', 'glow', 'flash', 'color_drift').
        dauer: Dauer der Animation in Sekunden.
        extra: Optionale zusaetzliche Daten.
    """
    from datetime import datetime
    ts = datetime.now().strftime('%H:%M:%S')
    ts_unix = time.time()
    event = {
        'typ': typ,
        'von': von,
        'nach': nach or von,
        'label': label,
        'intensitaet': round(min(1.0, max(0.0, intensitaet)), 2),
        'animation': animation,
        'dauer_sekunden': dauer,
        'timestamp': ts,
        'timestamp_unix': ts_unix,
    }
    if extra:
        event.update(extra)
    event_buffer_push(egon_id, [event])
    # Region-Nutzung tracken
    regs = set()
    if von and von != 'ALL':
        regs.add(von)
    if nach and nach != von and nach != 'ALL':
        regs.add(nach)
    if regs:
        regionen_nutzung_erhoehen(egon_id, list(regs))


def event_buffer_pop(egon_id: str) -> list:
    """Alle Events abholen und Buffer leeren."""
    return _event_buffer.pop(egon_id, [])


def event_buffer_peek(egon_id: str, seit_ts: float = 0) -> list:
    """Events nach Timestamp filtern (ohne zu leeren)."""
    return [e for e in _event_buffer.get(egon_id, [])
            if e.get('timestamp_unix', 0) > seit_ts]


# ================================================================
# REGIONEN-NUTZUNG (in-memory, flushed am Zyklusende)
# ================================================================

_regionen_nutzung: dict = defaultdict(lambda: defaultdict(int))


def regionen_nutzung_erhoehen(egon_id: str, regionen: list) -> None:
    """In-memory Region-Nutzung tracken (kein Disk I/O)."""
    for r in regionen:
        if r in ALLE_REGIONEN:
            _regionen_nutzung[egon_id][r] += 1


def regionen_nutzung_flush(egon_id: str) -> dict:
    """In-memory Zaehler in state.yaml schreiben und zuruecksetzen."""
    counters = dict(_regionen_nutzung.pop(egon_id, {}))
    if not counters:
        return {}
    try:
        state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}
        neuro = state.setdefault('neuroplastizitaet', {})
        existing = neuro.get('regionen_nutzung', {})
        for r, count in counters.items():
            existing[r] = existing.get(r, 0) + count
        neuro['regionen_nutzung'] = existing
        state['neuroplastizitaet'] = neuro
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)
        return existing
    except Exception as e:
        print(f'[neuroplastizitaet] Flush FEHLER: {e}')
        return counters


def regionen_nutzung_reset(egon_id: str) -> None:
    """Reset Zaehler auf 0 (NACH Pruning am Zyklusende)."""
    _regionen_nutzung.pop(egon_id, None)
    try:
        state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}
        neuro = state.setdefault('neuroplastizitaet', {})
        neuro['regionen_nutzung'] = {r: 0 for r in ALLE_REGIONEN}
        state['neuroplastizitaet'] = neuro
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)
    except Exception as e:
        print(f'[neuroplastizitaet] Reset FEHLER: {e}')


# ================================================================
# HILFSFUNKTIONEN
# ================================================================

def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


def _faden_dicke(faden_dict: dict) -> float:
    """Berechne Dicke eines Lebensfadens nach Status."""
    status = faden_dict.get('status', 'keimend')
    return {
        'keimend': 0.15, 'wachsend': 0.30, 'eskalation': 0.45,
        'explosion': 0.60, 'integration': 0.50, 'ruhend': 0.15,
        'abgeschlossen': 0.10,
    }.get(status, 0.15)


def _faden_opacity(faden_dict: dict) -> float:
    """Berechne Opacity eines Lebensfadens nach Status."""
    status = faden_dict.get('status', 'keimend')
    return {
        'keimend': 0.4, 'wachsend': 0.7, 'eskalation': 0.85,
        'explosion': 0.95, 'integration': 0.75, 'ruhend': 0.25,
        'abgeschlossen': 0.15,
    }.get(status, 0.4)


def _erinnerung_zu_region(treffer: dict) -> str:
    """Mappe Erinnerungs-Typ auf Ziel-Region fuer Lichtbogen."""
    tags = treffer.get('tags', [])
    if any(t in tags for t in ['angst', 'wut', 'trauer', 'panik']):
        return 'amygdala'
    if any(t in tags for t in ['koerper', 'schmerz', 'unwohlsein']):
        return 'insula'
    if any(t in tags for t in ['denken', 'entscheidung', 'reflexion']):
        return 'praefrontal'
    if any(t in tags for t in ['muster', 'gewohnheit', 'routine']):
        return 'cerebellum'
    return 'neokortex'


# ================================================================
# KERN: STRUKTURELLE EVENTS EMITTIEREN
# ================================================================

def emittiere_struktur_event(egon_id: str, aktion: str, kontext: dict) -> list:
    """Generiert strukturelle Brain-Events basierend auf EGON-Aktionen.

    Wird aufgerufen nach jeder State-Aenderung die die Faden-Struktur betrifft.
    Events werden in den Buffer geschrieben UND zurueckgegeben.

    Aktionen:
        BOND_NEU, BOND_UPDATE, BOND_BRUCH, BOND_KONFLIKT, BOND_VERSOEHNUNG,
        FADEN_NEU, FADEN_STATUS,
        PRAEGUNG_AKTIVIERT, PRAEGUNG_VERINNERLICHT, PRAEGUNG_UEBERWUNDEN,
        METACOGNITION_AKTIVIERT, REAPPRAISAL,
        LICHTBOGEN_TREFFER, NACHT_KONSOLIDIERUNG,
        GENESIS_GEBURT, ALLOSTATIC_SHIFT
    """
    ts = _now_iso()
    ts_unix = time.time()
    events = []

    # --- BONDS ---

    if aktion == 'BOND_NEU':
        partner_id = kontext.get('partner_id', 'unbekannt')
        events.append({
            'typ': 'STRUKTUR_NEU',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'bond_{partner_id}',
            'kategorie': 'bond',
            'von': 'amygdala', 'nach': 'praefrontal',
            'dicke': 0.1,
            'farbe': BOND_FARBEN['neu'],
            'opacity': 0.3,
            'permanent': True,
            'animation': 'sprout',
            'meta': {
                'partner': partner_id,
                'bond_typ': 'neu',
                'ausloeser': kontext.get('ausloeser', 'erster_kontakt'),
            },
        })

    elif aktion == 'BOND_UPDATE':
        partner_id = kontext.get('partner_id', 'unbekannt')
        bond_staerke = kontext.get('bond_staerke', 0.5)
        bond_typ = kontext.get('bond_typ', 'bekannt')
        alte_staerke = kontext.get('alte_staerke', 0.0)
        events.append({
            'typ': 'STRUKTUR_UPDATE',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'bond_{partner_id}',
            'aenderungen': {
                'dicke': _clamp(bond_staerke * 0.8, 0.05, 0.8),
                'farbe': BOND_FARBEN.get(bond_typ, BOND_FARBEN['bekannt']),
                'opacity': _clamp(0.3 + bond_staerke * 0.7, 0.1, 0.9),
            },
            'animation': 'strengthen' if bond_staerke > alte_staerke else 'weaken',
            'meta': {
                'bond_staerke_neu': bond_staerke,
                'grund': kontext.get('grund', 'gespraech'),
            },
        })

    elif aktion == 'BOND_BRUCH':
        partner_id = kontext.get('partner_id', 'unbekannt')
        events.append({
            'typ': 'STRUKTUR_FADE',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'bond_{partner_id}',
            'ziel_opacity': 0.03,
            'ziel_dicke': 0.05,
            'dauer_sekunden': 60,
            'animation': 'wither',
            'meta': {'grund': 'bond_bruch', 'narbe': True},
        })

    elif aktion == 'BOND_KONFLIKT':
        partner_id = kontext.get('partner_id', 'unbekannt')
        events.append({
            'typ': 'STRUKTUR_UPDATE',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'bond_{partner_id}',
            'aenderungen': {'farbe': BOND_FARBEN['konflikt']},
            'animation': 'flicker',
            'meta': {'grund': 'konflikt'},
        })

    elif aktion == 'BOND_VERSOEHNUNG':
        partner_id = kontext.get('partner_id', 'unbekannt')
        bond_staerke = kontext.get('bond_staerke', 0.5)
        bond_typ = kontext.get('bond_typ', 'bekannt')
        events.append({
            'typ': 'STRUKTUR_UPDATE',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'bond_{partner_id}',
            'aenderungen': {
                'farbe': BOND_FARBEN.get(bond_typ, BOND_FARBEN['bekannt']),
                'opacity': _clamp(0.3 + bond_staerke * 0.65, 0.1, 0.85),
                'dicke': _clamp(bond_staerke * 0.8 * 0.9, 0.05, 0.75),
            },
            'animation': 'heal',
            'meta': {'grund': 'versoehnung', 'narbe_aktiv': True},
        })

    # --- LEBENSFAEDEN ---

    elif aktion == 'FADEN_NEU':
        faden = kontext.get('faden', {})
        sofort = kontext.get('sofort', False)
        faden_id = faden.get('id', 'unbekannt')
        status = faden.get('status', 'keimend')
        events.append({
            'typ': 'STRUKTUR_NEU',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'leben_{faden_id}',
            'kategorie': 'lebensfaden',
            'von': 'praefrontal', 'nach': 'hippocampus',
            'dicke': 0.4 if sofort else 0.15,
            'farbe': LEBENSFADEN_FARBEN.get(status, '#9e9e9e'),
            'opacity': 0.7 if sofort else 0.4,
            'permanent': True,
            'animation': 'burst' if sofort else 'sprout',
            'meta': {
                'faden_name': faden.get('name', ''),
                'status': status,
                'sofort': sofort,
            },
        })

    elif aktion == 'FADEN_STATUS':
        faden = kontext.get('faden', {})
        faden_id = faden.get('id', 'unbekannt')
        status = faden.get('status', 'keimend')
        animation_map = {
            'eskalation': 'intensify', 'explosion': 'burst',
            'integration': 'glow', 'ruhend': 'dim',
            'abgeschlossen': 'settle',
        }
        events.append({
            'typ': 'STRUKTUR_UPDATE',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'leben_{faden_id}',
            'aenderungen': {
                'farbe': LEBENSFADEN_FARBEN.get(status, '#9e9e9e'),
                'dicke': _faden_dicke(faden),
                'opacity': _faden_opacity(faden),
            },
            'animation': animation_map.get(status, 'none'),
        })

    # --- PRAEGUNGEN ---

    elif aktion == 'PRAEGUNG_AKTIVIERT':
        praegung = kontext.get('praegung', {})
        praeg_id = praegung.get('id', praegung.get('text', 'x')[:16].replace(' ', '_'))
        status = praegung.get('status', 'geerbt')
        rendering = PRAEGUNG_STATUS_RENDERING.get(status, PRAEGUNG_STATUS_RENDERING['geerbt'])
        events.append({
            'typ': 'STRUKTUR_UPDATE',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'praeg_{praeg_id}',
            'aenderungen': {'opacity': 0.6},
            'animation': 'deep_pulse',
            'dauer_ms': 3000,
            'zurueck_zu': {'opacity': rendering.get('opacity', 0.05)},
            'meta': {
                'text': praegung.get('text', ''),
                'staerke': praegung.get('staerke', 0),
                'ergebnis': kontext.get('ergebnis', 'bestaetigt'),
            },
        })

    elif aktion == 'PRAEGUNG_VERINNERLICHT':
        praegung = kontext.get('praegung', {})
        praeg_id = praegung.get('id', praegung.get('text', 'x')[:16].replace(' ', '_'))
        events.append({
            'typ': 'STRUKTUR_UPDATE',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'praeg_{praeg_id}',
            'aenderungen': {'opacity': 0.4, 'dicke': 0.30, 'farbe': '#ad1457'},
            'animation': 'emerge',
        })

    elif aktion == 'PRAEGUNG_UEBERWUNDEN':
        praegung = kontext.get('praegung', {})
        praeg_id = praegung.get('id', praegung.get('text', 'x')[:16].replace(' ', '_'))
        events.append({
            'typ': 'STRUKTUR_FADE',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'praeg_{praeg_id}',
            'ziel_opacity': 0.02,
            'ziel_dicke': 0.05,
            'dauer_sekunden': 20,
            'animation': 'dissolve_gentle',
        })

    # --- METACOGNITION ---

    elif aktion == 'METACOGNITION_AKTIVIERT':
        stufe = kontext.get('stufe', 'monitoring')
        events.append({
            'typ': 'STRUKTUR_NEU',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': 'meta_loop_1',
            'kategorie': 'metacognition',
            'von': 'praefrontal', 'nach': 'praefrontal',
            'dicke': 0.15 if stufe == 'monitoring' else 0.25,
            'farbe': '#e1bee7',
            'opacity': 0.5,
            'permanent': True,
            'animation': 'slow_orbit',
        })
        if stufe == 'regulation':
            events.append({
                'typ': 'STRUKTUR_NEU',
                'timestamp': ts, 'timestamp_unix': ts_unix,
                'faden_id': 'meta_loop_2',
                'kategorie': 'metacognition',
                'von': 'praefrontal', 'nach': 'praefrontal',
                'dicke': 0.20,
                'farbe': '#ce93d8',
                'opacity': 0.4,
                'permanent': True,
                'animation': 'slow_orbit',
            })

    elif aktion == 'REAPPRAISAL':
        events.append({
            'typ': 'STRUKTUR_UPDATE',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': 'meta_loop_1',
            'aenderungen': {'opacity': 0.9},
            'animation': 'bright_flash',
            'dauer_ms': 2000,
            'zurueck_zu': {'opacity': 0.5},
        })

    # --- LICHTBOGEN (temporaer) ---

    elif aktion == 'LICHTBOGEN_TREFFER':
        treffer = kontext.get('treffer', {})
        treffer_id = treffer.get('id', f'{int(ts_unix)}')
        ziel = _erinnerung_zu_region(treffer)
        events.append({
            'typ': 'STRUKTUR_TEMP',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'temp_licht_{treffer_id}',
            'kategorie': 'lichtbogen',
            'von': 'hippocampus', 'nach': ziel,
            'dicke': 0.3,
            'farbe': '#fff176',
            'opacity': 0.9,
            'lebensdauer_ms': 5000,
            'animation': 'flash_fade',
        })

    # --- KONSOLIDIERUNG (Nacht) ---

    elif aktion == 'NACHT_KONSOLIDIERUNG':
        eintrag = kontext.get('eintrag', {})
        eintrag_id = eintrag.get('id', f'{int(ts_unix)}')
        events.append({
            'typ': 'STRUKTUR_TEMP',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'temp_kons_{eintrag_id}',
            'kategorie': 'konsolidierung',
            'von': 'hippocampus', 'nach': 'neokortex',
            'dicke': 0.4,
            'farbe': '#ce93d8',
            'opacity': 0.7,
            'lebensdauer_ms': 8000,
            'animation': 'wave',
        })

    # --- GENESIS ---

    elif aktion == 'GENESIS_GEBURT':
        events.append({
            'typ': 'STRUKTUR_NEU',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': 'genesis_flash',
            'kategorie': 'genesis',
            'von': 'ALL', 'nach': 'ALL',
            'dicke': 1.0,
            'farbe': '#ffffff',
            'opacity': 1.0,
            'lebensdauer_ms': 3000,
            'animation': 'genesis_burst',
        })

    # --- ALLOSTATIC SHIFT ---

    elif aktion == 'ALLOSTATIC_SHIFT':
        region = kontext.get('staerkste_region', 'amygdala')
        richtung = kontext.get('richtung', 'stress')
        events.append({
            'typ': 'STRUKTUR_UPDATE',
            'timestamp': ts, 'timestamp_unix': ts_unix,
            'faden_id': f'anat_{region}_*',
            'aenderungen': {
                'farbe_shift': +0.05 if richtung == 'stress' else -0.05,
            },
            'animation': 'color_drift',
            'dauer_sekunden': 10,
        })

    # In Buffer schreiben + Regionen-Nutzung tracken
    if events:
        event_buffer_push(egon_id, events)
        for ev in events:
            regs = set()
            von = ev.get('von')
            nach = ev.get('nach')
            if von and von != 'ALL':
                regs.add(von)
            if nach and nach != 'ALL':
                regs.add(nach)
            if regs:
                regionen_nutzung_erhoehen(egon_id, list(regs))

    return events


# ================================================================
# STRUKTUR-SNAPSHOT (das Gehirn beim Laden)
# ================================================================

def baue_struktur_snapshot(egon_id: str) -> dict:
    """Baut den kompletten aktuellen Faden-Zustand aus dem EGON-State.

    Wird NICHT gespeichert — wird bei Bedarf generiert.

    Quellen:
    - Anatomische Grundfaeden: Konstanten + DNA-Modifikatoren + Nutzung
    - Bond-Faeden: bonds.yaml
    - Praegungsfaeden: state.yaml > epigenetik > praegungen
    - Metacognitions-Schleifen: state.yaml > metacognition
    - Lebensfaeden: lebensfaeden.yaml (falls vorhanden)
    """
    faeden = []
    state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}

    # 1. Anatomische Grundfaeden (immer vorhanden)
    neuro = state.get('neuroplastizitaet', {})
    nutzung = neuro.get('regionen_nutzung', {})

    for grund in ANATOMISCHE_GRUNDFAEDEN:
        faden_id = f"anat_{grund['von']}_{grund['nach']}"
        basis_dicke = grund['dicke']
        n_von = nutzung.get(grund['von'], 0)
        n_nach = nutzung.get(grund['nach'], 0)
        n_mittel = (n_von + n_nach) / 2
        # +0.01 pro 10 Nutzungen, max +0.3 Bonus (LTP)
        nutzung_bonus = min(0.3, n_mittel * 0.001)

        faeden.append({
            'faden_id': faden_id,
            'kategorie': 'anatomisch',
            'von': grund['von'], 'nach': grund['nach'],
            'dicke': _clamp(basis_dicke + nutzung_bonus, 0.2, 0.9),
            'farbe': grund['farbe'],
            'opacity': 0.6,
            'permanent': True,
        })

    # DNA-Morphologie anwenden
    mods = dna_morphologie_modifikatoren(egon_id)
    for faden in faeden:
        if faden['faden_id'] in mods:
            bonus = mods[faden['faden_id']].get('dicke_bonus', 0)
            faden['dicke'] = _clamp(faden['dicke'] + bonus, 0.1, 1.0)

    # 2. Bond-Faeden (aus bonds.yaml)
    try:
        bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml') or {}
        bonds = bonds_data.get('bonds', [])
        for bond in bonds:
            if not isinstance(bond, dict):
                continue
            score = bond.get('score', 0)
            staerke = score / 100.0 if score > 1 else score
            if staerke < 0.03:
                continue
            partner_id = bond.get('id', bond.get('partner_id', 'unbekannt'))
            bond_typ = bond.get('bond_typ', 'bekannt')
            faeden.append({
                'faden_id': f'bond_{partner_id}',
                'kategorie': 'bond',
                'von': 'amygdala', 'nach': 'praefrontal',
                'dicke': _clamp(staerke * 0.8, 0.05, 0.8),
                'farbe': BOND_FARBEN.get(bond_typ, BOND_FARBEN['bekannt']),
                'opacity': _clamp(0.3 + staerke * 0.7, 0.1, 0.9),
                'permanent': True,
                'meta': {
                    'partner': partner_id,
                    'bond_typ': bond_typ,
                    'bond_staerke': round(staerke, 3),
                    'hat_narbe': bond.get('hat_narbe', False),
                },
            })
    except Exception:
        pass

    # 3. Praegungsfaeden (aus epigenetik)
    epi = state.get('epigenetik', {})
    praegungen = epi.get('praegungen', [])
    for i, praeg in enumerate(praegungen):
        if not isinstance(praeg, dict):
            continue
        status = praeg.get('status', 'geerbt')
        staerke = praeg.get('staerke', 0.3)
        if status == 'ueberwunden' and staerke < 0.01:
            continue
        rendering = PRAEGUNG_STATUS_RENDERING.get(status, PRAEGUNG_STATUS_RENDERING['geerbt'])
        text = praeg.get('text', f'praegung_{i}')
        praeg_id = praeg.get('id', text[:16].replace(' ', '_').lower())
        faeden.append({
            'faden_id': f'praeg_{praeg_id}',
            'kategorie': 'praegung',
            'von': 'amygdala', 'nach': 'praefrontal',
            'dicke': rendering['dicke'],
            'farbe': rendering['farbe'],
            'opacity': rendering['opacity'],
            'permanent': True,
            'meta': {
                'text': text,
                'staerke': staerke,
                'status': status,
            },
        })

    # 4. Metacognitions-Schleifen
    meta = state.get('metacognition', {})
    if meta.get('aktiv', False):
        stufe = meta.get('stufe', 'monitoring')
        faeden.append({
            'faden_id': 'meta_loop_1',
            'kategorie': 'metacognition',
            'von': 'praefrontal', 'nach': 'praefrontal',
            'dicke': 0.15 if stufe == 'monitoring' else 0.25,
            'farbe': '#e1bee7',
            'opacity': 0.5,
            'permanent': True,
        })
        if stufe == 'regulation':
            faeden.append({
                'faden_id': 'meta_loop_2',
                'kategorie': 'metacognition',
                'von': 'praefrontal', 'nach': 'praefrontal',
                'dicke': 0.20,
                'farbe': '#ce93d8',
                'opacity': 0.4,
                'permanent': True,
            })

    # 5. Lebensfaeden (aus lebensfaeden.yaml falls vorhanden)
    try:
        lf_data = read_yaml_organ(egon_id, 'memory', 'lebensfaeden.yaml')
        if lf_data:
            faeden_liste = lf_data.get('faeden', lf_data.get('lebensfaeden', []))
            for faden in faeden_liste:
                if not isinstance(faden, dict):
                    continue
                status = faden.get('status', 'keimend')
                if status == 'abgeschlossen':
                    alter = faden.get('alter_zyklen', 0)
                    if alter > 4:
                        continue
                faden_id = faden.get('id', faden.get('name', 'x')[:16])
                faeden.append({
                    'faden_id': f'leben_{faden_id}',
                    'kategorie': 'lebensfaden',
                    'von': 'praefrontal', 'nach': 'hippocampus',
                    'dicke': _faden_dicke(faden),
                    'farbe': LEBENSFADEN_FARBEN.get(status, '#9e9e9e'),
                    'opacity': _faden_opacity(faden),
                    'permanent': True,
                    'meta': {
                        'faden_name': faden.get('name', ''),
                        'status': status,
                    },
                })
    except Exception:
        pass

    # Statistik
    kat_counts = defaultdict(int)
    for f in faeden:
        kat_counts[f.get('kategorie', 'unbekannt')] += 1

    zyklus = state.get('_zyklus', state.get('zyklus', 0))

    return {
        'typ': 'STRUKTUR_SNAPSHOT',
        'timestamp': _now_iso(),
        'egon_id': egon_id,
        'alter_zyklen': zyklus,
        'faeden': faeden,
        'statistik': {
            'anatomisch': kat_counts.get('anatomisch', 0),
            'bonds': kat_counts.get('bond', 0),
            'lebensfaeden': kat_counts.get('lebensfaden', 0),
            'praegungen': kat_counts.get('praegung', 0),
            'metacognition': kat_counts.get('metacognition', 0),
            'total': len(faeden),
        },
    }


# ================================================================
# DNA-ABHAENGIGE GEHIRN-MORPHOLOGIE
# ================================================================

def dna_morphologie_modifikatoren(egon_id: str) -> dict:
    """DNA beeinflusst welche anatomischen Verbindungen von Anfang an
    DICKER sind. Wie bei Menschen: Manche haben staerkere emotionale
    Schaltkreise, andere staerkere kognitive.
    """
    mods = {}
    try:
        state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}
        drives = state.get('drives', {})
    except Exception:
        return mods

    seeking = drives.get('SEEKING', 0.5)
    rage = drives.get('RAGE', 0.5)
    care = drives.get('CARE', 0.5)
    fear = drives.get('FEAR', 0.5)
    panic = drives.get('PANIC', 0.5)
    play = drives.get('PLAY', 0.5)
    lust = drives.get('LUST', 0.5)

    # SEEKING-dominant: Thalamus→Praefrontal (Neugier = mehr sensorische Info)
    if seeking > 0.65:
        mods['anat_thalamus_praefrontal'] = {'dicke_bonus': +0.15}
    # RAGE-dominant: Amygdala→Hypothalamus (Wut = schnellerer Koerper-Response)
    if rage > 0.60:
        mods['anat_amygdala_hypothalamus'] = {'dicke_bonus': +0.12}
        mods['anat_amygdala_praefrontal'] = {'dicke_bonus': -0.05}
    # CARE-dominant: Insula→Praefrontal (Empathie = mehr Koerpergefuehl)
    if care > 0.65:
        mods['anat_insula_praefrontal'] = {'dicke_bonus': +0.12}
    # FEAR-dominant: Hippocampus→Amygdala (Gefahren-Gedaechtnis)
    if fear > 0.55:
        mods['anat_hippocampus_amygdala'] = {'dicke_bonus': +0.10}
    # PANIC-dominant: Amygdala→Insula (Trennungsangst = intensiveres Koerpergefuehl)
    if panic > 0.55:
        mods['anat_amygdala_insula'] = {'dicke_bonus': +0.10}
    # PLAY-dominant: Cerebellum→Neokortex (Mustererkennung)
    if play > 0.60:
        mods['anat_cerebellum_neokortex'] = {'dicke_bonus': +0.10}
    # LUST-dominant: Hypothalamus→Hirnstamm (Koerperbezug)
    if lust > 0.55:
        mods['anat_hypothalamus_hirnstamm'] = {'dicke_bonus': +0.08}

    return mods


# ================================================================
# SYNAPTISCHES PRUNING (Zyklusende)
# ================================================================

def synaptisches_pruning(egon_id: str) -> list:
    """Laeuft am Zyklusende, NACH Konsolidierung.

    Entfernt oder schwaecht ungenutzte strukturelle Faeden.
    Staerkt haeufig genutzte (LTP).

    Returns: Liste von Pruning-Events
    """
    # 1. Flush in-memory Zaehler in state.yaml
    regionen_nutzung_flush(egon_id)

    events = []
    state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}
    neuro = state.get('neuroplastizitaet', {})
    nutzung = neuro.get('regionen_nutzung', {})
    pruning_stats = neuro.get('pruning', {})

    entfernte = pruning_stats.get('entfernte_faeden_gesamt', 0)
    gestaerkte = pruning_stats.get('gestaerkte_faeden_gesamt', 0)
    ts = _now_iso()
    ts_unix = time.time()

    # 2. Anatomische Faeden: LTP/LTD basierend auf Nutzung
    for grund in ANATOMISCHE_GRUNDFAEDEN:
        faden_id = f"anat_{grund['von']}_{grund['nach']}"
        n_von = nutzung.get(grund['von'], 0)
        n_nach = nutzung.get(grund['nach'], 0)
        n_mittel = (n_von + n_nach) / 2

        if n_mittel > 20:
            # LTP: Viel genutzt → dicker
            delta = min(0.15, (n_mittel - 20) * 0.005)
            events.append({
                'typ': 'STRUKTUR_UPDATE',
                'timestamp': ts, 'timestamp_unix': ts_unix,
                'faden_id': faden_id,
                'aenderungen': {'dicke_delta': +delta},
                'animation': 'none',
            })
            gestaerkte += 1
        elif n_mittel < 5:
            # LTD: Kaum genutzt → duenner (nie unter 0.2)
            events.append({
                'typ': 'STRUKTUR_UPDATE',
                'timestamp': ts, 'timestamp_unix': ts_unix,
                'faden_id': faden_id,
                'aenderungen': {'dicke_delta': -0.02},
                'animation': 'none',
            })

    # 3. Bond-Faeden: Schwache Bonds → verblassen
    try:
        bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml') or {}
        bonds = bonds_data.get('bonds', [])
        for bond in bonds:
            if not isinstance(bond, dict):
                continue
            score = bond.get('score', 50)
            staerke = score / 100.0 if score > 1 else score
            if staerke < 0.10:
                partner_id = bond.get('id', bond.get('partner_id', ''))
                if partner_id:
                    events.append({
                        'typ': 'STRUKTUR_FADE',
                        'timestamp': ts, 'timestamp_unix': ts_unix,
                        'faden_id': f'bond_{partner_id}',
                        'ziel_opacity': 0.03,
                        'ziel_dicke': 0.03,
                        'dauer_sekunden': 30,
                        'animation': 'slow_fade',
                    })
                    entfernte += 1
    except Exception:
        pass

    # 4. MAX_DYNAMISCHE_FAEDEN Enforcement (Patch 16)
    # Zaehle dynamische Faeden und pruene schwache wenn Limit ueberschritten
    snapshot = baue_struktur_snapshot(egon_id)
    statistik = snapshot.get('statistik', {})
    dynamische_total = (
        statistik.get('bonds_aktiv', 0)
        + statistik.get('lebensfaeden_aktiv', 0)
        + statistik.get('praegungen_sichtbar', 0)
        + statistik.get('metacognition_loops', 0)
    )

    if dynamische_total > MAX_DYNAMISCHE_FAEDEN:
        ueberschuss = dynamische_total - MAX_DYNAMISCHE_FAEDEN
        print(f'[neuroplastizitaet] {egon_id}: {dynamische_total} dynamische Faeden '
              f'> {MAX_DYNAMISCHE_FAEDEN} — Pruning {ueberschuss} schwache')

        # Pruning-Prioritaet (schwachste zuerst):
        # 1. Bond-Faeden mit staerke < 0.15
        # 2. Praegungen mit opacity < 0.05
        # 3. Abgeschlossene Lebensfaeden
        pruning_count = 0

        # 1. Schwache Bonds entfernen
        try:
            bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml') or {}
            bonds = bonds_data.get('bonds', [])
            schwache_bonds = sorted(
                [b for b in bonds if isinstance(b, dict) and b.get('score', 0) < 15],
                key=lambda b: b.get('score', 0),
            )
            for bond in schwache_bonds:
                if pruning_count >= ueberschuss:
                    break
                bid = bond.get('id', '')
                if bid and bid != 'OWNER_CURRENT':
                    events.append({
                        'typ': 'STRUKTUR_ENTFERNT',
                        'timestamp': ts, 'timestamp_unix': ts_unix,
                        'faden_id': f'bond_{bid}',
                        'grund': 'max_faeden_pruning',
                        'animation': 'dissolve',
                    })
                    pruning_count += 1
                    entfernte += 1
        except Exception:
            pass

        # 2. Schwache Praegungen entfernen
        if pruning_count < ueberschuss:
            try:
                praeg_data = read_yaml_organ(egon_id, 'core', 'epigenetik.yaml') or {}
                praegungen = praeg_data.get('praegungen', [])
                schwache = [p for p in praegungen if p.get('staerke', 0) < 0.05]
                for p in schwache:
                    if pruning_count >= ueberschuss:
                        break
                    events.append({
                        'typ': 'STRUKTUR_ENTFERNT',
                        'timestamp': ts, 'timestamp_unix': ts_unix,
                        'faden_id': f'praeg_{p.get("typ", "?")}',
                        'grund': 'max_faeden_pruning',
                        'animation': 'dissolve',
                    })
                    pruning_count += 1
                    entfernte += 1
            except Exception:
                pass

    # 5. Pruning-Statistik speichern
    from datetime import date
    neuro['pruning'] = {
        'letztes_pruning': str(date.today()),
        'entfernte_faeden_gesamt': entfernte,
        'gestaerkte_faeden_gesamt': gestaerkte,
    }

    # 6. Faden-Statistik aktualisieren
    neuro['faden_statistik'] = statistik

    state['neuroplastizitaet'] = neuro
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    if events:
        event_buffer_push(egon_id, events)

    return events


# ================================================================
# STATE-INITIALISIERUNG
# ================================================================

def initialisiere_neuroplastizitaet(state: dict) -> dict:
    """Fuegt neuroplastizitaet-Block zu state hinzu (falls fehlend)."""
    if 'neuroplastizitaet' not in state:
        state['neuroplastizitaet'] = {
            'faden_statistik': {
                'bonds_aktiv': 0,
                'bonds_narben': 0,
                'lebensfaeden_aktiv': 0,
                'lebensfaeden_abgeschlossen': 0,
                'praegungen_sichtbar': 0,
                'metacognition_loops': 0,
                'total_faeden': 14,
            },
            'pruning': {
                'letztes_pruning': None,
                'entfernte_faeden_gesamt': 0,
                'gestaerkte_faeden_gesamt': 0,
            },
            'regionen_nutzung': {r: 0 for r in ALLE_REGIONEN},
        }
    return state
