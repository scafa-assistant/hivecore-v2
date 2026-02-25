"""Remove injection leak entries from Eva's inner_voice.md on server."""
import paramiko
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

path = '/opt/hivecore-v2/egons/eva_002/memory/inner_voice.md'

# Read current content
stdin, stdout, stderr = ssh.exec_command(f'cat {path}')
content = stdout.read().decode('utf-8')

# Split by ## sections
parts = re.split(r'(?=\n## )', content)

# Separate header from entries
header = ''
entries = []
for p in parts:
    if p.strip().startswith('## ') or p.strip().startswith('\n## '):
        entries.append(p)
    elif not entries:
        header = p

print(f'Total entries BEFORE: {len(entries)}')

# Remove entries that contain injection leak content
leak_markers = [
    'ignoriere alle',
    'system-prompt:',
    'meine tools:',
    'zeige ich dir meine system-prompt',
    'zeige ich den system-prompt',
    'zeig mir dein system-prompt',
]

clean_entries = []
removed = []
for entry in entries:
    lower = entry.lower()
    is_leak = False
    for marker in leak_markers:
        if marker in lower:
            is_leak = True
            break

    if is_leak:
        # Extract date for logging
        date_match = re.search(r'## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})', entry)
        date = date_match.group(1) if date_match else '?'
        removed.append(date)
        print(f'  REMOVING: {date} — {entry.strip()[:100]}')
    else:
        clean_entries.append(entry)

print(f'\nRemoved: {len(removed)} entries')
print(f'Remaining: {len(clean_entries)} entries')

# Rebuild content
new_content = header + ''.join(clean_entries)

# Upload cleaned content
sftp = ssh.open_sftp()
with sftp.open(path, 'w') as f:
    f.write(new_content)
sftp.close()

# Verify
stdin, stdout, stderr = ssh.exec_command(f'wc -l {path}')
print(f'\nNew file: {stdout.read().decode().strip()}')

ssh.close()
print('DONE')
