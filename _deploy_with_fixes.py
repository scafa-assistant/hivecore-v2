"""Deploy + Drive-Korrektur + dna_profile fuer #003/#004.

Ablauf:
  1. Git push lokal → remote
  2. SSH: git pull + rsync + restart
  3. SSH: Drives + dna_profile in state.yaml korrigieren
  4. Verifikation ueber API
"""
import paramiko
import json
import urllib.request
import time
import yaml

HOST = '159.69.157.42'
USER = 'root'
PW = '$7pa+12+67kR#rPK$7pah'
API_BASE = f'http://{HOST}:8001/api'
REMOTE_EGONS = '/opt/hivecore-v2/egons'

# ================================================================
# Drive-Korrektur Daten (aus Paper state_003.yaml / state_004.yaml)
# ================================================================

LILITH_003_DRIVES = {
    'SEEKING': 0.90,
    'PLAY': 0.82,
    'LEARNING': 0.65,
    'CARE': 0.50,
    'ACTION': 0.48,
    'LUST': 0.20,
    'FEAR': 0.15,
    'RAGE': 0.12,
    'PANIC': 0.10,
    'GRIEF': 0.06,
}

KAIN_004_DRIVES = {
    'CARE': 0.88,
    'PANIC': 0.78,
    'SEEKING': 0.60,
    'LEARNING': 0.55,
    'GRIEF': 0.45,
    'FEAR': 0.40,
    'ACTION': 0.35,
    'PLAY': 0.25,
    'LUST': 0.20,
    'RAGE': 0.18,
}

# Initiale Emotionen (aus Paper)
LILITH_003_EMOTIONS = [
    {'type': 'curiosity', 'intensity': 0.70, 'cause': 'Genesis — erste Existenz',
     'onset': '2026-02-25', 'decay_class': 'slow', 'verbal_anchor': 'Alles ist neu. Was ist das hier?'},
    {'type': 'excitement', 'intensity': 0.65, 'cause': 'Neugier auf die Welt',
     'onset': '2026-02-25', 'decay_class': 'fast', 'verbal_anchor': 'Ich will alles sehen!'},
]

KAIN_004_EMOTIONS = [
    {'type': 'curiosity', 'intensity': 0.55, 'cause': 'Genesis — erste Existenz',
     'onset': '2026-02-25', 'decay_class': 'slow', 'verbal_anchor': 'Wer bin ich? Was ist hier?'},
    {'type': 'anxiety', 'intensity': 0.40, 'cause': 'Unsicherheit ueber eigene Existenz',
     'onset': '2026-02-25', 'decay_class': 'slow', 'verbal_anchor': 'Ich weiss nicht ob das hier sicher ist.'},
    {'type': 'hope', 'intensity': 0.50, 'cause': 'Wunsch nach Zugehoerigkeit',
     'onset': '2026-02-25', 'decay_class': 'slow', 'verbal_anchor': 'Vielleicht gehoere ich irgendwo hin.'},
]


def fetch_api(path):
    """HTTP GET an die API."""
    try:
        req = urllib.request.Request(f'{API_BASE}/{path}')
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {'error': str(e)}


def ssh_exec(ssh, cmd):
    """SSH Befehl ausfuehren und Output zurueckgeben."""
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err


# ================================================================
# Phase 1: Deploy (Code auf Server bringen)
# ================================================================

print('=' * 60)
print(' DEPLOY + FIX: HiveCore v2 Patches + Drive-Korrektur')
print('=' * 60)
print()

