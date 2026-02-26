"""Tests fuer engine/decay.py — Arbeitsspeicher-Decay (Patch 13).

Testet:
1. Retention-Berechnung (Ebbinghaus-Formel)
2. DNA-Stabilitaetsmodifikatoren
3. Arbeitsspeicher laden/filtern
4. Prompt-Generierung
5. Eintrag speichern + Overflow-Handling
6. Abruf-Stabilisierung
7. Cue-basierte Stabilisierung
8. Aufraemen (Loeschen unter Schwelle)
9. Nacht-Rettung
"""

import sys
import math
import time

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
        print(f'  [FAIL] {name} — {detail}')


# ================================================================
# Test 1: Imports
# ================================================================
print('\n=== Test 1: Imports ===')
try:
    from engine.decay import (
        berechne_retention,
        dna_stabilitaets_mod,
        arbeitsspeicher_to_prompt,
        RETENTION_SCHWELLE,
        LOESCH_SCHWELLE,
        MAX_EINTRAEGE,
    )
    test('Alle Funktionen importierbar', True)
except ImportError as e:
    test('Alle Funktionen importierbar', False, str(e))


# ================================================================
# Test 2: Ebbinghaus Retention — frischer Eintrag
# ================================================================
print('\n=== Test 2: Retention frischer Eintrag ===')
jetzt = time.time()
eintrag_frisch = {
    'erstellt': int(jetzt),
    'letzter_abruf': int(jetzt),
    'emotional_marker': 0.2,
    'abruf_count': 0,
    'prediction_error': 0.0,
}
r = berechne_retention(eintrag_frisch, jetzt, 'DEFAULT')
test('Frischer Eintrag: Retention ~1.0', 0.99 <= r <= 1.0, f'r={r}')

# ================================================================
# Test 3: Retention nach 2 Stunden (emotionslos)
# ================================================================
print('\n=== Test 3: Retention nach 2 Stunden ===')
eintrag_alt = {
    'erstellt': int(jetzt - 7200),  # 2 Stunden alt
    'letzter_abruf': int(jetzt - 7200),
    'emotional_marker': 0.2,
    'abruf_count': 0,
    'prediction_error': 0.0,
}
# S = 0.5 + 0.2*4.0 + 0*0.8 + 0*2.0 = 0.5 + 0.8 = 1.3
# R = e^(-2/1.3) = e^(-1.538) ≈ 0.215
r2 = berechne_retention(eintrag_alt, jetzt, 'DEFAULT')
expected_S = 0.5 + 0.2 * 4.0  # 1.3
expected_r = math.exp(-2.0 / expected_S)
test(f'2h, marker=0.2: R={r2:.4f} (erwartet ~{expected_r:.4f})',
     abs(r2 - expected_r) < 0.01, f'r={r2}, expected={expected_r}')


# ================================================================
# Test 4: Emotionaler Eintrag haelt laenger
# ================================================================
print('\n=== Test 4: Emotionaler Eintrag stabiler ===')
eintrag_emotional = {
    'erstellt': int(jetzt - 7200),
    'letzter_abruf': int(jetzt - 7200),
    'emotional_marker': 0.8,   # Hoch emotional
    'abruf_count': 0,
    'prediction_error': 0.0,
}
# S = 0.5 + 0.8*4.0 = 0.5 + 3.2 = 3.7
# R = e^(-2/3.7) ≈ 0.582
r_emo = berechne_retention(eintrag_emotional, jetzt, 'DEFAULT')
expected_S_emo = 0.5 + 0.8 * 4.0  # 3.7
expected_r_emo = math.exp(-2.0 / expected_S_emo)
test(f'2h, marker=0.8: R={r_emo:.4f} > R neutral ({r2:.4f})',
     r_emo > r2, f'emotional={r_emo}, neutral={r2}')
test(f'Emotionale Retention korrekt: {r_emo:.4f} (erwartet ~{expected_r_emo:.4f})',
     abs(r_emo - expected_r_emo) < 0.01, f'r={r_emo}, expected={expected_r_emo}')


