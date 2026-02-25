"""Read Eva's first dream from experience.yaml."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

stdin, stdout, stderr = ssh.exec_command(
    'cat /opt/hivecore-v2/egons/eva_002/memory/experience.yaml 2>&1'
)
print(stdout.read().decode('utf-8'))

ssh.close()
