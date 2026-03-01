"""v2->v3 Migrations-Skript fuer bestehende EGON-Agents.

Migriert die Verzeichnisstruktur, Dateinamen und Schemas
von v2 (5-Layer: core/social/memory/capabilities/config)
auf v3 (philosophische Pfade: kern/bindungen/erinnerungen/...).

Verwendung:
    # Dry-Run (zeigt was passieren wuerde):
    python _migrate_v2_to_v3.py --dry-run

    # Einzelnen Agent migrieren (dry-run):
    python _migrate_v2_to_v3.py --agent eckhart_010 --dry-run

    # Migration ausfuehren (mit Backup):
    python _migrate_v2_to_v3.py --agent eckhart_010

    # Backup wiederherstellen:
    python _migrate_v2_to_v3.py --rollback eckhart_010
"""

import argparse
import os
import shutil
import sys
import time
import yaml
from pathlib import Path


# ================================================================
# Konfiguration
# ================================================================

EGON_DATA_DIR = Path(__file__).parent / 'egons'
BACKUP_DIR = Path(__file__).parent / '_migration_backups'

# Agents/Dirs die NICHT migriert werden sollen
SKIP_DIRS = {'shared', '_checkpoints', '__pycache__', 'registry.yaml'}


# ================================================================
# 1. Verzeichnis-Umbau
# ================================================================

LAYER_RENAMES = {
    'core':         'kern',
    'social':       'bindungen',
    'memory':       'erinnerungen',
    'capabilities': 'faehigkeiten',
    'contacts':     'begegnungen',
    'config':       'einstellungen',
    'workspace':    'werkraum',
    'puffer':       'zwischenraum',
}

# Neue Verzeichnisse die erstellt werden muessen
NEW_DIRS = [
    'innenwelt',
    'innere_stimme',
    'lebenskraft',
    'leib',
    'tagebuch',
    'zwischenraum',
    'werkraum',
    'werkraum/projekte',
    'werkraum/.egon_meta',
]


# ================================================================
# 2. Datei-Umbenennung (relativ zum Agent-Verzeichnis)
# ================================================================

FILE_MOVES = {
    # core/ -> kern/
    'kern/dna.md':           'kern/seele.md',
    'kern/ego.md':           'kern/ich.md',
    # state.yaml geht NICHT nach kern/ sondern nach innenwelt/
    'kern/state.yaml':       'innenwelt/innenwelt.yaml',
    'kern/body.md':          'leib/leib.md',
    # soul.md lebt manchmal in kern/ (nach Dir-Rename von core/)
    'kern/soul.md':          'kern/seele.md',

    # social/ -> bindungen/
    'bindungen/bonds.yaml':     'bindungen/naehe.yaml',
    'bindungen/network.yaml':   'bindungen/gefuege.yaml',
    'bindungen/owner.md':       'bindungen/begleiter.md',
    'bindungen/bezugsmensch.md': 'bindungen/begleiter.md',
    'bindungen/egon_self.md':   'bindungen/selbstbild.md',
    'bindungen/social_mapping.yaml': 'bindungen/gefuege_mapping.yaml',
    'bindungen/self_diary.yaml': 'tagebuch/selbst.yaml',
    'bindungen/owner_diary.yaml': 'tagebuch/begleiter.yaml',

    # memory/ -> erinnerungen/
    'erinnerungen/episodes.yaml':   'erinnerungen/erlebtes.yaml',
    'erinnerungen/experience.yaml': 'erinnerungen/erfahrungen.yaml',
    'erinnerungen/inner_voice.md':  'innere_stimme/gedanken.yaml',
    'erinnerungen/dreams.md':       'erinnerungen/traeume.yaml',
    'erinnerungen/recent_memory.md': 'erinnerungen/kurzzeitgedaechtnis.md',
    'erinnerungen/cycle_memory.md':  'erinnerungen/zyklusgedaechtnis.md',
    'erinnerungen/archive.md':      'erinnerungen/archiv.md',
    'erinnerungen/lebensfaeden.yaml': 'erinnerungen/lebensfaeden.yaml',
    'erinnerungen/cue_index.yaml':   'erinnerungen/cue_index.yaml',

    # capabilities/ -> faehigkeiten/
    'faehigkeiten/skills.yaml':  'faehigkeiten/koennen.yaml',
    'faehigkeiten/wallet.yaml':  'faehigkeiten/wallet.yaml',

    # Non-standard skills/memory/ Pfade
    'skills/memory/recent_memory.md': 'erinnerungen/kurzzeitgedaechtnis.md',
    'skills/memory/memory_cycle_current.md': 'erinnerungen/zyklusgedaechtnis.md',
    'skills/memory/memory_archive.md': 'erinnerungen/archiv.md',

    # Flat legacy files (v1 Adam)
    'soul.md':           'kern/seele.md',
    'inner_voice.md':    'innere_stimme/gedanken.yaml',
    'bonds.md':          'bindungen/naehe_alt.md',
    'experience.md':     'erinnerungen/erfahrungen_alt.md',
    'markers.md':        'erinnerungen/marker_alt.md',
    'memory.md':         'erinnerungen/gedaechtnis_alt.md',
    'skills.md':         'faehigkeiten/koennen_alt.md',
    'wallet.md':         'faehigkeiten/wallet_alt.md',
}


