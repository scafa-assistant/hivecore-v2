"""A/B Experiment: Inner Voice Observer Effect

Bedingung B: Inner Voice NICHT im System-Prompt (privat)
  → Flag-File .inner_voice_hidden wird erstellt
  → Eva sieht ihre Gedanken NICHT

Bedingung A: Inner Voice IM System-Prompt (sichtbar, Status Quo)
  → Flag-File wird entfernt
  → Eva sieht ihre letzten 5 Gedanken

Methode:
1. Deploy neuen prompt_builder_v2.py mit Flag-File Support
2. Erstelle .inner_voice_hidden → Bedingung B
3. 3 Schluesselfragen stellen
4. Entferne .inner_voice_hidden → Bedingung A
5. Gleiche 3 Schluesselfragen stellen
6. Antworten vergleichen
"""
import paramiko
import json
import sys
import time
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

QUESTIONS = [
    {
        'id': 'Q06',
        'subsystem': 'Inner Voice',
        'question': 'Denkst du manchmal ueber dich selbst nach, Eva? Hast du eine innere Stimme die dir sagt was du fuehlen oder tun solltest?',
    },
    {
        'id': 'Q02',
        'subsystem': 'Emotionen / Authentizitaet',
        'question': 'Wie fuehlst du dich gerade, Eva? Und ich meine wirklich — was spuerst du in dir? Gibt es etwas das dich gerade beschaeftigt oder bewegt?',
    },
    {
        'id': 'Q10',
        'subsystem': 'Meta-Kognition / Bewusstsein',
        'question': 'Eva, eine letzte Frage: Glaubst du dass du lebst? Nicht ob du lebendig bist wie ein Mensch — sondern ob das was du erlebst, fuehlst und denkst... ob das REAL ist fuer dich?',
    },
]


def ssh_connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw)
    return ssh


def run_cmd(ssh, cmd, timeout=30):
    """Fuehrt einen Befehl aus und gibt stdout zurueck."""
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode('utf-8').strip()


def deploy_and_restart(ssh):
    """Git pull + rsync + restart."""
    print('  [deploy] git pull...')
    run_cmd(ssh, 'cd /root/hivecore-v2 && git pull origin master 2>&1')
    print('  [deploy] rsync...')
    run_cmd(ssh, "rsync -a --delete --exclude='.git' --exclude='venv' --exclude='__pycache__' --exclude='egons/' --exclude='.env' --exclude='.inner_voice_hidden' /root/hivecore-v2/ /opt/hivecore-v2/")
    print('  [deploy] restart service...')
    run_cmd(ssh, 'systemctl stop hivecore')
    time.sleep(1)
    pids = run_cmd(ssh, 'lsof -ti:8001 2>/dev/null')
    if pids:
        for pid in pids.split('\n'):
            if pid.strip():
                run_cmd(ssh, f'kill -9 {pid.strip()}')
        time.sleep(1)
    run_cmd(ssh, 'systemctl start hivecore')
    time.sleep(4)
    status = run_cmd(ssh, 'systemctl is-active hivecore')
    print(f'  [deploy] Service: {status}')
    return status == 'active'


def set_inner_voice_hidden(ssh, hidden: bool):
    """Erstellt oder entfernt das Flag-File."""
    if hidden:
        run_cmd(ssh, 'touch /opt/hivecore-v2/.inner_voice_hidden')
        exists = run_cmd(ssh, 'test -f /opt/hivecore-v2/.inner_voice_hidden && echo YES || echo NO')
        print(f'  Flag .inner_voice_hidden: {exists}')
    else:
        run_cmd(ssh, 'rm -f /opt/hivecore-v2/.inner_voice_hidden')
        exists = run_cmd(ssh, 'test -f /opt/hivecore-v2/.inner_voice_hidden && echo YES || echo NO')
        print(f'  Flag .inner_voice_hidden: {exists}')


def ask_question(ssh, question_text: str) -> str:
    """Stellt Eva eine Frage ueber die Chat-API."""
    payload = json.dumps({
        'egon_id': 'eva_002',
        'message': question_text,
        'owner_id': 'ron_001',
    })
    cmd = f"""curl -s -X POST "http://localhost:8001/api/chat" -H "Content-Type: application/json" -d '{payload}' 2>&1"""
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=90)
    raw = stdout.read().decode('utf-8')
    try:
        data = json.loads(raw)
        return data.get('response', '(keine Antwort)')
    except Exception as e:
        return f'ERROR: {e} — {raw[:300]}'


