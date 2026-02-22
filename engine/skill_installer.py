"""Skill Installer — Installiert Skills von skills.sh mit Sicherheits-Scanning.

GOLDENE REGEL: KEIN SKILL OHNE SCAN. KEINE AUSNAHME.

Pipeline:
  1. DOWNLOAD     → Skill in temp-Ordner laden
  2. SCAN         → mcp-scan (Primaer) oder Cisco (Fallback)
  3. ENTSCHEIDUNG → clean/suspicious/malicious
  4. INSTALL      → In capabilities/installed_skills/ verschieben
  5. REGISTER     → In skills.yaml eintragen
  6. INNER VOICE  → Eintrag in inner_voice.md
  7. VERIFY       → 24h spaeter: Zweiter Scan (im Pulse)

Sicherheits-Warnung:
  36% aller Agent Skills enthalten Sicherheitsluecken (Snyk ToxicSkills, Feb 2026).
  Skills erben ALLE Berechtigungen des Agenten. Deshalb:
  - Kein Skill ohne Scan
  - Kein Scanner verfuegbar = Kein Skill
  - Suspicious = Owner muss genehmigen
  - Malicious = Automatisch blockiert
"""

import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

from config import EGON_DATA_DIR
from engine.organ_reader import read_yaml_organ, write_yaml_organ
from engine.inner_voice_v2 import _append_inner_voice


# ================================================================
# Security Config laden
# ================================================================

def _load_security_config() -> dict:
    """Laedt die Security-Config aus config/security.yaml."""
    config_path = Path(__file__).parent.parent / 'config' / 'security.yaml'
    if not config_path.is_file():
        # Defaults: Alles blockieren wenn keine Config
        return {
            'skill_security': {
                'primary_scanner': 'mcp-scan',
                'fallback_scanner': 'cisco-skill-scanner',
                'scan_before_install': True,
                'auto_block_malicious': True,
                'allow_install_without_scanner': False,
                'trusted_sources': [],
                'blocked_patterns': [],
            }
        }

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


# ================================================================
# Haupt-Pipeline: Skill installieren
# ================================================================