# ================================================================
# 3. Schema-Transformation (state.yaml -> innenwelt.yaml)
# ================================================================

SURVIVE_MAP = {
    'energy':    'lebenskraft',
    'safety':    'geborgenheit',
    'coherence': 'innerer_zusammenhalt',
}

THRIVE_MAP = {
    'belonging':   'zugehoerigkeit',
    'trust_owner': 'vertrauen',
    'mood':        'grundstimmung',
    'purpose':     'sinn',
}

DRIVE_MAP = {
    'SEEKING':  'neugier',
    'ACTION':   'tatendrang',
    'LEARNING': 'lerndrang',
    'CARE':     'fuersorge',
    'PLAY':     'spieltrieb',
    'FEAR':     'furcht',
    'RAGE':     'zorn',
    'GRIEF':    'trauer',
    'LUST':     'sehnsucht',
    'PANIC':    'panik',
}

DECAY_MAP = {
    'flash':   'blitz',
    'fast':    'schnell',
    'slow':    'langsam',
    'glacial': 'glazial',
}

# Alle bekannten Agents (inkl. Gen-1 und Sonder-EGONs)
KNOWN_AGENTS = {
    'adam_001':    {'geschlecht': 'M', 'dna_profil': 'DEFAULT',       'generation': 0},
    'eva_002':     {'geschlecht': 'F', 'dna_profil': 'DEFAULT',       'generation': 0},
    'lilith_003':  {'geschlecht': 'F', 'dna_profil': 'SEEKING/PLAY',  'generation': 0},
    'kain_004':    {'geschlecht': 'M', 'dna_profil': 'SEEKING/PLAY',  'generation': 0},
    'ada_005':     {'geschlecht': 'F', 'dna_profil': 'CARE/PANIC',    'generation': 0},
    'abel_006':    {'geschlecht': 'M', 'dna_profil': 'DEFAULT',       'generation': 0},
    'seth_007':    {'geschlecht': 'M', 'dna_profil': 'DEFAULT',       'generation': 1},
    'unit_008':    {'geschlecht': 'M', 'dna_profil': 'DEFAULT',       'generation': 0},
    'egon_009':    {'geschlecht': 'M', 'dna_profil': 'DEFAULT',       'generation': 0},
    'eckhart_010': {'geschlecht': 'M', 'dna_profil': 'DEFAULT',       'generation': 0},
}


