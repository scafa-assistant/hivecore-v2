"""
Redeploy v3 — Engine + alle 10 EGONs auf den Server.

Ablauf:
  1. SSH Verbindung
  2. __pycache__ loeschen
  3. Engine-Dateien hochladen
  4. Alte EGONs auf Server loeschen (kain_004, abel_006, seth_007, unit_008, egon_009)
  5. Alle 10 EGON-Verzeichnisse hochladen (v3-Struktur)
  6. Service restart
  7. Verifikation (v3-Check)
"""
import paramiko
import json
import urllib.request
import time
import os
import stat

HOST = '159.69.157.42'
USER = 'root'
PW = '$7pa+12+67kR#rPK$7pah'
API_BASE = f'http://{HOST}:8001/api'
LOCAL_BASE = 'C:/Dev/EGONS/hivecore-v2'
REMOTE_BASE = '/opt/hivecore-v2'

# ============================================================
# Alle 10 EGONs (v3)
# ============================================================
EGON_IDS = [
    'adam_001', 'eva_002', 'lilith_003', 'marx_004', 'ada_005',
    'parzival_006', 'sokrates_007', 'leibniz_008', 'goethe_009', 'eckhart_010',
]

# Alte IDs die auf dem Server geloescht werden muessen
OLD_EGON_IDS = ['kain_004', 'abel_006', 'seth_007', 'unit_008', 'egon_009']

# ============================================================
# Engine + API + Frontend Dateien
# ============================================================
DEPLOY_ENGINE_FILES = [
    # Core Engine
    'engine/organ_reader.py',
    'engine/state_manager.py',
    'engine/state_validator.py',
    'engine/yaml_to_prompt.py',
    'engine/prompt_builder.py',
    'engine/prompt_builder_v2.py',
    'engine/pulse.py',
    'engine/pulse_v2.py',
    'engine/context_budget_v2.py',
    'engine/visibility_v2.py',
    'engine/snapshot.py',
    'engine/checkpoint.py',
    'engine/transaction.py',
    'engine/agent_loop.py',
    'engine/tools.py',
    # Subsysteme
    'engine/naming.py',
    'engine/somatic_gate.py',
    'engine/circadian.py',
    'engine/lobby.py',
    'engine/social_mapping.py',
    'engine/recent_memory.py',
    'engine/bonds_v2.py',
    'engine/resonanz.py',
    'engine/genesis.py',
    'engine/contact_manager.py',
    'engine/episodes_v2.py',
    'engine/experience_v2.py',
    'engine/groupchat.py',
    'engine/response_parser.py',
    'engine/motor_translator.py',
    'engine/interaction_log.py',
    'engine/owner_portrait.py',
    'engine/self_diary.py',
    # Patch-Systeme
    'engine/homoestase.py',
    'engine/thalamus.py',
    'engine/cue_index.py',
    'engine/decay.py',
    'engine/metacognition.py',
    'engine/epigenetik.py',
    'engine/multi_egon.py',
    'engine/neuroplastizitaet.py',
    'engine/kalibrierung.py',
    'engine/langzeit_skalierung.py',
    'engine/lebensfaeden.py',
    'engine/inner_cycle.py',
    'engine/vergessenspuffer.py',
    'engine/erkenntnisse.py',
    'engine/traum_reflexion.py',
    'engine/puls_hierarchie.py',
    'engine/inner_voice_v2.py',
    'engine/inner_voice.py',
    'engine/markers.py',
    'engine/memory.py',
    'engine/dna_compressor.py',
    # API
    'api/brain.py',
    'api/chat.py',
    'api/files.py',
    'api/profile.py',
    'api/profile_server.py',
    'api/lobby.py',
    'api/groupchat.py',
    'api/voice.py',
    # LLM
    'llm/router.py',
    'llm/planner.py',
    # Root
    'main.py',
    'config.py',
    '.env',
    # Frontend
    'neuromap/index.html',
    'neuromap/neuromap.jsx',
    'neuromap/api.js',
    'neuromap/style.css',
    'groupchat/index.html',
]


def sftp_mkdir_p(sftp, remote_dir):
    """mkdir -p ueber SFTP."""
    dirs_to_create = []
    d = remote_dir
    while d and d != '/':
        try:
            sftp.stat(d)
            break
        except FileNotFoundError:
            dirs_to_create.append(d)
            d = '/'.join(d.split('/')[:-1])
    for d in reversed(dirs_to_create):
        try:
            sftp.mkdir(d)
        except IOError:
            pass


def sftp_upload_dir(sftp, local_dir, remote_dir, label=''):
    """Ganzes Verzeichnis rekursiv hochladen."""
    count = 0
    for root, dirs, files in os.walk(local_dir):
        rel_root = os.path.relpath(root, local_dir).replace('\\', '/')
        if rel_root == '.':
            rel_root = ''
        for f in files:
            local_path = os.path.join(root, f).replace('\\', '/')
            if rel_root:
                remote_path = f'{remote_dir}/{rel_root}/{f}'
            else:
                remote_path = f'{remote_dir}/{f}'
            remote_file_dir = '/'.join(remote_path.split('/')[:-1])
            sftp_mkdir_p(sftp, remote_file_dir)
            try:
                sftp.put(local_path, remote_path)
                count += 1
            except Exception as e:
                print(f'    [ERR] {remote_path}: {e}')
    if label:
        print(f'    {label}: {count} Dateien')
    return count


