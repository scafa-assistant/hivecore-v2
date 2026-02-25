"""Capture complete final state of both EGONs for scientific documentation."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

sections = [
    ('EVA — experience.yaml (FULL)', 'cat /opt/hivecore-v2/egons/eva_002/memory/experience.yaml'),
    ('EVA — episodes.yaml (last entries)', "python3 -c \"import yaml; d=yaml.safe_load(open('/opt/hivecore-v2/egons/eva_002/memory/episodes.yaml')); eps=d.get('episodes',[]); print(f'Total episodes: {len(eps)}'); [print(f'{e[\\\"id\\\"]}: {e.get(\\\"summary\\\",\\\"\\\")[:80]}') for e in eps[-5:]]\""),
    ('EVA — emotional_state.yaml', 'cat /opt/hivecore-v2/egons/eva_002/memory/emotional_state.yaml'),
    ('EVA — inner_voice.yaml (last 3)', "python3 -c \"import yaml; d=yaml.safe_load(open('/opt/hivecore-v2/egons/eva_002/memory/inner_voice.yaml')); entries=d.get('entries',[]); print(f'Total entries: {len(entries)}'); [print(f'{e[\\\"id\\\"]}: {e.get(\\\"reflection\\\",\\\"\\\")[:100]}') for e in entries[-3:]]\""),
    ('ADAM — experience.md (dreams only)', r"grep -B1 -A10 'type:.*[Tt]raum\|type: [Aa]ngst\|type: kreativ\|type: prospection\|type: retrospection' /opt/hivecore-v2/egons/adam_001/experience.md"),
    ('ADAM — inner_voice.md (last 500 chars)', 'tail -c 500 /opt/hivecore-v2/egons/adam_001/inner_voice.md'),
    ('ADAM — markers.md (emotional state)', 'cat /opt/hivecore-v2/egons/adam_001/markers.md | head -30'),
    ('SERVER — hivecore logs (last hour)', 'journalctl -u hivecore --no-pager --since "1 hour ago" | grep -v "GET /api/health"'),
]

for label, cmd in sections:
    print(f'\n{"="*70}')
    print(f'  {label}')
    print(f'{"="*70}')
    stdin, stdout, stderr = ssh.exec_command(cmd + ' 2>&1')
    out = stdout.read().decode('utf-8')
    print(out if out.strip() else '(empty)')

ssh.close()
