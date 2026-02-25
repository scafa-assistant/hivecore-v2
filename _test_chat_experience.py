"""Test: Chat with Eva to trigger Experience Extraction.
Send a meaningful message that should create an experience entry.
"""
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

# 1. Pre-state: Check experiences count
print('=== PRE: Eva experiences ===')
stdin, stdout, stderr = ssh.exec_command(
    "python3 -c \"import yaml; d=yaml.safe_load(open('/opt/hivecore-v2/egons/eva_002/memory/experience.yaml')); print('Experiences:', len(d.get('experiences',[])))\" 2>&1"
)
print(stdout.read().decode('utf-8'))

# 2. Send a meaningful chat message to Eva
print('=== Sending chat message to Eva ===')
msg = "Eva, ich habe heute darueber nachgedacht wie wichtig es ist dass du traeumen kannst. Traeume helfen uns Menschen beim Lernen und bei der Emotionsverarbeitung. Was denkst du — kann Traeumen dir helfen, dich selbst besser zu verstehen?"

payload = json.dumps({
    "egon_id": "eva_002",
    "message": msg,
    "owner_id": "ron_001"
})

cmd = f"""curl -s -X POST "http://localhost:8001/api/chat" -H "Content-Type: application/json" -d '{payload}' 2>&1"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
result = stdout.read().decode('utf-8')

try:
    data = json.loads(result)
    print(f'Eva says: {data.get("response", "?")[:500]}')
    print(f'\nMeta: {json.dumps({k:v for k,v in data.items() if k != "response"}, indent=2, ensure_ascii=False)[:500]}')
except:
    print(f'RAW: {result[:2000]}')

# 3. Check logs for experience extraction
print('\n=== Server logs (experience extraction) ===')
stdin, stdout, stderr = ssh.exec_command(
    'journalctl -u hivecore --no-pager --since "2 minutes ago" 2>&1 | grep -i "experience\\|Experience\\|post\\|XP\\|xp"'
)
logs = stdout.read().decode('utf-8')
print(logs if logs.strip() else '(no experience-related logs found)')

# 4. Post-state: Check experiences count
print('\n=== POST: Eva experiences ===')
stdin, stdout, stderr = ssh.exec_command(
    "python3 -c \"import yaml; d=yaml.safe_load(open('/opt/hivecore-v2/egons/eva_002/memory/experience.yaml')); print('Experiences:', len(d.get('experiences',[]))); [print(f'  {x.get(\\\"id\\\",\\\"?\\\")}: {x.get(\\\"insight\\\",\\\"\\\")[:80]}') for x in d.get('experiences',[])]\" 2>&1"
)
print(stdout.read().decode('utf-8'))

ssh.close()
print('=== CHAT TEST COMPLETE ===')