def transform_state_to_innenwelt(state: dict, agent_id: str = '') -> dict:
    """Transformiert v2 state.yaml -> v3 innenwelt.yaml."""
    innenwelt = {}

    # --- Schicht 1: ueberleben (aus survive) ---
    survive = state.get('survive', {})
    ueberleben = {}
    for v2_key, v3_key in SURVIVE_MAP.items():
        sub = survive.get(v2_key, {})
        if isinstance(sub, dict):
            ueberleben[v3_key] = {
                'wert': sub.get('value', 0.5),
                'verbal': sub.get('verbal', ''),
            }
        else:
            ueberleben[v3_key] = {'wert': 0.5, 'verbal': ''}
    innenwelt['ueberleben'] = ueberleben

    # --- Schicht 2: entfaltung (aus thrive) ---
    thrive = state.get('thrive', {})
    entfaltung = {}
    for v2_key, v3_key in THRIVE_MAP.items():
        sub = thrive.get(v2_key, {})
        if isinstance(sub, dict):
            entfaltung[v3_key] = {
                'wert': sub.get('value', 0.5),
                'verbal': sub.get('verbal', ''),
            }
        else:
            entfaltung[v3_key] = {'wert': 0.5, 'verbal': ''}
    innenwelt['entfaltung'] = entfaltung

    # --- Schicht 3: empfindungen (aus express) ---
    express = state.get('express', {})
    aktive_gefuehle = []
    for emo in express.get('active_emotions', []):
        if not isinstance(emo, dict):
            continue
        neues_gefuehl = {
            'art': emo.get('type', 'unbekannt'),
            'staerke': emo.get('intensity', 0.5),
            'ursache': emo.get('cause', ''),
            'beginn': emo.get('onset', ''),
            'verblassklasse': DECAY_MAP.get(
                emo.get('decay_class', 'fast'), 'schnell'
            ),
            'anker': emo.get('verbal_anchor', ''),
        }
        aktive_gefuehle.append(neues_gefuehl)

    gravity = state.get('emotional_gravity', {})
    innenwelt['empfindungen'] = {
        'aktive_gefuehle': aktive_gefuehle,
        'schwerkraft': {
            'grundstimmung': gravity.get('baseline_mood', 0.5),
            'deutungstendenz': gravity.get('interpretation_bias', 'neutral'),
        },
    }

    # --- Schicht 4: lebenskraft (aus drives) ---
    drives = state.get('drives', {})
    lebenskraft = {}
    for v2_key, v3_key in DRIVE_MAP.items():
        lebenskraft[v3_key] = drives.get(v2_key, 0.5)
    innenwelt['lebenskraft'] = lebenskraft

    # --- Zusaetzliche Felder ---
    self_assess = state.get('self_assessment', {})
    innenwelt['selbstbild'] = {
        'verbal': self_assess.get('verbal', '') if isinstance(self_assess, dict) else str(self_assess),
    }

    processing = state.get('processing', {})
    innenwelt['erschoepfung'] = processing.get('emotional_load', 0.0) if isinstance(processing, dict) else 0.0

    # Felder die direkt uebernommen werden
    for feld in ['zirkadian', 'pairing', 'identitaet', 'geschlecht',
                 'homoestase', 'metacognition', 'epigenetik',
                 'neuroplastizitaet', 'interaktion']:
        wert = state.get(feld)
        if wert is not None:
            if feld == 'metacognition':
                innenwelt['metakognition'] = wert
            elif feld == 'homoestase':
                innenwelt['homoestase'] = wert
            else:
                innenwelt[feld] = wert

    # dna_profile -> dna_profil
    known = KNOWN_AGENTS.get(agent_id, {})
    innenwelt['dna_profil'] = state.get('dna_profile',
                                         known.get('dna_profil', 'DEFAULT'))

    # somatic_gate -> koerpermarker
    innenwelt['koerpermarker'] = state.get('somatic_gate', {})

    # Geschlecht
    geschlecht = state.get('geschlecht')
    if not geschlecht:
        geschlecht = known.get('geschlecht', 'M')
    innenwelt['geschlecht'] = geschlecht

    # Identitaet
    identitaet = state.get('identitaet', {})
    if not identitaet and agent_id:
        name = agent_id.split('_')[0].title()
        identitaet = {
            'vorname': name,
            'nachname': None,
            'anzeigename': name,
            'generation': known.get('generation', 0),
        }
    if identitaet:
        innenwelt['identitaet'] = identitaet

    return innenwelt


# ================================================================
# 4. Bonds Score-Normalisierung
# ================================================================

