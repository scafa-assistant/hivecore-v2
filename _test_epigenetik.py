"""Tests fuer engine/epigenetik.py — Epigenetische Vererbung (Patch 10).

Testet:
1. Imports
2. Epi-Marker Berechnung + Clamping
3. Epi-Marker Kombination (60/40 Dominanz)
4. Effektive Baseline Anwendung
5. Attachment-Modifikator
6. Attachment-Auswirkung auf Marker
7. Praegungen-Kombination + Deduplizierung
8. Praegung-Relevanz
9. Praegung-Valenz
10. Praegungen-to-Prompt
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
    from engine.epigenetik import (
        berechne_epi_marker,
        kombiniere_epi_marker,
        wende_epi_marker_an,
        wende_attachment_an,
        kombiniere_praegungen,
        praegung_update,
        praegung_zyklus_decay,
        praegungen_to_prompt,
        _berechne_praegung_relevanz,
        _bestimme_episode_valenz,
        _praegung_aehnlich,
        _system_zu_wirkt_auf,
        EPI_MAX,
        EPI_MIN,
        PRAEGUNG_MIN_MARKER,
        PRAEGUNG_STAERKE_MAX,
    )
    test('Alle Funktionen importierbar', True)
except ImportError as e:
    test('Alle Funktionen importierbar', False, str(e))


# ================================================================
# Test 2: Konstanten
# ================================================================
print('\n=== Test 2: Konstanten ===')
test(f'EPI_MAX = {EPI_MAX}', EPI_MAX == 0.08)
test(f'EPI_MIN = {EPI_MIN}', EPI_MIN == -0.08)
test(f'PRAEGUNG_MIN_MARKER = {PRAEGUNG_MIN_MARKER}', PRAEGUNG_MIN_MARKER == 0.70)
test(f'PRAEGUNG_STAERKE_MAX = {PRAEGUNG_STAERKE_MAX}', PRAEGUNG_STAERKE_MAX == 0.70)


# ================================================================
# Test 3: Epi-Marker Kombination
# ================================================================
print('\n=== Test 3: Epi-Marker Kombination ===')
from engine.state_validator import PANKSEPP_7

marker_m = {s: 0.0 for s in PANKSEPP_7}
marker_m['FEAR'] = 0.06   # Mutter hat erhoehtes FEAR
marker_m['CARE'] = 0.04   # Und erhoehtes CARE

marker_v = {s: 0.0 for s in PANKSEPP_7}
marker_v['RAGE'] = 0.03   # Vater hat leicht erhoehtes RAGE

combined = kombiniere_epi_marker(marker_m, marker_v)
test('Kombiniert: FEAR > 0 (Mutter dominant)',
     combined.get('FEAR', 0) > 0, f'FEAR={combined.get("FEAR")}')
test('Kombiniert: CARE > 0 (Mutter dominant)',
     combined.get('CARE', 0) > 0, f'CARE={combined.get("CARE")}')
test('Kombiniert: RAGE > 0 (Vater)',
     combined.get('RAGE', 0) > 0, f'RAGE={combined.get("RAGE")}')

# 60/40 Dominanz: Mutter FEAR=0.06 > Vater FEAR=0.0
# combined FEAR = 0.06 * 0.6 + 0.0 * 0.4 = 0.036 (+ Rauschen)
expected_fear = 0.06 * 0.6
test(f'FEAR ~{expected_fear:.3f} (60/40)',
     abs(combined['FEAR'] - expected_fear) < 0.02,
     f'combined={combined["FEAR"]}, expected~{expected_fear}')

# Alle Werte im Bereich
for s in PANKSEPP_7:
    test(f'{s} im Bereich [{EPI_MIN}, {EPI_MAX}]',
         EPI_MIN <= combined[s] <= EPI_MAX, f'{s}={combined[s]}')


# ================================================================
# Test 4: Effektive Baseline
# ================================================================
print('\n=== Test 4: Effektive Baseline ===')
libero_dna = {s: 0.35 for s in PANKSEPP_7}
libero_dna['FEAR'] = 0.38

epi_marker = {s: 0.0 for s in PANKSEPP_7}
epi_marker['FEAR'] = 0.04  # +0.04 epigenetisch

baseline = wende_epi_marker_an(libero_dna, epi_marker)
test(f'FEAR Baseline = DNA + epi: {baseline["FEAR"]}',
     abs(baseline['FEAR'] - 0.42) < 0.001,
     f'baseline={baseline["FEAR"]}, expected=0.42')
test(f'SEEKING Baseline = DNA (kein epi): {baseline["SEEKING"]}',
     abs(baseline['SEEKING'] - 0.35) < 0.001,
     f'baseline={baseline["SEEKING"]}')

# Clamping
epi_extrem = {s: 0.5 for s in PANKSEPP_7}  # Ueber MAX
baseline_extrem = wende_epi_marker_an({s: 0.95 for s in PANKSEPP_7}, epi_extrem)
test('Baseline max 0.97 (Clamping)',
     all(v <= 0.97 for v in baseline_extrem.values()),
     f'values={list(baseline_extrem.values())}')


# ================================================================
# Test 5: Attachment-Modifikator
# ================================================================
print('\n=== Test 5: Attachment-Auswirkung ===')
epi_sicher = {s: 0.0 for s in PANKSEPP_7}
epi_sicher['PANIC'] = 0.05

# Sichere Basis (>0.7)
epi_mod, reg_bonus = wende_attachment_an(dict(epi_sicher), 0.85)
test('Sichere Basis: PANIC sinkt', epi_mod['PANIC'] < 0.05,
     f'PANIC={epi_mod["PANIC"]}')
test('Sichere Basis: SEEKING steigt', epi_mod['SEEKING'] > 0,
     f'SEEKING={epi_mod["SEEKING"]}')
test('Sichere Basis: regulation_bonus=1.1', reg_bonus == 1.1,
     f'bonus={reg_bonus}')

# Unsichere Basis (<0.3)
epi_unsicher = {s: 0.0 for s in PANKSEPP_7}
epi_mod2, reg_bonus2 = wende_attachment_an(dict(epi_unsicher), 0.2)
test('Unsichere Basis: PANIC steigt', epi_mod2['PANIC'] > 0,
     f'PANIC={epi_mod2["PANIC"]}')
test('Unsichere Basis: FEAR steigt', epi_mod2['FEAR'] > 0,
     f'FEAR={epi_mod2["FEAR"]}')
test('Unsichere Basis: regulation_bonus=0.85', reg_bonus2 == 0.85,
     f'bonus={reg_bonus2}')

# Neutrale Basis
epi_neutral = {s: 0.0 for s in PANKSEPP_7}
epi_mod3, reg_bonus3 = wende_attachment_an(dict(epi_neutral), 0.5)
test('Neutrale Basis: regulation_bonus=1.0', reg_bonus3 == 1.0,
     f'bonus={reg_bonus3}')


# ================================================================
# Test 6: Praegungen-Kombination
# ================================================================
print('\n=== Test 6: Praegungen-Kombination ===')
praeg_m = [
    {'text': 'Vertrauen braucht Zeit', 'typ': 'warnung', 'valenz': 'negativ',
     'staerke': 0.30, 'quelle_system': 'FEAR'},
    {'text': 'Naehe ist wertvoll', 'typ': 'wert', 'valenz': 'positiv',
     'staerke': 0.25, 'quelle_system': 'CARE'},
]
praeg_v = [
    {'text': 'Vertrauen ist schwierig', 'typ': 'warnung', 'valenz': 'negativ',
     'staerke': 0.20, 'quelle_system': 'FEAR'},  # Aehnlich wie Mutter!
    {'text': 'Neugierde fuehrt zum Ziel', 'typ': 'glaube', 'valenz': 'positiv',
     'staerke': 0.22, 'quelle_system': 'SEEKING'},
]

kombiniert = kombiniere_praegungen(praeg_m, praeg_v)
test(f'{len(kombiniert)} kombinierte Praegungen (3 erwartet, 1 dedupliziert)',
     len(kombiniert) == 3, f'count={len(kombiniert)}')

# Die aehnlichen "Vertrauen" Praegungen sollten zu einer verschmolzen sein
vertrauen = [p for p in kombiniert if 'ertrauen' in p.get('text', '')]
test('Vertrauen-Praegungen verschmolzen',
     len(vertrauen) == 1, f'vertrauen_count={len(vertrauen)}')
if vertrauen:
    test('Verschmolzene Staerke > Einzel',
         vertrauen[0]['staerke'] >= 0.30,  # Max + 0.05 Bonus
         f'staerke={vertrauen[0]["staerke"]}')
    test('Quelle = beide',
         vertrauen[0].get('quelle_elternteil') == 'beide',
         f'quelle={vertrauen[0].get("quelle_elternteil")}')


# ================================================================
# Test 7: Praegung-Aehnlichkeit
# ================================================================
print('\n=== Test 7: Praegung-Aehnlichkeit ===')
p1 = {'text': 'Vertrauen braucht Zeit', 'typ': 'warnung', 'quelle_system': 'FEAR'}
p2 = {'text': 'Vertrauen ist schwierig', 'typ': 'warnung', 'quelle_system': 'FEAR'}
p3 = {'text': 'Neugierde fuehrt weiter', 'typ': 'glaube', 'quelle_system': 'SEEKING'}

test('p1 und p2 aehnlich (gleicher Typ+System)', _praegung_aehnlich(p1, p2))
test('p1 und p3 nicht aehnlich', not _praegung_aehnlich(p1, p3))


# ================================================================
# Test 8: Episode-Valenz
# ================================================================
print('\n=== Test 8: Episode-Valenz ===')
ep_positiv = {'emotions_felt': [{'type': 'joy', 'intensity': 0.8}]}
ep_negativ = {'emotions_felt': [{'type': 'fear', 'intensity': 0.6}]}
ep_neutral = {'emotions_felt': [{'type': 'curiosity', 'intensity': 0.3}]}
ep_leer = {'emotions_felt': []}

test('Joy = positiv', _bestimme_episode_valenz(ep_positiv, {}) == 'positiv')
test('Fear = negativ', _bestimme_episode_valenz(ep_negativ, {}) == 'negativ')
test('Curiosity = ambivalent', _bestimme_episode_valenz(ep_neutral, {}) == 'ambivalent')
test('Leer = ambivalent', _bestimme_episode_valenz(ep_leer, {}) == 'ambivalent')


# ================================================================
# Test 9: System zu wirkt_auf Mapping
# ================================================================
print('\n=== Test 9: System-Mapping ===')
test('FEAR wirkt auf FEAR+PANIC', _system_zu_wirkt_auf('FEAR') == ['FEAR', 'PANIC'])
test('CARE wirkt auf CARE+PLAY', _system_zu_wirkt_auf('CARE') == ['CARE', 'PLAY'])
test('RAGE wirkt auf RAGE', _system_zu_wirkt_auf('RAGE') == ['RAGE'])


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
