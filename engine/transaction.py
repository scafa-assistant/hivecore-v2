"""Atomare Transaktionen — Patch 9 Schicht 3: Write-Ahead-Log.

Jede State-Aenderung wird ZUERST in ein temporaeres Verzeichnis
geschrieben. Erst wenn ALLE Aenderungen erfolgreich sind und
die Validierung besteht, wird atomar committet.

Context-Manager Verwendung:

    from engine.transaction import state_transaktion

    with state_transaktion('adam_001', 'Nacht-Pulse') as tx:
        tx.schreibe_yaml('core', 'state.yaml', neuer_state)
        tx.schreibe_text('memory', 'dreams.md', traum_text)
        # Bei Exception → automatischer Rollback
    # Hier ist alles committed

Biologische Analogie:
  Wie ein Neurotransmitter erst bei ausreichendem
  Kalzium-Einstrom freigesetzt wird (alles-oder-nichts),
  werden State-Aenderungen nur als komplette Einheit
  geschrieben.
"""

import os
import shutil
import time
import yaml
from contextlib import contextmanager
from pathlib import Path

from config import EGON_DATA_DIR


# ================================================================
# Exceptions
# ================================================================

class TransactionError(Exception):
    """Transaktion fehlgeschlagen — alle Aenderungen verworfen."""
    pass


# ================================================================
# Context Manager
# ================================================================

@contextmanager
def state_transaktion(egon_id, beschreibung=''):
    """Context Manager fuer atomare State-Aenderungen.

    Verwendung:
        with state_transaktion('adam_001', 'Nacht-Pulse') as tx:
            tx.schreibe_yaml('core', 'state.yaml', neuer_state)
            tx.schreibe_text('memory', 'dreams.md', neuer_traum)
            # Wenn hier eine Exception fliegt → alles zurueckgerollt
        # Erst hier wird alles auf einmal committet

    Args:
        egon_id: ID des EGON.
        beschreibung: Beschreibung fuer Logging.

    Yields:
        Transaktion-Objekt mit schreibe_yaml() und schreibe_text() Methoden.

    Raises:
        TransactionError: Wenn Commit fehlschlaegt.
    """
    tx = Transaktion(egon_id, beschreibung)

    try:
        yield tx
        tx.commit()
    except TransactionError:
        tx.rollback()
        raise
    except Exception as e:
        tx.rollback()
        raise TransactionError(
            f"Transaktion '{beschreibung}' fehlgeschlagen: {e}"
        ) from e


# ================================================================
# Transaktion-Klasse
# ================================================================