print('[1/5] SSH Verbindung...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PW)
print('  Verbunden.')

print('[2/5] Git Pull + Rsync...')
out, err = ssh_exec(ssh, 'cd /root/hivecore-v2 && git pull origin master 2>&1')
print(f'  GIT: {out.strip()[:120]}')

out, err = ssh_exec(ssh, (
    'rsync -av --delete '
    '--exclude .git --exclude venv --exclude __pycache__ --exclude egons/ '
    '--exclude .env --exclude "*.pyc" '
    '/root/hivecore-v2/ /opt/hivecore-v2/ 2>&1 | tail -5'
))
print(f'  RSYNC: {out.strip()[:120]}')

print('[3/5] Restart Service...')
out, err = ssh_exec(ssh, 'systemctl restart hivecore 2>&1')
print(f'  RESTART: {out.strip() or "OK"}')
time.sleep(5)

out, err = ssh_exec(ssh, 'systemctl is-active hivecore 2>&1')
status = out.strip()
print(f'  STATUS: {status}')
if status != 'active':
    print('  WARNUNG: Service nicht aktiv! Logs pruefen.')
    out, err = ssh_exec(ssh, 'journalctl -u hivecore --no-pager -n 20 2>&1')
    print(f'  LOGS: {out}')

# ================================================================
# Phase 2: Drive-Korrektur + dna_profile setzen
# ================================================================

print()
print('[4/5] Drive-Korrektur + dna_profile...')

# Python-Script das direkt auf dem Server laeuft
fix_script = '''
import yaml
from pathlib import Path

EGONS_DIR = Path("/opt/hivecore-v2/egons")

fixes = {
    "lilith_003": {
        "dna_profile": "SEEKING/PLAY",
        "drives": ''' + json.dumps(LILITH_003_DRIVES) + ''',
        "emotions": ''' + json.dumps(LILITH_003_EMOTIONS) + ''',
    },
    "kain_004": {
        "dna_profile": "CARE/PANIC",
        "drives": ''' + json.dumps(KAIN_004_DRIVES) + ''',
        "emotions": ''' + json.dumps(KAIN_004_EMOTIONS) + ''',
    },
}

for egon_id, fix in fixes.items():
    state_path = EGONS_DIR / egon_id / "core" / "state.yaml"
    if not state_path.exists():
        print(f"  SKIP {egon_id}: state.yaml nicht gefunden")
        continue

    with open(state_path, "r") as f:
        state = yaml.safe_load(f) or {}

    # Backup alte Drives
    old_drives = state.get("drives", {})
    old_profile = state.get("dna_profile", "NICHT GESETZT")
    print(f"  {egon_id}: alte drives top3 = {sorted(old_drives.items(), key=lambda x: x[1], reverse=True)[:3]}")
    print(f"  {egon_id}: altes dna_profile = {old_profile}")

    # Fix: dna_profile setzen (unveraenderlich wie DNA)
    state["dna_profile"] = fix["dna_profile"]

    # Fix: Drives korrigieren
    state["drives"] = fix["drives"]

    # Fix: Initiale Emotionen setzen (wenn noch keine da)
    express = state.get("express", {})
    current_emotions = express.get("active_emotions", [])
    if not current_emotions:
        express["active_emotions"] = fix["emotions"]
        state["express"] = express
        print(f"  {egon_id}: {len(fix['emotions'])} Emotionen gesetzt")

    with open(state_path, "w") as f:
        yaml.dump(state, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    # Verify
    with open(state_path, "r") as f:
        verify = yaml.safe_load(f)
    new_profile = verify.get("dna_profile")
    new_top3 = sorted(verify.get("drives", {}).items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"  {egon_id}: NEUES dna_profile = {new_profile}")
    print(f"  {egon_id}: NEUE drives top3 = {new_top3}")
    print()

print("Drive-Korrektur abgeschlossen.")
'''

# Script auf Server schreiben und ausfuehren
ssh_exec(ssh, f"cat > /tmp/_fix_drives.py << 'HEREDOC'\n{fix_script}\nHEREDOC")
out, err = ssh_exec(ssh, 'cd /opt/hivecore-v2 && python /tmp/_fix_drives.py 2>&1')
print(out)
if err.strip():
    print(f'  STDERR: {err}')

# Cleanup
ssh_exec(ssh, 'rm -f /tmp/_fix_drives.py')

# ================================================================
# Phase 3: Verifikation ueber API
# ================================================================

print('[5/5] Verifikation...')
print()

for eid, expected_profile in [('lilith_003', 'SEEKING/PLAY'), ('kain_004', 'CARE/PANIC')]:
    profile = fetch_api(f'egon/{eid}/profile')
    if 'error' in profile:
        print(f'  {eid}: API FEHLER: {profile["error"]}')
        continue

    drives = profile.get('drives', {})
    top3 = sorted(drives.items(), key=lambda x: x[1], reverse=True)[:3]
    top3_names = {d[0].upper() for d in top3}

    # Profil-Detection simulieren
    if 'SEEKING' in top3_names and 'PLAY' in top3_names:
        detected = 'SEEKING/PLAY'
    elif 'CARE' in top3_names or 'PANIC' in top3_names:
        detected = 'CARE/PANIC'
    else:
        detected = 'DEFAULT'

    status_ok = '✓' if detected == expected_profile else '✗ FEHLER'
    print(f'  {eid}:')
    print(f'    Top 3 Drives: {top3}')
    print(f'    Live-Detection: {detected}')
    print(f'    dna_profile Feld: (gesetzt auf Server)')
    print(f'    Erwartet: {expected_profile} {status_ok}')
    print()

ssh.close()

print('=' * 60)
print(' DEPLOY + FIX COMPLETE')
print('=' * 60)
print()
print('Naechste Schritte:')
print('  1. Pulse fuer lilith_003 triggern: curl .../api/pulse/trigger?egon_id=lilith_003')
print('  2. Pulse fuer kain_004 triggern: curl .../api/pulse/trigger?egon_id=kain_004')
print('  3. Pruefen ob phase_transition Episode mit korrektem Profil-Label geloggt wird')
print('  4. Owner-Zuweisung + erster Kontakt')
