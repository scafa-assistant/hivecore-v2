"""Test: Trigger Adam's pulse via /api/pulse/trigger."""
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

# Check env vars for BRAIN_VERSION
print('=== Checking actual BRAIN_VERSION in running service ===')
stdin, stdout, stderr = ssh.exec_command(
    "grep BRAIN_VERSION /opt/hivecore-v2/.env 2>&1"
)
env_result = stdout.read().decode()
print('From .env:', env_result or '(not in .env)')

stdin, stdout, stderr = ssh.exec_command(
    "grep BRAIN_VERSION /etc/systemd/system/hivecore.service 2>&1"
)
print('From systemd:', stdout.read().decode() or '(not in service)')

# The correct endpoint
print('\n=== Triggering Adam pulse via /api/pulse/trigger?egon_id=adam_001 ===')
stdin, stdout, stderr = ssh.exec_command(
    'curl -s "http://localhost:8001/api/pulse/trigger?egon_id=adam_001" 2>&1',
    timeout=120
)
result = stdout.read().decode('utf-8')
try:
    data = json.loads(result)
    # Pretty print with focus on dream_generation step
    for key, value in data.get('pulse', {}).items():
        if key == 'dream_generation':
            print(f'\n*** {key}: {json.dumps(value, indent=2, ensure_ascii=False)} ***')
        else:
            val_str = json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else str(value)
            print(f'{key}: {val_str[:100]}')
except:
    print('RAW:', result[:3000])

ssh.close()
