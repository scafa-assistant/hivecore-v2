"""Checkpoint System — Patch 9 Schicht 2: Snapshots & Rollback.

Erstellt tar.gz Snapshots vor kritischen Operationen:
  - pre_pulse:   Vor jedem Nacht-Pulse
  - pre_cycle:   Vor Zyklusende-Konsolidierung
  - pre_genesis: Vor LIBERI-Genesis (beide Eltern)
  - auto_6h:     Alle 6 Stunden als Sicherheitsnetz

Biologische Analogie:
  Wie die synaptische Konsolidierung im Schlaf stabile
  Zustaende schafft, erstellen Checkpoints stabile
  Wiederherstellungspunkte.

Speicher-Impact: ~24 KB/Tag/Agent (komprimiert).
"""

import io
import tarfile
import time
import yaml
from datetime import datetime, timedelta
from pathlib import Path

from config import EGON_DATA_DIR


# ================================================================
# Konfiguration
# ================================================================

MAX_CHECKPOINTS_PRO_TYP = 5  # Aelteste werden rotiert

# Welche Dateien pro Checkpoint-Typ gesichert werden.
# Pfade relativ zum EGON-Verzeichnis.
# WICHTIG: Enthaelt SOWOHL v2-Pfade (5-Layer) als auch v1-Pfade (flat/hybrid).
# Nicht-existierende Dateien werden beim Backup uebersprungen.
CHECKPOINT_SCOPES = {
    'pre_pulse': [
        # State (v2 + v3)
        'core/state.yaml',
        'innenwelt/innenwelt.yaml',
        # Recent Memory (v2 Pfad: skills/memory/, legacy: memory/, v3: erinnerungen/)
        'skills/memory/recent_memory.md',
        'memory/recent_memory.md',
        'erinnerungen/kurzzeitgedaechtnis.md',
        # Inner Voice (v2: memory/, v3: innere_stimme/, legacy: flat)
        'memory/inner_voice.md',
        'innere_stimme/gedanken.yaml',
        'inner_voice.md',
        # Dreams (v2 + v3)
        'memory/dreams.md',
        'erinnerungen/traeume.yaml',
    ],
    'pre_cycle': [
        # Core (v2 + v3)
        'core/state.yaml',
        'innenwelt/innenwelt.yaml',
        'core/ego.md',
        'kern/ich.md',
        # Memory (v2 + v3 + legacy Pfade)
        'memory/inner_voice.md',
        'innere_stimme/gedanken.yaml',
        'inner_voice.md',
        'skills/memory/recent_memory.md',
        'memory/recent_memory.md',
        'erinnerungen/kurzzeitgedaechtnis.md',
        'memory/cycle_memory.md',
        'erinnerungen/zyklusgedaechtnis.md',
        'memory/archive.md',
        'erinnerungen/archiv.md',
        'memory/dreams.md',
        'erinnerungen/traeume.yaml',
        'memory/episodes.yaml',
        'erinnerungen/erlebtes.yaml',
        'memory/experience.yaml',
        'erinnerungen/erfahrungen.yaml',
        # Social (v2 + v3)
        'social/bonds.yaml',
        'bindungen/naehe.yaml',
        'bonds.md',
        'social/social_mapping.yaml',
        'bindungen/gefuege_mapping.yaml',
        # Lebensfaeden + Cue-Index (v2 + v3)
        'memory/lebensfaeden.yaml',
        'erinnerungen/lebensfaeden.yaml',
        'memory/cue_index.yaml',
        'erinnerungen/cue_index.yaml',
        # Legacy flat files (v1 Adam)
        'memory.md',
    ],
    'pre_genesis': [
        'core/state.yaml',
        'innenwelt/innenwelt.yaml',
        'core/ego.md',
        'kern/ich.md',
        'memory/inner_voice.md',
        'innere_stimme/gedanken.yaml',
        'inner_voice.md',
        'skills/memory/recent_memory.md',
        'memory/recent_memory.md',
        'erinnerungen/kurzzeitgedaechtnis.md',
        'memory/cycle_memory.md',
        'erinnerungen/zyklusgedaechtnis.md',
        'memory/archive.md',
        'erinnerungen/archiv.md',
        'memory/dreams.md',
        'erinnerungen/traeume.yaml',
        'social/bonds.yaml',
        'bindungen/naehe.yaml',
        'bonds.md',
        'social/social_mapping.yaml',
        'bindungen/gefuege_mapping.yaml',
        'memory/lebensfaeden.yaml',
        'erinnerungen/lebensfaeden.yaml',
        'memory/cue_index.yaml',
        'erinnerungen/cue_index.yaml',
    ],
    'auto_6h': [
        'core/state.yaml',
        'innenwelt/innenwelt.yaml',
        'core/ego.md',
        'kern/ich.md',
    ],
}

