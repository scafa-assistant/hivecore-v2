"""Baseline-Snapshot: Adam + Eva + Pulse-Logs VOR Patch-Deploy sichern.

Zieht ALLE Daten vom Server in einen timestamped Ordner.
Kritisch: Diese Daten sind der Pilotstudien-Datensatz (20.02-25.02).
"""
import paramiko
import os
from datetime import datetime
from pathlib import Path

HOST = '159.69.157.42'
USER = 'root'
PW = 'z##rPK$7pahrwQ2H67kR'
REMOTE_EGONS = '/opt/hivecore-v2/egons'

# Lokaler Snapshot-Ordner
timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
LOCAL_BASE = Path(f'C:/Dev/EGONS/hivecore-v2/snapshots/pre_patch_{timestamp}')
LOCAL_BASE.mkdir(parents=True, exist_ok=True)

print(f'=== BASELINE SNAPSHOT ===')
print(f'Ziel: {LOCAL_BASE}')
print()

# SSH Verbindung
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PW)
sftp = ssh.open_sftp()


def download_recursive(remote_path, local_path):
    """Rekursiv alle Dateien runterladen."""
    local_path = Path(local_path)
    local_path.mkdir(parents=True, exist_ok=True)

    count = 0
    try:
        entries = sftp.listdir_attr(remote_path)
    except FileNotFoundError:
        print(f'  [SKIP] {remote_path} existiert nicht')
        return 0

    for entry in entries:
        remote_file = f'{remote_path}/{entry.filename}'
        local_file = local_path / entry.filename

        if entry.st_mode & 0o40000:  # Directory
            count += download_recursive(remote_file, local_file)
        else:
            try:
                sftp.get(remote_file, str(local_file))
                count += 1
            except Exception as e:
                print(f'  [ERR] {remote_file}: {e}')
    return count


# ================================================================
# 1. Adam komplett sichern
# ================================================================
print('[1/5] Adam sichern...')
# Pruefe welche Adam-Varianten existieren
for name in ['adam', 'adam_001']:
    try:
        sftp.stat(f'{REMOTE_EGONS}/{name}')
        n = download_recursive(f'{REMOTE_EGONS}/{name}', LOCAL_BASE / name)
        print(f'  {name}: {n} Dateien gesichert')
    except FileNotFoundError:
        print(f'  {name}: nicht vorhanden')

# ================================================================
# 2. Eva komplett sichern
# ================================================================
print('[2/5] Eva sichern...')
for name in ['eva', 'eva_002']:
    try:
        sftp.stat(f'{REMOTE_EGONS}/{name}')
        n = download_recursive(f'{REMOTE_EGONS}/{name}', LOCAL_BASE / name)
        print(f'  {name}: {n} Dateien gesichert')
    except FileNotFoundError:
        print(f'  {name}: nicht vorhanden')

# ================================================================
# 3. Shared-Ordner sichern (friendships, lobby)
# ================================================================
print('[3/5] Shared sichern...')
try:
    n = download_recursive(f'{REMOTE_EGONS}/shared', LOCAL_BASE / 'shared')
    print(f'  shared: {n} Dateien gesichert')
except Exception as e:
    print(f'  shared: {e}')

# ================================================================
# 4. Pulse-Logs / Cron-Logs suchen
# ================================================================
print('[4/5] Pulse-Logs suchen...')

# Scheduler/Cron-Logs
log_searches = [
    'find /opt/hivecore-v2 -name "*.log" -o -name "pulse_history*" -o -name "pulse_log*" 2>/dev/null',
    'find /opt/hivecore-v2/egons -name "ledger*" -o -name "pulse*log*" 2>/dev/null',
    'journalctl -u hivecore --since "2025-02-20" --until "2025-02-26" --no-pager 2>/dev/null | head -200',
    'crontab -l 2>/dev/null',
    'cat /opt/hivecore-v2/server.log 2>/dev/null | grep -i pulse | tail -50',
]