# ============================================================
# START
# ============================================================
print('=' * 60)
print(' REDEPLOY v3 — 10 EGONs + Engine')
print('=' * 60)
print()

# 1. SSH
print('[1/7] SSH Verbindung...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PW, timeout=30)
sftp = ssh.open_sftp()
print('  Verbunden.')

# 2. __pycache__ loeschen
print()
print('[2/7] __pycache__ loeschen...')
for subdir in ['engine', 'api', 'llm', '']:
    cache_dir = f'{REMOTE_BASE}/{subdir}/__pycache__' if subdir else f'{REMOTE_BASE}/__pycache__'
    ssh.exec_command(f'rm -rf {cache_dir}')
print('  OK')

# 3. Engine-Dateien hochladen
print()
print(f'[3/7] {len(DEPLOY_ENGINE_FILES)} Engine-Dateien hochladen...')
ok_count = 0
err_count = 0
for rel_path in DEPLOY_ENGINE_FILES:
    local_path = os.path.join(LOCAL_BASE, rel_path).replace('\\', '/')
    remote_path = f'{REMOTE_BASE}/{rel_path}'
    remote_dir = '/'.join(remote_path.split('/')[:-1])
    sftp_mkdir_p(sftp, remote_dir)
    try:
        sftp.put(local_path, remote_path)
        ok_count += 1
    except Exception as e:
        print(f'  [ERR] {rel_path}: {e}')
        err_count += 1
print(f'  {ok_count} OK, {err_count} Fehler')

# 4. Alte EGONs auf Server loeschen
print()
print('[4/7] Alte EGONs loeschen (Server)...')
for old_id in OLD_EGON_IDS:
    remote_egon = f'{REMOTE_BASE}/egons/{old_id}'
    stdin, stdout, stderr = ssh.exec_command(f'rm -rf {remote_egon} 2>&1')
    out = stdout.read().decode().strip()
    print(f'  rm -rf {old_id}: {out or "OK"}')
# Auch alte Symlinks loeschen (seth_007, unit_008, egon_009 waren Symlinks)
for old_id in OLD_EGON_IDS:
    ssh.exec_command(f'rm -f {REMOTE_BASE}/egons/{old_id} 2>&1')

# 5. Alle 10 EGON-Verzeichnisse hochladen
print()
print('[5/7] 10 EGONs hochladen (v3-Struktur)...')
total_files = 0
for egon_id in EGON_IDS:
    local_egon = os.path.join(LOCAL_BASE, 'egons', egon_id).replace('\\', '/')
    remote_egon = f'{REMOTE_BASE}/egons/{egon_id}'
    # Erst altes Verzeichnis auf Server loeschen (fuer sauberen Upload)
    ssh.exec_command(f'rm -rf {remote_egon}')
    time.sleep(0.2)
    count = sftp_upload_dir(sftp, local_egon, remote_egon, label=egon_id)
    total_files += count
print(f'  TOTAL: {total_files} Dateien fuer {len(EGON_IDS)} EGONs')

# 6. Restart
print()
print('[6/7] Service restart...')
stdin, stdout, stderr = ssh.exec_command('systemctl restart egon.service 2>&1')
out = stdout.read().decode()
print(f'  RESTART: {out.strip() or "OK"}')
time.sleep(5)
stdin, stdout, stderr = ssh.exec_command('systemctl is-active egon.service 2>&1')
status = stdout.read().decode().strip()
print(f'  STATUS: {status}')

# 7. Verifikation
print()
print('[7/7] Verifikation...')

verify_script = r'''
import sys, os
sys.path.insert(0, '/opt/hivecore-v2')
os.chdir('/opt/hivecore-v2')
os.environ['EGON_DATA_DIR'] = '/opt/hivecore-v2/egons'

EGON_IDS = [
    'adam_001', 'eva_002', 'lilith_003', 'marx_004', 'ada_005',
    'parzival_006', 'sokrates_007', 'leibniz_008', 'goethe_009', 'eckhart_010',
]

V3_DIRS = [
    'kern', 'innenwelt', 'bindungen', 'erinnerungen', 'erkenntnisse',
    'faehigkeiten', 'einstellungen', 'innere_stimme', 'kraft',
    'lebenskraft', 'leib', 'tagebuch', 'werkraum', 'zwischenraum',
]

V3_FILES = [
    'kern/seele.md', 'kern/ich.md', 'kern/weisheiten.md', 'kern/lebensweg.md',
    'innenwelt/innenwelt.yaml', 'innenwelt/koerpergefuehl.yaml',
    'bindungen/naehe.yaml', 'bindungen/gefuege.yaml', 'bindungen/begleiter.md',
    'leib/leib.md',
    'erinnerungen/erlebtes.yaml', 'erinnerungen/erfahrungen.yaml',
    'innere_stimme/gedanken.yaml',
    'kraft/register.json',
]

errors = 0

# Check 1: v3 Verzeichnisse
print('--- v3 Verzeichnisse ---')
for eid in EGON_IDS:
    missing = []
    for d in V3_DIRS:
        path = f'/opt/hivecore-v2/egons/{eid}/{d}'
        if not os.path.isdir(path):
            missing.append(d)
    if missing:
        print(f'  {eid}: FEHLT {missing}')
        errors += 1
    else:
        print(f'  {eid}: 14/14 Dirs OK')

# Check 2: Kritische v3 Dateien
print('--- Kritische Dateien ---')
for eid in EGON_IDS:
    missing = []
    for f in V3_FILES:
        path = f'/opt/hivecore-v2/egons/{eid}/{f}'
        if not os.path.isfile(path) or os.path.getsize(path) < 5:
            missing.append(f)
    if missing:
        print(f'  {eid}: FEHLT {missing}')
        errors += 1
    else:
        print(f'  {eid}: {len(V3_FILES)}/{len(V3_FILES)} Dateien OK')

# Check 3: innenwelt.yaml v3 Schema
print('--- innenwelt.yaml Schema ---')
import yaml
for eid in EGON_IDS:
    path = f'/opt/hivecore-v2/egons/{eid}/innenwelt/innenwelt.yaml'
    try:
        with open(path) as fh:
            state = yaml.safe_load(fh)
        has_v3 = all(k in state for k in ['ueberleben', 'entfaltung', 'empfindungen', 'lebenskraft', 'identitaet'])
        name = state.get('identitaet', {}).get('vorname', '?')
        profil = state.get('dna_profil', '?')
        print(f'  {eid}: v3={"OK" if has_v3 else "FAIL"} name={name} profil={profil}')
        if not has_v3:
            errors += 1
    except Exception as e:
        print(f'  {eid}: FEHLER {e}')
        errors += 1

# Check 4: Alte EGONs geloescht
print('--- Alte EGONs ---')
for old_id in ['kain_004', 'abel_006', 'seth_007', 'unit_008', 'egon_009']:
    path = f'/opt/hivecore-v2/egons/{old_id}'
    if os.path.exists(path):
        print(f'  {old_id}: NOCH DA — bitte manuell loeschen!')
        errors += 1
    else:
        print(f'  {old_id}: geloescht OK')

# Check 5: Engine Imports
print('--- Engine Imports ---')
try:
    from engine.organ_reader import read_organ, write_organ
    print('  organ_reader: OK')
except Exception as e:
    print(f'  organ_reader: FAIL {e}')
    errors += 1

try:
    from engine.groupchat import GRUPPENCHAT_EGONS
    print(f'  groupchat: {len(GRUPPENCHAT_EGONS)} EGONs OK')
except Exception as e:
    print(f'  groupchat: FAIL {e}')
    errors += 1

try:
    from engine.lobby import write_lobby, read_lobby
    from engine.resonanz import REIFE_MIN_DAYS
    from engine.genesis import INKUBATION_TAGE
    print(f'  lobby+resonanz+genesis: OK (REIFE={REIFE_MIN_DAYS}d, INKUBATION={INKUBATION_TAGE}d)')
except Exception as e:
    print(f'  subsysteme: FAIL {e}')
    errors += 1

# Check 6: organ_reader Alias-Layer
print('--- Alias-Layer ---')
try:
    from engine.organ_reader import LAYER_ALIASES, FILE_ALIASES
    print(f'  LAYER_ALIASES: {len(LAYER_ALIASES)} Eintraege')
    print(f'  FILE_ALIASES: {len(FILE_ALIASES)} Eintraege')
except Exception as e:
    print(f'  Alias-Layer: FAIL {e}')
    errors += 1

print()
if errors == 0:
    print('=== ALLE CHECKS BESTANDEN ===')
else:
    print(f'=== {errors} FEHLER GEFUNDEN ===')
'''

sftp.open('/tmp/_verify_v3.py', 'w').write(verify_script)
stdin, stdout, stderr = ssh.exec_command(
    'cd /opt/hivecore-v2 && source venv/bin/activate 2>/dev/null; python3 /tmp/_verify_v3.py 2>&1'
)
out = stdout.read().decode('ascii', errors='replace')
print(out)
err = stderr.read().decode('ascii', errors='replace')
if err.strip():
    print(f'  STDERR: {err[:500]}')
ssh.exec_command('rm -f /tmp/_verify_v3.py')

# API Health
time.sleep(2)
try:
    req = urllib.request.Request(f'http://{HOST}:8001/')
    with urllib.request.urlopen(req, timeout=10) as resp:
        health = json.loads(resp.read().decode())
    print(f'  API: {health.get("name", "?")} v{health.get("version", "?")} — {health.get("egon_count", "?")} EGONs')
except Exception as e:
    print(f'  API: {e}')

sftp.close()
ssh.close()
print()
print('REDEPLOY v3 COMPLETE')