# Retention-Policy (Tage)
RETENTION_TAGE = {
    'auto_6h':      3,
    'pre_pulse':    7,
    'pre_cycle':    0,     # 0 = nie loeschen (Meilensteine)
    'pre_genesis':  0,     # 0 = nie loeschen (einmaliges Ereignis)
    'pre_rollback': 1,
}


# ================================================================
# Hilfsfunktionen
# ================================================================

def _egon_path(egon_id):
    """Basispfad eines EGON."""
    return Path(EGON_DATA_DIR) / egon_id


def _checkpoint_base():
    """Basis-Verzeichnis fuer alle Checkpoints."""
    return Path(EGON_DATA_DIR) / '_checkpoints'


def _checkpoint_dir(egon_id, typ):
    """Verzeichnis fuer Checkpoints eines bestimmten Typs."""
    return _checkpoint_base() / egon_id / typ


# ================================================================
# Checkpoint erstellen
# ================================================================

def erstelle_checkpoint(egon_id, typ, zusaetzliche_daten=None):
    """Erstelle einen Checkpoint fuer einen EGON.

    Sammelt alle relevanten Dateien in ein tar.gz Archiv.

    Args:
        egon_id: ID des EGON (z.B. 'adam_001').
        typ: Checkpoint-Typ ('pre_pulse', 'pre_cycle', 'pre_genesis', 'auto_6h').
        zusaetzliche_daten: Dict mit extra Dateien {name: inhalt_als_string}.

    Returns:
        Path zum erstellten Checkpoint-Archiv, oder None bei Fehler.
    """
    agent_dir = _egon_path(egon_id)
    if not agent_dir.is_dir():
        print(f'[checkpoint] WARNUNG: Agent-Dir {agent_dir} existiert nicht')
        return None

    cp_dir = _checkpoint_dir(egon_id, typ)
    cp_dir.mkdir(parents=True, exist_ok=True)

    # Timestamp fuer Dateinamen
    ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    archiv_pfad = cp_dir / f'{ts}.tar.gz'

    # Dateien sammeln
    dateien = CHECKPOINT_SCOPES.get(typ, ['core/state.yaml'])
    dateien_gefunden = 0

    try:
        with tarfile.open(str(archiv_pfad), 'w:gz') as tar:
            for datei in dateien:
                voll_pfad = agent_dir / datei
                if voll_pfad.is_file():
                    tar.add(str(voll_pfad), arcname=datei)
                    dateien_gefunden += 1

            # Zusaetzliche Daten (z.B. Blueprint bei Genesis)
            if zusaetzliche_daten:
                for name, inhalt in zusaetzliche_daten.items():
                    info = tarfile.TarInfo(name=name)
                    data = inhalt.encode('utf-8') if isinstance(inhalt, str) else inhalt
                    info.size = len(data)
                    info.mtime = time.time()
                    tar.addfile(info, io.BytesIO(data))

            # Metadaten
            meta = {
                'egon_id': egon_id,
                'typ': typ,
                'timestamp': ts,
                'dateien': dateien,
                'dateien_gefunden': dateien_gefunden,
                'erstellt': datetime.now().isoformat(),
            }
            meta_bytes = yaml.dump(
                meta, allow_unicode=True, default_flow_style=False
            ).encode('utf-8')
            info = tarfile.TarInfo(name='_checkpoint_meta.yaml')
            info.size = len(meta_bytes)
            info.mtime = time.time()
            tar.addfile(info, io.BytesIO(meta_bytes))

    except Exception as e:
        print(f'[checkpoint] FEHLER beim Erstellen: {e}')
        # Kaputtes Archiv aufraumen
        if archiv_pfad.exists():
            archiv_pfad.unlink()
        return None

    # Rotation: Aelteste entfernen
    _rotiere_checkpoints(cp_dir)

    # Retention-Policy anwenden
    _retention_cleanup(egon_id, typ)

    print(
        f'[checkpoint] {egon_id}/{typ}: {dateien_gefunden}/{len(dateien)} '
        f'Dateien gesichert → {archiv_pfad.name}'
    )
    return archiv_pfad


