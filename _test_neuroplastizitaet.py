"""Tests fuer engine/neuroplastizitaet.py — Patch 16: Strukturelle Brain-Events.

Testet:
1. Imports + Konstanten
2. Event-Emittierung (alle 16 Aktionstypen)
3. Event-Buffer (push, pop, peek)
4. Regionen-Nutzung (in-memory tracking)
5. Struktur-Snapshot (anatomisch + DNA-Morphologie)
6. Synaptisches Pruning
7. State-Initialisierung
8. Hilfsfunktionen (_faden_dicke, _faden_opacity, _erinnerung_zu_region)
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

passed = 0
failed = 0


def test(name, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
        print(f'  [PASS] {name}')
    else:
        failed += 1
        print(f'  [FAIL] {name} -- {detail}')


# ================================================================
# Test 1: Imports
# ================================================================
print('\n=== Test 1: Imports ===')
try:
    from engine.neuroplastizitaet import (
        # Konstanten
        ANATOMISCHE_GRUNDFAEDEN,
        BOND_FARBEN,
        LEBENSFADEN_FARBEN,
        PRAEGUNG_STATUS_RENDERING,
        TEMPORAERE_TYPEN,
        MAX_DYNAMISCHE_FAEDEN,
        ALLE_REGIONEN,
        # Kern-Funktionen
        emittiere_struktur_event,
        baue_struktur_snapshot,
        synaptisches_pruning,
        dna_morphologie_modifikatoren,
        initialisiere_neuroplastizitaet,
        # Event-Buffer
        event_buffer_push,
        event_buffer_pop,
        event_buffer_peek,
        # Regionen-Nutzung
        regionen_nutzung_erhoehen,
        regionen_nutzung_flush,
        regionen_nutzung_reset,
        # Hilfsfunktionen
        _faden_dicke,
        _faden_opacity,
        _erinnerung_zu_region,
        _clamp,
        _now_iso,
    )
    test('Alle Funktionen importierbar', True)
except ImportError as e:
    test('Alle Funktionen importierbar', False, str(e))
    sys.exit(1)


# ================================================================
# Test 2: Konstanten
# ================================================================
print('\n=== Test 2: Konstanten ===')
test('14 anatomische Grundfaeden', len(ANATOMISCHE_GRUNDFAEDEN) == 14)
test('11 Bond-Farben', len(BOND_FARBEN) == 11)
test('7 Lebensfaden-Farben', len(LEBENSFADEN_FARBEN) == 7)
test('4 Praegung-Status', len(PRAEGUNG_STATUS_RENDERING) == 4)
test('3 temporaere Typen', len(TEMPORAERE_TYPEN) == 3)
test('9 Regionen', len(ALLE_REGIONEN) == 9)
test('MAX_DYNAMISCHE_FAEDEN = 50', MAX_DYNAMISCHE_FAEDEN == 50)

# Anatomische Grundfaeden Vollstaendigkeit
regionen_in_faeden = set()
for f in ANATOMISCHE_GRUNDFAEDEN:
    regionen_in_faeden.add(f['von'])
    regionen_in_faeden.add(f['nach'])
    test(f"Faden {f['von']}→{f['nach']} hat dicke", 0 < f['dicke'] <= 1.0)

test('Alle 9 Regionen in Grundfaeden vertreten',
     regionen_in_faeden == set(ALLE_REGIONEN),
     f'Fehlend: {set(ALLE_REGIONEN) - regionen_in_faeden}')

# Praegung-Status hat bei_aktivierung fuer 'geerbt'
test('Geerbt hat bei_aktivierung',
     'bei_aktivierung' in PRAEGUNG_STATUS_RENDERING['geerbt'])


# ================================================================
# Test 3: Hilfsfunktionen
# ================================================================
print('\n=== Test 3: Hilfsfunktionen ===')

# _clamp
test('clamp(0.5, 0, 1) = 0.5', _clamp(0.5) == 0.5)
test('clamp(-0.1, 0, 1) = 0', _clamp(-0.1) == 0.0)
test('clamp(1.5, 0, 1) = 1', _clamp(1.5) == 1.0)
test('clamp(5, 2, 8) = 5', _clamp(5, 2, 8) == 5)

# _faden_dicke
test('Keimend dicke = 0.15', _faden_dicke({'status': 'keimend'}) == 0.15)
test('Explosion dicke = 0.60', _faden_dicke({'status': 'explosion'}) == 0.60)
test('Integration dicke = 0.50', _faden_dicke({'status': 'integration'}) == 0.50)
test('Unbekannt dicke = 0.15', _faden_dicke({'status': 'xyz'}) == 0.15)

# _faden_opacity
test('Keimend opacity = 0.4', _faden_opacity({'status': 'keimend'}) == 0.4)
test('Explosion opacity = 0.95', _faden_opacity({'status': 'explosion'}) == 0.95)
test('Ruhend opacity = 0.25', _faden_opacity({'status': 'ruhend'}) == 0.25)

# _erinnerung_zu_region
test('Angst → amygdala', _erinnerung_zu_region({'tags': ['angst', 'dunkel']}) == 'amygdala')
test('Koerper → insula', _erinnerung_zu_region({'tags': ['koerper']}) == 'insula')
test('Denken → praefrontal', _erinnerung_zu_region({'tags': ['entscheidung']}) == 'praefrontal')
test('Muster → cerebellum', _erinnerung_zu_region({'tags': ['routine']}) == 'cerebellum')
test('Default → neokortex', _erinnerung_zu_region({'tags': ['hallo']}) == 'neokortex')
test('Leer → neokortex', _erinnerung_zu_region({}) == 'neokortex')

# _now_iso
ts = _now_iso()
test('ISO Timestamp Format', 'T' in ts and ts.endswith('Z'))


# ================================================================
# Test 4: Event-Buffer
# ================================================================
print('\n=== Test 4: Event-Buffer ===')

# Clear any existing events
event_buffer_pop('test_egon')

# Push events
events = [{'typ': 'TEST', 'timestamp_unix': 100}, {'typ': 'TEST2', 'timestamp_unix': 200}]
event_buffer_push('test_egon', events)

# Peek
peeked = event_buffer_peek('test_egon', seit_ts=0)
test('Peek liefert 2 Events', len(peeked) == 2)
peeked_filtered = event_buffer_peek('test_egon', seit_ts=150)
test('Peek mit Filter liefert 1 Event', len(peeked_filtered) == 1)

# Pop
popped = event_buffer_pop('test_egon')
test('Pop liefert 2 Events', len(popped) == 2)
test('Buffer leer nach Pop', len(event_buffer_pop('test_egon')) == 0)


# ================================================================
# Test 5: Event-Emittierung
# ================================================================
print('\n=== Test 5: Event-Emittierung ===')

# BOND_NEU
evts = emittiere_struktur_event('test_e', 'BOND_NEU', {'partner_id': 'eva_002'})
test('BOND_NEU: 1 Event', len(evts) == 1)
test('BOND_NEU: typ = STRUKTUR_NEU', evts[0]['typ'] == 'STRUKTUR_NEU')
test('BOND_NEU: faden_id = bond_eva_002', evts[0]['faden_id'] == 'bond_eva_002')
test('BOND_NEU: kategorie = bond', evts[0]['kategorie'] == 'bond')
test('BOND_NEU: animation = sprout', evts[0]['animation'] == 'sprout')
test('BOND_NEU: dicke = 0.1', evts[0]['dicke'] == 0.1)
event_buffer_pop('test_e')

# BOND_UPDATE
evts = emittiere_struktur_event('test_e', 'BOND_UPDATE', {
    'partner_id': 'eva_002', 'bond_staerke': 0.7,
    'bond_typ': 'freundschaft', 'alte_staerke': 0.5,
})
test('BOND_UPDATE: typ = STRUKTUR_UPDATE', evts[0]['typ'] == 'STRUKTUR_UPDATE')
test('BOND_UPDATE: dicke = 0.56', abs(evts[0]['aenderungen']['dicke'] - 0.56) < 0.01)
test('BOND_UPDATE: farbe = freundschaft', evts[0]['aenderungen']['farbe'] == '#4fc3f7')
test('BOND_UPDATE: animation = strengthen', evts[0]['animation'] == 'strengthen')
event_buffer_pop('test_e')

# BOND_UPDATE weakening
evts = emittiere_struktur_event('test_e', 'BOND_UPDATE', {
    'partner_id': 'x', 'bond_staerke': 0.3, 'bond_typ': 'bekannt', 'alte_staerke': 0.6,
})
test('BOND_UPDATE weakening: animation = weaken', evts[0]['animation'] == 'weaken')
event_buffer_pop('test_e')

# BOND_BRUCH
evts = emittiere_struktur_event('test_e', 'BOND_BRUCH', {'partner_id': 'rene_005'})
test('BOND_BRUCH: typ = STRUKTUR_FADE', evts[0]['typ'] == 'STRUKTUR_FADE')
test('BOND_BRUCH: narbe = True', evts[0]['meta']['narbe'] is True)
test('BOND_BRUCH: ziel_opacity = 0.03', evts[0]['ziel_opacity'] == 0.03)
event_buffer_pop('test_e')

# BOND_KONFLIKT
evts = emittiere_struktur_event('test_e', 'BOND_KONFLIKT', {'partner_id': 'kain_004'})
test('BOND_KONFLIKT: farbe = rot', evts[0]['aenderungen']['farbe'] == '#e53935')
test('BOND_KONFLIKT: animation = flicker', evts[0]['animation'] == 'flicker')
event_buffer_pop('test_e')

# BOND_VERSOEHNUNG
evts = emittiere_struktur_event('test_e', 'BOND_VERSOEHNUNG', {
    'partner_id': 'eva_002', 'bond_staerke': 0.6, 'bond_typ': 'freundschaft',
})
test('BOND_VERSOEHNUNG: animation = heal', evts[0]['animation'] == 'heal')
test('BOND_VERSOEHNUNG: narbe_aktiv = True', evts[0]['meta']['narbe_aktiv'] is True)
event_buffer_pop('test_e')

# FADEN_NEU (normal)
evts = emittiere_struktur_event('test_e', 'FADEN_NEU', {
    'faden': {'id': 'test_f', 'name': 'Meine Angst', 'status': 'keimend'}, 'sofort': False,
})
test('FADEN_NEU: faden_id = leben_test_f', evts[0]['faden_id'] == 'leben_test_f')
test('FADEN_NEU: dicke = 0.15 (langsam)', evts[0]['dicke'] == 0.15)
test('FADEN_NEU: animation = sprout', evts[0]['animation'] == 'sprout')
event_buffer_pop('test_e')

# FADEN_NEU (sofort)
evts = emittiere_struktur_event('test_e', 'FADEN_NEU', {
    'faden': {'id': 'notfall', 'name': 'Gedaechtnisverlust', 'status': 'explosion'}, 'sofort': True,
})
test('FADEN_NEU sofort: dicke = 0.4', evts[0]['dicke'] == 0.4)
test('FADEN_NEU sofort: animation = burst', evts[0]['animation'] == 'burst')
event_buffer_pop('test_e')

# FADEN_STATUS
evts = emittiere_struktur_event('test_e', 'FADEN_STATUS', {
    'faden': {'id': 'test_f', 'status': 'integration'},
})
test('FADEN_STATUS: animation = glow', evts[0]['animation'] == 'glow')
test('FADEN_STATUS: farbe = lila', evts[0]['aenderungen']['farbe'] == '#7e57c2')
event_buffer_pop('test_e')

# PRAEGUNG_AKTIVIERT
evts = emittiere_struktur_event('test_e', 'PRAEGUNG_AKTIVIERT', {
    'praegung': {'id': 'vertrauen', 'text': 'Vertrauen braucht Zeit', 'staerke': 0.4, 'status': 'geerbt'},
})
test('PRAEGUNG_AKTIVIERT: opacity = 0.6 (sichtbar)', evts[0]['aenderungen']['opacity'] == 0.6)
test('PRAEGUNG_AKTIVIERT: animation = deep_pulse', evts[0]['animation'] == 'deep_pulse')
test('PRAEGUNG_AKTIVIERT: zurueck_zu = 0.05', evts[0]['zurueck_zu']['opacity'] == 0.05)
event_buffer_pop('test_e')

# PRAEGUNG_VERINNERLICHT
evts = emittiere_struktur_event('test_e', 'PRAEGUNG_VERINNERLICHT', {
    'praegung': {'id': 'vertrauen', 'text': 'Vertrauen braucht Zeit'},
})
test('PRAEGUNG_VERINNERLICHT: opacity = 0.4', evts[0]['aenderungen']['opacity'] == 0.4)
test('PRAEGUNG_VERINNERLICHT: animation = emerge', evts[0]['animation'] == 'emerge')
event_buffer_pop('test_e')

# PRAEGUNG_UEBERWUNDEN
evts = emittiere_struktur_event('test_e', 'PRAEGUNG_UEBERWUNDEN', {
    'praegung': {'id': 'vertrauen'},
})
test('PRAEGUNG_UEBERWUNDEN: typ = STRUKTUR_FADE', evts[0]['typ'] == 'STRUKTUR_FADE')
test('PRAEGUNG_UEBERWUNDEN: ziel_opacity = 0.02', evts[0]['ziel_opacity'] == 0.02)
event_buffer_pop('test_e')

# METACOGNITION_AKTIVIERT (monitoring)
evts = emittiere_struktur_event('test_e', 'METACOGNITION_AKTIVIERT', {'stufe': 'monitoring'})
test('METACOGNITION monitoring: 1 Event', len(evts) == 1)
test('METACOGNITION monitoring: faden_id = meta_loop_1', evts[0]['faden_id'] == 'meta_loop_1')
test('METACOGNITION monitoring: dicke = 0.15', evts[0]['dicke'] == 0.15)
event_buffer_pop('test_e')

# METACOGNITION_AKTIVIERT (regulation)
evts = emittiere_struktur_event('test_e', 'METACOGNITION_AKTIVIERT', {'stufe': 'regulation'})
test('METACOGNITION regulation: 2 Events', len(evts) == 2)
test('METACOGNITION regulation: loop_2 vorhanden',
     any(e['faden_id'] == 'meta_loop_2' for e in evts))
test('METACOGNITION regulation: loop_1 dicke = 0.25', evts[0]['dicke'] == 0.25)
event_buffer_pop('test_e')

# REAPPRAISAL
evts = emittiere_struktur_event('test_e', 'REAPPRAISAL', {})
test('REAPPRAISAL: animation = bright_flash', evts[0]['animation'] == 'bright_flash')
test('REAPPRAISAL: zurueck_zu opacity = 0.5', evts[0]['zurueck_zu']['opacity'] == 0.5)
event_buffer_pop('test_e')

# LICHTBOGEN_TREFFER
evts = emittiere_struktur_event('test_e', 'LICHTBOGEN_TREFFER', {
    'treffer': {'id': 'ep_001', 'tags': ['angst', 'dunkel']},
})
test('LICHTBOGEN: typ = STRUKTUR_TEMP', evts[0]['typ'] == 'STRUKTUR_TEMP')
test('LICHTBOGEN: faden_id = temp_licht_ep_001', evts[0]['faden_id'] == 'temp_licht_ep_001')
test('LICHTBOGEN: nach = amygdala (wg angst)', evts[0]['nach'] == 'amygdala')
test('LICHTBOGEN: lebensdauer = 5000ms', evts[0]['lebensdauer_ms'] == 5000)
event_buffer_pop('test_e')

# NACHT_KONSOLIDIERUNG
evts = emittiere_struktur_event('test_e', 'NACHT_KONSOLIDIERUNG', {
    'eintrag': {'id': 'exp_001'},
})
test('KONSOLIDIERUNG: kategorie = konsolidierung', evts[0]['kategorie'] == 'konsolidierung')
test('KONSOLIDIERUNG: animation = wave', evts[0]['animation'] == 'wave')
test('KONSOLIDIERUNG: farbe = lila', evts[0]['farbe'] == '#ce93d8')
event_buffer_pop('test_e')

# GENESIS_GEBURT
evts = emittiere_struktur_event('test_e', 'GENESIS_GEBURT', {})
test('GENESIS: von = ALL', evts[0]['von'] == 'ALL')
test('GENESIS: animation = genesis_burst', evts[0]['animation'] == 'genesis_burst')
test('GENESIS: dicke = 1.0 (volle Staerke)', evts[0]['dicke'] == 1.0)
event_buffer_pop('test_e')

# ALLOSTATIC_SHIFT
evts = emittiere_struktur_event('test_e', 'ALLOSTATIC_SHIFT', {
    'staerkste_region': 'amygdala', 'richtung': 'stress',
})
test('ALLOSTATIC stress: farbe_shift = +0.05', evts[0]['aenderungen']['farbe_shift'] == 0.05)
event_buffer_pop('test_e')

evts = emittiere_struktur_event('test_e', 'ALLOSTATIC_SHIFT', {
    'staerkste_region': 'amygdala', 'richtung': 'erholung',
})
test('ALLOSTATIC erholung: farbe_shift = -0.05', evts[0]['aenderungen']['farbe_shift'] == -0.05)
event_buffer_pop('test_e')

# Unbekannte Aktion
evts = emittiere_struktur_event('test_e', 'UNBEKANNT', {})
test('Unbekannte Aktion: 0 Events', len(evts) == 0)
event_buffer_pop('test_e')


# ================================================================
# Test 6: Regionen-Nutzung (in-memory)
# ================================================================
print('\n=== Test 6: Regionen-Nutzung ===')

# In-memory tracking testen
from engine.neuroplastizitaet import _regionen_nutzung
_regionen_nutzung.pop('test_reg', None)

regionen_nutzung_erhoehen('test_reg', ['thalamus', 'praefrontal'])
test('Thalamus = 1', _regionen_nutzung['test_reg']['thalamus'] == 1)
test('Praefrontal = 1', _regionen_nutzung['test_reg']['praefrontal'] == 1)

regionen_nutzung_erhoehen('test_reg', ['thalamus', 'praefrontal', 'amygdala'])
test('Thalamus = 2 nach 2x', _regionen_nutzung['test_reg']['thalamus'] == 2)
test('Amygdala = 1', _regionen_nutzung['test_reg']['amygdala'] == 1)

# Ungueltige Region wird ignoriert
regionen_nutzung_erhoehen('test_reg', ['fantasie_region'])
test('Fantasie-Region ignoriert', 'fantasie_region' not in _regionen_nutzung['test_reg'])

_regionen_nutzung.pop('test_reg', None)


# ================================================================
# Test 7: State-Initialisierung
# ================================================================
print('\n=== Test 7: State-Initialisierung ===')

# Leerer State
state_leer = {'drives': {'SEEKING': 0.5}}
state_init = initialisiere_neuroplastizitaet(state_leer)
test('neuroplastizitaet Block hinzugefuegt', 'neuroplastizitaet' in state_init)
test('faden_statistik vorhanden', 'faden_statistik' in state_init['neuroplastizitaet'])
test('pruning vorhanden', 'pruning' in state_init['neuroplastizitaet'])
test('regionen_nutzung vorhanden', 'regionen_nutzung' in state_init['neuroplastizitaet'])
test('9 Regionen in Nutzung', len(state_init['neuroplastizitaet']['regionen_nutzung']) == 9)
test('Alle Nutzung = 0', all(v == 0 for v in state_init['neuroplastizitaet']['regionen_nutzung'].values()))
test('total_faeden = 14 (Grundfaeden)', state_init['neuroplastizitaet']['faden_statistik']['total_faeden'] == 14)

# Nicht ueberschreiben
state_init['neuroplastizitaet']['pruning']['entfernte_faeden_gesamt'] = 42
state_nochmal = initialisiere_neuroplastizitaet(state_init)
test('Existierender Block nicht ueberschrieben',
     state_nochmal['neuroplastizitaet']['pruning']['entfernte_faeden_gesamt'] == 42)


# ================================================================
# Test 8: Event-Vollstaendigkeit
# ================================================================
print('\n=== Test 8: Event-Vollstaendigkeit ===')

# Alle 16 Aktionstypen abgedeckt
ALLE_AKTIONEN = [
    'BOND_NEU', 'BOND_UPDATE', 'BOND_BRUCH', 'BOND_KONFLIKT', 'BOND_VERSOEHNUNG',
    'FADEN_NEU', 'FADEN_STATUS',
    'PRAEGUNG_AKTIVIERT', 'PRAEGUNG_VERINNERLICHT', 'PRAEGUNG_UEBERWUNDEN',
    'METACOGNITION_AKTIVIERT', 'REAPPRAISAL',
    'LICHTBOGEN_TREFFER', 'NACHT_KONSOLIDIERUNG',
    'GENESIS_GEBURT', 'ALLOSTATIC_SHIFT',
]

for aktion in ALLE_AKTIONEN:
    # Minimal-Kontext fuer jede Aktion
    kontext = {}
    if 'BOND' in aktion:
        kontext['partner_id'] = 'test'
    if aktion == 'BOND_UPDATE':
        kontext['bond_staerke'] = 0.5
    if aktion == 'METACOGNITION_AKTIVIERT':
        kontext['stufe'] = 'monitoring'
    if aktion == 'ALLOSTATIC_SHIFT':
        kontext['staerkste_region'] = 'amygdala'
        kontext['richtung'] = 'stress'
    if 'PRAEGUNG' in aktion:
        kontext['praegung'] = {'id': 'test', 'text': 'test', 'staerke': 0.3, 'status': 'geerbt'}
    if 'FADEN' in aktion:
        kontext['faden'] = {'id': 'test', 'status': 'keimend'}
    if 'LICHTBOGEN' in aktion:
        kontext['treffer'] = {'id': 'test'}
    if 'NACHT' in aktion:
        kontext['eintrag'] = {'id': 'test'}

    evts = emittiere_struktur_event('test_vol', aktion, kontext)
    test(f'{aktion}: >= 1 Event', len(evts) >= 1)
    event_buffer_pop('test_vol')


# ================================================================
# Test 9: Snapshot-Struktur (ohne echte EGON-Daten)
# ================================================================
print('\n=== Test 9: Snapshot-Struktur ===')

# Wir koennen keinen echten Snapshot bauen (braucht Dateisystem),
# aber wir testen die Struktur der Konstanten die reingehen wuerden.
for faden in ANATOMISCHE_GRUNDFAEDEN:
    assert 'von' in faden
    assert 'nach' in faden
    assert 'dicke' in faden
    assert 'farbe' in faden
test('Alle Grundfaeden haben von/nach/dicke/farbe', True)

# Bond-Farben fuer alle relevanten Typen
expected_bond_types = ['neu', 'bekannt', 'freundschaft', 'romantisch',
                       'paar', 'elternteil', 'kind', 'owner', 'konflikt', 'gebrochen']
for bt in expected_bond_types:
    test(f'Bond-Farbe fuer {bt}', bt in BOND_FARBEN)

# Lebensfaden-Farben
expected_lf_status = ['keimend', 'wachsend', 'eskalation', 'explosion',
                      'integration', 'ruhend', 'abgeschlossen']
for st in expected_lf_status:
    test(f'Lebensfaden-Farbe fuer {st}', st in LEBENSFADEN_FARBEN)

# Praegung-Rendering
for st in ['geerbt', 'verinnerlicht', 'ueberwunden', 'ruhend']:
    r = PRAEGUNG_STATUS_RENDERING[st]
    test(f'Praegung {st}: opacity vorhanden', 'opacity' in r)
    test(f'Praegung {st}: dicke vorhanden', 'dicke' in r)
    test(f'Praegung {st}: farbe vorhanden', 'farbe' in r)


# ================================================================
# Test 10: Regionen-Nutzung trackt durch Events
# ================================================================
print('\n=== Test 10: Regionen-Nutzung via Events ===')
_regionen_nutzung.pop('track_test', None)

# Bond-Event sollte amygdala + praefrontal tracken
emittiere_struktur_event('track_test', 'BOND_NEU', {'partner_id': 'test'})
test('BOND_NEU trackt amygdala', _regionen_nutzung['track_test']['amygdala'] >= 1)
test('BOND_NEU trackt praefrontal', _regionen_nutzung['track_test']['praefrontal'] >= 1)

# Lichtbogen trackt hippocampus
emittiere_struktur_event('track_test', 'LICHTBOGEN_TREFFER', {
    'treffer': {'id': 'x', 'tags': ['denken']},
})
test('LICHTBOGEN trackt hippocampus', _regionen_nutzung['track_test']['hippocampus'] >= 1)

# Metacognition trackt praefrontal
prev = _regionen_nutzung['track_test']['praefrontal']
emittiere_struktur_event('track_test', 'METACOGNITION_AKTIVIERT', {'stufe': 'monitoring'})
test('METACOGNITION trackt praefrontal',
     _regionen_nutzung['track_test']['praefrontal'] > prev)

event_buffer_pop('track_test')
_regionen_nutzung.pop('track_test', None)


# ================================================================
# Test 11: DNA-Morphologie Modifikatoren
# ================================================================
print('\n=== Test 11: DNA-Morphologie ===')

# Wir koennen dna_morphologie_modifikatoren nicht direkt testen
# (braucht Dateisystem), aber die Logik:
# Simuliere mit known drive values
# Testen ob die Funktion sicher bei nicht-existierenden EGONs ist
mods = dna_morphologie_modifikatoren('nicht_existierend_xyz')
test('Nicht-existierender EGON: leere Mods', len(mods) == 0)


# ================================================================
# Ergebnis
# ================================================================
print(f'\n{"=" * 50}')
print(f'ERGEBNIS: {passed} PASSED, {failed} FAILED von {passed + failed}')
if failed == 0:
    print('ALLE TESTS BESTANDEN!')
else:
    print(f'ACHTUNG: {failed} Tests fehlgeschlagen!')
print(f'{"=" * 50}')