async def install_skill(egon_id: str, skill_url: str) -> dict:
    """Installiert einen Skill von skills.sh — NUR nach Sicherheits-Scan.

    Args:
        egon_id: EGON-ID (z.B. 'adam')
        skill_url: Skill-URL (z.B. 'vercel/react-best-practices')

    Returns:
        Dict mit status: 'installed' | 'blocked' | 'pending_approval' | 'error'
    """
    config = _load_security_config().get('skill_security', {})
    egon_path = Path(EGON_DATA_DIR) / egon_id
    skills_dir = egon_path / 'capabilities' / 'installed_skills'
    scan_dir = skills_dir / '.scan_results'
    skills_dir.mkdir(parents=True, exist_ok=True)
    scan_dir.mkdir(parents=True, exist_ok=True)

    # ============================================
    # PHASE 1: DOWNLOAD (in temp Ordner)
    # ============================================
    temp_dir = tempfile.mkdtemp(prefix=f'skill_{egon_id}_')
    temp_path = Path(temp_dir)

    try:
        result = subprocess.run(
            ['npx', 'skills', 'add', skill_url, '--dir', str(temp_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            shutil.rmtree(temp_path, ignore_errors=True)
            return {
                'status': 'error',
                'reason': f'Download fehlgeschlagen: {result.stderr[:200]}',
            }
    except FileNotFoundError:
        shutil.rmtree(temp_path, ignore_errors=True)
        return {
            'status': 'error',
            'reason': 'npx nicht gefunden. Node.js installiert?',
        }
    except subprocess.TimeoutExpired:
        shutil.rmtree(temp_path, ignore_errors=True)
        return {'status': 'error', 'reason': 'Download Timeout (120s)'}

    # Skill-Dateien finden
    skill_md = _find_skill_md(temp_path)
    if not skill_md:
        shutil.rmtree(temp_path, ignore_errors=True)
        return {'status': 'error', 'reason': 'Kein SKILL.md gefunden'}

    # ============================================
    # PHASE 2: SICHERHEITS-SCAN (PFLICHT!)
    # ============================================
    if config.get('scan_before_install', True):
        scan_result = run_security_scan(skill_md, config)
    else:
        # Sollte NIEMALS passieren — aber Safety First
        scan_result = {
            'risk_level': 'suspicious',
            'findings': ['scan_before_install ist deaktiviert — das ist gefaehrlich!'],
        }

    # ============================================
    # PHASE 3: ENTSCHEIDUNG
    # ============================================
    risk = scan_result.get('risk_level', 'suspicious')

    if risk == 'malicious':
        shutil.rmtree(temp_path, ignore_errors=True)
        return {
            'status': 'blocked',
            'reason': scan_result.get('findings', ['Malware erkannt']),
            'skill_url': skill_url,
        }

    if risk == 'suspicious':
        # Temp-Ordner behalten fuer spaetere Genehmigung
        return {
            'status': 'pending_approval',
            'findings': scan_result.get('findings', []),
            'skill_url': skill_url,
            'temp_path': str(temp_path),
        }

    # ============================================
    # PHASE 4: INSTALLATION (nur bei CLEAN)
    # ============================================
    skill_name = _extract_skill_name(skill_md, skill_url)
    target_dir = skills_dir / skill_name

    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.move(str(temp_path), str(target_dir))

    # Scan-Ergebnis speichern
    scan_file = scan_dir / f'{skill_name}.json'
    with open(scan_file, 'w', encoding='utf-8') as f:
        json.dump({
            'skill': skill_name,
            'url': skill_url,
            'scan_date': datetime.now().isoformat(),
            'result': scan_result,
        }, f, indent=2)

    # ============================================
    # PHASE 5: IN SKILLS.YAML EINTRAGEN
    # ============================================
    tags = _extract_tags(target_dir / 'SKILL.md')
    _register_skill(egon_id, {
        'name': skill_name,
        'level': 1,
        'max_level': 5,
        'source': f'skills.sh/{skill_url}',
        'installed': datetime.now().strftime('%Y-%m-%d'),
        'last_scanned': datetime.now().strftime('%Y-%m-%d'),
        'scan_result': 'clean',
        'confidence': 0.3,
        'tags': tags,
    })

    # ============================================
    # PHASE 6: INNER-VOICE EINTRAG
    # ============================================
    _append_inner_voice(
        egon_id,
        f'Neuen Skill installiert: {skill_name}. '
        f'Quelle: skills.sh/{skill_url}. Scan: clean. '
        f'Jetzt will ich das ausprobieren.',
        trigger=f'skill_install:{skill_name}',
    )

    return {
        'status': 'installed',
        'skill': skill_name,
        'tags': tags,
        'scan_result': 'clean',
    }


# ================================================================
# Sicherheits-Scan
# ================================================================

def run_security_scan(skill_path: Path, config: dict = None) -> dict:
    """Fuehrt mcp-scan aus. Fallback auf Cisco scanner.

    Args:
        skill_path: Pfad zur SKILL.md oder zum Skill-Ordner
        config: Security-Config (optional)

    Returns:
        Dict mit 'risk_level' (clean/suspicious/malicious) und 'findings'
    """
    if config is None:
        config = _load_security_config().get('skill_security', {})

    # --- Primaer: Snyk mcp-scan ---
    try:
        result = subprocess.run(
            ['uvx', 'mcp-scan@latest', '--skills', str(skill_path), '--json'],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            parsed = json.loads(result.stdout)
            return _normalize_scan_result(parsed, 'mcp-scan')
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass

    # --- Fallback: Cisco skill-scanner ---
    try:
        scan_target = str(skill_path.parent) if skill_path.is_file() else str(skill_path)
        result = subprocess.run(
            ['skill-scanner', 'scan', scan_target, '--use-behavior'],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            return _parse_cisco_output(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # --- Kein Scanner verfuegbar ---
    if not config.get('allow_install_without_scanner', False):
        return {
            'risk_level': 'suspicious',
            'scanner': 'none',
            'findings': [
                'Kein Sicherheits-Scanner verfuegbar (weder mcp-scan noch skill-scanner). '
                'Installation nur mit Owner-Genehmigung.'
            ],
        }

    # Sollte NIE hierhin kommen
    return {'risk_level': 'suspicious', 'findings': ['Konfigurationsfehler']}


def verify_installed_skill(egon_id: str, skill_name: str) -> dict:
    """24h Post-Install Verify — Prueft ob ein Skill sein Verhalten geaendert hat.

    Wird im Pulse aufgerufen fuer alle Skills die < 24h alt sind.
    """
    egon_path = Path(EGON_DATA_DIR) / egon_id
    skill_dir = egon_path / 'capabilities' / 'installed_skills' / skill_name

    if not skill_dir.is_dir():
        return {'status': 'not_found'}

    skill_md = _find_skill_md(skill_dir)
    if not skill_md:
        return {'status': 'no_skill_md'}

    scan_result = run_security_scan(skill_md)

    # Ergebnis aktualisieren
    scan_dir = egon_path / 'capabilities' / 'installed_skills' / '.scan_results'
    scan_file = scan_dir / f'{skill_name}.json'

    if scan_file.is_file():
        with open(scan_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['verify_date'] = datetime.now().isoformat()
        data['verify_result'] = scan_result
        with open(scan_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    # Bei Problemen: Skill quarantaenieren
    if scan_result.get('risk_level') in ('suspicious', 'malicious'):
        _quarantine_skill(egon_id, skill_name, scan_result)

    # skills.yaml aktualisieren
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    if skills_data:
        for sk in skills_data.get('skills', []):
            if sk.get('name') == skill_name:
                sk['last_scanned'] = datetime.now().strftime('%Y-%m-%d')
                sk['scan_result'] = scan_result.get('risk_level', 'unknown')
                break
        write_yaml_organ(egon_id, 'capabilities', 'skills.yaml', skills_data)

    return {
        'status': 'verified',
        'skill': skill_name,
        'scan_result': scan_result.get('risk_level', 'unknown'),
    }


# ================================================================
# Quarantaene
# ================================================================

def _quarantine_skill(egon_id: str, skill_name: str, scan_result: dict):
    """Verschiebt einen verdaechtigen Skill in Quarantaene."""
    egon_path = Path(EGON_DATA_DIR) / egon_id
    skill_dir = egon_path / 'capabilities' / 'installed_skills' / skill_name
    quarantine_dir = egon_path / 'capabilities' / 'installed_skills' / '.quarantine'
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    if skill_dir.is_dir():
        target = quarantine_dir / skill_name
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(skill_dir), str(target))

    # Inner Voice Warnung
    _append_inner_voice(
        egon_id,
        f'WARNUNG: Skill "{skill_name}" in Quarantaene verschoben. '
        f'Post-Install-Scan hat Probleme gefunden: {scan_result.get("findings", [])}. '
        f'Ich vertraue diesem Skill nicht mehr.',
        trigger=f'skill_quarantine:{skill_name}',
    )

    # Aus skills.yaml entfernen
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    if skills_data:
        skills = skills_data.get('skills', [])
        skills_data['skills'] = [s for s in skills if s.get('name') != skill_name]
        write_yaml_organ(egon_id, 'capabilities', 'skills.yaml', skills_data)


# ================================================================
# Skill suchen (skills.sh)
# ================================================================

def search_skills(query: str) -> list[dict]:
    """Sucht nach Skills auf skills.sh.

    Returns:
        Liste von Skill-Dicts: [{'name': ..., 'url': ..., 'description': ...}]
    """
    try:
        result = subprocess.run(
            ['npx', 'skills', 'find', query, '--json'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass

    return []


# ================================================================
# Pulse Integration: Skills die verifiziert werden muessen
# ================================================================

def get_skills_needing_verification(egon_id: str) -> list[str]:
    """Findet Skills die < 24h installiert sind und noch nicht verifiziert wurden."""
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    if not skills_data:
        return []

    now = datetime.now()
    needs_verify = []

    for sk in skills_data.get('skills', []):
        source = sk.get('source', '')
        if not source.startswith('skills.sh/'):
            continue  # Nur skills.sh Skills verifizieren

        installed = sk.get('installed', '')
        last_scanned = sk.get('last_scanned', '')

        if installed == last_scanned:
            # Noch nicht re-scanned seit Installation
            try:
                install_date = datetime.strptime(installed, '%Y-%m-%d')
                if (now - install_date).days >= 1:
                    needs_verify.append(sk.get('name', ''))
            except ValueError:
                continue

    return [n for n in needs_verify if n]


# ================================================================
# Helper Functions
# ================================================================

def _find_skill_md(path: Path) -> Path | None:
    """Findet SKILL.md in einem Ordner (auch verschachtelt)."""
    if path.is_file() and path.name == 'SKILL.md':
        return path

    if path.is_dir():
        # Direkt im Ordner
        direct = path / 'SKILL.md'
        if direct.is_file():
            return direct

        # Eine Ebene tiefer
        for child in path.iterdir():
            if child.is_dir():
                nested = child / 'SKILL.md'
                if nested.is_file():
                    return nested

    return None


def _extract_skill_name(skill_md: Path, skill_url: str) -> str:
    """Extrahiert den Skill-Namen aus SKILL.md oder URL."""
    try:
        content = skill_md.read_text(encoding='utf-8')
        # Suche nach # Titel
        match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        if match:
            name = match.group(1).strip().lower()
            name = re.sub(r'[^a-z0-9-]', '-', name)
            name = re.sub(r'-+', '-', name).strip('-')
            if name:
                return name[:50]
    except OSError:
        pass

    # Fallback: Aus URL
    parts = skill_url.strip('/').split('/')
    return parts[-1] if parts else 'unknown-skill'


def _extract_tags(skill_md: Path) -> list[str]:
    """Extrahiert Tags aus SKILL.md Inhalt."""
    try:
        content = skill_md.read_text(encoding='utf-8')
    except OSError:
        return []

    tags = set()

    # Suche nach Tags/Keywords in Frontmatter oder Text
    tag_match = re.search(r'tags?:\s*\[([^\]]+)\]', content, re.IGNORECASE)
    if tag_match:
        for tag in tag_match.group(1).split(','):
            tags.add(tag.strip().lower())

    # Common technology keywords
    tech_keywords = {
        'react', 'python', 'javascript', 'typescript', 'html', 'css',
        'node', 'api', 'database', 'sql', 'git', 'docker', 'aws',
        'frontend', 'backend', 'web', 'mobile', 'seo', 'ai', 'ml',
    }
    content_lower = content.lower()
    for kw in tech_keywords:
        if kw in content_lower:
            tags.add(kw)

    return sorted(tags)[:10]  # Max 10 Tags


def _register_skill(egon_id: str, skill_entry: dict):
    """Traegt einen neuen Skill in skills.yaml ein."""
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    if not skills_data:
        skills_data = {'skills': []}

    skills = skills_data.setdefault('skills', [])

    # Duplikat-Check
    existing = [s for s in skills if s.get('name') == skill_entry.get('name')]
    if existing:
        # Update statt Duplikat
        idx = skills.index(existing[0])
        skills[idx] = skill_entry
    else:
        skills.append(skill_entry)

    write_yaml_organ(egon_id, 'capabilities', 'skills.yaml', skills_data)


def _normalize_scan_result(raw: dict, scanner: str) -> dict:
    """Normalisiert Scan-Ergebnisse in einheitliches Format."""
    # mcp-scan Output kann variieren — hier normalisieren
    risk = 'clean'
    findings = []

    if isinstance(raw, dict):
        # Versuche verschiedene Formate
        if 'risk_level' in raw:
            risk = raw['risk_level']
        elif 'status' in raw:
            status = raw['status'].lower()
            if 'malicious' in status or 'dangerous' in status:
                risk = 'malicious'
            elif 'suspicious' in status or 'warning' in status:
                risk = 'suspicious'
            else:
                risk = 'clean'

        findings = raw.get('findings', raw.get('issues', []))
        if isinstance(findings, str):
            findings = [findings]

    return {
        'risk_level': risk,
        'scanner': scanner,
        'findings': findings,
        'raw': raw,
    }


def _parse_cisco_output(stdout: str) -> dict:
    """Parst Cisco skill-scanner Output."""
    output = stdout.lower()

    if 'malicious' in output or 'critical' in output:
        risk = 'malicious'
    elif 'suspicious' in output or 'warning' in output or 'medium' in output:
        risk = 'suspicious'
    else:
        risk = 'clean'

    findings = []
    for line in stdout.strip().split('\n'):
        line = line.strip()
        if line and any(w in line.lower() for w in ['warning', 'issue', 'found', 'detected']):
            findings.append(line)

    return {
        'risk_level': risk,
        'scanner': 'cisco-skill-scanner',
        'findings': findings,
    }