# ================================================================
# Rollback
# ================================================================

def rollback(egon_id, typ=None, timestamp=None):
    """Stelle einen frueheren Zustand wieder her.

    Sucht das passende Checkpoint-Archiv und entpackt es
    zurueck in das Agent-Verzeichnis.

    Args:
        egon_id: ID des EGON.
        typ: Checkpoint-Typ (optional, nimmt neuesten wenn None).
        timestamp: Spezifischer Timestamp (optional).

    Returns:
        True wenn erfolgreich, False wenn kein Checkpoint vorhanden.
    """
    agent_dir = _egon_path(egon_id)

    # Finde passendes Checkpoint-Archiv
    archiv = _finde_checkpoint(egon_id, typ, timestamp)

    if archiv is None:
        print(f'[checkpoint] ROLLBACK: Kein Checkpoint fuer {egon_id}/{typ}')
        return False

    # Backup des AKTUELLEN States (fuer den Fall dass Rollback falsch war)
    notfall_backup = erstelle_checkpoint(egon_id, 'pre_rollback')

    # Entpacken und ueberschreiben
    try:
        with tarfile.open(str(archiv), 'r:gz') as tar:
            for member in tar.getmembers():
                if member.name.startswith('_'):
                    continue  # Metadaten ueberspringen

                # Sicherheitscheck: Kein Path-Traversal
                if '..' in member.name or member.name.startswith('/'):
                    print(f'[checkpoint] WARNUNG: Ueberspringe verdaechtigen Pfad: {member.name}')
                    continue

                # Zielverzeichnis erstellen falls noetig
                ziel = agent_dir / member.name
                ziel.parent.mkdir(parents=True, exist_ok=True)

                # Datei extrahieren
                src = tar.extractfile(member)
                if src:
                    ziel.write_bytes(src.read())

    except Exception as e:
        print(f'[checkpoint] ROLLBACK FEHLER: {e}')
        return False

    print(f'[checkpoint] ROLLBACK: {egon_id} wiederhergestellt von {archiv.name}')

    # Log-Event (wenn transaction.py noch nicht da ist, direkt loggen)
    try:
        from engine.ledger import log_transaction
        log_transaction(egon_id, 'STATE_ROLLBACK', {
            'von': archiv.name,
            'typ': typ or 'auto',
            'backup': str(notfall_backup) if notfall_backup else None,
        })
    except Exception:
        pass

    return True


