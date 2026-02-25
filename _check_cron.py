"""Check cron jobs and pulse scheduling on server."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

# Check crontab
print('=== Crontab ===')
stdin, stdout, stderr = ssh.exec_command('crontab -l 2>&1')
print(stdout.read().decode('utf-8'))

# Check systemd timers
print('=== Systemd Timers ===')
stdin, stdout, stderr = ssh.exec_command('systemctl list-timers --all 2>&1 | head -20')
print(stdout.read().decode('utf-8'))

# Check if there's a pulse scheduler in the code
print('=== Pulse scheduling in code ===')
stdin, stdout, stderr = ssh.exec_command('grep -r "pulse" /opt/hivecore-v2/cron* /opt/hivecore-v2/scheduler* /opt/hivecore-v2/main.py 2>&1 | grep -v __pycache__')
print(stdout.read().decode('utf-8'))

# Check for APScheduler or similar
stdin, stdout, stderr = ssh.exec_command('grep -r "scheduler\|cron\|schedule\|apscheduler\|BackgroundScheduler\|@repeat" /opt/hivecore-v2/main.py /opt/hivecore-v2/engine/scheduler* 2>&1 | grep -v __pycache__')
print(stdout.read().decode('utf-8'))

ssh.close()