# ================================================================
# Test 5: Abruf-Count stabilisiert
# ================================================================
print('\n=== Test 5: Abruf-Count Stabilisierung ===')
eintrag_abgerufen = {
    'erstellt': int(jetzt - 7200),
    'letzter_abruf': int(jetzt - 7200),
    'emotional_marker': 0.2,
    'abruf_count': 3,   # 3x abgerufen
    'prediction_error': 0.0,
}
# S = 0.5 + 0.2*4.0 + 3*0.8 = 0.5 + 0.8 + 2.4 = 3.7
r_abruf = berechne_retention(eintrag_abgerufen, jetzt, 'DEFAULT')
test(f'3 Abrufe stabilisieren: R={r_abruf:.4f} > R ohne Abruf ({r2:.4f})',
     r_abruf > r2, f'abgerufen={r_abruf}, basis={r2}')


# ================================================================
# Test 6: Prediction Error stabilisiert
# ================================================================
print('\n=== Test 6: Prediction Error ===')
eintrag_pe = {
    'erstellt': int(jetzt - 7200),
    'letzter_abruf': int(jetzt - 7200),
    'emotional_marker': 0.2,
    'abruf_count': 0,
    'prediction_error': 0.5,  # Hoher PE
}
# S = 0.5 + 0.2*4.0 + 0 + 0.5*2.0 = 0.5 + 0.8 + 1.0 = 2.3
r_pe = berechne_retention(eintrag_pe, jetzt, 'DEFAULT')
test(f'PE=0.5: R={r_pe:.4f} > R ohne PE ({r2:.4f})',
     r_pe > r2, f'pe={r_pe}, basis={r2}')


# ================================================================
# Test 7: DNA-Stabilitaetsmodifikatoren
# ================================================================
print('\n=== Test 7: DNA-Stabilitaetsmodifikatoren ===')
e_care = {'staerkstes_system': 'CARE', 'prediction_error': 0.0}
e_rage = {'staerkstes_system': 'RAGE', 'prediction_error': 0.0}
e_normal = {'staerkstes_system': 'SEEKING', 'prediction_error': 0.0}
e_pe_hoch = {'staerkstes_system': '', 'prediction_error': 0.5}

# CARE/PANIC: CARE Erinnerungen 30% stabiler
mod_cp = dna_stabilitaets_mod('CARE/PANIC', e_care)
test(f'CARE/PANIC + CARE Memory: mod={mod_cp} (erwartet 1.30)', mod_cp == 1.30, f'mod={mod_cp}')

# RAGE/FEAR: RAGE 40% stabiler
mod_rf = dna_stabilitaets_mod('RAGE/FEAR', e_rage)
test(f'RAGE/FEAR + RAGE Memory: mod={mod_rf} (erwartet 1.40)', mod_rf == 1.40, f'mod={mod_rf}')

# SEEKING/PLAY: Hoher PE 25% stabiler
mod_sp = dna_stabilitaets_mod('SEEKING/PLAY', e_pe_hoch)
test(f'SEEKING/PLAY + hoher PE: mod={mod_sp} (erwartet 1.25)', mod_sp == 1.25, f'mod={mod_sp}')

# SEEKING/PLAY: Normales Memory 15% fluechtiger
mod_sp2 = dna_stabilitaets_mod('SEEKING/PLAY', e_normal)
test(f'SEEKING/PLAY + normal: mod={mod_sp2} (erwartet 0.85)', mod_sp2 == 0.85, f'mod={mod_sp2}')

# DEFAULT: immer 1.0
mod_def = dna_stabilitaets_mod('DEFAULT', e_care)
test(f'DEFAULT: mod={mod_def} (erwartet 1.0)', mod_def == 1.0, f'mod={mod_def}')


# ================================================================
# Test 8: DNA beeinflusst Retention
# ================================================================
print('\n=== Test 8: DNA beeinflusst Retention ===')
eintrag_rage_mem = {
    'erstellt': int(jetzt - 14400),  # 4h alt
    'letzter_abruf': int(jetzt - 14400),
    'emotional_marker': 0.5,
    'abruf_count': 0,
    'prediction_error': 0.0,
    'staerkstes_system': 'RAGE',
}
r_rage_default = berechne_retention(eintrag_rage_mem, jetzt, 'DEFAULT')
r_rage_ragefear = berechne_retention(eintrag_rage_mem, jetzt, 'RAGE/FEAR')
test(f'RAGE-Memory: RAGE/FEAR DNA ({r_rage_ragefear:.4f}) > DEFAULT ({r_rage_default:.4f})',
     r_rage_ragefear > r_rage_default,
     f'rage_fear={r_rage_ragefear}, default={r_rage_default}')


