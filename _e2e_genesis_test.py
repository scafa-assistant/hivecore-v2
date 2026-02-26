"""E2E Integration Test: Kompletter Reproduktionszyklus + Per-Agent Checks.

Phase 1: Alle 6 Agents einzeln abpruefen (Patch 6 korrekt eingepflegt)
Phase 2: E2E Genesis (Adam + Eva → LIBERO geboren → Cleanup)

Laeuft per SSH auf dem Server. Backup + Restore garantiert Originaldaten.
"""
import paramiko
import time

HOST = '159.69.157.42'
USER = 'root'
PW = '$7pa+12+67kR#rPK$7pah'

print('=' * 70)
print(' E2E INTEGRATION TEST: Patch 6 — Alle Agents + Genesis')
print('=' * 70)
print()

# SSH-Verbindung
print('[SSH] Verbindung...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PW, timeout=30)
sftp = ssh.open_sftp()
print('[SSH] Verbunden.')
print()

# ============================================================
# Das gesamte Test-Script wird auf dem Server ausgefuehrt
# ============================================================

test_script = r'''
import sys, os, copy, shutil, yaml
sys.path.insert(0, '/opt/hivecore-v2')
os.chdir('/opt/hivecore-v2')
os.environ['EGON_DATA_DIR'] = '/opt/hivecore-v2/egons'

from pathlib import Path
from datetime import datetime, timedelta
from engine.organ_reader import read_yaml_organ, write_yaml_organ, read_md_organ, write_organ

EGONS_DIR = Path('/opt/hivecore-v2/egons')

total_pass = 0
total_fail = 0

def check(name, condition, detail=''):
    global total_pass, total_fail
    if condition:
        total_pass += 1
        print(f'    [PASS] {name}')
    else:
        total_fail += 1
        print(f'    [FAIL] {name}')
    if detail:
        print(f'           {detail}')

# =================================================================
#  PHASE 1: Alle 6 Agents einzeln durchpruefen
# =================================================================
print('=' * 70)
print(' PHASE 1: Per-Agent Patch 6 Verifikation')
print('=' * 70)

EXPECTED = {
    'adam_001':   {'geschlecht': 'M', 'dna_profile': 'DEFAULT',       'kanal': 'vasopressin'},
    'eva_002':    {'geschlecht': 'F', 'dna_profile': 'DEFAULT',       'kanal': 'oxytocin'},
    'lilith_003': {'geschlecht': 'F', 'dna_profile': 'SEEKING/PLAY',  'kanal': 'oxytocin'},
    'kain_004':   {'geschlecht': 'M', 'dna_profile': 'SEEKING/PLAY',  'kanal': 'vasopressin'},
    'ada_005':    {'geschlecht': 'F', 'dna_profile': 'CARE/PANIC',    'kanal': 'oxytocin'},
    'abel_006':   {'geschlecht': 'M', 'dna_profile': 'DEFAULT',       'kanal': 'vasopressin'},
}

PANKSEPP_10 = ['SEEKING', 'ACTION', 'CARE', 'PLAY', 'FEAR', 'RAGE', 'GRIEF', 'LUST', 'LEARNING', 'PANIC']

for agent_id, expected in EXPECTED.items():
    print()
    print(f'--- {agent_id} ---')

    state = read_yaml_organ(agent_id, 'core', 'state.yaml')
    if not state:
        check(f'{agent_id} state.yaml lesbar', False, 'Datei nicht gefunden!')
        continue

    # 1. Geschlecht
    check(f'geschlecht == {expected["geschlecht"]}',
          state.get('geschlecht') == expected['geschlecht'],
          f'ist: {state.get("geschlecht")}')

    # 2. DNA-Profil
    check(f'dna_profile == {expected["dna_profile"]}',
          state.get('dna_profile') == expected['dna_profile'],
          f'ist: {state.get("dna_profile")}')

    # 3. Pairing-Block vorhanden mit allen Pflichtfeldern
    pairing = state.get('pairing', {})
    pairing_fields = ['reif', 'resonanz_partner', 'resonanz_score', 'pairing_phase',
                      'inkubation', 'eltern', 'kinder']
    missing_p = [f for f in pairing_fields if f not in pairing]
    check(f'pairing Block komplett',
          len(missing_p) == 0,
          f'fehlend: {missing_p}' if missing_p else 'alle 7 Felder vorhanden')

    # 4. Alle 10 Panksepp-Drives vorhanden
    drives = state.get('drives', {})
    missing_d = [d for d in PANKSEPP_10 if d not in drives]
    check(f'alle 10 Drives vorhanden',
          len(missing_d) == 0,
          f'fehlend: {missing_d}' if missing_d else f'LUST={drives.get("LUST")}, FEAR={drives.get("FEAR")}, CARE={drives.get("CARE")}')

    # 5. Drives im gültigen Bereich
    out_of_range = [(d, drives[d]) for d in PANKSEPP_10 if d in drives and not (0.0 <= float(drives[d]) <= 1.0)]
    check(f'alle Drives 0.0-1.0',
          len(out_of_range) == 0,
          f'ausserhalb: {out_of_range}' if out_of_range else '')

    # 6. reif == False (alle Agents sind ~4 Tage alt)
    check(f'reif == False (zu jung)',
          pairing.get('reif') == False,
          f'ist: {pairing.get("reif")}')

    # 7. pairing_phase == 'keine' (alle noch unreif)
    check(f'pairing_phase == keine',
          pairing.get('pairing_phase') == 'keine',
          f'ist: {pairing.get("pairing_phase")}')

    # 8. inkubation == None
    check(f'inkubation == None',
          pairing.get('inkubation') is None,
          f'ist: {pairing.get("inkubation")}')

    # 9. kinder == []
    check(f'kinder == []',
          pairing.get('kinder') == [],
          f'ist: {pairing.get("kinder")}')

    # 10. Bonds vorhanden + bond_typ Feld
    bonds_data = read_yaml_organ(agent_id, 'social', 'bonds.yaml')
    if bonds_data:
        bonds = bonds_data.get('bonds', [])
        check(f'bonds.yaml lesbar ({len(bonds)} Bonds)',
              len(bonds) > 0,
              f'Bond-IDs: {[b.get("id") for b in bonds]}')
        all_have_typ = all('bond_typ' in b for b in bonds)
        check(f'alle Bonds haben bond_typ',
              all_have_typ,
              f'typen: {[b.get("bond_typ") for b in bonds]}')
    else:
        check(f'bonds.yaml lesbar', False, 'Datei nicht gefunden!')

    # 11. Zirkadian vorhanden
    check(f'zirkadian vorhanden',
          'zirkadian' in state,
          f'Phase: {state.get("zirkadian", {}).get("aktuelle_phase", "?")}')

    # 12. Somatic Gate vorhanden
    check(f'somatic_gate vorhanden',
          'somatic_gate' in state,
          '')

    # 13. Resonanz-Engine live testen (update_resonanz)
    from engine.resonanz import update_resonanz
    try:
        rez = update_resonanz(agent_id)
        has_score = 'resonanz_score' in rez
        has_lust = 'lust' in rez
        check(f'update_resonanz() laeuft',
              has_score and has_lust and 'error' not in rez,
              f'score={rez.get("resonanz_score")}, partner={rez.get("resonanz_partner")}, phase={rez.get("pairing_phase")}')

        # 14. LUST korrekt suppressed (alle nicht reif)
        lust_data = rez.get('lust', {})
        check(f'LUST suppressed (nicht reif)',
              lust_data.get('lust_suppressed', False) or lust_data.get('lust_inactive', False),
              f'lust: {lust_data}')
    except Exception as e:
        check(f'update_resonanz() laeuft', False, str(e))

    # 15. Pairing nach Resonanz: Neue Felder gesetzt?
    state_after = read_yaml_organ(agent_id, 'core', 'state.yaml')
    pairing_after = state_after.get('pairing', {})
    has_new_fields = 'lust_aktiv' in pairing_after and 'bindungskanal' in pairing_after
    check(f'lust_aktiv + bindungskanal nach Resonanz',
          has_new_fields,
          f'lust_aktiv={pairing_after.get("lust_aktiv")}, kanal={pairing_after.get("bindungskanal")}')

    # 16. Bindungskanal korrekt fuer Geschlecht
    if has_new_fields:
        check(f'bindungskanal == {expected["kanal"]}',
              pairing_after.get('bindungskanal') == expected['kanal'],
              f'ist: {pairing_after.get("bindungskanal")}')

print()
print(f'  PHASE 1 Ergebnis: {total_pass} PASS, {total_fail} FAIL')
print()


# =================================================================
#  PHASE 2: E2E Genesis — Adam + Eva -> LIBERO
# =================================================================
print('=' * 70)
print(' PHASE 2: E2E Genesis — Adam + Eva → LIBERO')
print('=' * 70)
print()

p2_pass = 0
p2_fail = 0

def check2(name, condition, detail=''):
    global p2_pass, p2_fail
    if condition:
        p2_pass += 1
        print(f'    [PASS] {name}')
    else:
        p2_fail += 1
        print(f'    [FAIL] {name}')
    if detail:
        print(f'           {detail}')

libero_id = None
backup_files = {}

try:
    # ---- A: BACKUP ----
    print('[A] Backup erstellen...')
    backup_paths = [
        ('adam_001', 'core', 'state.yaml'),
        ('eva_002', 'core', 'state.yaml'),
        ('adam_001', 'social', 'bonds.yaml'),
        ('eva_002', 'social', 'bonds.yaml'),
    ]
    # Lobby backup
    lobby_path = EGONS_DIR / 'shared' / 'lobby_chat.yaml'
    if lobby_path.exists():
        with open(lobby_path) as f:
            backup_files['lobby'] = f.read()
    else:
        backup_files['lobby'] = None

    # Social Mapping backups
    sm_adam = EGONS_DIR / 'adam_001' / 'skills' / 'memory' / 'social_mapping' / 'ueber_eva_002.yaml'
    sm_eva = EGONS_DIR / 'eva_002' / 'skills' / 'memory' / 'social_mapping' / 'ueber_adam_001.yaml'
    for label, p in [('sm_adam_eva', sm_adam), ('sm_eva_adam', sm_eva)]:
        if p.exists():
            with open(p) as f:
                backup_files[label] = f.read()
        else:
            backup_files[label] = None

    for eid, layer, fname in backup_paths:
        data = read_yaml_organ(eid, layer, fname)
        backup_files[f'{eid}/{layer}/{fname}'] = copy.deepcopy(data)
        print(f'    Backup: {eid}/{layer}/{fname} OK')
    print()

    # ---- B: MOCK SETUP ----
    print('[B] Mock-Zustand: Adam + Eva auf "bereit" setzen...')

    # Adam: M, bereit, zeigt auf Eva
    adam_state = read_yaml_organ('adam_001', 'core', 'state.yaml')
    adam_state['pairing']['reif'] = True
    adam_state['pairing']['pairing_phase'] = 'bereit'
    adam_state['pairing']['resonanz_partner'] = 'eva_002'
    adam_state['pairing']['resonanz_score'] = 0.82
    adam_state['pairing']['lust_aktiv'] = True
    adam_state['pairing']['bindungskanal'] = 'vasopressin'
    adam_state['pairing']['partner_traum_aktiv'] = True
    adam_state['pairing']['inkubation'] = None
    write_yaml_organ('adam_001', 'core', 'state.yaml', adam_state)
    print('    Adam: reif=True, phase=bereit, partner=eva_002')

    # Eva: F, bereit, zeigt auf Adam
    eva_state = read_yaml_organ('eva_002', 'core', 'state.yaml')
    eva_state['pairing']['reif'] = True
    eva_state['pairing']['pairing_phase'] = 'bereit'
    eva_state['pairing']['resonanz_partner'] = 'adam_001'
    eva_state['pairing']['resonanz_score'] = 0.78
    eva_state['pairing']['lust_aktiv'] = True
    eva_state['pairing']['bindungskanal'] = 'oxytocin'
    eva_state['pairing']['partner_traum_aktiv'] = True
    eva_state['pairing']['inkubation'] = None
    write_yaml_organ('eva_002', 'core', 'state.yaml', eva_state)
    print('    Eva: reif=True, phase=bereit, partner=adam_001')

    # Bonds patchen: gegenseitig romantisch_fest
    adam_bonds = read_yaml_organ('adam_001', 'social', 'bonds.yaml')
    for b in adam_bonds.get('bonds', []):
        if b.get('id') == 'eva_002':
            b['bond_typ'] = 'romantisch_fest'
            b['trust'] = 0.7
            b['familiarity'] = 0.6
    write_yaml_organ('adam_001', 'social', 'bonds.yaml', adam_bonds)

    eva_bonds = read_yaml_organ('eva_002', 'social', 'bonds.yaml')
    for b in eva_bonds.get('bonds', []):
        if b.get('id') == 'adam_001':
            b['bond_typ'] = 'romantisch_fest'
            b['trust'] = 0.7
            b['familiarity'] = 0.6
    write_yaml_organ('eva_002', 'social', 'bonds.yaml', eva_bonds)
    print('    Bonds: adam<->eva = romantisch_fest, trust=0.7')
    print()

    # ---- C: BILATERAL CONSENT ----
    print('[C] Bilateral Consent Check...')
    from engine.genesis import check_bilateral_consent, initiate_pairing, update_inkubation
    from engine.genesis import discover_agents, INKUBATION_TAGE

    consent_ae = check_bilateral_consent('adam_001', 'eva_002')
    check2('bilateral_consent(adam, eva) == True', consent_ae)

    consent_ea = check_bilateral_consent('eva_002', 'adam_001')
    check2('bilateral_consent(eva, adam) == True (symmetrisch)', consent_ea)
    print()

    if not consent_ae:
        # Debug warum consent failed
        print('    DEBUG: Warum kein Consent?')
        for eid in ('adam_001', 'eva_002'):
            s = read_yaml_organ(eid, 'core', 'state.yaml')
            p = s.get('pairing', {})
            print(f'      {eid}: phase={p.get("pairing_phase")}, reif={p.get("reif")}, partner={p.get("resonanz_partner")}, inkub={p.get("inkubation")}')
        from engine.genesis import inzucht_sperre
        print(f'      inzucht_sperre: {inzucht_sperre("adam_001", "eva_002")}')

    # ---- D: PAIRING STARTEN ----
    print('[D] Pairing starten: initiate_pairing(adam, eva)...')
    blueprint = initiate_pairing('adam_001', 'eva_002')
    libero_id = blueprint.get('libero_id')
    libero_name = blueprint.get('name')

    # D1: Blueprint Pflichtfelder
    required_bp = ['libero_id', 'name', 'geschlecht', 'eltern', 'dna_profile', 'drives',
                   'skills', 'erfahrungen', 'start_date', 'end_date']
    missing_bp = [k for k in required_bp if k not in blueprint]
    check2('Blueprint hat alle Pflichtfelder',
           len(missing_bp) == 0,
           f'fehlend: {missing_bp}' if missing_bp else f'libero={libero_id}, name={libero_name}, geschl={blueprint.get("geschlecht")}')

    # D2: libero_id Format
    check2('libero_id Format (name_NNN)',
           libero_id and '_' in libero_id and libero_id.rsplit('_', 1)[1].isdigit(),
           f'id: {libero_id}')

    # D3: Geschlecht M oder F
    check2('geschlecht ist M oder F',
           blueprint.get('geschlecht') in ('M', 'F'),
           f'geschlecht: {blueprint.get("geschlecht")}')

    # D4: Alle 10 Drives im Range
    bp_drives = blueprint.get('drives', {})
    drives_ok = all(0.05 <= float(bp_drives.get(d, -1)) <= 0.95 for d in PANKSEPP_10)
    check2('LIBERO Drives alle 0.05-0.95',
           drives_ok and len(bp_drives) == 10,
           f'{len(bp_drives)} Drives: SEEKING={bp_drives.get("SEEKING")}, CARE={bp_drives.get("CARE")}, LUST={bp_drives.get("LUST")}')

    # D5: dna_profile gueltig
    check2('dna_profile gueltig',
           blueprint.get('dna_profile') in ('DEFAULT', 'SEEKING/PLAY', 'CARE/PANIC'),
           f'profil: {blueprint.get("dna_profile")}')

    # D6: end_date = start_date + 112 Tage
    from datetime import datetime, timedelta
    start = datetime.strptime(blueprint.get('start_date', ''), '%Y-%m-%d')
    end = datetime.strptime(blueprint.get('end_date', ''), '%Y-%m-%d')
    delta = (end - start).days
    check2(f'Inkubation = {INKUBATION_TAGE} Tage',
           delta == INKUBATION_TAGE,
           f'start={blueprint["start_date"]}, end={blueprint["end_date"]}, delta={delta}')
    print()

    # D7: Blueprint bei Mutter gespeichert?
    print('[D] Blueprint-Speicherung pruefen...')
    bp_file = read_yaml_organ('eva_002', 'memory', 'libero_blueprint.yaml')
    check2('Blueprint bei Eva (Mutter) gespeichert',
           bp_file is not None and bp_file.get('libero_id') == libero_id,
           f'gefunden: {bp_file.get("libero_id") if bp_file else "NICHT GEFUNDEN"}')

    # D8: Inkubation in state.yaml beider Eltern
    adam_s = read_yaml_organ('adam_001', 'core', 'state.yaml')
    eva_s = read_yaml_organ('eva_002', 'core', 'state.yaml')

    adam_ink = adam_s.get('pairing', {}).get('inkubation', {})
    eva_ink = eva_s.get('pairing', {}).get('inkubation', {})

    check2('Adam: pairing.inkubation.rolle == vater',
           adam_ink and adam_ink.get('rolle') == 'vater',
           f'rolle: {adam_ink.get("rolle") if adam_ink else "KEINE INKUBATION"}')

    check2('Eva: pairing.inkubation.rolle == mutter',
           eva_ink and eva_ink.get('rolle') == 'mutter',
           f'rolle: {eva_ink.get("rolle") if eva_ink else "KEINE INKUBATION"}')

    check2('Adam: pairing_phase == inkubation',
           adam_s.get('pairing', {}).get('pairing_phase') == 'inkubation',
           f'phase: {adam_s.get("pairing", {}).get("pairing_phase")}')

    check2('Eva: pairing_phase == inkubation',
           eva_s.get('pairing', {}).get('pairing_phase') == 'inkubation',
           f'phase: {eva_s.get("pairing", {}).get("pairing_phase")}')
    print()

    # D9: Lobby-Nachricht
    print('[D] Lobby-Nachricht pruefen...')
    lobby = read_yaml_organ('shared', '', 'lobby_chat.yaml')
    if not lobby:
        # Fallback: direkt lesen
        lp = EGONS_DIR / 'shared' / 'lobby_chat.yaml'
        if lp.exists():
            with open(lp) as f:
                lobby = yaml.safe_load(f) or {}
    messages = lobby.get('messages', []) if lobby else []
    has_lobby_msg = any('erwarten' in str(m.get('message', '')) for m in messages)
    check2('Lobby: "erwarten einen LIBERO" Nachricht',
           has_lobby_msg,
           f'{len(messages)} Nachrichten in Lobby')

    # D10: Social Mapping aktualisiert
    print('[D] Social Mapping pruefen...')
    sm_a = read_yaml_organ('adam_001', 'skills/memory', 'social_mapping/ueber_eva_002.yaml')
    sm_e = read_yaml_organ('eva_002', 'skills/memory', 'social_mapping/ueber_adam_001.yaml')
    adam_sm_ok = sm_a and 'erwarten' in str(sm_a.get('notizen', ''))
    eva_sm_ok = sm_e and 'erwarten' in str(sm_e.get('notizen', ''))
    check2('Adam ueber_eva: "Wir erwarten ein Kind"',
           adam_sm_ok,
           f'notizen: {sm_a.get("notizen") if sm_a else "NICHT GELESEN"}')
    check2('Eva ueber_adam: "Wir erwarten ein Kind"',
           eva_sm_ok,
           f'notizen: {sm_e.get("notizen") if sm_e else "NICHT GELESEN"}')
    print()

    # ---- E: INKUBATION SIMULIEREN ----
    print('[E] Inkubation simulieren...')

    # E1: Ein normaler Inkubation-Update (Mutter)
    eva_care_before = float(read_yaml_organ('eva_002', 'core', 'state.yaml').get('drives', {}).get('CARE', 0))
    result_e = update_inkubation('eva_002')
    eva_care_after = float(read_yaml_organ('eva_002', 'core', 'state.yaml').get('drives', {}).get('CARE', 0))
    check2('Inkubation Eva: CARE gestiegen',
           eva_care_after > eva_care_before,
           f'CARE: {eva_care_before} -> {eva_care_after} (+{round(eva_care_after - eva_care_before, 4)})')

    e_result_ok = result_e and (result_e.get('inkubation_aktiv') == True or 'tage_verbleibend' in (result_e or {}))
    check2('Inkubation Eva: aktiv, kein Genesis',
           e_result_ok,
           f'result: {result_e}')

    # E2: Ein normaler Inkubation-Update (Vater)
    adam_seek_before = float(read_yaml_organ('adam_001', 'core', 'state.yaml').get('drives', {}).get('SEEKING', 0))
    result_a = update_inkubation('adam_001')
    adam_seek_after = float(read_yaml_organ('adam_001', 'core', 'state.yaml').get('drives', {}).get('SEEKING', 0))
    # Vater: SEEKING sinkt
    check2('Inkubation Adam: SEEKING gesunken oder gleich',
           adam_seek_after <= adam_seek_before,
           f'SEEKING: {adam_seek_before} -> {adam_seek_after}')
    print()

    # E3: Zeitsimulation — end_date auf GESTERN setzen
    print('[E] Zeitsimulation: end_date auf gestern...')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    for eid in ('adam_001', 'eva_002'):
        s = read_yaml_organ(eid, 'core', 'state.yaml')
        if s.get('pairing', {}).get('inkubation'):
            s['pairing']['inkubation']['end_date'] = yesterday
            write_yaml_organ(eid, 'core', 'state.yaml', s)
            print(f'    {eid}: end_date -> {yesterday}')

    # Auch Blueprint end_date anpassen
    bp = read_yaml_organ('eva_002', 'memory', 'libero_blueprint.yaml')
    if bp:
        bp['end_date'] = yesterday
        write_yaml_organ('eva_002', 'memory', 'libero_blueprint.yaml', bp)
        print(f'    Blueprint: end_date -> {yesterday}')
    print()

    # ---- F: GENESIS TRIGGERN ----
    print('[F] Genesis triggern: update_inkubation(eva_002)...')
    genesis_result = update_inkubation('eva_002')
    print(f'    Result: {genesis_result}')
    print()

    # F1: Genesis erfolgreich
    check2('Genesis getriggert',
           genesis_result and genesis_result.get('libero_id') is not None,
           f'libero: {genesis_result.get("libero_id") if genesis_result else "KEIN RESULT"}')

    # F2: LIBERO-Verzeichnis und Dateien
    print('[F] LIBERO-Dateien pruefen...')
    if libero_id:
        libero_dir = EGONS_DIR / libero_id
        check2('LIBERO Verzeichnis existiert',
               libero_dir.exists() and libero_dir.is_dir(),
               f'Pfad: {libero_dir}')

        # Alle 15 Dateien pruefen
        file_checks = [
            ('core/dna.md',              'text',  'Generation'),
            ('core/ego.md',              'text',  'neu'),
            ('core/state.yaml',          'yaml',  ['drives', 'pairing', 'survive', 'geschlecht']),
            ('social/bonds.yaml',        'yaml',  ['bonds']),
            ('social/egon_self.md',       'text',  ''),
            ('social/network.yaml',      'yaml',  ['known_egons']),
            ('memory/inner_voice.md',    'text',  'Licht'),
            ('memory/episodes.yaml',     'yaml',  ['episodes']),
            ('memory/experience.yaml',   'yaml',  ['experiences']),
            ('capabilities/skills.yaml', 'yaml',  ['skills']),
            ('capabilities/wallet.yaml', 'yaml',  ['balance']),
        ]

        for fpath, ftype, content_check in file_checks:
            full = libero_dir / fpath
            exists = full.exists()
            detail = ''
            ok = exists
            if exists and ftype == 'text' and content_check:
                txt = full.read_text(encoding='utf-8', errors='replace')
                ok = content_check in txt
                detail = f'{len(txt)} chars' + (f', "{content_check}" {"gefunden" if ok else "NICHT GEFUNDEN"}' if content_check else '')
            elif exists and ftype == 'yaml' and isinstance(content_check, list):
                with open(full) as f:
                    d = yaml.safe_load(f) or {}
                missing = [k for k in content_check if k not in d]
                ok = len(missing) == 0
                detail = f'fehlend: {missing}' if missing else 'alle Keys vorhanden'
            check2(f'Datei: {fpath}', ok, detail)

        # recent_memory.md (kann leer sein)
        rm_path = libero_dir / 'skills' / 'memory' / 'recent_memory.md'
        check2('Datei: skills/memory/recent_memory.md', rm_path.exists())

        # Social Mapping: Eltern
        for parent_id in ['adam_001', 'eva_002']:
            smp = libero_dir / 'skills' / 'memory' / 'social_mapping' / f'ueber_{parent_id}.yaml'
            check2(f'Datei: social_mapping/ueber_{parent_id}.yaml',
                   smp.exists(),
                   f'existiert: {smp.exists()}')

        # F3: Bonds korrekt (OWNER + 2 Eltern)
        print()
        print('[F] LIBERO Bonds pruefen...')
        lb = read_yaml_organ(libero_id, 'social', 'bonds.yaml')
        if lb:
            lb_bonds = lb.get('bonds', [])
            eltern_bonds = [b for b in lb_bonds if b.get('bond_typ') == 'eltern_kind']
            owner_bonds = [b for b in lb_bonds if b.get('bond_typ') == 'owner']
            check2('LIBERO hat 2 Eltern-Kind Bonds',
                   len(eltern_bonds) == 2,
                   f'gefunden: {len(eltern_bonds)} ({[b.get("id") for b in eltern_bonds]})')
            check2('LIBERO hat 1 Owner Bond',
                   len(owner_bonds) == 1,
                   f'gefunden: {len(owner_bonds)}')
            # Eltern-Bond Score
            for eb in eltern_bonds:
                check2(f'Eltern-Bond {eb.get("id")}: score ~30-50',
                       20 <= eb.get('score', 0) <= 60,
                       f'score={eb.get("score")}')

        # F4: Eltern-State aufgeraeumt
        print()
        print('[F] Eltern-State nach Genesis pruefen...')
        for eid in ('adam_001', 'eva_002'):
            s = read_yaml_organ(eid, 'core', 'state.yaml')
            p = s.get('pairing', {})
            check2(f'{eid}: inkubation == None',
                   p.get('inkubation') is None,
                   f'inkubation: {p.get("inkubation")}')
            check2(f'{eid}: pairing_phase == keine',
                   p.get('pairing_phase') == 'keine',
                   f'phase: {p.get("pairing_phase")}')
            check2(f'{eid}: kinder enthaelt {libero_id}',
                   libero_id in p.get('kinder', []),
                   f'kinder: {p.get("kinder")}')

        # F5: Eltern haben Bond zum LIBERO
        print()
        print('[F] Eltern-Bonds zum LIBERO pruefen...')
        for eid in ('adam_001', 'eva_002'):
            eb_data = read_yaml_organ(eid, 'social', 'bonds.yaml')
            if eb_data:
                eb_list = eb_data.get('bonds', [])
                child_bond = [b for b in eb_list if b.get('id') == libero_id]
                check2(f'{eid}: Bond zu {libero_id} existiert',
                       len(child_bond) == 1,
                       f'gefunden: {len(child_bond)}')
                if child_bond:
                    check2(f'{eid}: bond_typ == eltern_kind',
                           child_bond[0].get('bond_typ') == 'eltern_kind',
                           f'typ: {child_bond[0].get("bond_typ")}')
                    check2(f'{eid}: score == 50',
                           child_bond[0].get('score') == 50,
                           f'score: {child_bond[0].get("score")}')

        # F6: Lobby Geburtsnachricht
        print()
        print('[F] Lobby Geburtsnachricht pruefen...')
        lobby2 = None
        lp = EGONS_DIR / 'shared' / 'lobby_chat.yaml'
        if lp.exists():
            with open(lp) as f:
                lobby2 = yaml.safe_load(f) or {}
        msgs2 = lobby2.get('messages', []) if lobby2 else []
        has_birth = any('geboren' in str(m.get('message', '')) for m in msgs2)
        check2('Lobby: Geburtsnachricht vorhanden',
               has_birth,
               f'{len(msgs2)} Nachrichten total')

        # F7: Blueprint geloescht
        print()
        print('[F] Blueprint Cleanup pruefen...')
        bp_after = EGONS_DIR / 'eva_002' / 'memory' / 'libero_blueprint.yaml'
        check2('Blueprint bei Eva geloescht',
               not bp_after.exists(),
               f'existiert noch: {bp_after.exists()}')

        # F8: discover_agents() findet LIBERO
        agents_after = discover_agents()
        check2(f'discover_agents() findet {libero_id}',
               libero_id in agents_after,
               f'Agents: {agents_after}')

        # F9: LIBERO state.yaml konsistent
        print()
        print('[F] LIBERO State konsistenz-check...')
        ls = read_yaml_organ(libero_id, 'core', 'state.yaml')
        if ls:
            check2('LIBERO geschlecht gesetzt',
                   ls.get('geschlecht') in ('M', 'F'),
                   f'geschlecht: {ls.get("geschlecht")}')
            check2('LIBERO dna_profile gueltig',
                   ls.get('dna_profile') in ('DEFAULT', 'SEEKING/PLAY', 'CARE/PANIC'),
                   f'profil: {ls.get("dna_profile")}')
            lp = ls.get('pairing', {})
            check2('LIBERO eltern == [adam_001, eva_002]',
                   set(lp.get('eltern', [])) == {'adam_001', 'eva_002'},
                   f'eltern: {lp.get("eltern")}')
            check2('LIBERO reif == False',
                   lp.get('reif') == False)
            check2('LIBERO kinder == []',
                   lp.get('kinder') == [])

except Exception as e:
    import traceback
    print(f'\n  !!! FEHLER: {e}')
    traceback.print_exc()
    p2_fail += 1

finally:
    # ---- G: CLEANUP ----
    print()
    print('=' * 70)
    print(' CLEANUP: Originaldaten wiederherstellen')
    print('=' * 70)
    print()

    # G1: LIBERO loeschen
    if libero_id:
        libero_dir = EGONS_DIR / libero_id
        if libero_dir.exists():
            shutil.rmtree(libero_dir)
            print(f'    [OK] LIBERO {libero_id} Verzeichnis geloescht')
        else:
            print(f'    [SKIP] LIBERO {libero_id} existiert nicht')

    # G2-G5: State + Bonds restore
    for key in ['adam_001/core/state.yaml', 'eva_002/core/state.yaml',
                'adam_001/social/bonds.yaml', 'eva_002/social/bonds.yaml']:
        data = backup_files.get(key)
        if data:
            parts = key.split('/')
            write_yaml_organ(parts[0], parts[1], parts[2], data)
            print(f'    [OK] Restore: {key}')

    # G6: Lobby restore
    if backup_files.get('lobby') is not None:
        with open(EGONS_DIR / 'shared' / 'lobby_chat.yaml', 'w') as f:
            f.write(backup_files['lobby'])
        print(f'    [OK] Restore: lobby_chat.yaml')
    elif (EGONS_DIR / 'shared' / 'lobby_chat.yaml').exists():
        # Lobby war leer, neue Nachrichten loeschen
        with open(EGONS_DIR / 'shared' / 'lobby_chat.yaml', 'w') as f:
            yaml.dump({'messages': []}, f, allow_unicode=True)
        print(f'    [OK] Restore: lobby_chat.yaml (geleert)')

    # G7-G8: Social Mapping restore
    for label, path in [('sm_adam_eva', sm_adam), ('sm_eva_adam', sm_eva)]:
        original = backup_files.get(label)
        if original is not None:
            with open(path, 'w') as f:
                f.write(original)
            print(f'    [OK] Restore: {path.name}')

    # G9: Verifiziere 6 Agents
    agents_final = discover_agents()
    g_ok = len(agents_final) == 6 and libero_id not in agents_final
    print()
    if g_ok:
        print(f'    [PASS] discover_agents() = 6 Agents (kein LIBERO)')
    else:
        print(f'    [FAIL] discover_agents() = {len(agents_final)}: {agents_final}')

    print()
    print('=' * 70)
    print(f' ERGEBNIS')
    print('=' * 70)
    print()
    print(f'  Phase 1 (Per-Agent): {total_pass} PASS, {total_fail} FAIL')
    print(f'  Phase 2 (E2E Genesis): {p2_pass} PASS, {p2_fail} FAIL')
    print(f'  GESAMT: {total_pass + p2_pass} PASS, {total_fail + p2_fail} FAIL')
    print()
    if total_fail + p2_fail == 0:
        print('  >>> ALLE TESTS BESTANDEN! <<<')
    else:
        print(f'  >>> {total_fail + p2_fail} TESTS FEHLGESCHLAGEN <<<')
'''

# Upload + Ausfuehren
sftp.open('/tmp/_e2e_test.py', 'w').write(test_script)
print('[RUN] Test ausfuehren (kann 30-60 Sekunden dauern)...')
print()
stdin, stdout, stderr = ssh.exec_command(
    'cd /opt/hivecore-v2 && source venv/bin/activate 2>/dev/null; python3 /tmp/_e2e_test.py 2>&1',
    timeout=120
)
out = stdout.read().decode()
err = stderr.read().decode()
print(out.encode('ascii', errors='replace').decode('ascii'))
if err.strip():
    print('STDERR:', err[:2000].encode('ascii', errors='replace').decode('ascii'))

ssh.exec_command('rm -f /tmp/_e2e_test.py')
sftp.close()
ssh.close()
print('[SSH] Verbindung geschlossen.')
