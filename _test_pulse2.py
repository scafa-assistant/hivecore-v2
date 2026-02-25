"""Test: Trigger Adam's pulse via correct API endpoint."""
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

# Check BRAIN_VERSION in config
print('=== Config check ===')
stdin, stdout, stderr = ssh.exec_command(
    "grep BRAIN_VERSION /opt/hivecore-v2/config.py 2>&1"
)
print(stdout.read().decode())

# Check if Adam has soul.md (v1) or core/dna.md (v2)
stdin, stdout, stderr = ssh.exec_command(
    "ls -la /opt/hivecore-v2/egons/adam_001/soul.md /opt/hivecore-v2/egons/adam_001/core/dna.md 2>&1"
)
print('Adam brain files:', stdout.read().decode())

# Trigger pulse
print('\n=== Triggering Adam pulse via /pulse/trigger?egon_id=adam_001 ===')
stdin, stdout, stderr = ssh.exec_command(
    'curl -s "http://localhost:8001/pulse/trigger?egon_id=adam_001" 2>&1'
)
result = stdout.read().decode('utf-8')
try:
    data = json.loads(result)
    print(json.dumps(data, indent=2, ensure_ascii=False))
except:
    print('RAW:', result[:3000])

ssh.close()