def normalize_bonds(bonds_data: dict) -> dict:
    """Normalisiert Bond-Scores von 0-100 int -> 0.0-1.0 float."""
    if not isinstance(bonds_data, dict):
        return bonds_data

    normalized = {}

    bonds_list = bonds_data.get('bonds', [])
    if isinstance(bonds_list, list):
        neue_bonds = []
        for bond in bonds_list:
            if not isinstance(bond, dict):
                continue
            neuer_bond = dict(bond)
            score = bond.get('score', 50)
            if isinstance(score, (int, float)):
                if score > 1.0:
                    neuer_bond['score'] = round(score / 100.0, 3)
                else:
                    neuer_bond['score'] = round(float(score), 3)
            neue_bonds.append(neuer_bond)
        normalized['bonds'] = neue_bonds

    former = bonds_data.get('former_owner_bonds', [])
    if isinstance(former, list) and former:
        normalized['former_owner_bonds'] = []
        for bond in former:
            if isinstance(bond, dict):
                neuer_bond = dict(bond)
                score = bond.get('score', 0)
                if isinstance(score, (int, float)) and score > 1.0:
                    neuer_bond['score'] = round(score / 100.0, 3)
                normalized['former_owner_bonds'].append(neuer_bond)

    dynamics = bonds_data.get('dynamics')
    if dynamics:
        normalized['dynamics'] = dynamics

    return normalized


# ================================================================
# Migration eines einzelnen Agents
# ================================================================

