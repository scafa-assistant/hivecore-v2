"""FULL SYSTEM TEST: Experience System v2 — Dreams, Sparks, MTT
Scientific documentation run — all results logged with timestamps.
"""
import paramiko
import json
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
print(f'╔══════════════════════════════════════════════════════════════╗')
print(f'║  EXPERIENCE SYSTEM v2 — FULL SYSTEM TEST                   ║')
print(f'║  Timestamp: {timestamp}                      ║')
print(f'╚══════════════════════════════════════════════════════════════╝')

# ─── PRE-STATE: Snapshot before test ───
print('\n' + '='*60)
print('PRE-TEST STATE')
print('='*60)

print('\n--- Eva experience.yaml BEFORE pulse ---')
stdin, stdout, stderr = ssh.exec_command('cat /opt/hivecore-v2/egons/eva_002/memory/experience.yaml 2>&1')
eva_pre = stdout.read().decode('utf-8')
print(eva_pre)

print('\n--- Adam experience.md dream count BEFORE ---')
stdin, stdout, stderr = ssh.exec_command(
    r"grep -c 'type:.*[Tt]raum\|type: angst\|type: kreativ\|type: verarbeitungs' /opt/hivecore-v2/egons/adam_001/experience.md 2>&1"
)
adam_dream_count_pre = stdout.read().decode('utf-8').strip()
print(f'Adam dreams before: {adam_dream_count_pre}')

# ─── TEST 1: Eva Pulse (v2) ───
print('\n' + '='*60)
print('TEST 1: Eva Pulse (v2 Brain) — Dream + Spark + MTT')
print('='*60)

stdin, stdout, stderr = ssh.exec_command(
    'curl -s "http://localhost:8001/api/pulse/trigger?egon_id=eva_002" 2>&1',
    timeout=180
)
eva_result_raw = stdout.read().decode('utf-8')
try:
    eva_result = json.loads(eva_result_raw)
    print(f'\nBrain Version: {eva_result.get("brain_version", "?")}')
    print(f'EGON ID: {eva_result.get("egon_id", "?")}')
    pulse = eva_result.get('pulse', {})

    for key in ['emotional_state', 'social_bonds', 'inner_voice', 'state_update',
                'dream_generation', 'spark_check', 'mental_time_travel']:
        val = pulse.get(key)
        if val is not None:
            if isinstance(val, dict):
                print(f'\n*** {key} ***')
                print(json.dumps(val, indent=2, ensure_ascii=False))
            else:
                val_str = str(val)
                if len(val_str) > 200:
                    print(f'\n*** {key} ***')
                    print(val_str[:500])
                else:
                    print(f'{key}: {val_str}')
except Exception as e:
    print(f'PARSE ERROR: {e}')
    print(f'RAW: {eva_result_raw[:3000]}')

# ─── TEST 2: Adam Pulse (v1) ───
print('\n' + '='*60)
print('TEST 2: Adam Pulse (v1 Brain) — Dream Generation')
print('='*60)

stdin, stdout, stderr = ssh.exec_command(
    'curl -s "http://localhost:8001/api/pulse/trigger?egon_id=adam_001" 2>&1',
    timeout=180
)
adam_result_raw = stdout.read().decode('utf-8')
try:
    adam_result = json.loads(adam_result_raw)
    print(f'\nBrain Version: {adam_result.get("brain_version", "?")}')
    print(f'EGON ID: {adam_result.get("egon_id", "?")}')
    pulse = adam_result.get('pulse', {})

    for key in ['dream_generation']:
        val = pulse.get(key)
        if val is not None:
            if isinstance(val, dict):
                print(f'\n*** {key} ***')
                print(json.dumps(val, indent=2, ensure_ascii=False))
            else:
                print(f'{key}: {str(val)[:500]}')

    # Also show other interesting pulse data
    for key in ['emotional_decay', 'inner_voice']:
        val = pulse.get(key)
        if val and isinstance(val, str) and len(val) > 10:
            print(f'\n*** {key} ***')
            print(str(val)[:300])
except Exception as e:
    print(f'PARSE ERROR: {e}')
    print(f'RAW: {adam_result_raw[:3000]}')

# ─── POST-STATE: After both pulses ───
print('\n' + '='*60)
print('POST-TEST STATE')
print('='*60)

print('\n--- Eva experience.yaml AFTER pulse ---')
stdin, stdout, stderr = ssh.exec_command('cat /opt/hivecore-v2/egons/eva_002/memory/experience.yaml 2>&1')
eva_post = stdout.read().decode('utf-8')
print(eva_post)

print('\n--- Adam experience.md dream count AFTER ---')
stdin, stdout, stderr = ssh.exec_command(
    r"grep -c 'type:.*[Tt]raum\|type: angst\|type: kreativ\|type: verarbeitungs' /opt/hivecore-v2/egons/adam_001/experience.md 2>&1"
)
adam_dream_count_post = stdout.read().decode('utf-8').strip()
print(f'Adam dreams after: {adam_dream_count_post}')

print('\n--- Adam last dream ---')
stdin, stdout, stderr = ssh.exec_command(
    r"grep -B1 -A8 'type:.*[Tt]raum\|type: [Aa]ngst' /opt/hivecore-v2/egons/adam_001/experience.md 2>&1 | tail -20"
)
print(stdout.read().decode('utf-8'))

# ─── LOGS ───
print('\n' + '='*60)
print('SERVER LOGS DURING TEST')
print('='*60)
stdin, stdout, stderr = ssh.exec_command(
    'journalctl -u hivecore --no-pager --since "5 minutes ago" 2>&1'
)
print(stdout.read().decode('utf-8'))

# ─── SUMMARY ───
print('\n' + '='*60)
print('TEST SUMMARY')
print('='*60)
print(f'Timestamp: {timestamp}')
print(f'Eva brain: v2 | Adam brain: v1')
print(f'Adam dreams: {adam_dream_count_pre} → {adam_dream_count_post}')
print(f'Eva has dream D0001: {"D0001" in eva_pre}')
print(f'Eva post-pulse dreams: check above')

ssh.close()
print('\n=== TEST COMPLETE ===')
