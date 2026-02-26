"""Deploy per SFTP — Engine-Code + EGON-Daten (state, social_mapping, lobby).

Kein Git noetig. Kopiert geaenderte/neue Dateien direkt nach /opt/hivecore-v2/.
"""
import paramiko
import json
import urllib.request
import time
import os
import glob

HOST = '159.69.157.42'
USER = 'root'
PW = '$7pa+12+67kR#rPK$7pah'
API_BASE = f'http://{HOST}:8001/api'
LOCAL_BASE = 'C:/Dev/EGONS/hivecore-v2'
LOCAL_DATA = 'C:/Dev/EGONS/EGON_PATCHES/25.02/SERVER_BRAIN_DUMP/hivecore_live'
REMOTE_BASE = '/opt/hivecore-v2'
REMOTE_EGONS = f'{REMOTE_BASE}/egons'

AGENTS = ['adam_001', 'eva_002', 'lilith_003', 'kain_004', 'ada_005', 'abel_006']

# Engine-Dateien (relativ zu hivecore-v2/)
DEPLOY_FILES = [
    # Naming System (NEU)
    'engine/naming.py',
    # Neue Dateien (Patch 1-3)
    'engine/somatic_gate.py',
    'engine/circadian.py',
    'engine/lobby.py',
    'engine/social_mapping.py',
    'api/lobby.py',
    # Patch 5: Recent Memory
    'engine/recent_memory.py',
    # Patch 6 Phase 1: Geschlechtsspezifisches Bond-Wachstum
    'engine/bonds_v2.py',
    'engine/yaml_to_prompt.py',
    # Patch 6 Phase 2: Resonanz-Engine
    'engine/resonanz.py',
    # Patch 6 Phase 3: Genesis (Merge + Inkubation + LIBERI)
    'engine/genesis.py',
    # Modifizierte Dateien
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
# Phase 4: EGON-Daten hochladen (state.yaml, social_mapping, lobby)
# ================================================================
print()
print('[4/6] EGON-Daten hochladen...')

data_count = 0

def sftp_upload(local, remote):
    """Upload einzelne Datei, erstelle Remote-Verzeichnis falls noetig."""
    global data_count
    remote_dir = '/'.join(remote.split('/')[:-1])
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {remote_dir}')
        stdout.read()
    try:
        sftp.put(local, remote)
        data_count += 1
        return True
    except Exception as e:
        print(f'  [ERR] {local} -> {remote}: {e}')
        return False

# 4a: state.yaml fuer alle 6 Agents
for agent in AGENTS:
    local = f'{LOCAL_DATA}/{agent}/core/state.yaml'
    remote = f'{REMOTE_EGONS}/{agent}/core/state.yaml'
    if os.path.exists(local):
        sftp_upload(local, remote)
        print(f'  [OK] {agent}/core/state.yaml')
    else:
        print(f'  [SKIP] {agent}/core/state.yaml (lokal nicht gefunden)')

# 4b: social_mapping Dateien (Patch 5 Phase 2: neuer Pfad skills/memory/social_mapping/)
for agent in AGENTS:
    # Neuer Pfad hat Prioritaet
    sm_dir_new = f'{LOCAL_DATA}/{agent}/skills/memory/social_mapping'
    sm_dir_old = f'{LOCAL_DATA}/{agent}/social_mapping'
    sm_dir = sm_dir_new if os.path.isdir(sm_dir_new) else sm_dir_old
    if os.path.isdir(sm_dir):
        files = glob.glob(f'{sm_dir}/ueber_*.yaml')
        for f in files:
            fname = os.path.basename(f)
            # Immer in neuen Pfad auf Server hochladen
            remote = f'{REMOTE_EGONS}/{agent}/skills/memory/social_mapping/{fname}'
            sftp_upload(f.replace('\\', '/'), remote)
        print(f'  [OK] {agent}/skills/memory/social_mapping/ ({len(files)} Dateien)')

# 4c: shared/lobby_chat.yaml
lobby_local = f'{LOCAL_DATA}/shared/lobby_chat.yaml'
if os.path.exists(lobby_local):
    # Erstelle shared/ Verzeichnis auf Server
    stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {REMOTE_EGONS}/shared')
    stdout.read()
    sftp_upload(lobby_local, f'{REMOTE_EGONS}/shared/lobby_chat.yaml')
    print(f'  [OK] shared/lobby_chat.yaml')

# 4d: bonds.yaml fuer alle 6 Agents (Patch 6: +bond_typ)
for agent in AGENTS:
    local = f'{LOCAL_DATA}/{agent}/social/bonds.yaml'
    remote = f'{REMOTE_EGONS}/{agent}/social/bonds.yaml'
    if os.path.exists(local):
        sftp_upload(local, remote)
        print(f'  [OK] {agent}/social/bonds.yaml')
    else:
        print(f'  [SKIP] {agent}/social/bonds.yaml (lokal nicht gefunden)')

# 4e: skills/memory/recent_memory.md fuer alle 6 Agents
for agent in AGENTS:
    local = f'{LOCAL_DATA}/{agent}/skills/memory/recent_memory.md'
    remote = f'{REMOTE_EGONS}/{agent}/skills/memory/recent_memory.md'
    if os.path.exists(local):
        sftp_upload(local, remote)
        print(f'  [OK] {agent}/skills/memory/recent_memory.md')
    else:
        print(f'  [SKIP] {agent}/skills/memory/recent_memory.md (lokal nicht gefunden)')

print(f'  Gesamt: {data_count} Daten-Dateien hochgeladen')

# ================================================================
# Phase 5: Service restart (nach Daten-Upload)
# ================================================================
print()
print('[5/6] Service restart (nach Daten-Upload)...')

stdin, stdout, stderr = ssh.exec_command('systemctl restart hivecore 2>&1')
out = stdout.read().decode()
print(f'  RESTART: {out.strip() or "OK"}')
time.sleep(5)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active hivecore 2>&1')
status = stdout.read().decode().strip()
print(f'  STATUS: {status}')

# ================================================================
# Phase 6: Verifikation
# ================================================================
print()
print('[6/6] Verifikation...')

time.sleep(3)

expected_profiles = {
    'adam_001': 'DEFAULT',
    'eva_002': 'DEFAULT',
    'lilith_003': 'SEEKING/PLAY',
    'kain_004': 'SEEKING/PLAY',
    'ada_005': 'CARE/PANIC',
    'abel_006': 'DEFAULT',
}

# Pruefe state.yaml auf Server via SSH
verify_script = r'''
import yaml
from pathlib import Path

EGONS_DIR = Path("/opt/hivecore-v2/egons")
agents = ["adam_001", "eva_002", "lilith_003", "kain_004", "ada_005", "abel_006"]

for a in agents:
    state_path = EGONS_DIR / a / "core" / "state.yaml"
    if not state_path.exists():
        print(f"  {a}: state.yaml FEHLT")
        continue
    with open(state_path, "r") as f:
        d = yaml.safe_load(f) or {}
    dna = d.get("dna_profile", "FEHLT")
    zirk = "OK" if "zirkadian" in d else "FEHLT"
    som = "OK" if "somatic_gate" in d else "FEHLT"
    energy_s = d.get("survive", {}).get("energy", {}).get("value", "?")
    energy_z = d.get("zirkadian", {}).get("energy", "?")
    sync = "OK" if energy_s == energy_z else f"MISMATCH ({energy_s} vs {energy_z})"
    sm_dir_new = EGONS_DIR / a / "skills" / "memory" / "social_mapping"
    sm_dir_old = EGONS_DIR / a / "social_mapping"
    sm_dir = sm_dir_new if sm_dir_new.exists() else sm_dir_old
    sm_count = len(list(sm_dir.glob("ueber_*.yaml"))) if sm_dir.exists() else 0
    sm_path = "NEW" if sm_dir == sm_dir_new else "OLD"
    rm = "OK" if (EGONS_DIR / a / "skills" / "memory" / "recent_memory.md").exists() else "FEHLT"
    geschl = d.get("geschlecht", "FEHLT")
    pairing = "OK" if "pairing" in d else "FEHLT"
    # Bonds: bond_typ pruefen
    bonds_path = EGONS_DIR / a / "social" / "bonds.yaml"
    bond_typ_info = "?"
    if bonds_path.exists():
        with open(bonds_path, "r") as bf:
            bd = yaml.safe_load(bf) or {}
        bond_typs = [b.get("bond_typ", "FEHLT") for b in bd.get("bonds", [])]
        bond_typ_info = ",".join(bond_typs) if bond_typs else "keine_bonds"
    print(f"  {a}: dna={dna} geschl={geschl} pairing={pairing} zirk={zirk} som={som} bond_typ=[{bond_typ_info}] social_maps={sm_count}({sm_path}) recent_mem={rm}")

lobby = EGONS_DIR / "shared" / "lobby_chat.yaml"
print(f"  lobby_chat.yaml: {'OK' if lobby.exists() else 'FEHLT'}")
'''

sftp.open('/tmp/_verify.py', 'w').write(verify_script)
stdin, stdout, stderr = ssh.exec_command('python3 /tmp/_verify.py 2>&1')
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err.strip():
    print(f'  STDERR: {err}')
ssh.exec_command('rm -f /tmp/_verify.py')

# API Health
health = fetch_api('')
if 'error' in health:
    try:
        req = urllib.request.Request(f'http://{HOST}:8001/')
        with urllib.request.urlopen(req, timeout=10) as resp:
            health = json.loads(resp.read().decode())
    except:
        pass
print(f'  API: {health.get("name", "?")} v{health.get("version", "?")} -- {health.get("egon_count", "?")} EGONs')

sftp.close()
ssh.close()

print()
print('=' * 60)
print(' DEPLOY COMPLETE')
print('=' * 60)
