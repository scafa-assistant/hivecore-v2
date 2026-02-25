"""Deploy snapshot system to server."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

cmds = [
    ('1. Git pull', 'cd /root/hivecore-v2 && git pull origin master 2>&1'),
    ('2. Rsync to /opt', 'rsync -av --delete --exclude=".git" --exclude="venv" --exclude="__pycache__" --exclude="egons/" --exclude=".env" /root/hivecore-v2/ /opt/hivecore-v2/ 2>&1 | tail -5'),
    ('3. Create snapshots dir', 'mkdir -p /opt/hivecore-v2/egons/shared/snapshots && echo "OK"'),
    ('4. Restart service', 'systemctl restart hivecore 2>&1 && echo "Restarted"'),
    ('5. Check status', 'systemctl is-active hivecore 2>&1'),
    ('6. Verify snapshot.py', 'ls -la /opt/hivecore-v2/engine/snapshot.py 2>&1'),
    ('7. Verify scheduler import', 'grep -n "snapshot" /opt/hivecore-v2/scheduler.py 2>&1'),
    ('8. Verify pulse API', 'grep -n "snapshot" /opt/hivecore-v2/api/pulse.py 2>&1'),
    ('9. Quick health check', 'sleep 2 && curl -s http://localhost:8001/api/health 2>&1 | head -1'),
]

for label, cmd in cmds:
    print(f'\n=== {label} ===')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    print(stdout.read().decode('utf-8'))

ssh.close()
print('\n=== DEPLOY COMPLETE ===')
