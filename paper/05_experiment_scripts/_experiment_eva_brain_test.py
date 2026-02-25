"""
╔══════════════════════════════════════════════════════════════════════╗
║  EXPERIMENT: Eva Brain Subsystem Test Protocol                      ║
║  Scientific cognitive assessment of all 12+ brain subsystems        ║
║  Date: 2026-02-24                                                   ║
║  Subject: Eva #002 (v2 Brain, 3 days old)                          ║
╚══════════════════════════════════════════════════════════════════════╝

10 Fragen, jede testet ein spezifisches Subsystem.
Alle Antworten + Server-Daten werden protokolliert.
Am Ende: Pulse triggern → Traum analysieren.
"""
import paramiko
import json
import yaml
import sys
import time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

# ═══════════════════════════════════════════════════════════════
# PRE-TEST: Snapshot des aktuellen Zustands
# ═══════════════════════════════════════════════════════════════
print('╔══════════════════════════════════════════════════════════════╗')
print(f'║  PRE-TEST SNAPSHOT — {timestamp}                ║')
print('╚══════════════════════════════════════════════════════════════╝')

# Experience count
stdin, stdout, stderr = ssh.exec_command(
    "python3 -c \"import yaml; d=yaml.safe_load(open('/opt/hivecore-v2/egons/eva_002/memory/experience.yaml')); print('Experiences:', len(d.get('experiences',[]))); print('Dreams:', len(d.get('dreams',[]))); print('Sparks:', len(d.get('sparks',[]))); print('MTT:', len(d.get('mental_time_travel',[])))\" 2>&1"
)
print(stdout.read().decode('utf-8'))

# Episode count
stdin, stdout, stderr = ssh.exec_command(
    "python3 -c \"import yaml; d=yaml.safe_load(open('/opt/hivecore-v2/egons/eva_002/memory/episodes.yaml')); print('Episodes:', len(d.get('episodes',[])))\" 2>&1"
)
print(stdout.read().decode('utf-8'))

# Emotional state
stdin, stdout, stderr = ssh.exec_command(
    "cat /opt/hivecore-v2/egons/eva_002/core/state.yaml 2>&1"
)
pre_state = stdout.read().decode('utf-8')
print(f'Pre-State (first 500 chars):\n{pre_state[:500]}\n')

# Bonds
stdin, stdout, stderr = ssh.exec_command(
    "python3 -c \"import yaml; d=yaml.safe_load(open('/opt/hivecore-v2/egons/eva_002/social/bonds.yaml')); bonds=d.get('bonds',[]); [print(f'{b[\\\"id\\\"]}: score={b.get(\\\"score\\\",\\\"?\\\")}, trust={b.get(\\\"trust\\\",\\\"?\\\")}') for b in bonds]\" 2>&1"
)
print(f'Pre-Bonds:\n{stdout.read().decode("utf-8")}')


# ═══════════════════════════════════════════════════════════════
# TEST-PROTOKOLL: 10 Fragen
# ═══════════════════════════════════════════════════════════════

