"""Final test: Adam pulse with correct v1 routing + dream generation."""
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

# Trigger Adam pulse
print('=== Adam Pulse (should be v1 now) ===')
stdin, stdout, stderr = ssh.exec_command(
    'curl -s "http://localhost:8001/api/pulse/trigger?egon_id=adam_001" 2>&1',
    timeout=120
)
result = stdout.read().decode('utf-8')
try:
    data = json.loads(result)
    print(f"Brain version: {data.get('brain_version', '?')}")
    print(f"EGON: {data.get('egon_id', '?')}")
    for key, value in data.get('pulse', {}).items():
        val_str = json.dumps(value, indent=2, ensure_ascii=False) if isinstance(value, dict) else str(value)
        if key == 'dream_generation':
            print(f'\n*** {key} ***')
            print(val_str)
        else:
            print(f'{key}: {val_str[:120]}')
except:
    print('RAW:', result[:3000])

# Count dreams in experience.md
print('\n=== Dreams in experience.md ===')
stdin, stdout, stderr = ssh.exec_command(
    r"grep -c 'type:.*[Tt]raum\|type: angst\|type: kreativ\|type: verarbeitungs' /opt/hivecore-v2/egons/adam_001/experience.md 2>&1"
)
print(f'Dream entries: {stdout.read().decode().strip()}')

# Show all dream entries
print('\n=== All dream content ===')
stdin, stdout, stderr = ssh.exec_command(
    r"grep -A5 'type:.*[Tt]raum\|type: angst\|type: kreativ\|type: verarbeitungs' /opt/hivecore-v2/egons/adam_001/experience.md 2>&1"
)
print(stdout.read().decode('utf-8'))

# Also test Eva pulse
print('\n=== Eva Pulse (should be v2) ===')
stdin, stdout, stderr = ssh.exec_command(
    'curl -s "http://localhost:8001/api/pulse/trigger?egon_id=eva_002" 2>&1',
    timeout=120
)
result2 = stdout.read().decode('utf-8')
try:
    data2 = json.loads(result2)
    print(f"Brain version: {data2.get('brain_version', '?')}")
    for key, value in data2.get('pulse', {}).items():
        if key == 'dream_generation':
            val_str = json.dumps(value, indent=2, ensure_ascii=False) if isinstance(value, dict) else str(value)
            print(f'\n*** {key} ***')
            print(val_str)
except:
    print('RAW:', result2[:2000])

ssh.close()
