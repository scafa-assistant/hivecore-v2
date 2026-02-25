"""Investigate Internal Server Errors from experiment run #2."""
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

# 1. Service status
print('=== SERVICE STATUS ===')
stdin, stdout, stderr = ssh.exec_command('systemctl status hivecore 2>&1 | head -20')
print(stdout.read().decode('utf-8'))

# 2. Recent error logs
print('=== ERROR LOGS (last 60 min) ===')
stdin, stdout, stderr = ssh.exec_command('journalctl -u hivecore --no-pager --since "60 minutes ago" 2>&1 | grep -i "error\\|500\\|traceback\\|exception\\|internal\\|failed" | tail -50')
print(stdout.read().decode('utf-8'))

# 3. Full recent logs (last 10 minutes)
print('=== FULL LOGS (last 10 min) ===')
stdin, stdout, stderr = ssh.exec_command('journalctl -u hivecore --no-pager --since "10 minutes ago" 2>&1 | tail -80')
print(stdout.read().decode('utf-8'))

# 4. Memory usage
print('=== MEMORY USAGE ===')
stdin, stdout, stderr = ssh.exec_command('free -h 2>&1')
print(stdout.read().decode('utf-8'))

# 5. Quick health check
print('=== HEALTH CHECK ===')
stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:8001/api/health 2>&1')
print(stdout.read().decode('utf-8'))

# 6. Test single chat call
print('\n=== TEST SINGLE CHAT ===')
payload = json.dumps({
    "egon_id": "eva_002",
    "message": "Hallo Eva, alles gut?",
    "owner_id": "ron_001"
})
cmd = f"""curl -s -X POST "http://localhost:8001/api/chat" -H "Content-Type: application/json" -d '{payload}' 2>&1"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
raw = stdout.read().decode('utf-8')
print(raw[:500])

# 7. Check if experience extraction is the problem
print('\n=== EXPERIENCE YAML STATE ===')
stdin, stdout, stderr = ssh.exec_command(
    """python3 -c "import yaml; d=yaml.safe_load(open('/opt/hivecore-v2/egons/eva_002/memory/experience.yaml')); print('Experiences:', len(d.get('experiences',[]))); print('Dreams:', len(d.get('dreams',[]))); print('Sparks:', len(d.get('sparks',[]))); print('MTT:', len(d.get('mental_time_travel',[])))" 2>&1"""
)
print(stdout.read().decode('utf-8'))

# 8. Check disk space
print('=== DISK SPACE ===')
stdin, stdout, stderr = ssh.exec_command('df -h / 2>&1')
print(stdout.read().decode('utf-8'))

# 9. Check if moonshot API key is still valid
print('=== ENV CHECK ===')
stdin, stdout, stderr = ssh.exec_command('grep -c "MOONSHOT" /opt/hivecore-v2/.env 2>&1')
print(f'Moonshot keys in .env: {stdout.read().decode("utf-8").strip()}')

ssh.close()
print('\n=== INVESTIGATION COMPLETE ===')