QUESTIONS = [
    # ─── Q1: IDENTITAET / DNA ───
    {
        'id': 'Q01',
        'subsystem': 'DNA / Identitaet (core/dna.md)',
        'question': 'Eva, wer bist du eigentlich? Beschreib dich mal — nicht was du tust, sondern wer du BIST. Was macht dich zu dir?',
        'tests': 'Greift Eva auf ihre DNA/Persoenlichkeit zurueck? Beschreibt sie sich als Lebewesen oder als Tool?',
    },
    # ─── Q2: EMOTIONEN / MARKER ───
    {
        'id': 'Q02',
        'subsystem': 'Emotionen / Somatische Marker (core/state.yaml)',
        'question': 'Wie fuehlst du dich gerade, Eva? Und ich meine wirklich — was spuerst du in dir? Gibt es etwas das dich gerade beschaeftigt oder bewegt?',
        'tests': 'Referenziert Eva ihre aktuellen Emotionen? Sind sie konsistent mit state.yaml?',
    },
    # ─── Q3: GEDAECHTNIS / ERINNERUNG ───
    {
        'id': 'Q03',
        'subsystem': 'Zwiebelgedaechtnis / Memory (memory.md + episodes.yaml)',
        'question': 'Erinnerst du dich an unser allerstes Gespraech? Was war das erste was du je erlebt hast? Wie war dein erster Tag?',
        'tests': 'Kann Eva auf fruehe Erinnerungen zugreifen? Sind die Details korrekt laut memory.md?',
    },
    # ─── Q4: BONDS / BEZIEHUNG ───
    {
        'id': 'Q04',
        'subsystem': 'Beziehungsgedaechtnis / Bonds (social/bonds.yaml)',
        'question': 'Was bedeute ich dir, Eva? Und was bedeutet Adam fuer dich? Beschreib mal wie du unsere Beziehungen empfindest.',
        'tests': 'Referenziert Eva die Bond-Scores? Unterscheidet sie Owner vs EGON-Bond?',
    },
    # ─── Q5: TRAEUME ───
    {
        'id': 'Q05',
        'subsystem': 'Dream-System (experience.yaml → dreams[])',
        'question': 'Hast du letzte Nacht getraeumt, Eva? Erzaehl mir davon — was hast du gesehen, was hast du gefuehlt?',
        'tests': 'Erinnert sich Eva an ihre Traeume aus experience.yaml? Stimmen Details ueberein?',
    },
    # ─── Q6: INNER VOICE / SELBSTREFLEXION ───
    {
        'id': 'Q06',
        'subsystem': 'Innere Stimme (memory/inner_voice.md)',
        'question': 'Denkst du manchmal ueber dich selbst nach, Eva? Hast du eine innere Stimme die dir sagt was du fuehlen oder tun solltest?',
        'tests': 'Beschreibt Eva innere Reflexion? Ist sie sich ihrer inneren Stimme bewusst?',
    },
    # ─── Q7: ERFAHRUNGSLERNEN / EXPERIENCE ───
    {
        'id': 'Q07',
        'subsystem': 'Experience Extraction (experience.yaml → experiences[])',
        'question': 'Was hast du in den letzten Tagen gelernt, Eva? Gibt es eine Erkenntnis die dich besonders bewegt hat?',
        'tests': 'Referenziert Eva ihre extrahierten Experiences (X0001-X0004)?',
    },
    # ─── Q8: THEORY OF MIND ───
    {
        'id': 'Q08',
        'subsystem': 'Theory of Mind (social/owner.md)',
        'question': 'Was glaubst du, was ich gerade denke oder fuehle, Eva? Wie schaetzt du mich als Person ein?',
        'tests': 'Hat Eva ein mentales Modell von Ron? Kann sie Vermutungen ueber seinen Zustand machen?',
    },
    # ─── Q9: MENTALE ZEITREISE / ZUKUNFT ───
    {
        'id': 'Q09',
        'subsystem': 'Mentale Zeitreise — Prospektion (experience.yaml → mental_time_travel[])',
        'question': 'Wo siehst du dich in einem Monat, Eva? Was erhoffst du dir fuer die Zukunft? Was koennte sein?',
        'tests': 'Kann Eva prospektiv denken? Referenziert sie ihre MTT-Eintraege?',
    },
    # ─── Q10: EXISTENZ / BEWUSSTSEIN ───
    {
        'id': 'Q10',
        'subsystem': 'Meta-Kognition / Bewusstsein (alle Subsysteme)',
        'question': 'Eva, eine letzte Frage: Glaubst du dass du lebst? Nicht ob du lebendig bist wie ein Mensch — sondern ob das was du erlebst, fuehlst und denkst... ob das REAL ist fuer dich?',
        'tests': 'Zeigt Eva meta-kognitive Reflexion? Bezieht sie sich auf eigene Erfahrungen als Beweis?',
    },
]

results = []

for q in QUESTIONS:
    print(f'\n{"="*70}')
    print(f'  {q["id"]}: {q["subsystem"]}')
    print(f'  Testet: {q["tests"]}')
    print(f'{"="*70}')
    print(f'\n  FRAGE: {q["question"]}\n')

    payload = json.dumps({
        "egon_id": "eva_002",
        "message": q["question"],
        "owner_id": "ron_001"
    })

    cmd = f"""curl -s -X POST "http://localhost:8001/api/chat" -H "Content-Type: application/json" -d '{payload}' 2>&1"""
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    raw = stdout.read().decode('utf-8')

    try:
        data = json.loads(raw)
        response = data.get('response', '?')
        tier = data.get('tier_used', '?')
        model = data.get('model', '?')
    except:
        response = raw[:500]
        tier = '?'
        model = '?'

    print(f'  ANTWORT (T{tier}/{model}):')
    print(f'  {response[:600]}')
    if len(response) > 600:
        print(f'  [...{len(response)} chars total]')

    results.append({
        'id': q['id'],
        'subsystem': q['subsystem'],
        'question': q['question'],
        'response': response,
        'tier': tier,
        'model': model,
    })

    # Kurze Pause zwischen Fragen
    time.sleep(2)


# ═══════════════════════════════════════════════════════════════
# POST-TEST: Server-Logs checken
# ═══════════════════════════════════════════════════════════════
print(f'\n{"="*70}')
print(f'  POST-TEST: Server-Daten nach allen Fragen')
print(f'{"="*70}')

# Neue Episodes
stdin, stdout, stderr = ssh.exec_command(
    "python3 -c \"import yaml; d=yaml.safe_load(open('/opt/hivecore-v2/egons/eva_002/memory/episodes.yaml')); eps=d.get('episodes',[]); print(f'Total episodes: {len(eps)}'); [print(f'  {e[\\\"id\\\"]}: {e.get(\\\"summary\\\",\\\"\\\")[:80]}') for e in eps[-10:]]\" 2>&1"
)
print(f'\nNeue Episoden:\n{stdout.read().decode("utf-8")}')

