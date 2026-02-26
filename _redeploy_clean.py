"""Redeploy mit __pycache__ Cleanup — stellt sicher dass neuester Code geladen wird."""
import paramiko
import json
import urllib.request
import time
import os

HOST = '159.69.157.42'
USER = 'root'
PW = '$7pa+12+67kR#rPK$7pah'
API_BASE = f'http://{HOST}:8001/api'
LOCAL_BASE = 'C:/Dev/EGONS/hivecore-v2'
REMOTE_BASE = '/opt/hivecore-v2'

DEPLOY_FILES = [
    # Patch 9: State Recovery & Checkpoints
    'engine/state_validator.py',
    'engine/checkpoint.py',
    'engine/transaction.py',
    'engine/organ_reader.py',
    # Patch 14: Cue-Index
    'engine/cue_index.py',
    # Patch 8: Thalamus-Gate
    'engine/thalamus.py',
    # Patch 7: Echtzeit-Homoestase
    'engine/homoestase.py',
    # Patch 13: Arbeitsspeicher-Decay
    'engine/decay.py',
    # Patch 11: Metacognition
    'engine/metacognition.py',
    # Patch 10: Epigenetik
    'engine/epigenetik.py',
    # Patch 12: Multi-EGON Protokoll
    'engine/multi_egon.py',
    # Patch 16: Neuroplastizitaet
    'engine/neuroplastizitaet.py',
    # Existing
    'engine/naming.py',
    'engine/somatic_gate.py',
    'engine/circadian.py',
    'engine/lobby.py',
    'engine/social_mapping.py',
    'api/lobby.py',
    'engine/recent_memory.py',
    'engine/bonds_v2.py',
    'engine/yaml_to_prompt.py',
    'engine/resonanz.py',
    'engine/genesis.py',
    'engine/prompt_builder.py',
    'engine/prompt_builder_v2.py',
    'engine/pulse_v2.py',
    'engine/context_budget_v2.py',
    'engine/contact_manager.py',
    'engine/episodes_v2.py',
    'engine/experience_v2.py',
    'engine/state_manager.py',
    'engine/pulse.py',
    'api/chat.py',
    'api/profile.py',
    'api/profile_server.py',
    'main.py',
]

print('=' * 60)
print(' REDEPLOY MIT __PYCACHE__ CLEANUP')
print('=' * 60)
print()

