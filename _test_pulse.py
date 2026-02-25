"""Test: Trigger Adam's pulse and check if dream is generated."""
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

# Trigger Adam's pulse via API
print('=== Triggering Adam pulse... ===')
stdin, stdout, stderr = ssh.exec_command(
    'curl -s -X POST http://localhost:8001/api/pulse/adam_001 2>&1'
)
result = stdout.read().decode('utf-8')
try:
    data = json.loads(result)
    print(json.dumps(data, indent=2, ensure_ascii=False))
except:
    print('RAW:', result[:2000])

# Check experience.md for new dream
print('\n=== Checking experience.md for dreams... ===')
stdin, stdout, stderr = ssh.exec_command(
    'grep -c "type:.*traum" /opt/hivecore-v2/egons/adam_001/experience.md 2>&1'
)
count = stdout.read().decode().strip()
print(f'Dream entries found: {count}')

# Show last dream entry
print('\n=== Last dream entry: ===')
stdin, stdout, stderr = ssh.exec_command(
    "awk '/type:.*[Tt]raum/{found=1} found' /opt/hivecore-v2/egons/adam_001/experience.md | tail -20"
)
print(stdout.read().decode('utf-8'))

ssh.close()
