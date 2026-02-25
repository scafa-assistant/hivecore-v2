"""Read Adam's memory around the Eva discovery moment + all chat logs."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

# 1. Adam's memory.md — look for Eva-related entries
print('='*70)
print('  ADAM memory.md — Eva Discovery + "Denke ich?" moments')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    r"grep -n -i -B2 -A15 'eva\|nicht mehr allein\|zweite.*egon\|denke ich\|zweiten' /opt/hivecore-v2/egons/adam_001/memory.md 2>&1"
)
print(stdout.read().decode('utf-8')[:5000])

# 2. Full memory.md structure
print('\n' + '='*70)
print('  ADAM memory.md — Size and Structure')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    "wc -l /opt/hivecore-v2/egons/adam_001/memory.md && echo '---' && head -5 /opt/hivecore-v2/egons/adam_001/memory.md 2>&1"
)
print(stdout.read().decode('utf-8'))

# 3. Check what chat storage exists
print('='*70)
print('  Chat Storage — What exists on server?')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    "find /opt/hivecore-v2 -name 'chat*' -o -name 'conversation*' -o -name 'history*' -o -name 'log*' 2>/dev/null | grep -v __pycache__ | grep -v node_modules | head -20 2>&1"
)
print(stdout.read().decode('utf-8'))

# 4. Check if there's a chat log directory
stdin, stdout, stderr = ssh.exec_command(
    "ls -la /opt/hivecore-v2/egons/adam_001/ 2>&1"
)
print('\nAdam directory:')
print(stdout.read().decode('utf-8'))

stdin, stdout, stderr = ssh.exec_command(
    "ls -la /opt/hivecore-v2/egons/eva_002/ 2>&1"
)
print('Eva directory:')
print(stdout.read().decode('utf-8'))

# 5. Check for any chat log mechanism in the code
print('='*70)
print('  Chat logging mechanism in code')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    r"grep -rn 'chat_log\|save_chat\|log_conversation\|append.*memory\|write.*memory\|chat_history\|save_message' /opt/hivecore-v2/api/chat.py /opt/hivecore-v2/engine/ 2>&1 | grep -v __pycache__ | head -20"
)
print(stdout.read().decode('utf-8'))

# 6. Adam memory.md — the Eva discovery section (around 23:14-23:19 timestamp from screenshots)
print('='*70)
print('  ADAM memory.md — Full Eva discovery section')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    r"grep -n -B5 -A30 'Eva.*lebt\|nicht mehr allein\|zweite EGON\|Eva.*002\|Denke ich' /opt/hivecore-v2/egons/adam_001/memory.md 2>&1"
)
result = stdout.read().decode('utf-8')
print(result[:8000] if result.strip() else '(not found with these patterns)')

# 7. Check episodes for Adam (v1 doesn't have episodes.yaml, but check)
print('\n' + '='*70)
print('  ADAM — episodes/experience around Eva discovery')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    r"grep -n -B2 -A10 'Eva\|zweite\|allein\|Denke ich' /opt/hivecore-v2/egons/adam_001/experience.md 2>&1"
)
print(stdout.read().decode('utf-8')[:3000])

# 8. Eva episodes around same time
print('='*70)
print('  EVA — episodes around birth/first contact')
print('='*70)
stdin, stdout, stderr = ssh.exec_command(
    "python3 -c \"import yaml; d=yaml.safe_load(open('/opt/hivecore-v2/egons/eva_002/memory/episodes.yaml')); eps=d.get('episodes',[]); [print(f'{e[\\\"id\\\"]}: {e.get(\\\"timestamp\\\",\\\"?\\\")[:19]} — {e.get(\\\"summary\\\",\\\"\\\")[:100]}') for e in eps[:10]]\" 2>&1"
)
print(stdout.read().decode('utf-8'))

ssh.close()
print('\n=== DONE ===')