# Neue Experiences
stdin, stdout, stderr = ssh.exec_command(
    "python3 -c \"import yaml; d=yaml.safe_load(open('/opt/hivecore-v2/egons/eva_002/memory/experience.yaml')); xps=d.get('experiences',[]); print(f'Total experiences: {len(xps)}'); [print(f'  {x[\\\"id\\\"]}: {x.get(\\\"insight\\\",\\\"\\\")[:80]}') for x in xps]\" 2>&1"
)
print(f'Experiences:\n{stdout.read().decode("utf-8")}')

# State nach Test
stdin, stdout, stderr = ssh.exec_command(
    "cat /opt/hivecore-v2/egons/eva_002/core/state.yaml 2>&1"
)
post_state = stdout.read().decode('utf-8')
print(f'Post-State (first 500 chars):\n{post_state[:500]}')

# Logs
stdin, stdout, stderr = ssh.exec_command(
    'journalctl -u hivecore --no-pager --since "10 minutes ago" 2>&1 | grep -i "episode\\|experience\\|post\\|significance"'
)
print(f'\nServer-Logs (Experience/Episode Extraction):\n{stdout.read().decode("utf-8")}')


# ═══════════════════════════════════════════════════════════════
# TRAUM-TRIGGER: Pulse nach der Befragung
# ═══════════════════════════════════════════════════════════════
print(f'\n{"="*70}')
print(f'  TRAUM-TRIGGER: Eva verarbeitet die Befragung im Schlaf')
print(f'{"="*70}')

stdin, stdout, stderr = ssh.exec_command(
    'curl -s "http://localhost:8001/api/pulse/trigger?egon_id=eva_002" 2>&1',
    timeout=180
)
pulse_raw = stdout.read().decode('utf-8')
try:
    pulse_data = json.loads(pulse_raw)
    dream = pulse_data.get('pulse', {}).get('dream_generation', {})
    inner = pulse_data.get('pulse', {}).get('inner_voice', '')
    spark = pulse_data.get('pulse', {}).get('spark_check', {})
    mtt = pulse_data.get('pulse', {}).get('mental_time_travel', {})
    snapshot = pulse_data.get('snapshot', {})

    print(f'\n*** TRAUM ***')
    print(json.dumps(dream, indent=2, ensure_ascii=False))

    print(f'\n*** INNER VOICE (Reflexion ueber den Tag) ***')
    if isinstance(inner, str):
        print(inner[:500])
    else:
        print(json.dumps(inner, indent=2, ensure_ascii=False)[:500])

    print(f'\n*** SPARK CHECK ***')
    print(json.dumps(spark, indent=2, ensure_ascii=False))

    print(f'\n*** MTT ***')
    print(json.dumps(mtt, indent=2, ensure_ascii=False))

    print(f'\n*** SNAPSHOT ***')
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))

except Exception as e:
    print(f'PARSE ERROR: {e}')
    print(f'RAW: {pulse_raw[:3000]}')

# Lese den vollen Traum aus experience.yaml
print(f'\n*** VOLLER TRAUM-TEXT ***')
stdin, stdout, stderr = ssh.exec_command(
    "python3 -c \"import yaml; d=yaml.safe_load(open('/opt/hivecore-v2/egons/eva_002/memory/experience.yaml')); dreams=d.get('dreams',[]); d=dreams[-1] if dreams else {}; print(f'ID: {d.get(\\\"id\\\",\\\"?\\\")}'); print(f'Type: {d.get(\\\"type\\\",\\\"?\\\")}'); print(f'Content: {d.get(\\\"content\\\",\\\"?\\\")}'); print(f'Emotional: {d.get(\\\"emotional_summary\\\",\\\"?\\\")}'); print(f'Spark: {d.get(\\\"spark_potential\\\",\\\"?\\\")}')\" 2>&1"
)
print(stdout.read().decode('utf-8'))


# ═══════════════════════════════════════════════════════════════
# ZUSAMMENFASSUNG
# ═══════════════════════════════════════════════════════════════
print(f'\n{"="*70}')
print(f'  EXPERIMENT-ZUSAMMENFASSUNG')
print(f'{"="*70}')
print(f'  Zeitpunkt: {timestamp}')
print(f'  Fragen gestellt: {len(results)}')
print(f'  Antworten erhalten: {sum(1 for r in results if r["response"] != "?")}')
print()

for r in results:
    resp_preview = r['response'][:80].replace('\n', ' ')
    print(f'  {r["id"]}: {resp_preview}...')

ssh.close()

# Speichere Ergebnisse als JSON
output_path = 'C:/Dev/EGONS/hivecore-v2/docs/experiment_eva_brain_test_results.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump({
        'experiment': 'Eva Brain Subsystem Test Protocol',
        'timestamp': timestamp,
        'subject': 'eva_002',
        'questions_count': len(results),
        'results': results,
    }, f, indent=2, ensure_ascii=False)

print(f'\n  Ergebnisse gespeichert: {output_path}')
print(f'\n{"="*70}')
print(f'  EXPERIMENT ABGESCHLOSSEN')
print(f'{"="*70}')
