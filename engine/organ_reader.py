"""Organ Reader — liest Adams Organe aus der neuen 5-Schichten-Struktur.

Jedes Organ hat einen Platz in der neuen Ordnerstruktur:
  core/     → dna.md, ego.md, state.yaml
  social/   → bonds.yaml, network.yaml, owner.md, egon_self.md
  memory/   → episodes.yaml, inner_voice.md, experience.yaml
  contacts/ → active/*.yaml, resting/*.yaml
  capabilities/ → skills.yaml, wallet.yaml

Fallback: Wenn die neue Datei nicht existiert, sucht in der alten Stelle.

Patch 9: state.yaml wird beim Laden validiert und bei Bedarf
         automatisch repariert (Auto-Repair mit DNA-Baseline).
"""

import os
import yaml
from pathlib import Path
from config import EGON_DATA_DIR


def _egon_path(egon_id: str) -> Path:
    """Basispfad fuer einen EGON."""
    return Path(EGON_DATA_DIR) / egon_id


def read_organ(egon_id: str, layer: str, filename: str) -> str:
    """Liest ein Organ als Text.

    Args:
        egon_id: z.B. 'adam'
        layer: z.B. 'core', 'social', 'memory', 'capabilities'
        filename: z.B. 'dna.md', 'state.yaml'

    Returns:
        Dateiinhalt als String, oder '' wenn nicht gefunden.
    """
    # Neue Struktur: egons/adam/{layer}/{filename}
    new_path = _egon_path(egon_id) / layer / filename
    if new_path.is_file():
        return new_path.read_text(encoding='utf-8')

    # Fallback: Alte flache Struktur egons/adam/{filename}
    old_path = _egon_path(egon_id) / filename
    if old_path.is_file():
        return old_path.read_text(encoding='utf-8')

    return ''


def read_yaml_organ(egon_id: str, layer: str, filename: str) -> dict:
    """Liest ein YAML-Organ und parsed es.

    Patch 9: Wenn layer='core' und filename='state.yaml',
    wird der State nach dem Laden validiert und bei Bedarf
    automatisch repariert. Bei nicht-reparierbaren Fehlern
    wird ein Kaskaden-Rollback versucht.

    Returns:
        Parsed YAML als dict, oder {} bei Fehler/nicht gefunden.
    """
    text = read_organ(egon_id, layer, filename)
    if not text:
        return {}

    try:
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            return {}
    except yaml.YAMLError as e:
        print(f'[organ_reader] YAML Parse Error in {layer}/{filename}: {e}')
        # Patch 9: Bei state.yaml YAML-Fehler → Rollback versuchen
        if layer == 'core' and filename == 'state.yaml':
            try:
                from engine.checkpoint import kaskaden_rollback
                print(f'[organ_reader] state.yaml korrupt — starte Kaskaden-Rollback')
                if kaskaden_rollback(egon_id):
                    # Erneut lesen nach Rollback
                    text2 = read_organ(egon_id, layer, filename)
                    if text2:
                        data2 = yaml.safe_load(text2)
                        if isinstance(data2, dict):
                            return data2
            except Exception as e2:
                print(f'[organ_reader] Kaskaden-Rollback fehlgeschlagen: {e2}')
        return {}

    # Patch 9: State-Validierung fuer core/state.yaml
    if layer == 'core' and filename == 'state.yaml' and data:
        try:
            from engine.state_validator import lade_und_validiere
            data = lade_und_validiere(data, egon_id)
        except ImportError:
            pass  # Validator noch nicht deployed — weiter ohne
        except Exception as e:
            print(f'[organ_reader] State-Validierung fehlgeschlagen fuer {egon_id}: {e}')
            # Rollback versuchen
            try:
                from engine.checkpoint import kaskaden_rollback
                if kaskaden_rollback(egon_id):
                    text2 = read_organ(egon_id, layer, filename)
                    if text2:
                        data2 = yaml.safe_load(text2)
                        if isinstance(data2, dict):
                            return data2
            except Exception as e2:
                print(f'[organ_reader] Kaskaden-Rollback fehlgeschlagen: {e2}')
            # Wenn alles fehlschlaegt: leeres dict zurueckgeben
            return {}

    return data


def read_md_organ(egon_id: str, layer: str, filename: str) -> str:
    """Liest ein Markdown-Organ. Convenience-Alias fuer read_organ."""
    return read_organ(egon_id, layer, filename)


def write_organ(egon_id: str, layer: str, filename: str, content: str) -> None:
    """Schreibt ein Organ zurueck.

    Erstellt den Ordner falls noetig.
    """
    path = _egon_path(egon_id) / layer / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def write_yaml_organ(egon_id: str, layer: str, filename: str, data: dict) -> None:
    """Schreibt ein YAML-Organ zurueck.

    Nutzt allow_unicode=True damit deutsche Umlaute sauber bleiben.

    Patch 9: Fuer state.yaml wird vor dem Schreiben validiert.
    Schreibt ueber Temp-Datei + Rename fuer Atomaritaet.
    """
    path = _egon_path(egon_id) / layer / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    # Patch 9: Validierung vor dem Schreiben (nur state.yaml)
    if layer == 'core' and filename == 'state.yaml':
        try:
            from engine.state_validator import quick_validate
            fehler = quick_validate(data)
            if fehler:
                fatale = [f for f in fehler if not f.startswith('KONSISTENZ:')]
                if fatale:
                    print(f'[organ_reader] BLOCKIERT: state.yaml Write fuer {egon_id} '
                          f'hat {len(fatale)} fatale Fehler: {fatale}')
                    return  # Write blockieren
        except ImportError:
            pass  # Validator noch nicht deployed

    # Patch 9: Atomarer Write via Temp-Datei + Rename
    temp_path = path.with_suffix('.yaml.tmp')
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                data,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                width=120,
            )
        # Atomar ersetzen (rename ist atomar auf POSIX)
        temp_path.replace(path)
    except Exception as e:
        print(f'[organ_reader] Write-Fehler {layer}/{filename}: {e}')
        # Temp-Datei aufraumen
        if temp_path.exists():
            temp_path.unlink()
        raise


def list_contact_cards(egon_id: str, folder: str = 'active') -> list[dict]:
    """Liest alle Kontaktkarten aus contacts/{folder}/.

    Returns:
        Liste von parsed YAML-Dicts.
    """
    contacts_dir = _egon_path(egon_id) / 'contacts' / folder
    if not contacts_dir.is_dir():
        return []

    cards = []
    for card_file in sorted(contacts_dir.glob('*.yaml')):
        try:
            data = yaml.safe_load(card_file.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                cards.append(data)
        except yaml.YAMLError as e:
            print(f'[organ_reader] Contact card parse error {card_file}: {e}')

    return cards


def organ_exists(egon_id: str, layer: str, filename: str) -> bool:
    """Prueft ob ein Organ existiert (neue Struktur)."""
    return (_egon_path(egon_id) / layer / filename).is_file()