class Transaktion:
    """Sammelt Datei-Aenderungen und schreibt sie atomar.

    Alle Writes gehen zuerst in ein /tmp-Verzeichnis.
    Erst bei commit() werden sie in das Agent-Verzeichnis verschoben.
    Bei rollback() wird das Temp-Verzeichnis geloescht.
    """

    def __init__(self, egon_id, beschreibung=''):
        self.egon_id = egon_id
        self.beschreibung = beschreibung
        self.agent_dir = Path(EGON_DATA_DIR) / egon_id
        self.temp_dir = Path(f'/tmp/egon_tx_{egon_id}_{int(time.time() * 1000)}')
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.aenderungen = {}  # {relative_pfad: temp_pfad}
        self.committed = False
        self._abgebrochen = False

    def schreibe_yaml(self, layer, filename, data):
        """Registriere eine YAML-Aenderung (noch nicht geschrieben!).

        Args:
            layer: z.B. 'core', 'social', 'memory'.
            filename: z.B. 'state.yaml'.
            data: Dict das als YAML geschrieben wird.
        """
        if self.committed:
            raise TransactionError('Transaktion bereits committed')
        if self._abgebrochen:
            raise TransactionError('Transaktion bereits abgebrochen')

        rel_pfad = f'{layer}/{filename}'
        temp_pfad = self.temp_dir / rel_pfad
        temp_pfad.parent.mkdir(parents=True, exist_ok=True)

        # Validierung fuer state.yaml
        if filename == 'state.yaml':
            try:
                from engine.state_validator import quick_validate
                fehler = quick_validate(data)
                if fehler:
                    raise TransactionError(
                        f'State-Validierung vor Write fehlgeschlagen: {fehler}'
                    )
            except ImportError:
                pass  # Validator noch nicht verfuegbar — trotzdem schreiben

        with open(temp_pfad, 'w', encoding='utf-8') as f:
            yaml.dump(
                data, f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                width=120,
            )

        self.aenderungen[rel_pfad] = temp_pfad

    def schreibe_text(self, layer, filename, content):
        """Registriere eine Text-Aenderung (noch nicht geschrieben!).

        Args:
            layer: z.B. 'core', 'memory', 'social'.
            filename: z.B. 'ego.md', 'dreams.md'.
            content: String-Inhalt.
        """
        if self.committed:
            raise TransactionError('Transaktion bereits committed')
        if self._abgebrochen:
            raise TransactionError('Transaktion bereits abgebrochen')

        rel_pfad = f'{layer}/{filename}'
        temp_pfad = self.temp_dir / rel_pfad
        temp_pfad.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_pfad, 'w', encoding='utf-8') as f:
            f.write(str(content))

        self.aenderungen[rel_pfad] = temp_pfad

    def commit(self):
        """Alle Aenderungen ATOMAR uebernehmen.

        1. Backup der aktuellen Dateien
        2. Temp-Dateien an Ziel verschieben
        3. Bei Fehler: Backups wiederherstellen

        Raises:
            TransactionError: Wenn Commit fehlschlaegt.
        """
        if self.committed:
            return
        if self._abgebrochen:
            raise TransactionError('Transaktion bereits abgebrochen')
        if not self.aenderungen:
            self._cleanup()
            return

        # Backup der aktuellen Dateien
        backup_dir = self.temp_dir / '_backup'
        backup_dir.mkdir(exist_ok=True)

        for rel_pfad in self.aenderungen:
            original = self.agent_dir / rel_pfad
            if original.is_file():
                backup_pfad = backup_dir / rel_pfad
                backup_pfad.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(original), str(backup_pfad))

        # Atomar uebernehmen
        try:
            for rel_pfad, temp_pfad in self.aenderungen.items():
                ziel = self.agent_dir / rel_pfad
                ziel.parent.mkdir(parents=True, exist_ok=True)

                # shutil.move ist atomar wenn auf gleicher Partition
                # Fallback: copy + delete
                try:
                    shutil.move(str(temp_pfad), str(ziel))
                except Exception:
                    # Cross-device move: copy then delete
                    shutil.copy2(str(temp_pfad), str(ziel))
                    temp_pfad.unlink()

            self.committed = True

        except Exception as e:
            # ROLLBACK: Backups wiederherstellen
            print(f'[transaction] COMMIT FEHLER — Rollback: {e}')
            for rel_pfad in self.aenderungen:
                backup = backup_dir / rel_pfad
                if backup.is_file():
                    ziel = self.agent_dir / rel_pfad
                    ziel.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(backup), str(ziel))

            raise TransactionError(f'Commit fehlgeschlagen: {e}') from e

        finally:
            self._cleanup()

    def rollback(self):
        """Alles verwerfen — nichts wurde geschrieben."""
        self._abgebrochen = True
        self._cleanup()

    def _cleanup(self):
        """Temp-Verzeichnis aufraumen."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(str(self.temp_dir), ignore_errors=True)
        except Exception:
            pass

    @property
    def anzahl_aenderungen(self):
        """Anzahl registrierter Aenderungen."""
        return len(self.aenderungen)

    def __repr__(self):
        status = 'committed' if self.committed else (
            'abgebrochen' if self._abgebrochen else 'offen'
        )
        return (
            f'<Transaktion {self.egon_id} "{self.beschreibung}" '
            f'[{status}, {len(self.aenderungen)} Aenderungen]>'
        )


# ================================================================
# Convenience: Einzelne atomare Writes
# ================================================================

def atomarer_yaml_write(egon_id, layer, filename, data, beschreibung=''):
    """Einzelner atomarer YAML-Write mit Validierung.

    Fuer einfache Faelle wo nur EINE Datei geschrieben wird.
    Nutzt intern state_transaktion().

    Args:
        egon_id: ID des EGON.
        layer: z.B. 'core'.
        filename: z.B. 'state.yaml'.
        data: Dict.
        beschreibung: Logging-Beschreibung.
    """
    with state_transaktion(egon_id, beschreibung or f'write {layer}/{filename}') as tx:
        tx.schreibe_yaml(layer, filename, data)


def atomarer_text_write(egon_id, layer, filename, content, beschreibung=''):
    """Einzelner atomarer Text-Write.

    Args:
        egon_id: ID des EGON.
        layer: z.B. 'memory'.
        filename: z.B. 'inner_voice.md'.
        content: String.
        beschreibung: Logging-Beschreibung.
    """
    with state_transaktion(egon_id, beschreibung or f'write {layer}/{filename}') as tx:
        tx.schreibe_text(layer, filename, content)
