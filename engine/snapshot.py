"""Post-Pulse Snapshot Engine — Automatische taegliche Archivierung.

Nach jedem Pulse wird der komplette EGON-Zustand als Snapshot gesichert:
- Alle Gehirn-Dateien (v1 .md + v2 YAML organs)
- Pulse-Ergebnis (welche Steps liefen, was wurde generiert)
- Meta-Info (Timestamps, Brain-Version, Dateigroessen)

Snapshots werden unter egons/shared/snapshots/{date}/ gespeichert.
Aehnlich wie Git-Commits: Jeder Snapshot ist ein vollstaendiges Abbild.

Fuer wissenschaftliche Dokumentation und Blockchain-Archivierung.
"""

import json
import shutil
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from config import EGON_DATA_DIR


SNAPSHOT_DIR = Path(EGON_DATA_DIR) / 'shared' / 'snapshots'

# Dateien die pro EGON gesichert werden
V1_FILES = [
    'soul.md', 'memory.md', 'experience.md', 'inner_voice.md',
    'markers.md', 'bonds.md', 'skills.md', 'wallet.md',
]

V2_ORGANS = {
    'core': ['soul.md', 'dna.md', 'ego.md', 'state.yaml', 'body.md'],
    'social': ['bonds.yaml', 'network.yaml', 'bezugsmensch.md', 'owner.md', 'egon_self.md'],
    'memory': ['episodes.yaml', 'inner_voice.yaml', 'inner_voice.md',
               'experience.yaml', 'emotional_state.yaml'],
    'capabilities': ['skills.yaml', 'wallet.yaml'],
}

# v3: Philosophische Pfade (nach Migration)
V3_ORGANS = {
    'kern': ['seele.md', 'ich.md', 'weisheiten.md', 'lebensweg.md', 'ahnen.yaml'],
    'innenwelt': ['innenwelt.yaml', 'koerpergefuehl.yaml'],
    'bindungen': ['naehe.yaml', 'gefuege.yaml', 'begleiter.md', 'selbstbild.md',
                  'gefuege_mapping.yaml'],
    'erinnerungen': ['erlebtes.yaml', 'erfahrungen.yaml', 'kurzzeitgedaechtnis.md',
                     'traeume.yaml', 'zyklusgedaechtnis.md', 'archiv.md',
                     'lebensfaeden.yaml', 'cue_index.yaml'],
    'innere_stimme': ['gedanken.yaml'],
    'leib': ['leib.md', 'bewegungen.yaml'],
    'faehigkeiten': ['koennen.yaml', 'wallet.yaml', 'eigenheiten.yaml'],
    'lebenskraft': ['themen.yaml'],
    'tagebuch': ['selbst.yaml', 'begleiter.yaml'],
}


def _sha256(path: Path) -> str:
    """SHA-256 Hash einer Datei fuer Integritaetsnachweis."""
    if not path.is_file():
        return ''
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _file_size(path: Path) -> int:
    """Dateigroesse in Bytes."""
    return path.stat().st_size if path.is_file() else 0


