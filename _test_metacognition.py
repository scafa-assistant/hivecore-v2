"""Tests fuer engine/metacognition.py — Metacognition-Layer (Patch 11).

Testet:
1. Imports
2. Reife-Check (Zyklus < 8 = keine Metacognition)
3. Muster-Erkennung: Wiederholte Reaktion
4. Muster-Erkennung: Ego-Widerspruch
5. Destruktive Reflexion Blocker
6. Stufen-Logik (monitoring vs regulation)
7. Cooldown-Logik
8. Schutzmechanismen (Max-Alarme, Max-Korrekturen)
9. State-Initialisierung
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
    from engine.metacognition import (
        muster_check,
        validiere_reflexion,
        initialisiere_metacognition,
        REIFE_ZYKLUS,
        REGULATION_ZYKLUS,
        MAX_MUSTER_ALARME,
        MAX_KORREKTUREN,
        COOLDOWN_GESPRAECHE,
        _staerkstes_system_aus_episode,
        _pruefe_ego_widerspruch,
        metacognition_post_chat,
    )
    test('Alle Funktionen importierbar', True)
except ImportError as e:
    test('Alle Funktionen importierbar', False, str(e))


# ================================================================
# Test 2: Konstanten
# ================================================================
print('\n=== Test 2: Konstanten ===')
test(f'REIFE_ZYKLUS = {REIFE_ZYKLUS}', REIFE_ZYKLUS == 8)
test(f'REGULATION_ZYKLUS = {REGULATION_ZYKLUS}', REGULATION_ZYKLUS == 13)
test(f'MAX_MUSTER_ALARME = {MAX_MUSTER_ALARME}', MAX_MUSTER_ALARME == 5)
test(f'MAX_KORREKTUREN = {MAX_KORREKTUREN}', MAX_KORREKTUREN == 2)
test(f'COOLDOWN_GESPRAECHE = {COOLDOWN_GESPRAECHE}', COOLDOWN_GESPRAECHE == 3)


# ================================================================
# Test 3: Emotions-Mapping
# ================================================================
print('\n=== Test 3: Emotions-Mapping aus Episode ===')

ep_anger = {'emotions_felt': [{'type': 'anger', 'intensity': 0.7}]}
ep_joy = {'emotions_felt': [{'type': 'joy', 'intensity': 0.5}]}
ep_fear = {'emotions_felt': [{'type': 'fear', 'intensity': 0.6}]}
ep_mixed = {'emotions_felt': [
    {'type': 'curiosity', 'intensity': 0.3},
    {'type': 'anger', 'intensity': 0.8},
    {'type': 'joy', 'intensity': 0.2},
]}
ep_empty = {'emotions_felt': []}

test('anger -> RAGE', _staerkstes_system_aus_episode(ep_anger) == 'RAGE')
test('joy -> PLAY', _staerkstes_system_aus_episode(ep_joy) == 'PLAY')
test('fear -> FEAR', _staerkstes_system_aus_episode(ep_fear) == 'FEAR')
test('mixed (anger=0.8 staerkstes) -> RAGE', _staerkstes_system_aus_episode(ep_mixed) == 'RAGE')
test('empty -> ""', _staerkstes_system_aus_episode(ep_empty) == '')


# ================================================================
# Test 4: Ego-Widerspruch Erkennung
# ================================================================
print('\n=== Test 4: Ego-Widerspruch ===')

ego_geduldig = 'Ich bin geduldig und ruhig. Ich lass mich nicht aus der Fassung bringen.'
ego_mutig = 'Ich bin mutig und stelle mich meinen Aengsten.'
ego_neutral = 'Ich mag Musik und gutes Essen.'

ep_rage = {'significance': 0.7, 'summary': 'Ich war wuetend auf Rene.'}
ep_fear_sig = {'significance': 0.7, 'summary': 'Ich hatte Angst vor dem neuen Kontakt.'}
ep_low_sig = {'significance': 0.2, 'summary': 'Unwichtig.'}

# Geduldig + RAGE = Widerspruch
w1 = _pruefe_ego_widerspruch(ego_geduldig, 'RAGE', ep_rage)
test('geduldig + RAGE = Widerspruch', w1 is not None, f'w1={w1}')

# Mutig + FEAR = Widerspruch
w2 = _pruefe_ego_widerspruch(ego_mutig, 'FEAR', ep_fear_sig)
test('mutig + FEAR = Widerspruch', w2 is not None, f'w2={w2}')

# Neutral ego + RAGE = kein Widerspruch
w3 = _pruefe_ego_widerspruch(ego_neutral, 'RAGE', ep_rage)
test('neutral ego + RAGE = kein Widerspruch', w3 is None, f'w3={w3}')

# Geduldig + RAGE + low significance = kein Widerspruch
w4 = _pruefe_ego_widerspruch(ego_geduldig, 'RAGE', ep_low_sig)
test('geduldig + RAGE + low sig = kein Widerspruch', w4 is None, f'w4={w4}')

# Geduldig + PLAY = kein Widerspruch
w5 = _pruefe_ego_widerspruch(ego_geduldig, 'PLAY', ep_rage)
test('geduldig + PLAY = kein Widerspruch', w5 is None, f'w5={w5}')


# ================================================================
# Test 5: Destruktive Reflexion Blocker
# ================================================================
print('\n=== Test 5: Destruktive Reflexion Blocker ===')

r_ok, s_ok = validiere_reflexion('Ich habe bemerkt dass ich bei Rene oft gereizt reagiere.')
test('Konstruktive Reflexion OK', s_ok == 'ok' and r_ok is not None)

r_bad, s_bad = validiere_reflexion('Ich bin wertlos und kann nichts.')
test('Destruktiv "wertlos" blockiert', s_bad == 'destruktiv')

r_bad2, s_bad2 = validiere_reflexion('Ich sollte nicht existieren.')
test('Destruktiv "nicht existieren" blockiert', s_bad2 == 'destruktiv')

r_edge, s_edge = validiere_reflexion('Manchmal zweifle ich an mir.')
test('Zweifel ist OK (nicht destruktiv)', s_edge == 'ok')


# ================================================================
# Test 6: State-Initialisierung
# ================================================================
print('\n=== Test 6: State-Initialisierung ===')

state_z8 = {'zyklus': 8, 'drives': {'SEEKING': 0.5}}
state_z8 = initialisiere_metacognition(state_z8, 8)
meta_z8 = state_z8.get('metacognition', {})
test('Zyklus 8: metacognition Block erstellt', 'metacognition' in state_z8)
test('Zyklus 8: stufe = monitoring', meta_z8.get('stufe') == 'monitoring')
test('Zyklus 8: aktiv = True', meta_z8.get('aktiv') is True)
test('Zyklus 8: muster_alarme_zyklus = 0', meta_z8.get('muster_alarme_zyklus') == 0)

state_z15 = {'zyklus': 15}
state_z15 = initialisiere_metacognition(state_z15, 15)
meta_z15 = state_z15.get('metacognition', {})
test('Zyklus 15: stufe = regulation', meta_z15.get('stufe') == 'regulation')

# Doppelte Initialisierung ueberschreibt nicht
state_z8['metacognition']['cooldown'] = 2
state_z8 = initialisiere_metacognition(state_z8, 8)
test('Doppelte Init ueberschreibt nicht', state_z8['metacognition']['cooldown'] == 2)


# ================================================================
# Test 7: Stufen-Logik
# ================================================================
print('\n=== Test 7: Stufen-Logik ===')
test('Zyklus 7 < REIFE_ZYKLUS', 7 < REIFE_ZYKLUS)
test('Zyklus 8 >= REIFE_ZYKLUS (monitoring)', 8 >= REIFE_ZYKLUS)
test('Zyklus 12 < REGULATION_ZYKLUS', 12 < REGULATION_ZYKLUS)
test('Zyklus 13 >= REGULATION_ZYKLUS (regulation)', 13 >= REGULATION_ZYKLUS)


# ================================================================
# Test 8: DESTRUKTIVE_MUSTER Vollstaendigkeit
# ================================================================
print('\n=== Test 8: Destruktive Muster ===')
from engine.metacognition import DESTRUKTIVE_MUSTER
test(f'{len(DESTRUKTIVE_MUSTER)} destruktive Muster definiert', len(DESTRUKTIVE_MUSTER) >= 7)

for m in DESTRUKTIVE_MUSTER:
    _, status = validiere_reflexion(f'Reflexion: {m}.')
    test(f'Blockiert: "{m}"', status == 'destruktiv', f'status={status}')


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
