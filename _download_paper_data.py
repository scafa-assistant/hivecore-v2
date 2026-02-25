"""Download ALL current EGON data from server for paper folder."""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

PAPER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paper')

def ssh_connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw)
    return ssh

def download_file(sftp, remote_path, local_path):
    """Download a file, creating dirs as needed."""
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    try:
        sftp.get(remote_path, local_path)
        size = os.path.getsize(local_path)
        print(f'  OK: {remote_path} ({size} bytes)')
    except Exception as e:
        print(f'  SKIP: {remote_path} — {e}')

def run_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode('utf-8').strip()

ssh = ssh_connect()
sftp = ssh.open_sftp()

# ================================================================
# EVA 002 — Current live state (post all experiments)
# ================================================================
print('\n=== EVA 002 — Current Live State ===')
eva_base = '/opt/hivecore-v2/egons/eva_002'
eva_local = os.path.join(PAPER_DIR, '03_agent_data', 'eva_002_v2_brain')

eva_files = [
    'core/dna.md',
    'core/state.yaml',
    'memory/episodes.yaml',
    'memory/experience.yaml',
    'memory/emotional_state.yaml',
    'memory/inner_voice.md',
    'memory/inner_voice.yaml',
    'social/bonds.yaml',
    'social/reputation.yaml',
    'social/network.yaml',
    'capabilities/skills.yaml',
    'capabilities/wallet.yaml',
    'config/settings.yaml',
]

for f in eva_files:
    download_file(sftp, f'{eva_base}/{f}', os.path.join(eva_local, f))

# Also get wallet.md if exists
download_file(sftp, f'{eva_base}/wallet.md', os.path.join(eva_local, 'wallet.md'))

# ================================================================
# ADAM 001 — Current live state
# ================================================================
print('\n=== ADAM 001 — Current Live State ===')
adam_base = '/opt/hivecore-v2/egons/adam_001'
adam_local = os.path.join(PAPER_DIR, '03_agent_data', 'adam_001_v1_brain')

# v1 brain files
adam_v1_files = [
    'soul.md',
    'memory.md',
    'markers.md',
    'bonds.md',
    'inner_voice.md',
    'skills.md',
    'wallet.md',
    'experience.md',
]

for f in adam_v1_files:
    download_file(sftp, f'{adam_base}/{f}', os.path.join(adam_local, f))

# v2 overlay files (Adam has both)
adam_v2_files = [
    'core/dna.md',
    'core/state.yaml',
    'core/ego.md',
    'memory/episodes.yaml',
    'memory/experience.yaml',
    'memory/inner_voice.md',
    'social/bonds.yaml',
    'social/owner.md',
    'social/egon_self.md',
    'social/network.yaml',
    'capabilities/skills.yaml',
    'capabilities/wallet.yaml',
    'config/settings.yaml',
]

for f in adam_v2_files:
    download_file(sftp, f'{adam_base}/{f}', os.path.join(adam_local, f))

# ================================================================
# SERVER LOGS — Last 200 lines of service log
# ================================================================
print('\n=== Server Logs ===')
logs = run_cmd(ssh, 'journalctl -u hivecore --no-pager -n 200 2>&1')
log_path = os.path.join(PAPER_DIR, '06_server_snapshots', 'server_log_latest.txt')
os.makedirs(os.path.dirname(log_path), exist_ok=True)
with open(log_path, 'w', encoding='utf-8') as f:
    f.write(logs)
print(f'  OK: server_log_latest.txt ({len(logs)} chars)')

# ================================================================
# SNAPSHOT DATA — Latest snapshot info
# ================================================================
print('\n=== Snapshots ===')
snapshots = run_cmd(ssh, 'ls -la /opt/hivecore-v2/egons/eva_002/snapshots/ 2>&1')
snap_path = os.path.join(PAPER_DIR, '06_server_snapshots', 'eva_snapshots_listing.txt')
with open(snap_path, 'w', encoding='utf-8') as f:
    f.write(snapshots)
print(f'  OK: eva_snapshots_listing.txt')

adam_snapshots = run_cmd(ssh, 'ls -la /opt/hivecore-v2/egons/adam_001/snapshots/ 2>&1')
asnap_path = os.path.join(PAPER_DIR, '06_server_snapshots', 'adam_snapshots_listing.txt')
with open(asnap_path, 'w', encoding='utf-8') as f:
    f.write(adam_snapshots)
print(f'  OK: adam_snapshots_listing.txt')

# Inner voice hidden flag status
flag = run_cmd(ssh, 'test -f /opt/hivecore-v2/.inner_voice_hidden && echo "ACTIVE — Inner Voice is PRIVATE" || echo "NOT ACTIVE — Inner Voice is VISIBLE"')
flag_path = os.path.join(PAPER_DIR, '06_server_snapshots', 'inner_voice_hidden_flag_status.txt')
with open(flag_path, 'w', encoding='utf-8') as f:
    f.write(f'Flag-File: .inner_voice_hidden\n')
    f.write(f'Status: {flag}\n')
    f.write(f'Location: /opt/hivecore-v2/.inner_voice_hidden\n')
    f.write(f'Effect: When present, Inner Voice is generated and stored but NOT included in system prompt\n')
print(f'  OK: inner_voice_hidden_flag_status.txt — {flag}')

# Service status
svc = run_cmd(ssh, 'systemctl status hivecore 2>&1')
svc_path = os.path.join(PAPER_DIR, '06_server_snapshots', 'hivecore_service_status.txt')
with open(svc_path, 'w', encoding='utf-8') as f:
    f.write(svc)
print(f'  OK: hivecore_service_status.txt')

sftp.close()
ssh.close()
print('\n=== DOWNLOAD COMPLETE ===')
