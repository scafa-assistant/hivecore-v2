"""Test: Trigger pulse with snapshot for Eva, verify snapshot was created."""
import paramiko
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

# 1. Trigger Eva pulse (includes automatic snapshot)
print('=== Triggering Eva pulse with snapshot ===')
stdin, stdout, stderr = ssh.exec_command(
    'curl -s "http://localhost:8001/api/pulse/trigger?egon_id=eva_002" 2>&1',
    timeout=180
)
result = stdout.read().decode('utf-8')
try:
    data = json.loads(result)
    print(f'Brain: {data.get("brain_version")}')
    dream = data.get('pulse', {}).get('dream_generation', {})
    print(f'Dream: {json.dumps(dream, indent=2, ensure_ascii=False)[:300]}')
    snapshot = data.get('snapshot', {})
    print(f'\nSnapshot: {json.dumps(snapshot, indent=2, ensure_ascii=False)}')
except:
    print(f'RAW: {result[:2000]}')

# 2. Check snapshot directory
print('\n=== Snapshot directory ===')
stdin, stdout, stderr = ssh.exec_command(
    'find /opt/hivecore-v2/egons/shared/snapshots/ -type f 2>&1 | head -30'
)
print(stdout.read().decode('utf-8'))

# 3. Read SNAPSHOT_META.json
print('=== SNAPSHOT_META.json ===')
stdin, stdout, stderr = ssh.exec_command(
    'cat /opt/hivecore-v2/egons/shared/snapshots/2026-02-24/*/SNAPSHOT_META.json 2>&1 | head -50'
)
print(stdout.read().decode('utf-8'))

# 4. Check /api/snapshots endpoint
print('=== /api/snapshots endpoint ===')
stdin, stdout, stderr = ssh.exec_command(
    'curl -s "http://localhost:8001/api/snapshots" 2>&1'
)
snap_result = stdout.read().decode('utf-8')
try:
    snap_data = json.loads(snap_result)
    print(json.dumps(snap_data, indent=2, ensure_ascii=False)[:1000])
except:
    print(f'RAW: {snap_result[:1000]}')

# 5. Logs
print('\n=== Server logs ===')
stdin, stdout, stderr = ssh.exec_command(
    'journalctl -u hivecore --no-pager --since "2 minutes ago" 2>&1 | grep -v "GET /api/health"'
)
print(stdout.read().decode('utf-8'))

ssh.close()
print('=== TEST COMPLETE ===')