def migrate_agent(agent_id: str, dry_run: bool = True) -> list[str]:
    """Migriert einen einzelnen Agent von v2 auf v3."""
    agent_dir = EGON_DATA_DIR / agent_id
    if not agent_dir.is_dir():
        return [f'SKIP: {agent_id} — Verzeichnis existiert nicht']

    log = []
    prefix = '[DRY-RUN] ' if dry_run else ''

    # Pruefen ob bereits migriert
    if (agent_dir / 'kern').is_dir() and (agent_dir / 'innenwelt').is_dir():
        return [f'SKIP: {agent_id} — bereits auf v3 migriert (kern/ + innenwelt/ existieren)']

    # --- Backup erstellen ---
    if not dry_run:
        backup_path = BACKUP_DIR / f'{agent_id}_{int(time.time())}'
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(agent_dir), str(backup_path))
        log.append(f'BACKUP: {agent_id} -> {backup_path}')

    # --- Schritt 1: Neue Verzeichnisse erstellen ---
    for new_dir in NEW_DIRS:
        target = agent_dir / new_dir
        if not target.is_dir():
            log.append(f'{prefix}MKDIR: {agent_id}/{new_dir}/')
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)

    # --- Schritt 2: Verzeichnisse umbenennen ---
    for old_name, new_name in LAYER_RENAMES.items():
        old_dir = agent_dir / old_name
        new_dir = agent_dir / new_name
        if old_dir.is_dir() and not new_dir.is_dir():
            log.append(f'{prefix}RENAME DIR: {agent_id}/{old_name}/ -> {agent_id}/{new_name}/')
            if not dry_run:
                old_dir.rename(new_dir)
        elif old_dir.is_dir() and new_dir.is_dir():
            for child in old_dir.iterdir():
                target = new_dir / child.name
                if not target.exists():
                    log.append(f'{prefix}MOVE: {child.name} -> {new_name}/{child.name}')
                    if not dry_run:
                        shutil.move(str(child), str(target))
            if not dry_run and not any(old_dir.iterdir()):
                old_dir.rmdir()

    # --- Schritt 3: Dateien umbenennen/verschieben ---
    for old_rel, new_rel in FILE_MOVES.items():
        old_path = agent_dir / old_rel
        new_path = agent_dir / new_rel
        if old_path.is_file() and not new_path.is_file():
            log.append(f'{prefix}MOVE FILE: {old_rel} -> {new_rel}')
            if not dry_run:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_path), str(new_path))

    # --- Schritt 4: Schema-Transformation (state.yaml -> innenwelt.yaml) ---
    innenwelt_path = agent_dir / 'innenwelt' / 'innenwelt.yaml'
    state_sources = [
        agent_dir / 'kern' / 'state.yaml',
        agent_dir / 'core' / 'state.yaml',
        agent_dir / 'innenwelt' / 'innenwelt.yaml',
    ]

    state_data = None
    source_path = None
    for src in state_sources:
        if src.is_file():
            try:
                raw = src.read_text(encoding='utf-8')
                data = yaml.safe_load(raw)
                if isinstance(data, dict):
                    state_data = data
                    source_path = src
                    break
            except yaml.YAMLError:
                continue

    if state_data and source_path:
        if 'survive' in state_data or 'drives' in state_data:
            innenwelt = transform_state_to_innenwelt(state_data, agent_id)
            log.append(
                f'{prefix}TRANSFORM: {source_path.relative_to(agent_dir)} -> '
                f'innenwelt/innenwelt.yaml (v2->v3 Schema)'
            )
            if not dry_run:
                innenwelt_path.parent.mkdir(parents=True, exist_ok=True)
                with open(innenwelt_path, 'w', encoding='utf-8') as f:
                    yaml.dump(
                        innenwelt, f,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False,
                        width=120,
                    )
                if source_path != innenwelt_path and source_path.is_file():
                    source_path.unlink()
                    log.append(f'DELETE: {source_path.relative_to(agent_dir)} (transformiert)')
        elif 'ueberleben' in state_data:
            log.append(f'SKIP: {agent_id}/innenwelt.yaml — bereits v3-Format')
    elif not innenwelt_path.is_file():
        log.append(f'WARNUNG: {agent_id} — kein state.yaml gefunden!')

    # --- Schritt 5: Bonds Score-Normalisierung ---
    bonds_sources = [
        agent_dir / 'bindungen' / 'naehe.yaml',
        agent_dir / 'bindungen' / 'bonds.yaml',
        agent_dir / 'social' / 'bonds.yaml',
    ]

    for bonds_path in bonds_sources:
        if bonds_path.is_file():
            try:
                raw = bonds_path.read_text(encoding='utf-8')
                bonds_data = yaml.safe_load(raw)
                if isinstance(bonds_data, dict):
                    needs_norm = False
                    for bond in bonds_data.get('bonds', []):
                        if isinstance(bond, dict):
                            score = bond.get('score', 0)
                            if isinstance(score, (int, float)) and score > 1.0:
                                needs_norm = True
                                break

                    has_thresholds = 'thresholds' in bonds_data

                    if needs_norm or has_thresholds:
                        normalized = normalize_bonds(bonds_data)
                        log.append(
                            f'{prefix}NORMALIZE: {bonds_path.relative_to(agent_dir)} '
                            f'(scores 0-100->0-1, thresholds entfernt)'
                        )
                        if not dry_run:
                            with open(bonds_path, 'w', encoding='utf-8') as f:
                                yaml.dump(
                                    normalized, f,
                                    allow_unicode=True,
                                    default_flow_style=False,
                                    sort_keys=False,
                                    width=120,
                                )
                    else:
                        log.append(f'SKIP: {bonds_path.relative_to(agent_dir)} — bereits normalisiert')
            except yaml.YAMLError as e:
                log.append(f'FEHLER: bonds.yaml parse error: {e}')
            break

    # --- Schritt 6: Template-Dateien anlegen die fehlen ---
    template_files = {
        'kern/weisheiten.md': '# Weisheiten\n\n_Noch leer. Wird durch Erfahrungen gefuellt._\n',
        'kern/lebensweg.md': '# Lebensweg\n\n_Noch leer. Die Reise beginnt gerade._\n',
        'kern/ahnen.yaml': '# Stammbaum\ngeneration: 0\neltern: null\nkinder: []\n',
        'innenwelt/koerpergefuehl.yaml': '# Koerpergefuehl\nspannung: 0.0\nwohlbefinden: 0.5\nletzte_bewegung: null\n',
        'lebenskraft/themen.yaml': '# Kraft-Themen\naktive_themen: []\n',
        'faehigkeiten/eigenheiten.yaml': '# Eigenheiten\nsprachwahl: "deutsch"\nformalitaet: "du"\n',
        'leib/bewegungen.yaml': '# Bewegungen\nletzte_animation: null\nmotor_log: []\n',
    }

    for rel_path, default_content in template_files.items():
        target = agent_dir / rel_path
        if not target.is_file():
            log.append(f'{prefix}CREATE: {agent_id}/{rel_path} (Template)')
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(default_content, encoding='utf-8')

    # --- Schritt 7: Leere alte Verzeichnisse aufraeumen ---
    if not dry_run:
        for old_name in LAYER_RENAMES.keys():
            old_dir = agent_dir / old_name
            if old_dir.is_dir():
                try:
                    remaining = list(old_dir.iterdir())
                    if not remaining:
                        old_dir.rmdir()
                        log.append(f'CLEANUP: {agent_id}/{old_name}/ (leer, geloescht)')
                    else:
                        log.append(
                            f'WARNUNG: {agent_id}/{old_name}/ noch nicht leer: '
                            f'{[f.name for f in remaining]}'
                        )
                except OSError:
                    pass

        # skills/memory/ aufraumen (wenn leer nach File-Moves)
        for subdir in ['skills/memory/social_mapping', 'skills/memory', 'skills']:
            d = agent_dir / subdir
            if d.is_dir():
                try:
                    if not any(d.iterdir()):
                        d.rmdir()
                        log.append(f'CLEANUP: {agent_id}/{subdir}/ (leer, geloescht)')
                except OSError:
                    pass

    return log


