"""Organ Reader — liest Adams Organe aus der neuen 5-Schichten-Struktur.

Jedes Organ hat einen Platz in der neuen Ordnerstruktur:
  core/     → dna.md, ego.md, state.yaml
  social/   → bonds.yaml, network.yaml, owner.md, egon_self.md
  memory/   → episodes.yaml, inner_voice.md, experience.yaml
  contacts/ → active/*.yaml, resting/*.yaml
  capabilities/ → skills.yaml, wallet.yaml

Fallback: Wenn die neue Datei nicht existiert, sucht in der alten Stelle.
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

    Returns:
        Parsed YAML als dict, oder {} bei Fehler/nicht gefunden.
    """
    text = read_organ(egon_id, layer, filename)
    if not text:
        return {}

    try:
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError as e:
        print(f'[organ_reader] YAML Parse Error in {layer}/{filename}: {e}')
        return {}


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
    """
    path = _egon_path(egon_id) / layer / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )


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
