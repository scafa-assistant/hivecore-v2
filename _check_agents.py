"""Quick check: Alle 6 Agents state + bonds auf dem Server."""
import paramiko

HOST = '159.69.157.42'
USER = 'root'
PW = '$7pa+12+67kR#rPK$7pah'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PW, timeout=30)
sftp = ssh.open_sftp()

script = r'''
import yaml
from pathlib import Path

agents = ['adam_001', 'eva_002', 'lilith_003', 'kain_004', 'ada_005', 'abel_006']
base = Path('/opt/hivecore-v2/egons')

for a in agents:
    print(f'=== {a} ===')
    with open(base / a / 'core' / 'state.yaml') as f:
        s = yaml.safe_load(f)
    print(f'  geschlecht: {s.get("geschlecht")}')
    print(f'  dna_profile: {s.get("dna_profile")}')
    p = s.get('pairing', {})
    print(f'  pairing.reif: {p.get("reif")}')
    print(f'  pairing.resonanz_partner: {p.get("resonanz_partner")}')
    print(f'  pairing.resonanz_score: {p.get("resonanz_score")}')
    print(f'  pairing.pairing_phase: {p.get("pairing_phase")}')
    print(f'  pairing.lust_aktiv: {p.get("lust_aktiv", "FEHLT")}')
    print(f'  pairing.bindungskanal: {p.get("bindungskanal", "FEHLT")}')
    print(f'  pairing.partner_traum_aktiv: {p.get("partner_traum_aktiv", "FEHLT")}')
    print(f'  pairing.inkubation: {p.get("inkubation")}')
    print(f'  pairing.eltern: {p.get("eltern")}')
    print(f'  pairing.kinder: {p.get("kinder")}')
    d = s.get('drives', {})
    print(f'  drives.LUST: {d.get("LUST")}')
    print(f'  drives.FEAR: {d.get("FEAR")}')
    print(f'  drives.PANIC: {d.get("PANIC")}')
    print(f'  drives.CARE: {d.get("CARE")}')
    print(f'  drives.SEEKING: {d.get("SEEKING")}')
    bonds_path = base / a / 'social' / 'bonds.yaml'
    if bonds_path.exists():
        with open(bonds_path) as f:
            bd = yaml.safe_load(f) or {}
        bonds = bd.get('bonds', [])
        print(f'  bonds: {len(bonds)}')
        for b in bonds:
            print(f'    -> {b.get("id")}: bond_typ={b.get("bond_typ", "FEHLT")}, score={b.get("score")}, trust={b.get("trust", "?")}')
    else:
        print(f'  bonds: DATEI FEHLT')
    print()
'''

sftp.open('/tmp/_check.py', 'w').write(script)
stdin, stdout, stderr = ssh.exec_command('python3 /tmp/_check.py 2>&1')
print(stdout.read().decode())
ssh.exec_command('rm -f /tmp/_check.py')
sftp.close()
ssh.close()