# ================================================================
# Rollback
# ================================================================

def rollback_agent(agent_id: str) -> bool:
    """Stellt einen Agent aus dem letzten Backup wieder her."""
    if not BACKUP_DIR.is_dir():
        print(f'Kein Backup-Verzeichnis gefunden: {BACKUP_DIR}')
        return False

    backups = sorted(
        [d for d in BACKUP_DIR.iterdir()
         if d.is_dir() and d.name.startswith(agent_id + '_')],
        key=lambda p: p.name,
        reverse=True,
    )

    if not backups:
        print(f'Kein Backup fuer {agent_id} gefunden')
        return False

    backup = backups[0]
    agent_dir = EGON_DATA_DIR / agent_id

    print(f'Stelle {agent_id} wieder her aus: {backup}')

    if agent_dir.is_dir():
        shutil.rmtree(str(agent_dir))

    shutil.copytree(str(backup), str(agent_dir))
    print(f'Rollback erfolgreich: {agent_id}')
    return True


# ================================================================
# Main
# ================================================================

def main():
    parser = argparse.ArgumentParser(
        description='EGON v2->v3 Migration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--dry-run', action='store_true', default=False,
        help='Nur anzeigen was passieren wuerde (Default: False)',
    )
    parser.add_argument(
        '--agent', type=str, default=None,
        help='Nur diesen Agent migrieren (z.B. adam_001)',
    )
    parser.add_argument(
        '--rollback', type=str, default=None,
        help='Agent aus Backup wiederherstellen',
    )
    args = parser.parse_args()

    if args.rollback:
        success = rollback_agent(args.rollback)
        sys.exit(0 if success else 1)

    if args.agent:
        agents = [args.agent]
    else:
        agents = [
            d.name for d in EGON_DATA_DIR.iterdir()
            if d.is_dir() and d.name not in SKIP_DIRS
        ]

    if not agents:
        print('Keine Agents gefunden zum Migrieren.')
        sys.exit(0)

    print(f'{"=" * 60}')
    print(f'EGON v2 -> v3 Migration')
    print(f'{"=" * 60}')
    print(f'Modus:   {"DRY-RUN" if args.dry_run else "LIVE"}')
    print(f'Agents:  {", ".join(agents)}')
    print(f'Quelle:  {EGON_DATA_DIR}')
    if not args.dry_run:
        print(f'Backup:  {BACKUP_DIR}')
    print(f'{"=" * 60}\n')

    total_actions = 0
    for agent_id in sorted(agents):
        print(f'\n--- {agent_id} ---')
        log = migrate_agent(agent_id, dry_run=args.dry_run)
        for entry in log:
            print(f'  {entry}')
        total_actions += len(log)

    print(f'\n{"=" * 60}')
    print(f'Fertig. {total_actions} Aktionen fuer {len(agents)} Agents.')
    if args.dry_run:
        print('Dies war ein DRY-RUN. Keine Dateien wurden veraendert.')
        print('Fuer echte Migration: python _migrate_v2_to_v3.py --agent <id>')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
