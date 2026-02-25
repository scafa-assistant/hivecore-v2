"""Baseline-Snapshot via HTTP API (SSH blockiert).

Zieht alle lesbaren Organ-Dateien fuer alle EGONs via /api/egon/{id}/file/ Endpoint.
"""
import json
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_URL = 'http://159.69.157.42:8001/api'
timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
LOCAL_BASE = Path(f'C:/Dev/EGONS/hivecore-v2/snapshots/pre_patch_{timestamp}')
LOCAL_BASE.mkdir(parents=True, exist_ok=True)

# V1 files (Adam)
V1_FILES = ['soul.md', 'memory.md', 'experience.md', 'inner_voice.md', 'markers.md', 'bonds.md', 'skills.md', 'wallet.md']
# V2 mapped via same endpoint
V2_FILES = V1_FILES  # API maps to v2 organs automatically

ALL_EGONS = ['adam_001', 'eva_002', 'lilith_003', 'kain_004', 'ada_005', 'abel_006']


def fetch(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        return f'ERROR: {e}'


print(f'=== BASELINE SNAPSHOT (HTTP) ===')
print(f'Ziel: {LOCAL_BASE}')
print()

# ================================================================
# 1. Profile fuer alle EGONs
# ================================================================
print('[1/4] Profile sichern...')
profiles_dir = LOCAL_BASE / '_profiles'
profiles_dir.mkdir(exist_ok=True)

for eid in ALL_EGONS:
    data = fetch(f'{BASE_URL}/egon/{eid}/profile')
    (profiles_dir / f'{eid}_profile.json').write_text(data, encoding='utf-8')
    # Parse und zeige Zusammenfassung
    try:
        p = json.loads(data)
        print(f'  {eid}: name={p.get("name")}, mood={p.get("mood")}, '
              f'episodes={p.get("total_episodes")}, drives={p.get("drives", {})}')
    except:
        print(f'  {eid}: {data[:80]}')

# ================================================================
# 2. Organ-Dateien fuer alle EGONs
# ================================================================
print()
print('[2/4] Organ-Dateien sichern...')
for eid in ALL_EGONS:
    eid_dir = LOCAL_BASE / eid
    eid_dir.mkdir(exist_ok=True)
    saved = 0
    for fname in V1_FILES:
        data = fetch(f'{BASE_URL}/egon/{eid}/file/{fname}')
        if 'ERROR' not in data and 'Not Found' not in data:
            (eid_dir / fname).write_text(data, encoding='utf-8')
            saved += 1
    print(f'  {eid}: {saved}/{len(V1_FILES)} Dateien')

# ================================================================
# 3. Snapshots-Meta
# ================================================================
print()
print('[3/4] Snapshot-Metadaten sichern...')
snapshots_dir = LOCAL_BASE / '_snapshots'
snapshots_dir.mkdir(exist_ok=True)

for eid in ALL_EGONS:
    data = fetch(f'{BASE_URL}/snapshots?egon_id={eid}')
    (snapshots_dir / f'{eid}_snapshots.json').write_text(data, encoding='utf-8')
    try:
        s = json.loads(data)
        print(f'  {eid}: {s.get("count", 0)} Snapshots')
    except:
        print(f'  {eid}: {data[:60]}')

# Latest snapshots
for eid in ALL_EGONS:
    data = fetch(f'{BASE_URL}/snapshots/latest?egon_id={eid}')
    if 'ERROR' not in data and 'Not Found' not in data:
        (snapshots_dir / f'{eid}_latest.json').write_text(data, encoding='utf-8')

# ================================================================
# 4. Spezial: Traum-Daten + Experience
# ================================================================
print()
print('[4/4] Experience/Traum-Daten...')
for eid in ['adam_001', 'eva_002']:
    data = fetch(f'{BASE_URL}/egon/{eid}/file/experience.md')
    if 'ERROR' not in data and 'Not Found' not in data:
        # Zaehl Traeume
        dream_count = data.lower().count('traum') + data.lower().count('dream')
        print(f'  {eid}: experience geladen ({len(data)} chars, ~{dream_count} Traum-Referenzen)')

# ================================================================
# Zusammenfassung
# ================================================================
print()
total = sum(1 for _ in LOCAL_BASE.rglob('*') if _.is_file())
print(f'=== SNAPSHOT COMPLETE: {total} Dateien in {LOCAL_BASE} ===')
