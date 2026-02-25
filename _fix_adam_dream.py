"""Fix: Move Adam's dream from experience.yaml (v2) to experience.md (v1).
The pulse accidentally ran v2 code for Adam because BRAIN_VERSION=v2 in .env.
"""
import paramiko
import yaml
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

# 1. Read Adam's experience.yaml (v2 - accidentally created)
print('=== Reading Adam experience.yaml ===')
stdin, stdout, stderr = ssh.exec_command(
    'cat /opt/hivecore-v2/egons/adam_001/memory/experience.yaml 2>&1'
)
yaml_content = stdout.read().decode('utf-8')
print(yaml_content[:2000])

# 2. Parse dreams from it
try:
    data = yaml.safe_load(yaml_content)
    dreams = data.get('dreams', [])
    mtt = data.get('mental_time_travel', [])
    print(f'\nDreams found: {len(dreams)}')
    print(f'MTT found: {len(mtt)}')

    # 3. Convert dreams to v1 experience.md format and append
    for d in dreams:
        date = d.get('date', '?')
        dtype = d.get('type', 'Verarbeitungstraum')
        trigger = d.get('trigger', f'Tagesverarbeitung vom {date}')
        content = d.get('content', '').strip()
        emotional = d.get('emotional_summary', '')
        spark = str(d.get('spark_potential', False)).lower()

        # Format content with proper indentation
        content_lines = content.replace('\n', '\n  ')

        entry = (
            f'\n---\n'
            f'date: {date}\n'
            f'type: {dtype}\n'
            f'trigger: {trigger}\n'
            f'content: |\n'
            f'  {content_lines}\n'
            f'emotional_summary: {emotional}\n'
            f'spark_potential: {spark}\n'
            f'---\n'
        )
        print(f'\nAppending dream to experience.md:\n{entry}')

        # Append to experience.md
        sftp = ssh.open_sftp()
        with sftp.open('/opt/hivecore-v2/egons/adam_001/experience.md', 'a') as f:
            f.write(entry)
        sftp.close()

    # 4. Also convert MTT to experience.md format
    for m in mtt:
        date = m.get('date', '?')
        mtype = m.get('type', 'prospection')
        if mtype == 'retrospection':
            question = m.get('question', '')
            analysis = m.get('analysis', '').replace('\n', '\n  ')
            emo_weight = m.get('emotional_weight', 0.5)
            entry = (
                f'\n---\n'
                f'date: {date}\n'
                f'type: retrospection\n'
                f'question: {question}\n'
                f'analysis: |\n'
                f'  {analysis}\n'
                f'emotional_weight: {emo_weight}\n'
                f'---\n'
            )
        else:
            scenario = m.get('scenario', '')
            simulation = m.get('simulation', '').replace('\n', '\n  ')
            motivation = m.get('motivation', '')
            entry = (
                f'\n---\n'
                f'date: {date}\n'
                f'type: prospection\n'
                f'scenario: {scenario}\n'
                f'simulation: |\n'
                f'  {simulation}\n'
                f'motivation: {motivation}\n'
                f'---\n'
            )
        print(f'\nAppending MTT to experience.md:\n{entry}')
        sftp = ssh.open_sftp()
        with sftp.open('/opt/hivecore-v2/egons/adam_001/experience.md', 'a') as f:
            f.write(entry)
        sftp.close()

    print('\n=== Done! Dreams + MTT transferred to experience.md ===')

    # 5. Remove the accidentally created experience.yaml
    # Keep the memory/ dir but remove the yaml to avoid confusion
    stdin, stdout, stderr = ssh.exec_command(
        'rm -f /opt/hivecore-v2/egons/adam_001/memory/experience.yaml 2>&1'
    )
    print('Removed experience.yaml from Adam/memory/:', stdout.read().decode())

except Exception as e:
    print(f'ERROR: {e}')

ssh.close()