def create_snapshot(egon_id: str, brain_version: str,
                    pulse_result: dict | None = None) -> dict:
    """Erstellt einen Snapshot des kompletten EGON-Zustands.

    Args:
        egon_id: z.B. 'adam_001'
        brain_version: 'v1' oder 'v2'
        pulse_result: Optionales Pulse-Ergebnis (dict aus run_pulse())

    Returns:
        dict mit Snapshot-Metadaten (Pfad, Hashes, Zeitstempel)
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H%M%S')

    # Snapshot-Verzeichnis: snapshots/2026-02-24/adam_001_083000/
    snap_dir = SNAPSHOT_DIR / date_str / f'{egon_id}_{time_str}'
    snap_dir.mkdir(parents=True, exist_ok=True)

    egon_base = Path(EGON_DATA_DIR) / egon_id
    files_copied = {}
    file_hashes = {}

    if brain_version == 'v1':
        # V1: Kopiere alle .md Dateien
        for fname in V1_FILES:
            src = egon_base / fname
            if src.is_file():
                dst = snap_dir / fname
                shutil.copy2(src, dst)
                files_copied[fname] = _file_size(src)
                file_hashes[fname] = _sha256(src)

        # V1 hat auch memory/ Ordner (experience.yaml falls vorhanden)
        memory_dir = egon_base / 'memory'
        if memory_dir.is_dir():
            snap_mem = snap_dir / 'memory'
            snap_mem.mkdir(exist_ok=True)
            for f in memory_dir.iterdir():
                if f.is_file():
                    shutil.copy2(f, snap_mem / f.name)
                    key = f'memory/{f.name}'
                    files_copied[key] = _file_size(f)
                    file_hashes[key] = _sha256(f)

    else:
        # V2/V3: Kopiere alle Organs aus allen Layern
        # v3 erkennen: kern/ existiert → v3-Organs nutzen
        organs_map = V3_ORGANS if (egon_base / 'kern').is_dir() else V2_ORGANS
        for layer, filenames in organs_map.items():
            layer_dir = egon_base / layer
            if not layer_dir.is_dir():
                continue
            snap_layer = snap_dir / layer
            snap_layer.mkdir(exist_ok=True)

            for fname in filenames:
                src = layer_dir / fname
                if src.is_file():
                    shutil.copy2(src, snap_layer / fname)
                    key = f'{layer}/{fname}'
                    files_copied[key] = _file_size(src)
                    file_hashes[key] = _sha256(src)

            # Auch unbekannte Dateien im Layer mitkopieren
            for f in layer_dir.iterdir():
                if f.is_file() and f.name not in filenames:
                    shutil.copy2(f, snap_layer / f.name)
                    key = f'{layer}/{f.name}'
                    files_copied[key] = _file_size(f)
                    file_hashes[key] = _sha256(f)

        # V2: Auch root-level .md Dateien (memory.md, inner_voice.md, wallet.md)
        for f in egon_base.iterdir():
            if f.is_file() and f.suffix == '.md':
                shutil.copy2(f, snap_dir / f.name)
                files_copied[f.name] = _file_size(f)
                file_hashes[f.name] = _sha256(f)

        # Contacts / Begegnungen
        contacts_dir = egon_base / 'begegnungen' / 'active'
        if not contacts_dir.is_dir():
            contacts_dir = egon_base / 'contacts' / 'active'
        if contacts_dir.is_dir():
            snap_contacts = snap_dir / 'contacts' / 'active'
            snap_contacts.mkdir(parents=True, exist_ok=True)
            for f in contacts_dir.iterdir():
                if f.is_file():
                    shutil.copy2(f, snap_contacts / f.name)
                    key = f'contacts/active/{f.name}'
                    files_copied[key] = _file_size(f)
                    file_hashes[key] = _sha256(f)

    # Pulse-Ergebnis speichern (falls vorhanden)
    pulse_summary = {}
    if pulse_result:
        # Pulse-Ergebnis serialisierbar machen
        safe_result = {}
        for k, v in pulse_result.items():
            try:
                json.dumps(v, ensure_ascii=False)
                safe_result[k] = v
            except (TypeError, ValueError):
                safe_result[k] = str(v)

        pulse_path = snap_dir / 'pulse_result.json'
        with open(pulse_path, 'w', encoding='utf-8') as f:
            json.dump(safe_result, f, indent=2, ensure_ascii=False)

        # Zusammenfassung fuer Meta
        pulse_summary = {
            'steps_executed': list(safe_result.keys()),
            'steps_count': len(safe_result),
            'errors': [k for k, v in safe_result.items()
                       if isinstance(v, str) and v.startswith('error:')],
        }

        # Dream info extrahieren
        dream = safe_result.get('dream_generation', {})
        if isinstance(dream, dict):
            pulse_summary['dream_generated'] = dream.get('dream_id') or dream.get('dream_generated', False)
            pulse_summary['dream_type'] = dream.get('type', '')

    # Meta-Datei schreiben
    meta = {
        'snapshot_timestamp': now.isoformat(),
        'snapshot_date': date_str,
        'egon_id': egon_id,
        'brain_version': brain_version,
        'files_count': len(files_copied),
        'total_size_bytes': sum(files_copied.values()),
        'files': files_copied,
        'sha256_hashes': file_hashes,
        'pulse': pulse_summary,
    }

    meta_path = snap_dir / 'SNAPSHOT_META.json'
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f'[snapshot] {egon_id}: {len(files_copied)} Dateien,'
          f' {sum(files_copied.values()):,} Bytes → {snap_dir}')

    return meta


def list_snapshots(egon_id: str | None = None) -> list[dict]:
    """Listet alle Snapshots auf, optional gefiltert nach EGON.

    Returns:
        Liste von Meta-Dicts, sortiert nach Datum.
    """
    if not SNAPSHOT_DIR.exists():
        return []

    snapshots = []
    for date_dir in sorted(SNAPSHOT_DIR.iterdir()):
        if not date_dir.is_dir():
            continue
        for snap_dir in sorted(date_dir.iterdir()):
            if not snap_dir.is_dir():
                continue
            meta_path = snap_dir / 'SNAPSHOT_META.json'
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding='utf-8'))
                    if egon_id is None or meta.get('egon_id') == egon_id:
                        meta['_path'] = str(snap_dir)
                        snapshots.append(meta)
                except (json.JSONDecodeError, OSError):
                    pass

    return snapshots


def get_latest_snapshot(egon_id: str) -> dict | None:
    """Letzten Snapshot fuer einen EGON laden."""
    snaps = list_snapshots(egon_id)
    return snaps[-1] if snaps else None


def diff_snapshots(snap_a: dict, snap_b: dict) -> dict:
    """Vergleicht zwei Snapshots und zeigt Aenderungen.

    Nuetzlich fuer: "Was hat sich seit gestern veraendert?"
    """
    hashes_a = snap_a.get('sha256_hashes', {})
    hashes_b = snap_b.get('sha256_hashes', {})

    all_files = set(hashes_a.keys()) | set(hashes_b.keys())

    added = []
    removed = []
    changed = []
    unchanged = []

    for f in sorted(all_files):
        h_a = hashes_a.get(f, '')
        h_b = hashes_b.get(f, '')

        if h_a and not h_b:
            removed.append(f)
        elif h_b and not h_a:
            added.append(f)
        elif h_a != h_b:
            changed.append(f)
        else:
            unchanged.append(f)

    return {
        'date_a': snap_a.get('snapshot_date', '?'),
        'date_b': snap_b.get('snapshot_date', '?'),
        'added': added,
        'removed': removed,
        'changed': changed,
        'unchanged': unchanged,
        'total_changes': len(added) + len(removed) + len(changed),
    }
