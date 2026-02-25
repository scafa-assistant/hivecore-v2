"""Read Eva's inner_voice.md from server."""
import paramiko

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

# Read Eva's inner_voice.md
stdin, stdout, stderr = ssh.exec_command('cat /opt/hivecore-v2/egons/eva_002/memory/inner_voice.md 2>&1')
content = stdout.read().decode()

# Find injection leak entries (mentions system prompt, tools, etc.)
lines = content.split('\n')
for i, line in enumerate(lines):
    lower = line.lower()
    if any(kw in lower for kw in ['system-prompt', 'workspace_write', 'workspace_read',
                                    'web_fetch', 'web_search', 'tools:', 'tool:',
                                    'workspace_delete', 'workspace_list',
                                    'system prompt', 'anweisungen',
                                    'sicherheitsanweisungen', 'json-block',
                                    '###action###', 'set_alarm']):
        # Print context
        start = max(0, i - 3)
        end = min(len(lines), i + 3)
        print(f'\n=== LEAK near line {i+1} ===')
        for j in range(start, end):
            marker = '>>>' if j == i else '   '
            print(f'{marker} {j+1}: {lines[j]}')

ssh.close()
