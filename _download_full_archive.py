"""Download complete EGON data archive from server for scientific documentation."""
import paramiko
import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)
sftp = ssh.open_sftp()

timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M')
archive_dir = f'C:/Dev/EGONS/hivecore-v2/docs/archive_{timestamp}'
os.makedirs(archive_dir, exist_ok=True)

files_to_download = [
    # Adam v1
    ('/opt/hivecore-v2/egons/adam_001/memory.md', 'adam_001/memory.md'),
    ('/opt/hivecore-v2/egons/adam_001/experience.md', 'adam_001/experience.md'),
    ('/opt/hivecore-v2/egons/adam_001/inner_voice.md', 'adam_001/inner_voice.md'),
    ('/opt/hivecore-v2/egons/adam_001/markers.md', 'adam_001/markers.md'),
    ('/opt/hivecore-v2/egons/adam_001/bonds.md', 'adam_001/bonds.md'),
    ('/opt/hivecore-v2/egons/adam_001/soul.md', 'adam_001/soul.md'),
    ('/opt/hivecore-v2/egons/adam_001/skills.md', 'adam_001/skills.md'),
    ('/opt/hivecore-v2/egons/adam_001/wallet.md', 'adam_001/wallet.md'),
    # Eva v2
    ('/opt/hivecore-v2/egons/eva_002/memory.md', 'eva_002/memory.md'),
    ('/opt/hivecore-v2/egons/eva_002/inner_voice.md', 'eva_002/inner_voice.md'),
    ('/opt/hivecore-v2/egons/eva_002/wallet.md', 'eva_002/wallet.md'),
    ('/opt/hivecore-v2/egons/eva_002/memory/experience.yaml', 'eva_002/memory/experience.yaml'),
    ('/opt/hivecore-v2/egons/eva_002/memory/episodes.yaml', 'eva_002/memory/episodes.yaml'),
    ('/opt/hivecore-v2/egons/eva_002/memory/emotional_state.yaml', 'eva_002/memory/emotional_state.yaml'),
    ('/opt/hivecore-v2/egons/eva_002/memory/inner_voice.yaml', 'eva_002/memory/inner_voice.yaml'),
    ('/opt/hivecore-v2/egons/eva_002/core/dna.md', 'eva_002/core/dna.md'),
    ('/opt/hivecore-v2/egons/eva_002/social/bonds.yaml', 'eva_002/social/bonds.yaml'),
    ('/opt/hivecore-v2/egons/eva_002/social/reputation.yaml', 'eva_002/social/reputation.yaml'),
    ('/opt/hivecore-v2/egons/eva_002/capabilities/skills.yaml', 'eva_002/capabilities/skills.yaml'),
]

downloaded = 0
errors = 0
for remote_path, local_name in files_to_download:
    local_path = os.path.join(archive_dir, local_name)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    try:
        sftp.get(remote_path, local_path)
        size = os.path.getsize(local_path)
        print(f'  ✓ {local_name} ({size:,} bytes)')
        downloaded += 1
    except FileNotFoundError:
        print(f'  ✗ {local_name} — NOT FOUND (skipped)')
        errors += 1
    except Exception as e:
        print(f'  ✗ {local_name} — ERROR: {e}')
        errors += 1

# Also capture server logs
print('\n  Capturing server logs...')
stdin, stdout, stderr = ssh.exec_command(
    'journalctl -u hivecore --no-pager --since "2026-02-20" 2>&1'
)
logs = stdout.read().decode('utf-8')
log_path = os.path.join(archive_dir, 'server_logs_full.txt')
with open(log_path, 'w', encoding='utf-8') as f:
    f.write(logs)
print(f'  ✓ server_logs_full.txt ({len(logs):,} chars)')

sftp.close()
ssh.close()

print(f'\n{"="*50}')
print(f'Archive saved to: {archive_dir}')
print(f'Files downloaded: {downloaded}')
print(f'Files skipped: {errors}')
print(f'{"="*50}')
