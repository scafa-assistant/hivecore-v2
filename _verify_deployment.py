"""Verify full Experience System v2 deployment on server."""
import paramiko
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

cmds = [
    ('=== 1. Service Status ===', 'systemctl is-active hivecore 2>&1'),
    ('=== 2. experience_v2.py exists? ===', 'ls -la /opt/hivecore-v2/engine/experience_v2.py 2>&1'),
    ('=== 3. pulse_v2.py — Dream/Spark/MTT Steps ===',
     'grep -n "step_11\\|step_12\\|step_13\\|dream_generation\\|spark_check\\|mental_time_travel" /opt/hivecore-v2/engine/pulse_v2.py 2>&1'),
    ('=== 4. pulse.py v1 — Dream Step ===',
     'grep -n "step_9\\|dream_generation" /opt/hivecore-v2/engine/pulse.py 2>&1'),
    ('=== 5. api/pulse.py — Per-EGON Brain Detection ===',
     'grep -n "detect_brain\\|brain_version" /opt/hivecore-v2/api/pulse.py 2>&1'),
    ('=== 6. scheduler.py — Per-EGON Brain Detection ===',
     'grep -n "detect_brain\\|brain_version" /opt/hivecore-v2/scheduler.py 2>&1'),
    ('=== 7. chat.py — Experience Extraction ===',
     'grep -n "maybe_extract_experience\\|experience_v2" /opt/hivecore-v2/api/chat.py 2>&1'),
    ('=== 8. prompt_builder_v2.py — Dreams+Sparks in Prompt ===',
     'grep -n "dreams_to_prompt\\|sparks_to_prompt\\|TRAEUME\\|SPARKS" /opt/hivecore-v2/engine/prompt_builder_v2.py 2>&1'),
    ('=== 9. yaml_to_prompt.py — Dream/Spark Functions ===',
     'grep -n "def dreams_to_prompt\\|def sparks_to_prompt" /opt/hivecore-v2/engine/yaml_to_prompt.py 2>&1'),
    ('=== 10. context_budget_v2.py — Budget Entries ===',
     'grep -n "dreams\\|sparks" /opt/hivecore-v2/engine/context_budget_v2.py 2>&1'),
    ('=== 11. inner_voice_v2.py — Dream/Spark Cross-Refs ===',
     'grep -n "dream\\|spark\\|D0\\|S0" /opt/hivecore-v2/engine/inner_voice_v2.py 2>&1'),
    ('=== 12. prompt_builder.py v1 — _extract_dreams ===',
     'grep -n "_extract_dreams\\|TRAEUME" /opt/hivecore-v2/engine/prompt_builder.py 2>&1'),
    ('=== 13. Eva experience.yaml (FULL) ===',
     'cat /opt/hivecore-v2/egons/eva_002/memory/experience.yaml 2>&1'),
    ('=== 14. Adam experience.md (last 60 lines) ===',
     'tail -60 /opt/hivecore-v2/egons/adam_001/experience.md 2>&1'),
    ('=== 15. Recent hivecore logs ===',
     'journalctl -u hivecore --no-pager -n 20 2>&1'),
]

for label, cmd in cmds:
    print(label)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8')
    print(out if out.strip() else '(empty)')
    print()

ssh.close()
print('=== VERIFICATION COMPLETE ===')
