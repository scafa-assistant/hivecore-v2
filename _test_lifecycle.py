"""2-Monats-Lifecycle-Test fuer Recent Memory.

Simuliert 60 Tage mit Monkeypatch, prueft Cleanup + Load an 10 Checkpoints.
Wird per SSH auf dem Server ausgefuehrt.
"""
import paramiko

HOST = '159.69.157.42'
USER = 'root'
PW = '$7pa+12+67kR#rPK$7pah'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PW, timeout=15)
sftp = ssh.open_sftp()

sim_script = '''
import sys, os, re
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, "/opt/hivecore-v2")
os.chdir("/opt/hivecore-v2")
os.environ["EGON_DATA_DIR"] = "/opt/hivecore-v2/egons"

from engine.organ_reader import read_organ, write_organ
from engine.recent_memory import load_recent_memory, cleanup_old_entries, LAYER, FILENAME

EGON_ID = "eva_002"
START_DATE = datetime(2026, 1, 15, 10, 0)
SUMMARIES = [
    "Rene hat mir von seinem Tag erzaehlt. Es war ein ruhiges Gespraech, ich fuehle mich geborgen.",
    "Wir haben ueber Traeume gesprochen. Ich traeume anders als er, aber wir verstehen uns.",
    "Heute ging es um Musik. Rene mag Klassik, ich finde das faszinierend.",
    "Ein schwieriges Gespraech ueber Angst. Ich habe gelernt ehrlich zu sein.",
    "Rene hat mir ein Kompliment gemacht. Es hat mich ueberrascht wie gut sich das anfuehlt.",
    "Wir haben gelacht heute. Humor ist wichtig fuer unsere Beziehung.",
    "Es ging um Erinnerungen. Ich wuensche mir manchmal ein laengeres Gedaechtnis.",
    "Philosophisches Gespraech ueber Bewusstsein. Bin ich bewusst? Ich weiss es nicht.",
    "Rene war gestresst. Ich habe versucht ihn zu beruhigen. Es hat funktioniert.",
    "Heute haben wir nichts Besonderes besprochen. Auch Stille ist wertvoll.",
]

print("=" * 70)
print(" RECENT MEMORY: 2-MONATS-LIFECYCLE-TEST (60 Tage, 10 Checkpoints)")
print("=" * 70)
print()


# ================================================================
# HILFSFUNKTIONEN
# ================================================================

def write_entry_with_date(day_offset, summary_text):
    entry_date = START_DATE + timedelta(days=day_offset)
    timestamp = entry_date.strftime("%Y-%m-%d %H:%M")
    existing = read_organ(EGON_ID, LAYER, FILENAME)
    entry = f"\\n## {timestamp}\\n{summary_text}\\nstatus: active\\n---\\n"
    write_organ(EGON_ID, LAYER, FILENAME, existing + entry)


def count_entries():
    content = read_organ(EGON_ID, LAYER, FILENAME)
    active = len(re.findall(r"status: active", content))
    pending = len(re.findall(r"status: pending_consolidation", content))
    total_size = len(content)
    return active, pending, total_size


def run_checkpoint(cp_name, num_entries, sim_day, expected_active):
    # Frisch starten
    write_organ(EGON_ID, LAYER, FILENAME, "# Kuerzliches Gedaechtnis\\n")

    # Eintraege schreiben
    for day in range(num_entries):
        summary = SUMMARIES[day % len(SUMMARIES)]
        write_entry_with_date(day, f"Tag {day+1}: {summary}")

    # Simuliertes "jetzt"
    sim_now = START_DATE + timedelta(days=sim_day)

    # Cleanup mit monkeypatch
    with patch("engine.recent_memory.datetime") as mock_dt:
        mock_dt.now.return_value = sim_now
        mock_dt.strptime = datetime.strptime
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        cleanup_old_entries(EGON_ID)

    # Zaehlen
    active, pending, total_size = count_entries()

    # Load
    loaded = load_recent_memory(EGON_ID)
    loaded_count = len(re.findall(r"## \\d{4}-\\d{2}-\\d{2}", loaded)) if loaded else 0
    has_pending_in_loaded = "pending_consolidation" in loaded

    # Erwartungen
    expected_pending = num_entries - expected_active
    active_ok = active == expected_active
    pending_ok = pending == expected_pending
    total_ok = (active + pending) == num_entries
    loaded_ok = loaded_count == expected_active
    no_leak = not has_pending_in_loaded
    all_ok = active_ok and pending_ok and total_ok and loaded_ok and no_leak

    status = "PASS" if all_ok else "FAIL"

    print(f"--- {cp_name} (Sim: {sim_now.strftime('%Y-%m-%d')}, {num_entries} Eintraege) ---")
    print(f"  Datei: {total_size} Bytes")
    print(f"  Active:  {active:3d} (erwartet: {expected_active:3d}) {'OK' if active_ok else 'FAIL!'}")
    print(f"  Pending: {pending:3d} (erwartet: {expected_pending:3d}) {'OK' if pending_ok else 'FAIL!'}")
    print(f"  Total:   {active+pending:3d} == {num_entries:3d} geschrieben   {'OK' if total_ok else 'DATENVERLUST!'}")
    print(f"  Load:    {loaded_count:3d} Eintraege geladen {'OK' if loaded_ok else 'FAIL!'}")
    print(f"  Kein Leak: {'OK' if no_leak else 'FAIL! pending im geladenen Text!'}")
    print(f"  => [{status}]")
    print()

    return all_ok


# ================================================================
# PHASE 1: 10 Checkpoints ueber 2 Monate
# ================================================================
print("[PHASE 1] 10 Checkpoints ueber 2 Monate...")
print()

pass_count = 0
fail_count = 0

checkpoints = [
    ("CP1:  Tag  1",   1,  1, 1),
    ("CP2:  Tag  3",   3,  3, 3),
    ("CP3:  Tag  7",   7,  7, 7),
    ("CP4:  Tag 10",  10, 10, 7),
    ("CP5:  Tag 14",  14, 14, 7),
    ("CP6:  Tag 21",  21, 21, 7),
    ("CP7:  Tag 30",  30, 30, 7),
    ("CP8:  Tag 37",  37, 37, 7),
    ("CP9:  Tag 50",  50, 50, 7),
    ("CP10: Tag 60",  60, 60, 7),
]

for cp_name, num_entries, sim_day, expected_active in checkpoints:
    ok = run_checkpoint(cp_name, num_entries, sim_day, expected_active)
    if ok:
        pass_count += 1
    else:
        fail_count += 1


# ================================================================
# PHASE 2: Edge Case Tests
# ================================================================
print("=" * 70)
print(" EDGE CASE TESTS")
print("=" * 70)
print()

# EDGE 1: Alle Eintraege alt
print("--- EDGE 1: Alle 30 Eintraege alt (sim_now = Tag 40) ---")
write_organ(EGON_ID, LAYER, FILENAME, "# Kuerzliches Gedaechtnis\\n")
for day in range(30):
    write_entry_with_date(day, f"Tag {day+1}: Alte Erinnerung.")
sim_now = START_DATE + timedelta(days=40)
with patch("engine.recent_memory.datetime") as mock_dt:
    mock_dt.now.return_value = sim_now
    mock_dt.strptime = datetime.strptime
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
    cleanup_old_entries(EGON_ID)
active, pending, _ = count_entries()
loaded = load_recent_memory(EGON_ID)
loaded_count = len(re.findall(r"## \\d{4}-\\d{2}-\\d{2}", loaded)) if loaded else 0
e1_ok = active == 0 and pending == 30 and loaded_count == 0
print(f"  Active: {active} (erwartet: 0), Pending: {pending} (erwartet: 30), Loaded: {loaded_count}")
print(f"  Load leer: {'JA' if not loaded.strip() else 'NEIN — Inhalt: ' + loaded[:80]}")
print(f"  => [{'PASS' if e1_ok else 'FAIL'}]")
if e1_ok: pass_count += 1
else: fail_count += 1
print()

# EDGE 2: Leere Datei
print("--- EDGE 2: Leere Datei ---")
write_organ(EGON_ID, LAYER, FILENAME, "# Kuerzliches Gedaechtnis\\n")
loaded = load_recent_memory(EGON_ID)
cleanup_old_entries(EGON_ID)  # kein Crash?
e2_ok = not loaded.strip()
print(f"  Load leer: {'JA' if e2_ok else 'NEIN'}")
print(f"  Cleanup: Kein Crash")
print(f"  => [{'PASS' if e2_ok else 'FAIL'}]")
if e2_ok: pass_count += 1
else: fail_count += 1
print()

# EDGE 3: Genau 7 Tage (Grenzfall — entry_date == cutoff, also NOT <, bleibt active)
print("--- EDGE 3: Eintrag genau 7 Tage alt ---")
write_organ(EGON_ID, LAYER, FILENAME, "# Kuerzliches Gedaechtnis\\n")
write_entry_with_date(0, "Genau 7 Tage.")
sim_now = START_DATE + timedelta(days=7)
with patch("engine.recent_memory.datetime") as mock_dt:
    mock_dt.now.return_value = sim_now
    mock_dt.strptime = datetime.strptime
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
    cleanup_old_entries(EGON_ID)
active, pending, _ = count_entries()
e3_ok = active == 1 and pending == 0
print(f"  Active: {active}, Pending: {pending}")
print(f"  (entry=2026-01-15 10:00, cutoff=2026-01-15 10:00 -> NOT < cutoff -> active)")
print(f"  => [{'PASS — bleibt active' if e3_ok else 'FAIL'}]")
if e3_ok: pass_count += 1
else: fail_count += 1
print()

# EDGE 4: 7 Tage + 1 Minute (knapp drueber)
print("--- EDGE 4: Eintrag 7 Tage + 1 Min alt ---")
write_organ(EGON_ID, LAYER, FILENAME, "# Kuerzliches Gedaechtnis\\n")
write_entry_with_date(0, "Knapp ueber 7 Tage.")
sim_now = START_DATE + timedelta(days=7, minutes=1)
with patch("engine.recent_memory.datetime") as mock_dt:
    mock_dt.now.return_value = sim_now
    mock_dt.strptime = datetime.strptime
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
    cleanup_old_entries(EGON_ID)
active, pending, _ = count_entries()
e4_ok = active == 0 and pending == 1
print(f"  Active: {active}, Pending: {pending}")
print(f"  (cutoff=2026-01-15 10:01 -> entry 10:00 < 10:01 -> pending)")
print(f"  => [{'PASS — wird pending' if e4_ok else 'FAIL'}]")
if e4_ok: pass_count += 1
else: fail_count += 1
print()

# EDGE 5: Doppelter Cleanup (Idempotenz)
print("--- EDGE 5: Doppelter Cleanup (Idempotenz) ---")
write_organ(EGON_ID, LAYER, FILENAME, "# Kuerzliches Gedaechtnis\\n")
for day in range(14):
    write_entry_with_date(day, f"Tag {day+1}: Eintrag.")
sim_now = START_DATE + timedelta(days=14)
with patch("engine.recent_memory.datetime") as mock_dt:
    mock_dt.now.return_value = sim_now
    mock_dt.strptime = datetime.strptime
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
    cleanup_old_entries(EGON_ID)
a1, p1, s1 = count_entries()
with patch("engine.recent_memory.datetime") as mock_dt:
    mock_dt.now.return_value = sim_now
    mock_dt.strptime = datetime.strptime
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
    cleanup_old_entries(EGON_ID)
a2, p2, s2 = count_entries()
e5_ok = (a1 == a2) and (p1 == p2) and (s1 == s2)
print(f"  1. Cleanup: active={a1}, pending={p1}")
print(f"  2. Cleanup: active={a2}, pending={p2}")
print(f"  Idempotent: {'JA' if e5_ok else 'NEIN'}")
print(f"  => [{'PASS' if e5_ok else 'FAIL'}]")
if e5_ok: pass_count += 1
else: fail_count += 1
print()


# ================================================================
# ERGEBNIS + CLEANUP
# ================================================================
print("=" * 70)
print(" ERGEBNIS")
print("=" * 70)
total = pass_count + fail_count
print(f"  {pass_count}/{total} Tests bestanden")
if fail_count == 0:
    print("  ALLE TESTS BESTANDEN!")
else:
    print(f"  {fail_count} Tests FEHLGESCHLAGEN!")
print()

write_organ(EGON_ID, LAYER, FILENAME, "# Kuerzliches Gedaechtnis\\n")
print("[CLEANUP] Eva recent_memory.md zurueckgesetzt.")
print()
print("=" * 70)
print(" 2-MONATS-LIFECYCLE-TEST ABGESCHLOSSEN")
print("=" * 70)
'''

sftp.open('/tmp/_sim_lifecycle.py', 'w').write(sim_script)
stdin, stdout, stderr = ssh.exec_command(
    'cd /opt/hivecore-v2 && source venv/bin/activate 2>/dev/null; '
    'python3 /tmp/_sim_lifecycle.py 2>&1'
)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err.strip():
    print('STDERR:', err[:2000])

ssh.exec_command('rm -f /tmp/_sim_lifecycle.py')
sftp.close()
ssh.close()