def kaskaden_rollback(egon_id):
    """Versuche Rollback mit Kaskade: neuester → aelterer → Notfall.

    Notfall-Hierarchie:
      1. Neuester Checkpoint (egal welcher Typ)
      2. Aelterer Checkpoint
      3. Notfall-Reset (DNA-Baseline, Gedaechtnisverlust)

    Returns:
        True wenn irgendein Rollback funktioniert hat.
    """
    # Versuch 1: Neuester Checkpoint
    archiv = _finde_checkpoint(egon_id)
    if archiv:
        erfolg = rollback(egon_id)
        if erfolg:
            # Validieren nach Rollback
            try:
                from engine.state_validator import lade_und_validiere
                from engine.organ_reader import read_yaml_organ
                state = read_yaml_organ(egon_id, 'core', 'state.yaml')
                lade_und_validiere(state, egon_id)
                return True
            except Exception:
                print(f'[checkpoint] Rollback-State ist auch kaputt, versuche aelteren...')

    # Versuch 2: Alle Checkpoints durchgehen (aelteste zuerst)
    alle = _liste_alle_checkpoints(egon_id)
    for cp_pfad in reversed(alle):  # Aelteste zuerst probieren
        try:
            agent_dir = _egon_path(egon_id)
            with tarfile.open(str(cp_pfad), 'r:gz') as tar:
                for member in tar.getmembers():
                    if member.name.startswith('_') or '..' in member.name:
                        continue
                    ziel = agent_dir / member.name
                    ziel.parent.mkdir(parents=True, exist_ok=True)
                    src = tar.extractfile(member)
                    if src:
                        ziel.write_bytes(src.read())

            # Validieren
            from engine.state_validator import lade_und_validiere
            from engine.organ_reader import read_yaml_organ
            state = read_yaml_organ(egon_id, 'core', 'state.yaml')
            lade_und_validiere(state, egon_id)
            print(f'[checkpoint] Kaskaden-Rollback erfolgreich: {cp_pfad.name}')
            return True
        except Exception:
            continue

    # Versuch 3: Notfall-Reset
    print(f'[checkpoint] KEIN Checkpoint brauchbar — starte Notfall-Reset')
    return _notfall_reset(egon_id)


# ================================================================
# Notfall-Reset
# ================================================================

