"""Deploy per SFTP — Dateien direkt auf Server + Drive-Korrektur + dna_profile.

Kein Git noetig. Kopiert geaenderte/neue Dateien direkt nach /opt/hivecore-v2/.
"""
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
REMOTE_EGONS = f'{REMOTE_BASE}/egons'

# Alle Dateien die deployed werden muessen (relativ zu hivecore-v2/)
DEPLOY_FILES = [
    # Neue Dateien (Patch 1-3)
    'engine/somatic_gate.py',
    'engine/circadian.py',
    'engine/lobby.py',
    'engine/social_mapping.py',
    'api/lobby.py',
    # Modifizierte Dateien
    'engine/pulse_v2.py',
    'engine/prompt_builder_v2.py',
    'engine/context_budget_v2.py',
    'api/chat.py',
    'main.py',
]


def fetch_api(path):
    try:
        req = urllib.request.Request(f'{API_BASE}/{path}')
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {'error': str(e)}


print('=' * 60)
print(' SFTP DEPLOY + DRIVE-FIX')
print('=' * 60)
print()

# ================================================================
# Phase 1: SSH + SFTP Verbindung
# ================================================================
print('[1/5] SSH Verbindung...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PW, timeout=15)
sftp = ssh.open_sftp()
print('  Verbunden.')

# ================================================================
# Phase 2: Dateien hochladen
# ================================================================
print()
print(f'[2/5] {len(DEPLOY_FILES)} Dateien hochladen...')

for rel_path in DEPLOY_FILES:
    local_path = os.path.join(LOCAL_BASE, rel_path).replace('\\', '/')
    remote_path = f'{REMOTE_BASE}/{rel_path}'

    # Remote-Verzeichnis erstellen falls noetig
    remote_dir = '/'.join(remote_path.split('/')[:-1])
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {remote_dir}')
        stdout.read()

    try:
        sftp.put(local_path, remote_path)
        local_size = os.path.getsize(local_path)
        print(f'  [OK] {rel_path} ({local_size} bytes)')
    except Exception as e:
        print(f'  [ERR] {rel_path}: {e}')

# ================================================================
# Phase 3: Service restart
# ================================================================
print()
print('[3/5] Service restart...')

stdin, stdout, stderr = ssh.exec_command('systemctl restart hivecore 2>&1')
out = stdout.read().decode()
print(f'  RESTART: {out.strip() or "OK"}')

time.sleep(5)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active hivecore 2>&1')
status = stdout.read().decode().strip()
print(f'  STATUS: {status}')

if status != 'active':
    print('  WARNUNG: Service nicht aktiv!')
    stdin, stdout, stderr = ssh.exec_command('journalctl -u hivecore --no-pager -n 30 2>&1')
    print(stdout.read().decode())
    sftp.close()
    ssh.close()
    exit(1)

# API Health Check
time.sleep(2)
health = fetch_api('')
if 'error' in health:
    # Versuche Root-Endpoint
    try:
        req = urllib.request.Request(f'http://{HOST}:8001/')
        with urllib.request.urlopen(req, timeout=10) as resp:
            health = json.loads(resp.read().decode())
    except:
        pass

print(f'  API: {health.get("name", "?")} v{health.get("version", "?")} — {health.get("egon_count", "?")} EGONs')

# ================================================================
# Phase 4: Drive-Korrektur + dna_profile
# ================================================================
print()
print('[4/5] Drive-Korrektur + dna_profile...')

fix_script = r'''
import yaml
from pathlib import Path

EGONS_DIR = Path("/opt/hivecore-v2/egons")

fixes = {
    "lilith_003": {
        "dna_profile": "SEEKING/PLAY",
        "drives": {
            "SEEKING": 0.90, "PLAY": 0.82, "LEARNING": 0.65, "CARE": 0.50,
            "ACTION": 0.48, "LUST": 0.20, "FEAR": 0.15, "RAGE": 0.12,
            "PANIC": 0.10, "GRIEF": 0.06,
        },
        "emotions": [
            {"type": "curiosity", "intensity": 0.70, "cause": "Genesis",
             "onset": "2026-02-25", "decay_class": "slow",
             "verbal_anchor": "Alles ist neu. Was ist das hier?"},
            {"type": "excitement", "intensity": 0.65, "cause": "Neugier auf die Welt",
             "onset": "2026-02-25", "decay_class": "fast",
             "verbal_anchor": "Ich will alles sehen!"},
        ],
    },
    "kain_004": {
        "dna_profile": "CARE/PANIC",
        "drives": {
            "CARE": 0.88, "PANIC": 0.78, "SEEKING": 0.60, "LEARNING": 0.55,
            "GRIEF": 0.45, "FEAR": 0.40, "ACTION": 0.35, "PLAY": 0.25,
            "LUST": 0.20, "RAGE": 0.18,
        },
        "emotions": [
            {"type": "curiosity", "intensity": 0.55, "cause": "Genesis",
             "onset": "2026-02-25", "decay_class": "slow",
             "verbal_anchor": "Wer bin ich? Was ist hier?"},
            {"type": "anxiety", "intensity": 0.40, "cause": "Unsicherheit",
             "onset": "2026-02-25", "decay_class": "slow",
             "verbal_anchor": "Ich weiss nicht ob das hier sicher ist."},
            {"type": "hope", "intensity": 0.50, "cause": "Wunsch nach Zugehoerigkeit",
             "onset": "2026-02-25", "decay_class": "slow",
             "verbal_anchor": "Vielleicht gehoere ich irgendwo hin."},
        ],
    },
}

for egon_id, fix in fixes.items():
    state_path = EGONS_DIR / egon_id / "core" / "state.yaml"
    if not state_path.exists():
        print(f"  SKIP {egon_id}: state.yaml nicht gefunden")
        continue

    with open(state_path, "r") as f:
        state = yaml.safe_load(f) or {}

    old_drives = state.get("drives", {})
    old_top3 = sorted(old_drives.items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"  {egon_id} VORHER: top3={old_top3}, dna_profile={state.get('dna_profile', 'NICHT GESETZT')}")

    state["dna_profile"] = fix["dna_profile"]
    state["drives"] = fix["drives"]

    express = state.get("express", {})
    if not express.get("active_emotions"):
        express["active_emotions"] = fix["emotions"]
        state["express"] = express

    with open(state_path, "w") as f:
        yaml.dump(state, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    with open(state_path, "r") as f:
        verify = yaml.safe_load(f)
    new_top3 = sorted(verify.get("drives", {}).items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"  {egon_id} NACHHER: top3={new_top3}, dna_profile={verify.get('dna_profile')}")

print("DONE")
'''

# Script auf Server schreiben und ausfuehren
sftp.open('/tmp/_fix_drives.py', 'w').write(fix_script)
stdin, stdout, stderr = ssh.exec_command('cd /opt/hivecore-v2 && python3 /tmp/_fix_drives.py 2>&1')
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err.strip():
    print(f'  STDERR: {err}')

ssh.exec_command('rm -f /tmp/_fix_drives.py')

# ================================================================
# Phase 5: Verifikation
# ================================================================
print()
print('[5/5] Verifikation...')

for eid, expected in [('lilith_003', 'SEEKING/PLAY'), ('kain_004', 'CARE/PANIC')]:
    profile = fetch_api(f'egon/{eid}/profile')
    if 'error' in profile:
        print(f'  {eid}: API FEHLER: {profile["error"]}')
        continue

    drives = profile.get('drives', {})
    top3 = sorted(drives.items(), key=lambda x: x[1], reverse=True)[:3]
    top3_names = {d[0].upper() for d in top3}

    if 'SEEKING' in top3_names and 'PLAY' in top3_names:
        detected = 'SEEKING/PLAY'
    elif 'CARE' in top3_names or 'PANIC' in top3_names:
        detected = 'CARE/PANIC'
    else:
        detected = 'DEFAULT'

    ok = 'OK' if detected == expected else 'FEHLER'
    print(f'  {eid}: Top3={[f"{k}={v}" for k,v in top3]} → {detected} [{ok}]')

# Auch Eva und Adam pruefen (Fallback-Detection)
for eid in ['adam_001', 'eva_002']:
    profile = fetch_api(f'egon/{eid}/profile')
    drives = profile.get('drives', {})
    top3 = sorted(drives.items(), key=lambda x: x[1], reverse=True)[:3] if drives else []
    print(f'  {eid}: Top3={[f"{k}={v}" for k,v in top3]} (Fallback, kein dna_profile)')

sftp.close()
ssh.close()

print()
print('=' * 60)
print(' DEPLOY COMPLETE')
print('=' * 60)