# SSH
print('[1/5] SSH Verbindung...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PW, timeout=30)
sftp = ssh.open_sftp()
print('  Verbunden.')

# __pycache__ loeschen
print()
print('[2/5] __pycache__ loeschen...')
for subdir in ['engine', 'api', '']:
    cache_dir = f'{REMOTE_BASE}/{subdir}/__pycache__' if subdir else f'{REMOTE_BASE}/__pycache__'
    stdin, stdout, stderr = ssh.exec_command(f'rm -rf {cache_dir} 2>&1')
    out = stdout.read().decode().strip()
    print(f'  rm -rf {cache_dir}: {out or "OK"}')

# Dateien hochladen
print()
print(f'[3/5] {len(DEPLOY_FILES)} Dateien hochladen...')
for rel_path in DEPLOY_FILES:
    local_path = os.path.join(LOCAL_BASE, rel_path).replace('\\', '/')
    remote_path = f'{REMOTE_BASE}/{rel_path}'
    remote_dir = '/'.join(remote_path.split('/')[:-1])
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        ssh.exec_command(f'mkdir -p {remote_dir}')
    try:
        sftp.put(local_path, remote_path)
        local_size = os.path.getsize(local_path)
        print(f'  [OK] {rel_path} ({local_size} bytes)')
    except Exception as e:
        print(f'  [ERR] {rel_path}: {e}')

# Restart
print()
print('[4/5] Service restart...')
stdin, stdout, stderr = ssh.exec_command('systemctl restart hivecore 2>&1')
out = stdout.read().decode()
print(f'  RESTART: {out.strip() or "OK"}')
time.sleep(5)
stdin, stdout, stderr = ssh.exec_command('systemctl is-active hivecore 2>&1')
status = stdout.read().decode().strip()
print(f'  STATUS: {status}')

# Verifiziere Dateiinhalte auf dem Server
print()
print('[5/5] Verifiziere Dateiinhalte auf Server...')

verify_script = r'''
import sys
sys.path.insert(0, '/opt/hivecore-v2')
import os
os.chdir('/opt/hivecore-v2')
os.environ['EGON_DATA_DIR'] = '/opt/hivecore-v2/egons'

# Check 1: INKUBATION_TAGE
from engine.genesis import INKUBATION_TAGE
print(f'  INKUBATION_TAGE: {INKUBATION_TAGE} (erwartet: 112) {"OK" if INKUBATION_TAGE == 112 else "FAIL"}')

# Check 2: REIFE_MIN_DAYS
from engine.resonanz import REIFE_MIN_DAYS
print(f'  REIFE_MIN_DAYS: {REIFE_MIN_DAYS} (erwartet: 224) {"OK" if REIFE_MIN_DAYS == 224 else "FAIL"}')

# Check 3: _update_lust_system existiert
from engine.resonanz import _update_lust_system
print(f'  _update_lust_system: vorhanden {"OK"}')

# Check 4: _apply_phase_transition_effects existiert
from engine.resonanz import _apply_phase_transition_effects
print(f'  _apply_phase_transition_effects: vorhanden {"OK"}')

# Check 5: _has_exclusive_bond existiert
from engine.bonds_v2 import _has_exclusive_bond
print(f'  _has_exclusive_bond: vorhanden {"OK"}')

# Check 6: LUST-System funktioniert
mock_state = {
    'drives': {'LUST': 0.3, 'FEAR': 0.2, 'PANIC': 0.2},
    'geschlecht': 'M',
    'pairing': {},
}
result = _update_lust_system('test', mock_state, 'partner', 0.5, 'erkennung', 'keine', False)
print(f'  LUST test: {result}')
has_suppressed = result.get('lust_suppressed', False)
print(f'  LUST suppressed (reif=False): {"OK" if has_suppressed else "FAIL"}')

# Check 7: Lobby import funktioniert
from engine.lobby import write_lobby, read_lobby
print(f'  write_lobby: importierbar OK')

# Check 8: romantisch_fest in yaml_to_prompt
from engine.yaml_to_prompt import pairing_to_prompt
print(f'  pairing_to_prompt: importierbar OK')

# Check 9: Datei-Groessen pruefen
import os
files = {
    'engine/resonanz.py': 27000,
    'engine/genesis.py': 40000,
    'engine/bonds_v2.py': 16000,
}
for f, min_size in files.items():
    path = f'/opt/hivecore-v2/{f}'
    size = os.path.getsize(path)
    ok = size >= min_size
    print(f'  {f}: {size} bytes (min {min_size}) {"OK" if ok else "FAIL"}')
'''

sftp.open('/tmp/_verify.py', 'w').write(verify_script)
stdin, stdout, stderr = ssh.exec_command('cd /opt/hivecore-v2 && source venv/bin/activate 2>/dev/null; python3 /tmp/_verify.py 2>&1')
out = stdout.read().decode()
print(out)
err = stderr.read().decode()
if err.strip():
    print(f'  STDERR: {err[:500]}')
ssh.exec_command('rm -f /tmp/_verify.py')

# API Health
time.sleep(2)
try:
    req = urllib.request.Request(f'http://{HOST}:8001/')
    with urllib.request.urlopen(req, timeout=10) as resp:
        health = json.loads(resp.read().decode())
    print(f'  API: {health.get("name", "?")} v{health.get("version", "?")} -- {health.get("egon_count", "?")} EGONs')
except Exception as e:
    print(f'  API: {e}')

sftp.close()
ssh.close()
print()
print('REDEPLOY COMPLETE')