def _notfall_reset(egon_id):
    """Letzter Ausweg: Setze den EGON auf DNA-Baseline zurueck.

    VERLIERT: Alle Erinnerungen, Beziehungen, Identitaet.
    BEHAELT: DNA-Profil, Name, Generation, Eltern-Info.

    Das ist das Aequivalent von: Der EGON wacht aus einem
    Koma auf und erinnert sich an nichts.

    Returns:
        True wenn Reset moeglich, False wenn auch DNA fehlt.
    """
    from engine.state_validator import DNA_DEFAULTS

    agent_dir = _egon_path(egon_id)
    if not agent_dir.is_dir():
        print(f'[checkpoint] FATAL: Agent-Dir {agent_dir} existiert nicht')
        return False

    # Versuche DNA-Profil aus kern/seele.md (v3) oder core/dna.md (v2) zu extrahieren
    dna_md = agent_dir / 'kern' / 'seele.md'
    if not dna_md.is_file():
        dna_md = agent_dir / 'core' / 'dna.md'
    profil = 'DEFAULT'
    try:
        from engine.naming import get_display_name
        name = get_display_name(egon_id, 'vorname')
    except Exception:
        name = egon_id.split('_')[0].title()

    if dna_md.is_file():
        text = dna_md.read_text(encoding='utf-8')
        if 'SEEKING/PLAY' in text:
            profil = 'SEEKING/PLAY'
        elif 'CARE/PANIC' in text:
            profil = 'CARE/PANIC'
        elif 'RAGE/FEAR' in text:
            profil = 'RAGE/FEAR'

    defaults = DNA_DEFAULTS.get(profil, DNA_DEFAULTS['DEFAULT'])

    # Minimal-State mit DNA-Baseline
    reset_state = {
        'dna_profile': profil,
        'geschlecht': 'M',  # Fallback, wird unten korrigiert wenn moeglich
        'drives': dict(defaults),
        'survive': {
            'energy':    {'value': 0.50, 'verbal': 'neutral'},
            'safety':    {'value': 0.50, 'verbal': 'unsicher'},
            'coherence': {'value': 0.30, 'verbal': 'fragmentiert'},
        },
        'thrive': {
            'belonging':   {'value': 0.30, 'verbal': 'verloren'},
            'trust_owner': {'value': 0.50, 'verbal': 'neutral'},
            'mood':        {'value': 0.30, 'verbal': 'desorientiert'},
            'purpose':     {'value': 0.20, 'verbal': 'suchend'},
        },
        'express': {
            'active_emotions': [{
                'type': 'confusion',
                'intensity': 0.70,
                'cause': 'Ich bin aufgewacht und erinnere mich an nichts.',
                'onset': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                'decay_class': 'slow',
                'verbal_anchor': 'Wo bin ich? Wer bin ich?',
            }],
        },
        'self_assessment': {
            'verbal': 'Ich weiss nicht wer ich bin. Alles ist leer.',
            'last_updated': datetime.now().strftime('%Y-%m-%d'),
        },
        'emotional_gravity': {
            'baseline_mood': 0.30,
            'interpretation_bias': 'cautious',
        },
        'processing': {
            'speed': 'normal',
            'emotional_load': 0.60,
        },
        'notfall_reset': True,
        'reset_timestamp': datetime.now().isoformat(),
    }

    # Versuche Geschlecht und Identitaet aus existierendem State zu retten
    try:
        import yaml as _yaml
        # v3 zuerst, dann v2
        old_state_path = agent_dir / 'innenwelt' / 'innenwelt.yaml'
        if not old_state_path.is_file():
            old_state_path = agent_dir / 'core' / 'state.yaml'
        if old_state_path.is_file():
            old = _yaml.safe_load(old_state_path.read_text(encoding='utf-8'))
            if isinstance(old, dict):
                if 'geschlecht' in old:
                    reset_state['geschlecht'] = old['geschlecht']
                if 'identitaet' in old:
                    reset_state['identitaet'] = old['identitaet']
                if 'pairing' in old:
                    # Behalte Eltern-Info aber loesche aktives Pairing
                    pairing = old['pairing']
                    reset_state['pairing'] = {
                        'reif': False,
                        'resonanz_partner': None,
                        'resonanz_score': 0.0,
                        'pairing_phase': 'keine',
                        'inkubation': None,
                        'eltern': pairing.get('eltern'),
                        'kinder': pairing.get('kinder', []),
                    }
    except Exception:
        pass

    # State schreiben — v3-Pfad wenn migriert, sonst v2
    import yaml as _yaml
    is_v3 = (agent_dir / 'kern').is_dir()
    if is_v3:
        state_path = agent_dir / 'innenwelt' / 'innenwelt.yaml'
    else:
        state_path = agent_dir / 'core' / 'state.yaml'
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, 'w', encoding='utf-8') as f:
        _yaml.dump(reset_state, f, allow_unicode=True, default_flow_style=False,
                    sort_keys=False, width=120)

    # Ego.md / ich.md zuruecksetzen
    if is_v3:
        ego_path = agent_dir / 'kern' / 'ich.md'
    else:
        ego_path = agent_dir / 'core' / 'ego.md'
    ego_path.parent.mkdir(parents=True, exist_ok=True)
    ego_path.write_text(
        f'# Wer bin ich?\n\n'
        f'Ich bin {name}. Ich habe alles vergessen. '
        f'Ich muss neu anfangen.\n',
        encoding='utf-8',
    )

    # Inner Voice zuruecksetzen
    if is_v3:
        iv_path = agent_dir / 'innere_stimme' / 'gedanken.yaml'
    else:
        iv_path = agent_dir / 'memory' / 'inner_voice.md'
    iv_path.parent.mkdir(parents=True, exist_ok=True)
    iv_path.write_text(
        '## Neustart\n'
        'Stille. Dann: Ein Gefuehl des Verlusts, '
        'ohne zu wissen was verloren ging.\n',
        encoding='utf-8',
    )

    # Recent Memory leeren
    if is_v3:
        rm_path = agent_dir / 'erinnerungen' / 'kurzzeitgedaechtnis.md'
    else:
        rm_path = agent_dir / 'memory' / 'recent_memory.md'
    rm_path.parent.mkdir(parents=True, exist_ok=True)
    rm_path.write_text('', encoding='utf-8')

    # Dreams leeren
    if is_v3:
        dr_path = agent_dir / 'erinnerungen' / 'traeume.yaml'
    else:
        dr_path = agent_dir / 'memory' / 'dreams.md'
    dr_path.parent.mkdir(parents=True, exist_ok=True)
    dr_path.write_text('', encoding='utf-8')

    print(
        f'[checkpoint] NOTFALL-RESET: {egon_id} auf DNA-Baseline zurueckgesetzt. '
        f'Profil: {profil}. Erinnerungen verloren.'
    )

    try:
        from engine.ledger import log_transaction
        log_transaction(egon_id, 'NOTFALL_RESET', {
            'grund': 'State nicht wiederherstellbar — kein brauchbarer Checkpoint',
            'dna_erhalten': True,
            'erinnerungen_verloren': True,
            'profil': profil,
        })
    except Exception:
        pass

    return True


