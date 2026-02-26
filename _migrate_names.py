"""Migration: identitaet-Block fuer alle Gen-0 Agents in state.yaml einfuegen.

Jeder Agent bekommt:
  identitaet:
    vorname: <aus ID abgeleitet>
    nachname: null          # entsteht erst beim Pairing
    anzeigename: <Vorname>  # wird nach Pairing "Vorname Nachname"
    generation: 0

Laeuft per SSH/SFTP auf dem Live-Server.
"""
import paramiko
import yaml
import io

HOST = '159.69.157.42'
USER = 'root'
PW = '$7pa+12+67kR#rPK$7pah'
REMOTE_EGONS = '/opt/hivecore-v2/egons'

AGENTS = {
    'adam_001': 'Adam',
    'eva_002': 'Eva',
    'lilith_003': 'Lilith',
    'kain_004': 'Kain',
    'ada_005': 'Ada',
    'abel_006': 'Abel',
}

print('=' * 60)
print(' MIGRATION: identitaet-Block fuer Gen-0 Agents')
print('=' * 60)
print()

# SSH Verbindung
print('[1/3] SSH Verbindung...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PW, timeout=30)
sftp = ssh.open_sftp()
print('  Verbunden.')

# Migration
print()
print('[2/3] identitaet-Block einfuegen...')

for agent_id, vorname in AGENTS.items():
    state_path = f'{REMOTE_EGONS}/{agent_id}/core/state.yaml'
    print(f'\n  {agent_id}:')

    try:
        # State lesen
        with sftp.open(state_path, 'r') as f:
            state = yaml.safe_load(f.read().decode('utf-8'))

        if not state:
            print(f'    [SKIP] state.yaml leer oder nicht lesbar')
            continue

        # Pruefen ob identitaet schon existiert
        if 'identitaet' in state:
            ident = state['identitaet']
            print(f'    [SKIP] identitaet existiert bereits: '
                  f'{ident.get("vorname")} {ident.get("nachname", "(kein Nachname)")}')
            continue

        # identitaet-Block einfuegen
        state['identitaet'] = {
            'vorname': vorname,
            'nachname': None,
            'anzeigename': vorname,
            'generation': 0,
        }

        # Zurueckschreiben
        yaml_str = yaml.dump(state, default_flow_style=False, allow_unicode=True,
                             sort_keys=False)
        with sftp.open(state_path, 'w') as f:
            f.write(yaml_str.encode('utf-8'))

        print(f'    [OK] identitaet hinzugefuegt: vorname={vorname}, nachname=null, gen=0')

    except Exception as e:
        print(f'    [ERR] {e}')

# Verifikation
print()
print('[3/3] Verifikation...')

for agent_id, vorname in AGENTS.items():
    state_path = f'{REMOTE_EGONS}/{agent_id}/core/state.yaml'
    try:
        with sftp.open(state_path, 'r') as f:
            state = yaml.safe_load(f.read().decode('utf-8'))
        ident = state.get('identitaet', {})
        vn = ident.get('vorname', 'FEHLT')
        nn = ident.get('nachname')
        gen = ident.get('generation', '?')
        an = ident.get('anzeigename', 'FEHLT')
        nn_str = nn if nn else '(noch keiner)'
        print(f'  {agent_id}: vorname={vn}, nachname={nn_str}, '
              f'anzeige={an}, gen={gen}')
    except Exception as e:
        print(f'  {agent_id}: FEHLER {e}')

sftp.close()
ssh.close()
print()
print('MIGRATION COMPLETE')
