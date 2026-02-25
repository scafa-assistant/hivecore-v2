"""Check all chat storage locations on server."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

# 1. Shared chats directory
print('='*70)
print('  egons/shared/chats/ — Chat Thread Storage')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    "ls -la /opt/hivecore-v2/egons/shared/chats/ 2>&1"
)
print(stdout.read().decode('utf-8'))

# 2. Check any chat files
stdin, stdout, stderr = ssh.exec_command(
    "find /opt/hivecore-v2/egons/shared/chats/ -type f 2>&1 | head -20"
)
files = stdout.read().decode('utf-8')
print('Chat files:')
print(files if files.strip() else '(none)')

# 3. Read a sample chat file if exists
if files.strip():
    first_file = files.strip().split('\n')[0]
    print(f'\n--- First chat file: {first_file} ---')
    stdin, stdout, stderr = ssh.exec_command(f"cat '{first_file}' 2>&1 | head -50")
    print(stdout.read().decode('utf-8'))

# 4. Check thread_manager storage
print('\n' + '='*70)
print('  Thread Manager — How chats are stored')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    "grep -n 'def.*save\\|def.*load\\|def.*append\\|CHAT_DIR\\|chat_dir\\|thread_dir' /opt/hivecore-v2/engine/thread_manager.py 2>&1 | head -20"
)
print(stdout.read().decode('utf-8'))

# 5. Check memory.py storage
print('='*70)
print('  memory.py — append_memory function')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    "grep -n -A20 'async def append_memory' /opt/hivecore-v2/engine/memory.py 2>&1"
)
print(stdout.read().decode('utf-8'))

# 6. Adam memory.md — total conversation count
print('='*70)
print('  Adam memory.md — Conversation count')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    r"grep -c '^date:' /opt/hivecore-v2/egons/adam_001/memory.md 2>&1"
)
print(f"Total conversations in Adam memory.md: {stdout.read().decode('utf-8').strip()}")

stdin, stdout, stderr = ssh.exec_command(
    r"grep -c 'importance: high' /opt/hivecore-v2/egons/adam_001/memory.md 2>&1"
)
print(f"High importance conversations: {stdout.read().decode('utf-8').strip()}")

# 7. Eva memory.md
print('\n' + '='*70)
print('  Eva memory.md — Full content (first 100 lines)')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    "head -100 /opt/hivecore-v2/egons/eva_002/memory.md 2>&1"
)
print(stdout.read().decode('utf-8'))

stdin, stdout, stderr = ssh.exec_command(
    r"grep -c '^date:' /opt/hivecore-v2/egons/eva_002/memory.md 2>&1"
)
print(f"Total conversations in Eva memory.md: {stdout.read().decode('utf-8').strip()}")

# 8. Check if full chat threads exist
print('\n' + '='*70)
print('  Full chat threads (JSON)')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    "find /opt/hivecore-v2/egons -name '*.json' -path '*/chats/*' 2>&1 | head -20"
)
json_files = stdout.read().decode('utf-8')
print(json_files if json_files.strip() else '(no JSON chat files)')

stdin, stdout, stderr = ssh.exec_command(
    "find /opt/hivecore-v2/egons -name 'thread*' -o -name 'chat_*' 2>&1 | grep -v __pycache__ | head -20"
)
thread_files = stdout.read().decode('utf-8')
print(thread_files if thread_files.strip() else '(no thread files)')

ssh.close()
print('\n=== DONE ===')