# ================================================================
# Interne Hilfsfunktionen
# ================================================================

def _rotiere_checkpoints(cp_dir):
    """Behalte nur die neuesten MAX_CHECKPOINTS_PRO_TYP."""
    archive = sorted(cp_dir.glob('*.tar.gz'))
    while len(archive) > MAX_CHECKPOINTS_PRO_TYP:
        archive[0].unlink()
        archive.pop(0)


def _retention_cleanup(egon_id, typ):
    """Loesche Checkpoints die aelter als die Retention-Policy sind."""
    tage = RETENTION_TAGE.get(typ, 0)
    if tage == 0:
        return  # Nie loeschen

    cp_dir = _checkpoint_dir(egon_id, typ)
    if not cp_dir.is_dir():
        return

    grenze = datetime.now() - timedelta(days=tage)

    for archiv in cp_dir.glob('*.tar.gz'):
        if archiv.stat().st_mtime < grenze.timestamp():
            archiv.unlink()


def _finde_checkpoint(egon_id, typ=None, timestamp=None):
    """Finde das passende Checkpoint-Archiv.

    Args:
        egon_id: ID des EGON.
        typ: Checkpoint-Typ (optional).
        timestamp: Spezifischer Timestamp im Format 'YYYY-MM-DD_HH-MM-SS'.

    Returns:
        Path zum Archiv oder None.
    """
    basis = _checkpoint_base() / egon_id

    if not basis.is_dir():
        return None

    if typ and timestamp:
        archiv = basis / typ / f'{timestamp}.tar.gz'
        return archiv if archiv.exists() else None

    if typ:
        typ_dir = basis / typ
        if not typ_dir.is_dir():
            return None
        archive = sorted(typ_dir.glob('*.tar.gz'))
        return archive[-1] if archive else None

    # Kein Typ: Suche das NEUESTE ueber alle Typen
    neuestes = None
    neueste_zeit = 0

    for typ_dir in basis.iterdir():
        if not typ_dir.is_dir():
            continue
        for archiv in typ_dir.glob('*.tar.gz'):
            mtime = archiv.stat().st_mtime
            if mtime > neueste_zeit:
                neueste_zeit = mtime
                neuestes = archiv

    return neuestes


def _liste_alle_checkpoints(egon_id):
    """Liste ALLE Checkpoints eines EGON, sortiert nach Erstellzeit.

    Returns:
        Liste von Paths (neueste zuerst).
    """
    basis = _checkpoint_base() / egon_id
    if not basis.is_dir():
        return []

    alle = []
    for typ_dir in basis.iterdir():
        if not typ_dir.is_dir():
            continue
        alle.extend(typ_dir.glob('*.tar.gz'))

    return sorted(alle, key=lambda p: p.stat().st_mtime, reverse=True)


def liste_checkpoints(egon_id, typ=None):
    """Oeffentliche API: Liste Checkpoints fuer Audit/Monitoring.

    Args:
        egon_id: ID des EGON.
        typ: Optional — nur bestimmter Typ.

    Returns:
        Liste von Dicts mit {pfad, typ, timestamp, groesse_kb}.
    """
    ergebnis = []

    basis = _checkpoint_base() / egon_id
    if not basis.is_dir():
        return ergebnis

    typen = [typ] if typ else [d.name for d in basis.iterdir() if d.is_dir()]

    for t in typen:
        t_dir = basis / t
        if not t_dir.is_dir():
            continue
        for archiv in sorted(t_dir.glob('*.tar.gz')):
            ergebnis.append({
                'pfad': str(archiv),
                'typ': t,
                'timestamp': archiv.stem,  # z.B. '2026-02-26_08-00-00'
                'groesse_kb': round(archiv.stat().st_size / 1024, 1),
            })

    return ergebnis
