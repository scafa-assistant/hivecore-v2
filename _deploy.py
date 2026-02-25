"""Quick deploy script — git pull + rsync + restart on server."""
import paramiko

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

# git pull
stdin, stdout, stderr = ssh.exec_command('cd /root/hivecore-v2 && git pull origin master 2>&1')
print('GIT:', stdout.read().decode())

# rsync (excluding .git, venv, __pycache__, egons/, .env)
stdin, stdout, stderr = ssh.exec_command(
    'rsync -av --delete '
    '--exclude .git --exclude venv --exclude __pycache__ --exclude egons/ '
    '--exclude .env --exclude "*.pyc" '
    '/root/hivecore-v2/ /opt/hivecore-v2/ 2>&1 | tail -10'
)
print('RSYNC:', stdout.read().decode())

# restart
stdin, stdout, stderr = ssh.exec_command('systemctl restart hivecore 2>&1')
print('RESTART:', stdout.read().decode() or 'OK')

# status
stdin, stdout, stderr = ssh.exec_command('systemctl is-active hivecore 2>&1')
print('STATUS:', stdout.read().decode().strip())

ssh.close()
print('DONE')