logs_dir = LOCAL_BASE / '_logs'
logs_dir.mkdir(exist_ok=True)

for i, cmd in enumerate(log_searches):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip():
        log_file = logs_dir / f'log_search_{i}.txt'
        log_file.write_text(f'CMD: {cmd}\n\n{out}\n\nSTDERR:\n{err}')
        print(f'  [{i}] Gefunden: {out.strip()[:120]}')
    else:
        print(f'  [{i}] Nichts gefunden')

# Ledger-Dateien (enthalten Pulse-Timestamps)
print()
print('  Ledger-Dateien suchen...')
stdin, stdout, stderr = ssh.exec_command(
    f'find {REMOTE_EGONS} -name "ledger*" -type f 2>/dev/null'
)
ledger_files = stdout.read().decode().strip().split('\n')
for lf in ledger_files:
    if lf.strip():
        local_name = lf.strip().replace('/', '_').lstrip('_')
        try:
            sftp.get(lf.strip(), str(logs_dir / local_name))
            print(f'  Ledger: {lf.strip()}')
        except Exception as e:
            print(f'  Ledger ERR: {lf} → {e}')

# Server.log
print()
print('  server.log sichern...')
try:
    sftp.get('/opt/hivecore-v2/server.log', str(logs_dir / 'server.log'))
    print('  server.log gesichert')
except Exception as e:
    print(f'  server.log: {e}')

# ================================================================
# 5. Traum-Timestamps extrahieren
# ================================================================
print('[5/5] Traum-Timestamps pruefen...')

# Adam dreams
stdin, stdout, stderr = ssh.exec_command(
    f'cat {REMOTE_EGONS}/adam_001/memory/experience.yaml 2>/dev/null || '
    f'cat {REMOTE_EGONS}/adam/memory/experience.yaml 2>/dev/null'
)
adam_exp = stdout.read().decode()
if adam_exp:
    (logs_dir / 'adam_experience.yaml').write_text(adam_exp)
    # Traum-Zeilen extrahieren
    dream_lines = [l for l in adam_exp.split('\n') if 'dream' in l.lower() or 'D00' in l or 'date' in l.lower()]
    print(f'  Adam dreams: {len(dream_lines)} relevante Zeilen')

# Eva dreams
stdin, stdout, stderr = ssh.exec_command(
    f'cat {REMOTE_EGONS}/eva_002/memory/experience.yaml 2>/dev/null || '
    f'cat {REMOTE_EGONS}/eva/memory/experience.yaml 2>/dev/null'
)
eva_exp = stdout.read().decode()
if eva_exp:
    (logs_dir / 'eva_experience.yaml').write_text(eva_exp)
    dream_lines = [l for l in eva_exp.split('\n') if 'dream' in l.lower() or 'D00' in l or 'date' in l.lower()]
    print(f'  Eva dreams: {len(dream_lines)} relevante Zeilen')

# ================================================================
# Zusammenfassung
# ================================================================
print()
print('=== SNAPSHOT COMPLETE ===')
total = sum(1 for _ in LOCAL_BASE.rglob('*') if _.is_file())
print(f'Gesamt: {total} Dateien in {LOCAL_BASE}')
print()

# Verifiziere kritische Dateien
critical = [
    'adam_001/core/state.yaml', 'adam_001/core/dna.md',
    'adam_001/memory/episodes.yaml', 'adam_001/memory/experience.yaml',
    'adam_001/memory/inner_voice.md',
    'adam/core/state.yaml', 'adam/core/dna.md',
    'eva_002/core/state.yaml', 'eva_002/core/dna.md',
    'eva/core/state.yaml',
]
print('Kritische Dateien:')
for cf in critical:
    fp = LOCAL_BASE / cf
    if fp.exists():
        size = fp.stat().st_size
        print(f'  [OK] {cf} ({size} bytes)')
    # Nicht melden wenn nicht da — nicht alle Varianten existieren

sftp.close()
ssh.close()
print()
print('DONE. Baseline gesichert.')