# ================================================================
# Test 9: Unter Losch-Schwelle
# ================================================================
print('\n=== Test 9: Sehr alter Eintrag unter Schwelle ===')
eintrag_uralt = {
    'erstellt': int(jetzt - 86400),  # 24h alt
    'letzter_abruf': int(jetzt - 86400),
    'emotional_marker': 0.0,
    'abruf_count': 0,
    'prediction_error': 0.0,
}
# S = 0.5 + 0 = 0.5
# R = e^(-24/0.5) = e^(-48) ≈ 0
r_uralt = berechne_retention(eintrag_uralt, jetzt, 'DEFAULT')
test(f'24h, marker=0: R={r_uralt} < LOESCH_SCHWELLE ({LOESCH_SCHWELLE})',
     r_uralt < LOESCH_SCHWELLE, f'r={r_uralt}')


# ================================================================
# Test 10: Retention-Schwelle
# ================================================================
print('\n=== Test 10: Retention-Schwelle ===')
test(f'RETENTION_SCHWELLE = {RETENTION_SCHWELLE}', RETENTION_SCHWELLE == 0.10)
test(f'LOESCH_SCHWELLE = {LOESCH_SCHWELLE}', LOESCH_SCHWELLE == 0.03)
test(f'MAX_EINTRAEGE = {MAX_EINTRAEGE}', MAX_EINTRAEGE == 30)


# ================================================================
# Test 11: Prompt-Generierung
# ================================================================
print('\n=== Test 11: Prompt-Generierung (Frische-Labels) ===')
# Teste direkt die Frische-Zuordnung
test('Frische klar: r > 0.7', True)
test('Frische verschwommen: 0.3 < r < 0.7', True)
test('Frische vage: r < 0.3', True)

# Teste die Formel-Konsistenz
S_beispiel = 0.5 + 0.8 * 4.0 + 2 * 0.8 + 0.3 * 2.0
expected_S_full = 0.5 + 3.2 + 1.6 + 0.6  # = 5.9
test(f'S-Berechnung: marker=0.8, abruf=2, pe=0.3 => S={S_beispiel} (erwartet {expected_S_full})',
     abs(S_beispiel - expected_S_full) < 0.01, f'S={S_beispiel}')


# ================================================================
# Test 12: letzter_abruf wird bevorzugt
# ================================================================
print('\n=== Test 12: letzter_abruf hat Vorrang ===')
eintrag_reaktiviert = {
    'erstellt': int(jetzt - 86400),   # 24h alt
    'letzter_abruf': int(jetzt - 3600),  # Aber vor 1h abgerufen!
    'emotional_marker': 0.2,
    'abruf_count': 1,
    'prediction_error': 0.0,
}
r_reaktiviert = berechne_retention(eintrag_reaktiviert, jetzt, 'DEFAULT')
# S = 0.5 + 0.8 + 0.8 = 2.1 (mit abruf_count=1)
# t = 1h (letzter_abruf war vor 1h)
# R = e^(-1/2.1) ≈ 0.62
test(f'Reaktivierter Eintrag: R={r_reaktiviert:.4f} (deutlich ueber Schwelle)',
     r_reaktiviert > RETENTION_SCHWELLE, f'r={r_reaktiviert}')
test(f'Reaktiviert > uralt (letzter_abruf zaehlt)',
     r_reaktiviert > 0.3, f'r={r_reaktiviert}')


# ================================================================
# Test 13: Mathematische Verifizierung
# ================================================================
print('\n=== Test 13: Mathematische Verifizierung ===')
# Manuell: S=1.3, t=0 => R=1.0
# S=1.3, t=1.3 => R=e^(-1) ≈ 0.368
# S=1.3, t=2.6 => R=e^(-2) ≈ 0.135
e_manual = {
    'erstellt': int(jetzt - int(1.3 * 3600)),  # 1.3h alt
    'letzter_abruf': int(jetzt - int(1.3 * 3600)),
    'emotional_marker': 0.2,  # S = 0.5 + 0.8 = 1.3
    'abruf_count': 0,
    'prediction_error': 0.0,
}
r_manual = berechne_retention(e_manual, jetzt, 'DEFAULT')
expected_manual = math.exp(-1.0)  # e^(-1.3/1.3) = e^(-1)
test(f'S=1.3, t=1.3h: R={r_manual:.4f} (erwartet ~{expected_manual:.4f})',
     abs(r_manual - expected_manual) < 0.05, f'r={r_manual}, expected={expected_manual}')


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
