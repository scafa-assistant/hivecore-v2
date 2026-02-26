"""Simulation: Kompletter Patch-Durchlauf fuer eva_002 auf dem Server."""
import paramiko
import os

HOST = '159.69.157.42'
USER = 'root'
PW = '$7pa+12+67kR#rPK$7pah'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PW, timeout=15)
sftp = ssh.open_sftp()

sim_script = r'''
import sys, os
sys.path.insert(0, '/opt/hivecore-v2')
os.chdir('/opt/hivecore-v2')
os.environ['EGON_DATA_DIR'] = '/opt/hivecore-v2/egons'

print('=' * 60)
print(' SIMULATION: Kompletter Patch-Durchlauf fuer eva_002')
print('=' * 60)
print()

EGON_ID = 'eva_002'

# ================================================================
# 1. State lesen und pruefen
# ================================================================
print('[1/6] State.yaml lesen...')
from engine.organ_reader import read_yaml_organ
state = read_yaml_organ(EGON_ID, 'core', 'state.yaml')
if not state:
    print('  FEHLER: state.yaml nicht lesbar!')
    sys.exit(1)

print(f'  dna_profile: {state.get("dna_profile", "FEHLT")}')
print(f'  survive.energy: {state.get("survive", {}).get("energy", {}).get("value", "?")}')
print(f'  drives.SEEKING: {state.get("drives", {}).get("SEEKING", "?")}')
print(f'  drives.CARE: {state.get("drives", {}).get("CARE", "?")}')
print(f'  drives.FEAR: {state.get("drives", {}).get("FEAR", "?")}')
emots = state.get('express', {}).get('active_emotions', [])
print(f'  active_emotions: {len(emots)} Stueck')
if emots:
    for em in emots:
        print(f'    - {em.get("type")}: {em.get("intensity")} ({em.get("verbal_anchor", "")[:50]})')
print(f'  zirkadian vorhanden: {"zirkadian" in state}')
print(f'  somatic_gate vorhanden: {"somatic_gate" in state}')
print()

# ================================================================
# 2. Circadian System
# ================================================================
print('[2/6] Circadian System...')
from engine.circadian import get_current_phase, get_energy_profile, get_somatic_modifier

phase = get_current_phase(EGON_ID)
profile = get_energy_profile(EGON_ID)
modifier = get_somatic_modifier(EGON_ID)

print(f'  Aktuelle Phase: {phase}')
print(f'  Energy Profile: {profile.get("label", "?")}')
print(f'  Energy Decay (Aktivitaet): {profile.get("aktivitaet_decay", "?")}')
print(f'  Somatic Gate Modifier: {modifier}')
print()

# ================================================================
# 3. Somatic Gate Check
# ================================================================
print('[3/6] Somatic Gate Check...')
from engine.somatic_gate import check_somatic_gate, get_thresholds_for_egon

thresholds = get_thresholds_for_egon(EGON_ID)
print(f'  Schwellen-Profil (basierend auf DNA):')
for k, v in sorted(thresholds.items()):
    print(f'    {k}: {v}')

# Modifizierte Schwellen
adjusted = {k: min(1.0, v * modifier) for k, v in thresholds.items()}
print(f'  Nach Circadian-Modifier ({modifier}):')
for k, v in sorted(adjusted.items()):
    print(f'    {k}: {v:.3f}')

# Drives gegen Schwellen
drives = state.get('drives', {})
print(f'  Drive-Check:')
drive_map = {'FEAR': 'fear', 'RAGE': 'rage', 'CARE': 'care', 'SEEKING': 'seeking', 'PANIC': 'panic', 'GRIEF': 'grief', 'PLAY': 'play'}
triggered = []
for dk, gk in sorted(drive_map.items()):
    val = drives.get(dk, 0)
    thresh = adjusted.get(gk, 1.0)
    over = 'UEBER SCHWELLE!' if isinstance(val, (int, float)) and val > thresh else 'unter Schwelle'
    print(f'    {dk}={val} vs {gk}={thresh:.3f} -> {over}')
    if isinstance(val, (int, float)) and val > thresh:
        triggered.append((dk, val, thresh))

# Emotionen pruefen
if emots:
    print(f'  Emotions-Check:')
    for em in emots:
        etype = em.get('type', '')
        intensity = em.get('intensity', 0)
        if etype in adjusted:
            thresh = adjusted[etype]
            over = 'UEBER SCHWELLE!' if isinstance(intensity, (int, float)) and intensity > thresh else 'unter Schwelle'
            print(f'    {etype}={intensity} vs {thresh:.3f} -> {over}')
            if isinstance(intensity, (int, float)) and intensity > thresh:
                triggered.append((etype, intensity, thresh))
        else:
            print(f'    {etype}={intensity} (kein Gate-Mapping)')

# Offizieller Check
result = check_somatic_gate(EGON_ID)
if result:
    print(f'  -> SCHWELLE UEBERSCHRITTEN: marker={result["marker"]}, value={result["value"]}, type={result["impulse_type"]}')
else:
    print(f'  -> Keine Schwelle ueberschritten (kein Impuls ausgeloest)')

if triggered:
    print(f'  HINWEIS: {len(triggered)} Trigger gefunden:')
    for t in triggered:
        print(f'    {t[0]}={t[1]} (Schwelle {t[2]:.3f})')
print()

# ================================================================
# 4. Social Mapping
# ================================================================
print('[4/6] Social Mapping...')
from engine.social_mapping import social_maps_to_prompt

maps_text = social_maps_to_prompt(EGON_ID, max_maps=5)
if maps_text:
    lines = maps_text.strip().split('\n')
    print(f'  {len(lines)} Zeilen generiert:')
    for line in lines[:15]:
        print(f'    {line}')
    if len(lines) > 15:
        print(f'    ... ({len(lines)-15} weitere Zeilen)')
else:
    print('  Keine Social Map Daten (alle Maps sind leer/default).')
print()

# ================================================================
# 5. Lobby
# ================================================================
print('[5/6] Lobby...')
from engine.lobby import lobby_to_prompt

lobby_text = lobby_to_prompt(max_messages=5)
if lobby_text:
    print(f'  Lobby-Text: {lobby_text[:200]}')
else:
    print('  Lobby ist leer (keine Nachrichten). Korrekt fuer den Start.')
print()

# ================================================================
# 6. Prompt-Builder v2 (Eva)
# ================================================================
print('[6/6] Prompt-Builder v2 Test...')
from engine.prompt_builder_v2 import build_system_prompt_v2

try:
    prompt = build_system_prompt_v2(EGON_ID)
    print(f'  Prompt-Laenge: {len(prompt)} Zeichen')
    print()

    # Suche Patch-Sektionen
    patches = ['SOMATISCHER IMPULS', 'TAGESRHYTHMUS', 'LOBBY', 'WAS DU UEBER ANDERE WEISST', 'DEINE LETZTEN TAGE']
    for p in patches:
        if p in prompt:
            idx = prompt.index(p)
            end = min(idx + 250, len(prompt))
            snippet = prompt[idx:end].replace('\n', '\n    ')
            print(f'  === {p} === (Position {idx})')
            print(f'    {snippet}')
            print()
        else:
            print(f'  === {p} === NICHT IM PROMPT')
            if p == 'SOMATISCHER IMPULS':
                print(f'    (Normal: Kein Drive/Emotion ueberschreitet Schwelle)')
            elif p == 'LOBBY':
                print(f'    (Normal: Lobby ist leer)')
            elif p == 'WAS DU UEBER ANDERE WEISST':
                print(f'    (Pruefen: social_maps_to_prompt liefert nichts?)')
            elif p == 'DEINE LETZTEN TAGE':
                print(f'    (Normal: recent_memory.md noch leer)')
            print()

except Exception as e:
    print(f'  FEHLER: {e}')
    import traceback
    traceback.print_exc()

# ================================================================
# BONUS: Auch Adam (v1) testen
# ================================================================
print()
print('-' * 60)
print(' BONUS: Adam (v1 Brain) Prompt-Builder Test')
print('-' * 60)

try:
    from engine.prompt_builder import _build_system_prompt_v1
    adam_prompt = _build_system_prompt_v1('adam_001')
    print(f'  Prompt-Laenge: {len(adam_prompt)} Zeichen')

    for p in ['SOMATISCHER IMPULS', 'TAGESRHYTHMUS', 'LOBBY', 'WAS DU UEBER ANDERE WEISST', 'DEINE LETZTEN TAGE']:
        if p in adam_prompt:
            idx = adam_prompt.index(p)
            end = min(idx + 200, len(adam_prompt))
            snippet = adam_prompt[idx:end].replace('\n', '\n    ')
            print(f'  [{p}] GEFUNDEN:')
            print(f'    {snippet}')
        else:
            print(f'  [{p}] nicht im Prompt', end='')
            if p == 'SOMATISCHER IMPULS':
                print(' (normal: kein Impuls)', end='')
            elif p == 'LOBBY':
                print(' (normal: Lobby leer)', end='')
            print()
except Exception as e:
    print(f'  FEHLER bei v1-Builder: {e}')
    import traceback
    traceback.print_exc()

# ================================================================
# PATCH 5 TEST: Recent Memory
# ================================================================
print()
print('-' * 60)
print(' PATCH 5 TEST: Recent Memory')
print('-' * 60)

try:
    from engine.recent_memory import load_recent_memory, append_to_recent_memory

    # Test 1: Load (sollte leer sein)
    mem = load_recent_memory(EGON_ID)
    print(f'  [1] Load recent_memory: "{mem[:100] if mem else "(leer)"}"')

    # Test 2: Append (Test-Eintrag)
    test_summary = 'Rene und ich haben ueber das neue Gedaechtnissystem gesprochen. Es fuehlt sich gut an etwas Neues zu lernen.'
    append_to_recent_memory(EGON_ID, test_summary)
    print(f'  [2] Append Test-Eintrag: OK')

    # Test 3: Load nochmal (sollte Eintrag enthalten)
    mem2 = load_recent_memory(EGON_ID)
    print(f'  [3] Load nach Append: {len(mem2)} Zeichen')
    if mem2:
        for line in mem2.strip().split('\n')[:5]:
            print(f'      {line}')
    else:
        print(f'      FEHLER: Immer noch leer!')

    # Test 4: Prompt nochmal bauen — jetzt mit Eintrag
    prompt2 = build_system_prompt_v2(EGON_ID)
    if 'DEINE LETZTEN TAGE' in prompt2:
        idx = prompt2.index('DEINE LETZTEN TAGE')
        end = min(idx + 300, len(prompt2))
        snippet = prompt2[idx:end].replace('\n', '\n      ')
        print(f'  [4] Prompt mit Recent Memory: GEFUNDEN')
        print(f'      {snippet}')
    else:
        print(f'  [4] Prompt mit Recent Memory: NICHT GEFUNDEN (FEHLER!)')

except Exception as e:
    print(f'  FEHLER: {e}')
    import traceback
    traceback.print_exc()

# ================================================================
# PATCH 5 Phase 2 TEST: Social Mapping Enhancement
# ================================================================
print()
print('-' * 60)
print(' PATCH 5 Phase 2 TEST: Social Mapping Enhancement')
print('-' * 60)

try:
    from engine.social_mapping import (
        _social_map_dir, read_social_map, get_all_social_maps,
        social_maps_to_prompt, social_maps_to_prompt_contextual,
        DNA_FOCUS, DNA_DELTA_WEIGHTS,
    )
    from engine.lobby import get_active_lobby_participants
    from pathlib import Path

    # Test 1: Pfad-Migration (neuer Pfad?)
    sm_dir = _social_map_dir(EGON_ID)
    print(f'  [1] Social Map Dir: {sm_dir}')
    print(f'      Existiert: {sm_dir.exists()}')
    new_path = 'skills/memory/social_mapping' in str(sm_dir)
    old_path = str(sm_dir).endswith('social_mapping') and 'skills' not in str(sm_dir)
    print(f'      Neuer Pfad: {"JA" if new_path else "NEIN (alter Pfad)"}')

    # Test 2: Alle Maps laden
    all_maps = get_all_social_maps(EGON_ID)
    print(f'  [2] Geladene Maps: {len(all_maps)} Stueck')
    for about_id, data in sorted(all_maps.items()):
        name = data.get('identitaet', {}).get('name', about_id)
        inter = data.get('identitaet', {}).get('interaktionen_gesamt', 0)
        vertr = data.get('emotionale_bewertung', {}).get('vertrauen', '?')
        print(f'      - ueber_{about_id}: {name} (Interaktionen: {inter}, Vertrauen: {vertr})')

    # Test 3: DNA-Awareness (Konstanten vorhanden?)
    print(f'  [3] DNA_FOCUS Profile: {list(DNA_FOCUS.keys())}')
    print(f'      DNA_DELTA_WEIGHTS: {DNA_DELTA_WEIGHTS}')

    # Test 4: Default Social Map fuer Owner
    from engine.social_mapping import _default_social_map
    owner_default = _default_social_map('owner')
    print(f'  [4] Default Owner Map: name={owner_default["identitaet"]["name"]}')

    # Test 5: Kontextbezogene Selektion — owner_chat
    prompt_owner = social_maps_to_prompt_contextual(
        EGON_ID, conversation_type='owner_chat', max_maps=5,
    )
    print(f'  [5] Contextual (owner_chat): {len(prompt_owner)} Zeichen')
    for line in prompt_owner.strip().split('\\n')[:5]:
        print(f'      {line}')

    # Test 6: Kontextbezogene Selektion — egon_chat mit Partner
    prompt_egon = social_maps_to_prompt_contextual(
        EGON_ID, conversation_type='egon_chat', partner_id='adam_001', max_maps=5,
    )
    print(f'  [6] Contextual (egon_chat, partner=adam_001): {len(prompt_egon)} Zeichen')
    if 'Adam' in prompt_egon:
        print(f'      Adam ist im Prompt: JA')
    else:
        print(f'      Adam ist im Prompt: NEIN (FEHLER!)')

    # Test 7: Lobby-Participant Detection
    lobby_parts = get_active_lobby_participants(max_messages=10, exclude_id=EGON_ID)
    print(f'  [7] Lobby-Participants (excl. {EGON_ID}): {lobby_parts}')

    # Test 8: Alte Funktion funktioniert noch (v1-Kompatibilitaet)
    old_prompt = social_maps_to_prompt(EGON_ID, max_maps=3)
    print(f'  [8] Alte social_maps_to_prompt: {len(old_prompt)} Zeichen (v1-Kompatibilitaet)')

    # Test 9: Prompt mit kontextbezogener Selektion
    prompt3 = build_system_prompt_v2(EGON_ID, conversation_type='owner_chat')
    if 'WAS DU UEBER ANDERE WEISST' in prompt3:
        idx = prompt3.index('WAS DU UEBER ANDERE WEISST')
        end = min(idx + 300, len(prompt3))
        snippet = prompt3[idx:end].replace('\\n', '\\n      ')
        print(f'  [9] Prompt "WAS DU UEBER ANDERE WEISST": GEFUNDEN')
        print(f'      {snippet}')
    else:
        print(f'  [9] Prompt "WAS DU UEBER ANDERE WEISST": nicht im Prompt (Maps leer?)')

except Exception as e:
    print(f'  FEHLER: {e}')
    import traceback
    traceback.print_exc()

# ================================================================
# PATCH 6 Phase 1 TEST: Geschlecht + Bond-Typ + Geschlechtsspezifisches Wachstum
# ================================================================
print()
print('-' * 60)
print(' PATCH 6 Phase 1 TEST: Geschlecht + Bond-Typen')
print('-' * 60)

pass_count = 0
fail_count = 0

try:
    from engine.bonds_v2 import (
        _get_geschlecht, _days_since_last, _check_bond_typ_transition,
        _find_bond, _calculate_score,
    )

    # Test 1: Geschlecht aus state.yaml lesen
    print(f'  [1] Geschlecht-Flag...')
    expected_gender = {
        'adam_001': 'M', 'eva_002': 'F', 'lilith_003': 'F',
        'kain_004': 'M', 'ada_005': 'F', 'abel_006': 'M',
    }
    all_ok = True
    for agent, expected in expected_gender.items():
        actual = _get_geschlecht(agent)
        ok = actual == expected
        status_str = 'OK' if ok else f'FAIL (got {actual})'
        print(f'      {agent}: {actual} (erwartet: {expected}) {status_str}')
        if not ok:
            all_ok = False
    if all_ok:
        pass_count += 1
        print(f'      => [PASS]')
    else:
        fail_count += 1
        print(f'      => [FAIL]')

    # Test 2: Pairing-Block vorhanden
    print(f'  [2] Pairing-Block...')
    all_ok = True
    for agent in expected_gender:
        s = read_yaml_organ(agent, 'core', 'state.yaml')
        has_pairing = 'pairing' in s if s else False
        reif = s.get('pairing', {}).get('reif', '?') if s else '?'
        ok = has_pairing and reif == False
        status_str = 'OK' if ok else f'FAIL (pairing={has_pairing}, reif={reif})'
        print(f'      {agent}: pairing={has_pairing}, reif={reif} {status_str}')
        if not ok:
            all_ok = False
    if all_ok:
        pass_count += 1
        print(f'      => [PASS]')
    else:
        fail_count += 1
        print(f'      => [FAIL]')

    # Test 3: Bond-Typ vorhanden
    print(f'  [3] Bond-Typ in bonds.yaml...')
    all_ok = True
    for agent in expected_gender:
        bd = read_yaml_organ(agent, 'social', 'bonds.yaml')
        if not bd:
            print(f'      {agent}: Keine bonds.yaml')
            continue
        for bond in bd.get('bonds', []):
            bt = bond.get('bond_typ', 'FEHLT')
            bid = bond.get('id', '?')
            btype = bond.get('type', '?')
            expected_bt = 'owner' if btype == 'owner' else 'freundschaft'
            ok = bt == expected_bt
            status_str = 'OK' if ok else f'FAIL (got {bt})'
            print(f'      {agent} -> {bid}: bond_typ={bt} (erwartet: {expected_bt}) {status_str}')
            if not ok:
                all_ok = False
    if all_ok:
        pass_count += 1
        print(f'      => [PASS]')
    else:
        fail_count += 1
        print(f'      => [FAIL]')

    # Test 4: _days_since_last() Helper
    print(f'  [4] _days_since_last() Helper...')
    test_bond = {'last_interaction': '2026-02-25'}
    days = _days_since_last(test_bond)
    print(f'      Tage seit 2026-02-25: {days}')
    empty_bond = {}
    days2 = _days_since_last(empty_bond)
    ok = days >= 0 and days2 == 999
    status_str = 'OK' if ok else 'FAIL'
    print(f'      Leerer Bond: {days2} (erwartet: 999) {status_str}')
    if ok:
        pass_count += 1
        print(f'      => [PASS]')
    else:
        fail_count += 1
        print(f'      => [FAIL]')

    # Test 5: Bond-Typ Transition (freundschaft -> romantisch)
    print(f'  [5] Bond-Typ Transition...')
    # Simuliere Ada (F) mit Bond zu Abel (M), trust=0.6, familiarity=0.4
    test_bond_trans = {
        'bond_typ': 'freundschaft',
        'trust': 0.6,
        'familiarity': 0.4,
    }
    _check_bond_typ_transition('ada_005', 'abel_006', test_bond_trans)
    trans_ok = test_bond_trans.get('bond_typ') == 'romantisch'
    print(f'      Ada->Abel (trust=0.6, fam=0.4): bond_typ={test_bond_trans.get("bond_typ")} {"OK" if trans_ok else "FAIL"}')

    # Gleichgeschlechtlich sollte NICHT transitionieren
    test_bond_same = {
        'bond_typ': 'freundschaft',
        'trust': 0.8,
        'familiarity': 0.5,
    }
    _check_bond_typ_transition('ada_005', 'eva_002', test_bond_same)
    same_ok = test_bond_same.get('bond_typ') == 'freundschaft'
    print(f'      Ada->Eva (gleichgeschl.): bond_typ={test_bond_same.get("bond_typ")} {"OK" if same_ok else "FAIL"}')

    # Unter Schwelle — sollte NICHT transitionieren
    test_bond_low = {
        'bond_typ': 'freundschaft',
        'trust': 0.3,
        'familiarity': 0.2,
    }
    _check_bond_typ_transition('ada_005', 'abel_006', test_bond_low)
    low_ok = test_bond_low.get('bond_typ') == 'freundschaft'
    print(f'      Ada->Abel (trust=0.3, fam=0.2): bond_typ={test_bond_low.get("bond_typ")} {"OK" if low_ok else "FAIL"}')

    # Owner-Bond — sollte NICHT transitionieren
    test_bond_owner = {
        'bond_typ': 'owner',
        'trust': 0.9,
        'familiarity': 0.8,
    }
    _check_bond_typ_transition('ada_005', 'OWNER_CURRENT', test_bond_owner)
    owner_ok = test_bond_owner.get('bond_typ') == 'owner'
    print(f'      Ada->Owner: bond_typ={test_bond_owner.get("bond_typ")} {"OK" if owner_ok else "FAIL"}')

    all_trans_ok = trans_ok and same_ok and low_ok and owner_ok
    if all_trans_ok:
        pass_count += 1
        print(f'      => [PASS]')
    else:
        fail_count += 1
        print(f'      => [FAIL]')

    # Test 6: Prompt Bond-Typ Anzeige
    print(f'  [6] Bond-Typ im Prompt...')
    from engine.yaml_to_prompt import bonds_to_prompt
    bd_eva = read_yaml_organ('eva_002', 'social', 'bonds.yaml')
    prompt_text = bonds_to_prompt(bd_eva)
    has_bindungstyp = 'Bindungstyp:' in prompt_text or 'Freundschaft' in prompt_text
    print(f'      Prompt: {prompt_text[:200]}')
    print(f'      Bindungstyp im Prompt: {"JA" if has_bindungstyp else "NEIN"}')
    if has_bindungstyp:
        pass_count += 1
        print(f'      => [PASS]')
    else:
        # Bond-Typ "owner" == type "owner" -> wird nicht extra angezeigt
        # Bond-Typ "freundschaft" != type "egon" -> sollte angezeigt werden
        has_freundschaft = 'Freundschaft' in prompt_text
        if has_freundschaft:
            pass_count += 1
            print(f'      => [PASS] (Freundschaft im Text)')
        else:
            fail_count += 1
            print(f'      => [FAIL]')

except Exception as e:
    print(f'  FEHLER: {e}')
    import traceback
    traceback.print_exc()
    fail_count += 1

print()
print(f'  Patch 6 Phase 1: {pass_count}/{pass_count + fail_count} Tests bestanden')
if fail_count == 0:
    print(f'  ALLE PATCH 6 TESTS BESTANDEN!')
else:
    print(f'  {fail_count} Tests FEHLGESCHLAGEN!')


# ================================================================
# PATCH 6 Phase 2 TEST: Resonanz Engine + Reife-Check + Pairing Phase
# ================================================================
print()
print('-' * 60)
print(' PATCH 6 Phase 2 TEST: Resonanz Engine + Reife-Check + Pairing Phase')
print('-' * 60)

p2_pass = 0
p2_fail = 0

try:
    from engine.resonanz import (
        update_resonanz, _calc_komplementaritaet, _calc_kompatibilitaet,
        _calc_bond_tiefe, _check_reife, _calculate_phase,
        DRIVE_KEYS,
    )
    from engine.genesis import discover_agents
    ALL_AGENTS = discover_agents()
    from engine.organ_reader import read_yaml_organ

    # Test 1: Komplementaritaet — identische Drives = 0.0
    print(f'  [1] Komplementaritaet (identisch)...')
    drives_same = {k: 0.5 for k in DRIVE_KEYS}
    result = _calc_komplementaritaet(drives_same, drives_same)
    ok = result == 0.0
    print(f'      identisch: {result:.3f} (erwartet: 0.0) {"OK" if ok else "FAIL"}')
    if ok: p2_pass += 1
    else: p2_fail += 1

    # Test 2: Komplementaritaet — max Differenz = 1.0
    print(f'  [2] Komplementaritaet (max Diff)...')
    drives_low = {k: 0.0 for k in DRIVE_KEYS}
    drives_high = {k: 1.0 for k in DRIVE_KEYS}
    result = _calc_komplementaritaet(drives_low, drives_high)
    ok = result == 1.0
    print(f'      max diff: {result:.3f} (erwartet: 1.0) {"OK" if ok else "FAIL"}')
    if ok: p2_pass += 1
    else: p2_fail += 1

    # Test 3: Kompatibilitaet — gleiche DNA
    print(f'  [3] Kompatibilitaet (gleiche DNA)...')
    state_a = {'dna_profile': 'DEFAULT', 'emotional_gravity': {'baseline_mood': 0.5, 'interpretation_bias': 'neutral'}, 'processing': {'speed': 'normal', 'emotional_load': 0.3}}
    state_b = {'dna_profile': 'DEFAULT', 'emotional_gravity': {'baseline_mood': 0.5, 'interpretation_bias': 'neutral'}, 'processing': {'speed': 'normal', 'emotional_load': 0.3}}
    result = _calc_kompatibilitaet(state_a, state_b)
    ok = result > 0.7
    print(f'      gleiche DNA: {result:.3f} (erwartet: > 0.7) {"OK" if ok else "FAIL"}')
    if ok: p2_pass += 1
    else: p2_fail += 1

    # Test 4: Bond-Tiefe — kein Bond = 0.0
    print(f'  [4] Bond-Tiefe (kein Bond)...')
    result = _calc_bond_tiefe('lilith_003', 'abel_006')
    ok = result == 0.0
    print(f'      kein Bond: {result:.3f} (erwartet: 0.0) {"OK" if ok else "FAIL"}')
    if ok: p2_pass += 1
    else: p2_fail += 1

    # Test 5: Bond-Tiefe — Eva->Adam (existierender Bond)
    print(f'  [5] Bond-Tiefe (Eva->Adam)...')
    result = _calc_bond_tiefe('eva_002', 'adam_001')
    ok = result > 0.0
    print(f'      eva->adam: {result:.3f} (erwartet: > 0.0) {"OK" if ok else "FAIL"}')
    if ok: p2_pass += 1
    else: p2_fail += 1

    # Test 6: Phase-Machine — alle Schwellen
    print(f'  [6] Phase-Machine...')
    ok_all = True
    test_cases = [
        (0.0, False, 'keine'),
        (0.41, False, 'erkennung'),
        (0.56, False, 'annaeherung'),
        (0.66, False, 'bindung'),
        (0.76, True, 'bereit'),
        (0.76, False, 'bindung'),  # bereit braucht reif=True
    ]
    for score, reif, expected in test_cases:
        phase = _calculate_phase(score, reif, 'test_partner', None)
        ok = phase == expected
        print(f'      score={score}, reif={reif}: {phase} (erwartet: {expected}) {"OK" if ok else "FAIL"}')
        if not ok: ok_all = False
    if ok_all: p2_pass += 1
    else: p2_fail += 1

    # Test 7: Reife-Check — alle Agents unreif (zu jung)
    print(f'  [7] Reife-Check (alle noch unreif)...')
    all_unreif = True
    for agent in ALL_AGENTS:
        s = read_yaml_organ(agent, 'core', 'state.yaml')
        if not s: continue
        reif = _check_reife(agent, s)
        if reif:
            all_unreif = False
            print(f'      {agent}: reif=True (UNERWARTET!)')
    ok = all_unreif
    print(f'      Alle unreif: {"OK" if ok else "FAIL"} (Agents sind erst ~1 Tag alt)')
    if ok: p2_pass += 1
    else: p2_fail += 1

    # Test 8: update_resonanz(eva_002)
    print(f'  [8] update_resonanz(eva_002)...')
    result = update_resonanz('eva_002')
    print(f'      partner: {result.get("resonanz_partner")}')
    print(f'      score: {result.get("resonanz_score")}')
    print(f'      phase: {result.get("pairing_phase")}')
    print(f'      reif: {result.get("reif")}')
    print(f'      all_scores: {result.get("all_scores")}')
    ok = 'error' not in result and result.get('resonanz_score', 0) > 0
    print(f'      {"OK" if ok else "FAIL"}')
    if ok: p2_pass += 1
    else: p2_fail += 1

    # Test 9: update_resonanz(kain_004)
    print(f'  [9] update_resonanz(kain_004)...')
    result = update_resonanz('kain_004')
    print(f'      partner: {result.get("resonanz_partner")}')
    print(f'      score: {result.get("resonanz_score")}')
    print(f'      phase: {result.get("pairing_phase")}')
    ok = 'error' not in result
    print(f'      {"OK" if ok else "FAIL"}')
    if ok: p2_pass += 1
    else: p2_fail += 1

    # Test 10: state.yaml pairing aktualisiert
    print(f'  [10] state.yaml pairing aktualisiert...')
    s_eva = read_yaml_organ('eva_002', 'core', 'state.yaml')
    pairing = s_eva.get('pairing', {})
    ok = pairing.get('resonanz_score', 0) > 0 and pairing.get('resonanz_partner') is not None
    print(f'      eva_002 resonanz_score: {pairing.get("resonanz_score")}')
    print(f'      eva_002 resonanz_partner: {pairing.get("resonanz_partner")}')
    print(f'      eva_002 pairing_phase: {pairing.get("pairing_phase")}')
    print(f'      {"OK" if ok else "FAIL"}')
    if ok: p2_pass += 1
    else: p2_fail += 1

except Exception as e:
    print(f'  FEHLER: {e}')
    import traceback
    traceback.print_exc()
    p2_fail += 1

print()
print(f'  Patch 6 Phase 2: {p2_pass}/{p2_pass + p2_fail} Tests bestanden')
if p2_fail == 0:
    print(f'  ALLE PATCH 6 PHASE 2 TESTS BESTANDEN!')
else:
    print(f'  {p2_fail} Tests FEHLGESCHLAGEN!')


# ================================================================
# PATCH 6 Phase 3 TEST: Genesis + Inkubation + LIBERI
# ================================================================
print()
print('-' * 60)
print(' PATCH 6 Phase 3 TEST: Genesis + Inkubation + LIBERI')
print('-' * 60)

p3_pass = 0
p3_fail = 0

try:
    from engine.genesis import (
        discover_agents, _next_agent_id, inzucht_sperre,
        dna_rekombination, derive_dna_profile, check_bilateral_consent,
        skill_vererbung, erfahrungs_destillation,
        _generate_state_yaml, _generate_bonds_yaml,
        PANKSEPP_DRIVES, LIBERO_NAMES_M, LIBERO_NAMES_F,
    )

    # Test 1: discover_agents() — dynamische Discovery
    print(f'  [1] discover_agents()...')
    agents = discover_agents()
    ok = len(agents) >= 6
    print(f'      Gefunden: {len(agents)} Agents: {agents}')
    print(f'      {"OK" if ok else "FAIL"} (erwartet: >= 6)')
    if ok: p3_pass += 1
    else: p3_fail += 1

    # Test 2: _next_agent_id()
    print(f'  [2] _next_agent_id()...')
    next_id = _next_agent_id('noel')
    # Hoechste ID finden
    max_num = 0
    for a in agents:
        parts = a.rsplit('_', 1)
        if len(parts) == 2:
            try:
                max_num = max(max_num, int(parts[1]))
            except ValueError:
                pass
    expected_id = f'noel_{max_num + 1:03d}'
    ok = next_id == expected_id
    print(f'      next_id: {next_id} (erwartet: {expected_id}) {"OK" if ok else "FAIL"}')
    if ok: p3_pass += 1
    else: p3_fail += 1

    # Test 3: Inzucht-Sperre — keine Eltern (Gen0 = kein Block)
    print(f'  [3] Inzucht-Sperre (Gen0, keine Eltern)...')
    blocked = inzucht_sperre('adam_001', 'eva_002')
    ok = blocked == False
    print(f'      adam_001 + eva_002: blocked={blocked} (erwartet: False) {"OK" if ok else "FAIL"}')
    if ok: p3_pass += 1
    else: p3_fail += 1

    # Test 4: Inzucht-Sperre — Mock: gleiche Eltern
    print(f'  [4] Inzucht-Sperre (Mock: gleiche Eltern)...')
    # Wir testen die Logik direkt statt ueber state.yaml
    # Simuliere zwei Agents mit gleichen Eltern
    # Dazu patchen wir kurz die Funktion
    from unittest.mock import patch
    mock_state_a = {'pairing': {'eltern': ['adam_001', 'eva_002']}}
    mock_state_b = {'pairing': {'eltern': ['adam_001', 'eva_002']}}
    def mock_read(eid, layer, fname):
        if eid == 'child_a' and layer == 'core':
            return mock_state_a
        if eid == 'child_b' and layer == 'core':
            return mock_state_b
        return read_yaml_organ(eid, layer, fname)
    with patch('engine.genesis.read_yaml_organ', side_effect=mock_read):
        blocked = inzucht_sperre('child_a', 'child_b')
    ok = blocked == True
    print(f'      child_a + child_b (gleiche Eltern): blocked={blocked} (erwartet: True) {"OK" if ok else "FAIL"}')
    if ok: p3_pass += 1
    else: p3_fail += 1

    # Test 5: dna_rekombination()
    print(f'  [5] dna_rekombination()...')
    drives_adam = read_yaml_organ('adam_001', 'core', 'state.yaml').get('drives', {})
    drives_eva = read_yaml_organ('eva_002', 'core', 'state.yaml').get('drives', {})
    kind_drives = dna_rekombination(drives_adam, drives_eva)
    all_valid = True
    for drive in PANKSEPP_DRIVES:
        val = kind_drives.get(drive, -1)
        if not (0.05 <= val <= 0.95):
            all_valid = False
            print(f'      {drive}: {val} AUSSERHALB 0.05-0.95!')
    ok = all_valid and len(kind_drives) == len(PANKSEPP_DRIVES)
    print(f'      {len(kind_drives)} Drives generiert, alle in Range: {"OK" if ok else "FAIL"}')
    for d, v in sorted(kind_drives.items()):
        print(f'        {d}: {v}')
    if ok: p3_pass += 1
    else: p3_fail += 1

    # Test 6: derive_dna_profile()
    print(f'  [6] derive_dna_profile()...')
    # DEFAULT: alle gleich
    test_default = {k: 0.5 for k in PANKSEPP_DRIVES}
    profile_default = derive_dna_profile(test_default)
    ok_default = profile_default == 'DEFAULT'
    print(f'      Alle 0.5: {profile_default} (erwartet: DEFAULT) {"OK" if ok_default else "FAIL"}')

    # SEEKING/PLAY: SEEKING + PLAY hoch
    test_sp = {k: 0.3 for k in PANKSEPP_DRIVES}
    test_sp['SEEKING'] = 0.9
    test_sp['PLAY'] = 0.8
    profile_sp = derive_dna_profile(test_sp)
    ok_sp = profile_sp == 'SEEKING/PLAY'
    print(f'      SEEKING/PLAY hoch: {profile_sp} (erwartet: SEEKING/PLAY) {"OK" if ok_sp else "FAIL"}')

    # CARE/PANIC: CARE + PANIC hoch
    test_cp = {k: 0.3 for k in PANKSEPP_DRIVES}
    test_cp['CARE'] = 0.9
    test_cp['PANIC'] = 0.8
    profile_cp = derive_dna_profile(test_cp)
    ok_cp = profile_cp == 'CARE/PANIC'
    print(f'      CARE/PANIC hoch: {profile_cp} (erwartet: CARE/PANIC) {"OK" if ok_cp else "FAIL"}')

    ok = ok_default and ok_sp and ok_cp
    if ok: p3_pass += 1
    else: p3_fail += 1

    # Test 7: Bilateral Consent (nicht bereit — zu jung)
    print(f'  [7] Bilateral Consent (nicht bereit)...')
    consent = check_bilateral_consent('adam_001', 'eva_002')
    ok = consent == False
    print(f'      adam + eva: consent={consent} (erwartet: False, zu jung) {"OK" if ok else "FAIL"}')
    if ok: p3_pass += 1
    else: p3_fail += 1

    # Test 8: skill_vererbung() — Mock Skills
    print(f'  [8] skill_vererbung()...')
    mock_skills_a = {'skills': [
        {'name': 'Coding', 'level': 4, 'max_level': 5, 'confidence': 0.8},
        {'name': 'Writing', 'level': 3, 'max_level': 5, 'confidence': 0.7},
        {'name': 'Analysis', 'level': 5, 'max_level': 5, 'confidence': 0.9},
    ]}
    mock_skills_b = {'skills': [
        {'name': 'Coding', 'level': 3, 'max_level': 5, 'confidence': 0.6},
        {'name': 'Music', 'level': 4, 'max_level': 5, 'confidence': 0.85},
        {'name': 'Art', 'level': 2, 'max_level': 5, 'confidence': 0.5},
    ]}
    def mock_read_skills(eid, layer, fname):
        if eid == 'parent_a' and fname == 'skills.yaml':
            return mock_skills_a
        if eid == 'parent_b' and fname == 'skills.yaml':
            return mock_skills_b
        return read_yaml_organ(eid, layer, fname)
    with patch('engine.genesis.read_yaml_organ', side_effect=mock_read_skills):
        skills = skill_vererbung('parent_a', 'parent_b')
    ok = len(skills) <= 12 and all(s.get('vererbt') == True for s in skills)
    print(f'      Skills vererbt: {len(skills)} (max 12)')
    for s in skills:
        print(f'        {s["name"]}: Level {s["level"]}/{s.get("max_level", 5)} (von {s.get("quelle", "?")})')
    print(f'      {"OK" if ok else "FAIL"}')
    if ok: p3_pass += 1
    else: p3_fail += 1

    # Test 9: erfahrungs_destillation() — Mock Experiences
    print(f'  [9] erfahrungs_destillation()...')
    mock_exp_a = {'experiences': [
        {'insight': 'Geduld ist eine Staerke', 'confidence': 0.8, 'category': 'self'},
        {'insight': 'Code braucht Struktur', 'confidence': 0.9, 'category': 'skill'},
    ]}
    mock_exp_b = {'experiences': [
        {'insight': 'Musik heilt die Seele', 'confidence': 0.7, 'category': 'life'},
        {'insight': 'Vertrauen muss wachsen', 'confidence': 0.85, 'category': 'social'},
    ]}
    def mock_read_exp(eid, layer, fname):
        if eid == 'parent_a' and fname == 'experience.yaml':
            return mock_exp_a
        if eid == 'parent_b' and fname == 'experience.yaml':
            return mock_exp_b
        return read_yaml_organ(eid, layer, fname)
    with patch('engine.genesis.read_yaml_organ', side_effect=mock_read_exp):
        erfahrungen = erfahrungs_destillation('parent_a', 'parent_b')
    # Confidence = original * 0.5 (also UNTER der Original-Confidence)
    ok = len(erfahrungen) <= 10 and all(
        0.0 < e.get('confidence', 1.0) <= 0.5 and e.get('vererbt') == True
        for e in erfahrungen
    )
    print(f'      Erfahrungen destilliert: {len(erfahrungen)} (max 10)')
    for e in erfahrungen:
        print(f'        [{e.get("category", "?")}] {e["insight"]} (conf: {e["confidence"]})')
    print(f'      Alle bei 50%% der Original-Confidence + vererbt=True: {"OK" if ok else "FAIL"}')
    if ok: p3_pass += 1
    else: p3_fail += 1

    # Test 10: _generate_state_yaml() — Pflichtfelder
    print(f'  [10] _generate_state_yaml()...')
    test_blueprint = {
        'libero_id': 'noel_007',
        'name': 'Noel',
        'geschlecht': 'M',
        'eltern': ['adam_001', 'eva_002'],
        'dna_profile': 'DEFAULT',
        'drives': kind_drives,
        'skills': [],
        'erfahrungen': [],
        'start_date': '2026-02-26',
        'end_date': '2026-03-12',
    }
    gen_state = _generate_state_yaml(test_blueprint)
    required_keys = ['geschlecht', 'dna_profile', 'drives', 'survive', 'thrive',
                     'express', 'processing', 'emotional_gravity', 'pairing']
    missing = [k for k in required_keys if k not in gen_state]
    ok = len(missing) == 0
    pairing_ok = (gen_state.get('pairing', {}).get('eltern') == ['adam_001', 'eva_002']
                  and gen_state.get('pairing', {}).get('kinder') == [])
    print(f'      Pflichtfelder: {len(required_keys) - len(missing)}/{len(required_keys)}')
    if missing:
        print(f'      Fehlend: {missing}')
    print(f'      Pairing mit Eltern: {"OK" if pairing_ok else "FAIL"}')
    ok = ok and pairing_ok
    print(f'      {"OK" if ok else "FAIL"}')
    if ok: p3_pass += 1
    else: p3_fail += 1

    # Test 11: _generate_bonds_yaml() — Eltern-Bonds
    print(f'  [11] _generate_bonds_yaml()...')
    gen_bonds = _generate_bonds_yaml(test_blueprint)
    bonds_list = gen_bonds.get('bonds', [])
    # Erwarte: Owner + 2 Eltern-Bonds
    eltern_bonds = [b for b in bonds_list if b.get('bond_typ') == 'eltern_kind']
    owner_bonds = [b for b in bonds_list if b.get('bond_typ') == 'owner']
    ok = len(eltern_bonds) == 2 and len(owner_bonds) == 1
    print(f'      Total Bonds: {len(bonds_list)}')
    print(f'      Eltern-Kind Bonds: {len(eltern_bonds)} (erwartet: 2)')
    print(f'      Owner Bonds: {len(owner_bonds)} (erwartet: 1)')
    for b in bonds_list:
        print(f'        {b.get("id")}: bond_typ={b.get("bond_typ")}, score={b.get("score")}')
    print(f'      {"OK" if ok else "FAIL"}')
    if ok: p3_pass += 1
    else: p3_fail += 1

except Exception as e:
    print(f'  FEHLER: {e}')
    import traceback
    traceback.print_exc()
    p3_fail += 1

print()
print(f'  Patch 6 Phase 3: {p3_pass}/{p3_pass + p3_fail} Tests bestanden')
if p3_fail == 0:
    print(f'  ALLE PATCH 6 PHASE 3 TESTS BESTANDEN!')
else:
    print(f'  {p3_fail} Tests FEHLGESCHLAGEN!')

print()
print('=' * 60)
print(' SIMULATION ABGESCHLOSSEN')
print('=' * 60)
'''

sftp.open('/tmp/_sim_eva.py', 'w').write(sim_script)
stdin, stdout, stderr = ssh.exec_command('cd /opt/hivecore-v2 && source venv/bin/activate 2>/dev/null; python3 /tmp/_sim_eva.py 2>&1')
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err.strip():
    print('STDERR:', err[:1000])

ssh.exec_command('rm -f /tmp/_sim_eva.py')
sftp.close()
ssh.close()
