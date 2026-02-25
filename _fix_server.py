"""Fix server crash loop — kill zombie process on port 8001, clean restart."""
import paramiko
import json
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

# 1. Stop the service
print('=== STEP 1: Stop service ===')
stdin, stdout, stderr = ssh.exec_command('systemctl stop hivecore 2>&1')
print(stdout.read().decode('utf-8'))
time.sleep(2)

# 2. Find and kill anything on port 8001
print('=== STEP 2: Kill zombie on port 8001 ===')
stdin, stdout, stderr = ssh.exec_command('lsof -ti:8001 2>&1')
pids = stdout.read().decode('utf-8').strip()
print(f'PIDs on port 8001: {pids}')

if pids:
    for pid in pids.split('\n'):
        pid = pid.strip()
        if pid:
            stdin, stdout, stderr = ssh.exec_command(f'kill -9 {pid} 2>&1')
            print(f'Killed PID {pid}: {stdout.read().decode("utf-8")}')
    time.sleep(2)

# 3. Verify port is free
print('\n=== STEP 3: Verify port free ===')
stdin, stdout, stderr = ssh.exec_command('lsof -ti:8001 2>&1')
remaining = stdout.read().decode('utf-8').strip()
print(f'Remaining PIDs: {remaining if remaining else "NONE — PORT FREE"}')

# 4. Start service cleanly
print('\n=== STEP 4: Start service ===')
stdin, stdout, stderr = ssh.exec_command('systemctl start hivecore 2>&1')
print(stdout.read().decode('utf-8'))
time.sleep(3)

# 5. Check status
print('=== STEP 5: Verify service ===')
stdin, stdout, stderr = ssh.exec_command('systemctl status hivecore 2>&1 | head -15')
print(stdout.read().decode('utf-8'))

# 6. Health check
print('=== STEP 6: Health check ===')
stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:8001/api/health 2>&1')
print(stdout.read().decode('utf-8'))

# 7. Test chat
print('\n=== STEP 7: Test chat ===')
payload = json.dumps({
    "egon_id": "eva_002",
    "message": "Hey Eva, bist du wach?",
    "owner_id": "ron_001"
})
cmd = f"""curl -s -X POST "http://localhost:8001/api/chat" -H "Content-Type: application/json" -d '{payload}' 2>&1"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
raw = stdout.read().decode('utf-8')
try:
    data = json.loads(raw)
    print(f'Response: {data.get("response", "?")[:200]}')
    print(f'Tier: {data.get("tier_used")} | Model: {data.get("model")}')
except:
    print(f'Raw: {raw[:300]}')

ssh.close()
print('\n=== SERVER FIX COMPLETE ===')
