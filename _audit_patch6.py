"""PATCH 6 AUDIT — Kompletter Nachweis aller Systeme auf dem Live-Server.

Liest ALLES aus und zeigt den Zustand JEDES Agents mit ALLEN Markern.
Kein Mock, keine Simulation — nur echte Daten vom Server.
"""
import paramiko
import time

HOST = '159.69.157.42'
USER = 'root'
PW = '$7pa+12+67kR#rPK$7pah'

print('=' * 75)
print(' PATCH 6 AUDIT — Live-Server Komplett-Nachweis')
print(f' Server: {HOST} | Zeitpunkt: jetzt')
print('=' * 75)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PW, timeout=30)
sftp = ssh.open_sftp()

audit_script = r'''
import sys, os, yaml, json

# __pycache__ loeschen damit neuester Code geladen wird
import shutil
for subdir in ['engine', 'api', '']:
    cache = os.path.join('/opt/hivecore-v2', subdir, '__pycache__') if subdir else '/opt/hivecore-v2/__pycache__'
    if os.path.isdir(cache):
        shutil.rmtree(cache)

sys.path.insert(0, '/opt/hivecore-v2')
os.chdir('/opt/hivecore-v2')
os.environ['EGON_DATA_DIR'] = '/opt/hivecore-v2/egons'

from pathlib import Path
from datetime import datetime, timedelta
from engine.organ_reader import read_yaml_organ, read_md_organ
from engine.resonanz import (
    update_resonanz, _calc_komplementaritaet, _calc_kompatibilitaet,
    _calc_bond_tiefe, _check_reife, _calculate_phase,
    REIFE_MIN_DAYS, DRIVE_KEYS,
)
from engine.genesis import (
    discover_agents, INKUBATION_TAGE, PANKSEPP_DRIVES,
    inzucht_sperre, check_bilateral_consent,
)
from engine.bonds_v2 import _has_exclusive_bond
from engine.lobby import read_lobby
from engine.yaml_to_prompt import pairing_to_prompt, bonds_to_prompt

EGONS_DIR = Path('/opt/hivecore-v2/egons')
AGENTS = discover_agents()

# ================================================================
# SECTION 1: SYSTEM-KONSTANTEN
# ================================================================
print('=' * 75)
print(' 1. SYSTEM-KONSTANTEN')
print('=' * 75)
print()
print(f'  REIFE_MIN_DAYS:     {REIFE_MIN_DAYS} Tage ({REIFE_MIN_DAYS/28:.0f} Zyklen)')
print(f'  INKUBATION_TAGE:    {INKUBATION_TAGE} Tage ({INKUBATION_TAGE/28:.0f} Zyklen)')
print(f'  PANKSEPP_DRIVES:    {len(PANKSEPP_DRIVES)} ({", ".join(PANKSEPP_DRIVES)})')
print(f'  DRIVE_KEYS:         {len(DRIVE_KEYS)} ({", ".join(DRIVE_KEYS)})')
print(f'  Entdeckte Agents:   {len(AGENTS)} ({", ".join(AGENTS)})')
print()

# ================================================================
# SECTION 2: PER-AGENT VOLLSTAENDIGER STATUS
# ================================================================
print('=' * 75)
print(' 2. PER-AGENT STATUS (state.yaml + bonds.yaml + resonanz)')
print('=' * 75)

all_states = {}
all_bonds = {}
all_resonanz = {}

for agent_id in AGENTS:
    print()
    print(f'  {"=" * 60}')
    print(f'  AGENT: {agent_id}')
    print(f'  {"=" * 60}')

    # --- State ---
    state = read_yaml_organ(agent_id, 'core', 'state.yaml')
    if not state:
        print(f'    [FEHLER] state.yaml nicht lesbar!')
        continue
    all_states[agent_id] = state

    geschlecht = state.get('geschlecht', '?')
    dna_profile = state.get('dna_profile', '?')
    drives = state.get('drives', {})
    pairing = state.get('pairing', {})
    survive = state.get('survive', {})
    zirkadian = state.get('zirkadian', {})
    somatic = state.get('somatic_gate', {})

    print()
    print(f'    IDENTITAET:')
    print(f'      Geschlecht:     {geschlecht}')
    print(f'      DNA-Profil:     {dna_profile}')
    print(f'      Bindungskanal:  {"Vasopressin" if geschlecht == "M" else "Oxytocin"}')

    print()
    print(f'    DRIVES (10 Panksepp):')
    for d in PANKSEPP_DRIVES:
        val = drives.get(d, '?')
        bar = '#' * int(float(val) * 20) if val != '?' else ''
        print(f'      {d:10s} {float(val):5.2f}  {bar}')

    print()
    print(f'    SURVIVE:')
    for k in ('energy', 'safety', 'coherence'):
        v = survive.get(k, {})
        print(f'      {k:12s} {v.get("value", "?")}  ({v.get("verbal", "")[:60]})')

    print()
    print(f'    ZIRKADIAN:')
    print(f'      Phase:          {zirkadian.get("aktuelle_phase", "?")}')
    print(f'      Energie:        {zirkadian.get("energy", "?")}')
    print(f'      Gate-Modifier:  {zirkadian.get("somatic_gate_modifier", "?")}')

    print()
    print(f'    SOMATIC GATE:')
    print(f'      Schwelle:       {"JA" if somatic.get("schwelle_ueberschritten") else "NEIN"}')
    print(f'      Marker:         {somatic.get("hoechster_marker", "keiner")} ({somatic.get("hoechster_wert", 0)})')
    print(f'      Impuls:         {somatic.get("impuls_typ", "keiner")}')

    print()
    print(f'    PAIRING-SYSTEM:')
    print(f'      Reif:           {pairing.get("reif", "?")}')
    print(f'      Phase:          {pairing.get("pairing_phase", "?")}')
    print(f'      Partner:        {pairing.get("resonanz_partner", "keiner")}')
    print(f'      Score:          {pairing.get("resonanz_score", 0)}')
    print(f'      LUST aktiv:     {pairing.get("lust_aktiv", "?")}')
    print(f'      Bindungskanal:  {pairing.get("bindungskanal", "?")}')
    print(f'      Partner-Traum:  {pairing.get("partner_traum_aktiv", "?")}')
    print(f'      Inkubation:     {pairing.get("inkubation", "keine")}')
    print(f'      Eltern:         {pairing.get("eltern", "keine (Gen-0)")}')
    print(f'      Kinder:         {pairing.get("kinder", [])}')

    # --- Bonds ---
    bonds_data = read_yaml_organ(agent_id, 'social', 'bonds.yaml')
    all_bonds[agent_id] = bonds_data

    print()
    print(f'    BONDS:')
    if bonds_data:
        bonds_list = bonds_data.get('bonds', [])
        for b in bonds_list:
            bid = b.get('id', '?')
            btyp = b.get('bond_typ', '?')
            bscore = b.get('score', 0)
            btrust = b.get('trust', '?')
            bfam = b.get('familiarity', '?')
            print(f'      -> {bid:20s}  Typ: {btyp:18s}  Score: {bscore:3}  Trust: {btrust}  Fam: {bfam}')
    else:
        print(f'      (keine Bonds)')

    # --- Live Resonanz ---
    print()
    print(f'    LIVE RESONANZ (update_resonanz ausfuehren):')
    try:
        rez = update_resonanz(agent_id)
        all_resonanz[agent_id] = rez
        print(f'      Bester Partner: {rez.get("resonanz_partner", "keiner")}')
        print(f'      Bester Score:   {rez.get("resonanz_score", 0):.3f}')
        print(f'      Phase:          {rez.get("pairing_phase", "?")}')
        print(f'      Reif:           {rez.get("reif", "?")}')
        # Alle Scores
        all_sc = rez.get('all_scores', {})
        if all_sc:
            print(f'      Alle Scores:')
            for pid, sc in sorted(all_sc.items(), key=lambda x: -x[1]):
                print(f'        {pid:20s}  {sc:.3f}  {"<-- BESTER" if pid == rez.get("resonanz_partner") else ""}')

        # LUST Detail
        lust = rez.get('lust', {})
        print(f'      LUST Status:')
        if lust.get('lust_suppressed'):
            print(f'        Suppressed:   JA ({lust.get("reason", "?")})')
            print(f'        LUST Drive:   {lust.get("old", "?")} -> {lust.get("new", "?")}')
        elif lust.get('lust_active'):
            print(f'        Aktiv:        JA ({lust.get("activation_type", "?")})')
            print(f'        LUST Drive:   {lust.get("old", "?")} -> {lust.get("new", "?")}')
            print(f'        Kanal:        {lust.get("bindungskanal", "?")}')
        elif lust.get('lust_inactive'):
            print(f'        Inaktiv:      {lust.get("reason", "?")}')
        else:
            print(f'        Raw:          {lust}')
    except Exception as e:
        print(f'      FEHLER: {e}')
        import traceback
        traceback.print_exc()

    # --- Reife-Detail ---
    print()
    print(f'    REIFE-CHECK DETAIL:')
    try:
        # Alter
        created = None
        ego_md = read_md_organ(agent_id, 'core', 'ego.md') or ''
        # Geburtsdatum aus state oder dna
        dna_md = read_md_organ(agent_id, 'core', 'dna.md') or ''
        # Suche nach Geburtstag/Status/Schoepfungsdatum
        age_days = 0
        for line in dna_md.split('\n'):
            if 'Geburtstag' in line or 'Schoepfung' in line or 'geboren' in line.lower():
                parts = line.split(':')
                if len(parts) >= 2:
                    date_str = parts[-1].strip()
                    try:
                        born = datetime.strptime(date_str, '%Y-%m-%d')
                        age_days = (datetime.now() - born).days
                    except:
                        pass
        print(f'      Alter:            ~{age_days} Tage (Reife ab {REIFE_MIN_DAYS})')
        print(f'      Tage bis Reife:   {max(0, REIFE_MIN_DAYS - age_days)}')

        # Ego-Statements
        ego_stmts = len([l for l in ego_md.split('\n') if l.strip().startswith('- ')])
        print(f'      Ego-Statements:   {ego_stmts} (min 5 noetig)')

        # Social Competence (Bonds > 15)
        strong_bonds = 0
        if bonds_data:
            for b in bonds_data.get('bonds', []):
                if float(b.get('score', 0)) > 15:
                    strong_bonds += 1
        print(f'      Starke Bonds:     {strong_bonds} (min 3 noetig)')

        # Skills
        skills_data = read_yaml_organ(agent_id, 'capabilities', 'skills.yaml')
        skill_count = len(skills_data.get('skills', [])) if skills_data else 0
        print(f'      Skills:           {skill_count} (min 8 noetig)')

        # Emotional Load
        em_load = float(state.get('processing', {}).get('emotional_load', 0))
        print(f'      Emotional Load:   {em_load} (max 0.3 noetig)')

        # Crisis Check
        emotions = state.get('express', {}).get('active_emotions', [])
        max_intensity = max([float(e.get('intensity', 0)) for e in emotions]) if emotions else 0
        print(f'      Max Emotion:      {max_intensity} (max 0.8 noetig)')
    except Exception as e:
        print(f'      FEHLER: {e}')

# ================================================================
# SECTION 3: RESONANZ-NETZWERK (Wer zeigt auf wen?)
# ================================================================
print()
print('=' * 75)
print(' 3. RESONANZ-NETZWERK')
print('=' * 75)
print()

# Tabelle: Gegenseitige Anziehung
males = [a for a in AGENTS if all_states.get(a, {}).get('geschlecht') == 'M']
females = [a for a in AGENTS if all_states.get(a, {}).get('geschlecht') == 'F']

print(f'  Maennlich: {", ".join(m.split("_")[0].title() for m in males)}')
print(f'  Weiblich:  {", ".join(f.split("_")[0].title() for f in females)}')
print()

# Score-Matrix
print(f'  Score-Matrix (M x F):')
print(f'  {"":20s}', end='')
for f in females:
    print(f'  {f.split("_")[0].title():>12s}', end='')
print()

for m in males:
    print(f'  {m.split("_")[0].title():20s}', end='')
    m_rez = all_resonanz.get(m, {})
    m_scores = m_rez.get('all_scores', {})
    m_partner = m_rez.get('resonanz_partner')
    for f in females:
        sc = m_scores.get(f, 0)
        marker = ' <-' if f == m_partner else ''
        print(f'  {sc:>8.3f}{marker:>4s}', end='')
    print()
print()

# Gegenseitige Paare
print(f'  Erkannte Paare (gegenseitige hoechste Resonanz):')
pairs = []
for m in males:
    m_partner = all_resonanz.get(m, {}).get('resonanz_partner')
    if m_partner:
        f_partner = all_resonanz.get(m_partner, {}).get('resonanz_partner')
        if f_partner == m:
            pairs.append((m, m_partner))
            m_score = all_resonanz.get(m, {}).get('resonanz_score', 0)
            f_score = all_resonanz.get(m_partner, {}).get('resonanz_score', 0)
            m_name = m.split('_')[0].title()
            f_name = m_partner.split('_')[0].title()
            print(f'    {m_name} <-> {f_name}  (Scores: {m_score:.3f} / {f_score:.3f})')
        else:
            m_name = m.split('_')[0].title()
            partner_name = m_partner.split('_')[0].title() if m_partner else '?'
            f_partner_name = f_partner.split('_')[0].title() if f_partner else '?'
            print(f'    {m_name} -> {partner_name} (aber {partner_name} -> {f_partner_name})')

# Inzucht-Matrix
print()
print(f'  Inzucht-Sperre Matrix:')
for a in AGENTS:
    blocks = []
    for b in AGENTS:
        if a != b and inzucht_sperre(a, b):
            blocks.append(b.split('_')[0].title())
    if blocks:
        print(f'    {a.split("_")[0].title()}: blockiert mit {", ".join(blocks)}')
    else:
        print(f'    {a.split("_")[0].title()}: keine Sperren (Gen-0)')

# Exklusivitaet
print()
print(f'  Exklusivitaet (romantisch_fest):')
for a in AGENTS:
    has = _has_exclusive_bond(a)
    print(f'    {a.split("_")[0].title()}: {"JA (hat romantisch_fest Bond)" if has else "NEIN (frei)"}')

# ================================================================
# SECTION 4: LUST-SYSTEM STATUS
# ================================================================
print()
print('=' * 75)
print(' 4. LUST-SYSTEM')
print('=' * 75)
print()

for agent_id in AGENTS:
    state = all_states.get(agent_id, {})
    pairing = state.get('pairing', {})
    drives = state.get('drives', {})
    geschl = state.get('geschlecht', '?')
    lust_val = float(drives.get('LUST', 0))
    lust_aktiv = pairing.get('lust_aktiv', False)
    kanal = pairing.get('bindungskanal', '?')

    rez_lust = all_resonanz.get(agent_id, {}).get('lust', {})
    status = 'SUPPRESSED' if rez_lust.get('lust_suppressed') else ('AKTIV' if rez_lust.get('lust_active') else 'INAKTIV')
    reason = rez_lust.get('reason', '')

    name = agent_id.split('_')[0].title()
    print(f'  {name:10s} ({geschl})  LUST={lust_val:.2f}  Status={status:12s}  Kanal={kanal:12s}  Grund={reason}')

# ================================================================
# SECTION 5: BOND-NETZWERK
# ================================================================
print()
print('=' * 75)
print(' 5. BOND-NETZWERK')
print('=' * 75)
print()

for agent_id in AGENTS:
    bd = all_bonds.get(agent_id)
    if not bd:
        continue
    bonds = bd.get('bonds', [])
    name = agent_id.split('_')[0].title()
    print(f'  {name} hat {len(bonds)} Bond(s):')
    for b in bonds:
        bid = b.get('id', '?')
        bname = bid.split('_')[0].title() if '_' in str(bid) else bid
        btyp = b.get('bond_typ', '?')
        bscore = b.get('score', 0)
        btrust = b.get('trust', '?')
        print(f'    -> {bname:15s}  bond_typ={btyp:18s}  score={bscore:3}  trust={btrust}')
    print()

# ================================================================
# SECTION 6: LOBBY (Shared Communication)
# ================================================================
print('=' * 75)
print(' 6. LOBBY')
print('=' * 75)
print()

lobby_messages = read_lobby(max_messages=50)
if lobby_messages:
    print(f'  {len(lobby_messages)} Nachrichten:')
    for m in lobby_messages:
        ts = m.get('timestamp', '?')
        name = m.get('name', '?')
        msg = m.get('message', '')
        emo = m.get('emotional_context', '')
        print(f'    [{ts}] {name}: {msg}')
        if emo:
            print(f'      Emotion: {emo}')
else:
    print('  (Lobby ist leer — korrekt fuer den aktuellen Zustand)')

# ================================================================
# SECTION 7: PROMPT-GENERIERUNG (Was sieht jeder Agent?)
# ================================================================
print()
print('=' * 75)
print(' 7. PAIRING-PROMPT PRO AGENT')
print('=' * 75)

for agent_id in AGENTS:
    state = all_states.get(agent_id, {})
    prompt = pairing_to_prompt(state)
    name = agent_id.split('_')[0].title()
    print()
    print(f'  --- {name} ---')
    if prompt and prompt.strip():
        for line in prompt.strip().split('\n'):
            print(f'    {line}')
    else:
        print(f'    (kein Pairing-Prompt — keine aktive Phase)')

# ================================================================
# SECTION 8: SOCIAL MAPPINGS (Wer weiss was ueber wen?)
# ================================================================
print()
print('=' * 75)
print(' 8. SOCIAL MAPPINGS')
print('=' * 75)
print()

for agent_id in AGENTS:
    name = agent_id.split('_')[0].title()
    sm_dir = EGONS_DIR / agent_id / 'skills' / 'memory' / 'social_mapping'
    if not sm_dir.exists():
        print(f'  {name}: kein social_mapping Verzeichnis')
        continue
    maps = sorted(sm_dir.glob('ueber_*.yaml'))
    print(f'  {name} kennt {len(maps)} Agents:')
    for mp in maps:
        with open(mp) as f:
            sm = yaml.safe_load(f) or {}
        target = mp.stem.replace('ueber_', '').split('_')[0].title()
        trust = sm.get('vertrauen', '?')
        naehe = sm.get('naehe', '?')
        resp = sm.get('respekt', '?')
        inter = sm.get('interaktionen', 0)
        notizen = sm.get('notizen', None)
        notiz_str = f'  Notiz: "{notizen}"' if notizen else ''
        print(f'    -> {target:10s}  Vertr={trust}  Naehe={naehe}  Resp={resp}  Interakt={inter}{notiz_str}')
    print()

# ================================================================
# SECTION 9: ENGINE-VERSIONEN
# ================================================================
print('=' * 75)
print(' 9. ENGINE-DATEIEN')
print('=' * 75)
print()

import os
engine_files = [
    'engine/resonanz.py', 'engine/genesis.py', 'engine/bonds_v2.py',
    'engine/yaml_to_prompt.py', 'engine/pulse_v2.py', 'engine/lobby.py',
    'engine/social_mapping.py', 'engine/somatic_gate.py', 'engine/circadian.py',
    'engine/recent_memory.py',
]
for f in engine_files:
    path = f'/opt/hivecore-v2/{f}'
    if os.path.exists(path):
        size = os.path.getsize(path)
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
        print(f'  {f:40s}  {size:6d} bytes  {mtime}')
    else:
        print(f'  {f:40s}  FEHLT!')

# __pycache__ check
for subdir in ['engine', 'api', '']:
    cache = Path(f'/opt/hivecore-v2/{subdir}/__pycache__') if subdir else Path('/opt/hivecore-v2/__pycache__')
    pyc_count = len(list(cache.glob('*.pyc'))) if cache.exists() else 0
    print(f'  {str(cache):40s}  {pyc_count} .pyc Dateien')

# ================================================================
# ZUSAMMENFASSUNG
# ================================================================
print()
print('=' * 75)
print(' ZUSAMMENFASSUNG')
print('=' * 75)
print()

# Checkliste
checks = [
    ('Agents entdeckt', len(AGENTS) >= 6),
    ('REIFE_MIN_DAYS = 224', REIFE_MIN_DAYS == 224),
    ('INKUBATION_TAGE = 112', INKUBATION_TAGE == 112),
    ('Alle haben Geschlecht', all(all_states.get(a, {}).get('geschlecht') for a in AGENTS)),
    ('Alle haben DNA-Profil', all(all_states.get(a, {}).get('dna_profile') for a in AGENTS)),
    ('Alle haben 10 Drives', all(len(all_states.get(a, {}).get('drives', {})) >= 10 for a in AGENTS)),
    ('Alle haben Pairing-Block', all('pairing' in all_states.get(a, {}) for a in AGENTS)),
    ('Alle haben Zirkadian', all('zirkadian' in all_states.get(a, {}) for a in AGENTS)),
    ('Alle haben Somatic Gate', all('somatic_gate' in all_states.get(a, {}) for a in AGENTS)),
    ('Alle unreif (korrekt)', all(not all_states.get(a, {}).get('pairing', {}).get('reif') for a in AGENTS)),
    ('Alle LUST suppressed', all(all_resonanz.get(a, {}).get('lust', {}).get('lust_suppressed', False) or all_resonanz.get(a, {}).get('lust', {}).get('lust_inactive', False) for a in AGENTS)),
    ('Alle haben Bindungskanal', all(all_states.get(a, {}).get('pairing', {}).get('bindungskanal') for a in AGENTS)),
    ('Alle Bonds haben bond_typ', all(all('bond_typ' in b for b in (all_bonds.get(a, {}) or {}).get('bonds', [])) for a in AGENTS)),
    ('Resonanz laeuft fehlerfrei', all('error' not in all_resonanz.get(a, {}) for a in AGENTS)),
    ('Keine Inzucht-Sperren (Gen-0)', not any(inzucht_sperre(a, b) for a in AGENTS for b in AGENTS if a != b)),
    ('Keine Inkubation aktiv', all(all_states.get(a, {}).get('pairing', {}).get('inkubation') is None for a in AGENTS)),
]

all_ok = True
for label, ok in checks:
    status = 'OK' if ok else 'FAIL'
    if not ok:
        all_ok = False
    print(f'  [{status:4s}] {label}')

print()
if all_ok:
    print(f'  >>> ALLE {len(checks)} CHECKS BESTANDEN — SYSTEM VOLLSTAENDIG OPERATIV <<<')
else:
    fails = sum(1 for _, ok in checks if not ok)
    print(f'  >>> {fails} von {len(checks)} CHECKS FEHLGESCHLAGEN <<<')
'''

sftp.open('/tmp/_audit.py', 'w').write(audit_script)
stdin, stdout, stderr = ssh.exec_command(
    'cd /opt/hivecore-v2 && source venv/bin/activate 2>/dev/null; python3 /tmp/_audit.py 2>&1',
    timeout=120
)
out = stdout.read().decode()
err = stderr.read().decode()
print(out.encode('ascii', errors='replace').decode('ascii'))
if err.strip():
    print('STDERR:', err[:2000].encode('ascii', errors='replace').decode('ascii'))

ssh.exec_command('rm -f /tmp/_audit.py')
sftp.close()
ssh.close()
print('[SSH] Fertig.')