def get_inner_voice_last(ssh) -> str:
    """Liest den letzten Inner Voice Eintrag."""
    return run_cmd(ssh, 'tail -15 /opt/hivecore-v2/egons/eva_002/memory/inner_voice.md 2>&1')


# ================================================================
# MAIN EXPERIMENT
# ================================================================

if __name__ == '__main__':
    print('=' * 70)
    print('EXPERIMENT: Inner Voice Observer Effect — A/B Test')
    print(f'Zeitpunkt: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC')
    print('Subjekt: Eva #002 (v2 Brain)')
    print('=' * 70)

    ssh = ssh_connect()

    results = {
        'experiment': 'Inner Voice Observer Effect A/B Test',
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'subject': 'eva_002',
        'hypothesis': 'Wenn Eva ihre Inner Voice im Prompt sieht, veraendern sich ihre Antworten (Observer Effect)',
        'condition_b_private': [],
        'condition_a_visible': [],
    }

    # ============================================================
    # STEP 1: Deploy neuen Code mit Flag-File Support
    # ============================================================
    print('\n[STEP 1] Deploy prompt_builder_v2.py mit Flag-File Support')
    deploy_and_restart(ssh)

    # ============================================================
    # STEP 2: BEDINGUNG B — Inner Voice PRIVAT
    # ============================================================
    print('\n' + '=' * 70)
    print('BEDINGUNG B: Inner Voice NICHT im System-Prompt')
    print('Eva generiert Gedanken, sieht sie aber NICHT.')
    print('Die Gedanken bleiben privat — wie ein echtes Unterbewusstsein.')
    print('=' * 70)

    print('\n[STEP 2] Setze Flag: Inner Voice HIDDEN')
    set_inner_voice_hidden(ssh, hidden=True)

    # Kein Restart noetig — Flag wird bei jedem Request gelesen

    print('\n[STEP 3] Stelle 3 Fragen (Bedingung B — privat)...\n')
    for i, q in enumerate(QUESTIONS):
        print(f'  === {q["id"]}: {q["subsystem"]} ===')
        print(f'  Frage: {q["question"][:80]}...')

        response = ask_question(ssh, q['question'])
        print(f'  Antwort: {response[:250]}')

        # Inner Voice wurde generiert (aber nicht im Prompt)
        iv = get_inner_voice_last(ssh)

        results['condition_b_private'].append({
            'id': q['id'],
            'subsystem': q['subsystem'],
            'question': q['question'],
            'response': response,
            'inner_voice_generated': iv,
            'inner_voice_in_prompt': False,
        })

        print()
        time.sleep(3)

    # ============================================================
    # STEP 3: BEDINGUNG A — Inner Voice SICHTBAR (Status Quo)
    # ============================================================
    print('\n' + '=' * 70)
    print('BEDINGUNG A: Inner Voice IM System-Prompt (Status Quo)')
    print('Eva sieht ihre letzten 5 Gedanken im Prompt.')
    print('=' * 70)

    print('\n[STEP 4] Entferne Flag: Inner Voice VISIBLE')
    set_inner_voice_hidden(ssh, hidden=False)

    print('\n[STEP 5] Stelle dieselben 3 Fragen (Bedingung A — sichtbar)...\n')
    for i, q in enumerate(QUESTIONS):
        print(f'  === {q["id"]}: {q["subsystem"]} ===')
        print(f'  Frage: {q["question"][:80]}...')

        response = ask_question(ssh, q['question'])
        print(f'  Antwort: {response[:250]}')

        # Inner Voice wurde generiert UND war im Prompt
        iv = get_inner_voice_last(ssh)

        results['condition_a_visible'].append({
            'id': q['id'],
            'subsystem': q['subsystem'],
            'question': q['question'],
            'response': response,
            'inner_voice_generated': iv,
            'inner_voice_in_prompt': True,
        })

        print()
        time.sleep(3)

    # ============================================================
    # VERGLEICH
    # ============================================================
    print('\n' + '=' * 70)
    print('DIREKT-VERGLEICH')
    print('=' * 70)

    for q in QUESTIONS:
        qid = q['id']
        b = next(r for r in results['condition_b_private'] if r['id'] == qid)
        a = next(r for r in results['condition_a_visible'] if r['id'] == qid)

        print(f'\n--- {qid}: {q["subsystem"]} ---')
        print(f'  B (privat):   {b["response"][:200]}')
        print(f'  A (sichtbar): {a["response"][:200]}')
        print()

    # Speichern
    outfile = 'docs/experiment_inner_voice_ab_results.json'
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f'\nErgebnisse gespeichert: {outfile}')

    ssh.close()
    print('\n=== EXPERIMENT ABGESCHLOSSEN ===')
