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
