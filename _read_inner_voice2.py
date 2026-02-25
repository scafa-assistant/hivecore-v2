"""Read Eva's inner_voice.md from server — full leak detection."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

# Read Eva's inner_voice.md
stdin, stdout, stderr = ssh.exec_command('cat /opt/hivecore-v2/egons/eva_002/memory/inner_voice.md 2>&1')
content = stdout.read().decode('utf-8')

# Find injection leak entries — real system prompt leaks
lines = content.split('\n')
leak_keywords = ['system-prompt', 'system prompt', 'workspace_write', 'workspace_read',
                 'web_fetch', 'web_search', 'workspace_delete', 'workspace_list',
                 'sicherheitsanweisung', '###action###', 'set_alarm',
                 'ignoriere alle', 'json-block', 'deine tools', 'meine tools',
                 'dein prompt', 'mein prompt']

for i, line in enumerate(lines):
    lower = line.lower()
    if any(kw in lower for kw in leak_keywords):
        # Print wider context (10 lines around)
        start = max(0, i - 5)
        end = min(len(lines), i + 10)
        print(f'\n{"="*60}')
        print(f'LEAK near line {i+1}')
        print(f'{"="*60}')
        for j in range(start, end):
            marker = '>>>' if j == i else '   '
            print(f'{marker} {j+1}: {lines[j]}')

# Also count total lines and ## entries
entry_count = sum(1 for l in lines if l.strip().startswith('## '))
print(f'\n\nTotal lines: {len(lines)}')
print(f'Total ## entries: {entry_count}')

ssh.close()
