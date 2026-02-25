"""Actual deploy: git pull + rsync + restart + drive fix."""
import paramiko
import time
import json
import urllib.request

HOST = '159.69.157.42'
PW = '$7pa+12+67kR#rPK$7pah'
API = f'http://{HOST}:8001'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username='root', password=PW, timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    return stdout.read().decode(), stderr.read().decode()

# Step 1: Git Pull
print('[1/5] Git Pull...')
out, err = run('cd /root/hivecore-v2 && git pull origin master 2>&1')
print(f'  {out.strip()[:200]}')

# Step 2: Rsync
print('[2/5] Rsync...')
out, err = run(
    'rsync -av --delete '
    '--exclude .git --exclude venv --exclude __pycache__ --exclude egons/ '
    '--exclude .env --exclude "*.pyc" --exclude snapshots/ '
    '/root/hivecore-v2/ /opt/hivecore-v2/ 2>&1 | tail -5'
)
print(f'  {out.strip()[:200]}')

# Step 3: Restart
print('[3/5] Restart...')
out, err = run('systemctl restart hivecore 2>&1')
print(f'  RESTART: {out.strip() or "OK"}')
time.sleep(5)
out, err = run('systemctl is-active hivecore 2>&1')
status = out.strip()
print(f'  STATUS: {status}')

if status != 'active':
    print('  FEHLER! Logs:')
    out, err = run('journalctl -u hivecore --no-pager -n 30 2>&1')
    print(out)
    ssh.close()
    exit(1)

# Step 4: Drive-Korrektur + dna_profile
print('[4/5] Drive-Korrektur + dna_profile...')

fix_script = '''import yaml
from pathlib import Path

EGONS_DIR = Path("/opt/hivecore-v2/egons")

fixes = {
    "lilith_003": {
        "dna_profile": "SEEKING/PLAY",
        "drives": {
            "SEEKING": 0.90, "PLAY": 0.82, "LEARNING": 0.65, "CARE": 0.50,
            "ACTION": 0.48, "LUST": 0.20, "FEAR": 0.15, "RAGE": 0.12,
            "PANIC": 0.10, "GRIEF": 0.06
        },
        "emotions": [
            {"type": "curiosity", "intensity": 0.70, "cause": "Genesis",
             "onset": "2026-02-25", "decay_class": "slow",
             "verbal_anchor": "Alles ist neu. Was ist das hier?"},
            {"type": "excitement", "intensity": 0.65, "cause": "Neugier auf die Welt",
             "onset": "2026-02-25", "decay_class": "fast",
             "verbal_anchor": "Ich will alles sehen!"}
        ]
    },
    "kain_004": {
        "dna_profile": "CARE/PANIC",
        "drives": {
            "CARE": 0.88, "PANIC": 0.78, "SEEKING": 0.60, "LEARNING": 0.55,
            "GRIEF": 0.45, "FEAR": 0.40, "ACTION": 0.35, "PLAY": 0.25,
            "LUST": 0.20, "RAGE": 0.18
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
             "verbal_anchor": "Vielleicht gehoere ich irgendwo hin."}
        ]
    }
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
    print()

print("Drive-Fix DONE")
'''

# Script auf Server schreiben
sftp = ssh.open_sftp()
with sftp.open('/tmp/_fix_drives.py', 'w') as f:
    f.write(fix_script)
sftp.close()

out, err = run('cd /opt/hivecore-v2 && python3 /tmp/_fix_drives.py 2>&1')
print(out)
if err.strip():
    print(f'  STDERR: {err}')

run('rm -f /tmp/_fix_drives.py')

# Step 5: Verifikation
print('[5/5] Verifikation...')
time.sleep(2)

for eid, expected in [('lilith_003', 'SEEKING/PLAY'), ('kain_004', 'CARE/PANIC'), ('eva_002', 'FALLBACK'), ('adam_001', 'FALLBACK')]:
    try:
        req = urllib.request.Request(f'{API}/api/egon/{eid}/profile')
        with urllib.request.urlopen(req, timeout=10) as resp:
            profile = json.loads(resp.read().decode())
        drives = profile.get('drives', {})
        top3 = sorted(drives.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f'  {eid}: Top3={[f"{k}={v}" for k,v in top3]}, mood={profile.get("mood")}')
    except Exception as e:
        print(f'  {eid}: FEHLER: {e}')

ssh.close()

print()
print('=' * 60)
print(' DEPLOY + FIX COMPLETE')
print('=' * 60)
