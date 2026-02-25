#!/usr/bin/env python3
"""
HiveCore v2 - Full Brain Subsystem Verification
NO pulses triggered - read-only evidence gathering.
"""

import paramiko
import sys
from datetime import datetime

HOST = '159.69.157.42'
USER = 'root'
PASS = 'z##rPK$7pahrwQ2H67kR'

ADAM = '/opt/hivecore-v2/egons/adam_001'
EVA  = '/opt/hivecore-v2/egons/eva_002'


def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    return ssh


def run(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out, err


def banner(title):
    w = 72
    print()
    print('=' * w)
    print(f'  {title}')
    print('=' * w)


def sub(title):
    print()
    print(f'--- {title} ---')


def show(text, indent=2):
    prefix = ' ' * indent
    for line in text.rstrip().splitlines():
        print(f'{prefix}{line}')


def safe_run(ssh, cmd, timeout=60):
    out, err = run(ssh, cmd, timeout=timeout)
    if err.strip() and not out.strip():
        print(f'  [stderr] {err.strip()[:300]}')
    if out.strip():
        show(out)
    elif not err.strip():
        print('  (empty)')
    return out


def main():
    print('HiveCore v2 - Full Subsystem Verification')
    print(f'Timestamp : {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC')
    print(f'Server    : {HOST}')

    ssh = connect()
    print('SSH       : connected')
    print()

    banner('1. MARKER DECAY SYSTEM')
    sub('Adam - markers.md (current state)')
    safe_run(ssh, f'cat {ADAM}/markers.md')
    sub('Eva - markers (yaml or md)')
    out, _ = run(ssh, f'cat {EVA}/markers.yaml 2>/dev/null || cat {EVA}/markers.md 2>/dev/null || echo no_markers_file')
    show(out)
    sub('Evidence of decay')
    print('  Markers with intensity < 1.0 and decay_rate > 0 prove decay is active.')

    banner('2. INNER VOICE')
    sub('Adam - last 30 lines of inner_voice.md')
    safe_run(ssh, f'tail -30 {ADAM}/inner_voice.md')
    sub('Eva - inner voice (last 30 lines)')
    safe_run(ssh, f'tail -30 {EVA}/inner_voice.yaml 2>/dev/null || tail -30 {EVA}/inner_voice.md 2>/dev/null || echo not_found')

    banner('3. MEMORY SYSTEM')
    sub('Adam - memory.md HEAD (compressed section)')
    safe_run(ssh, f'head -20 {ADAM}/memory.md')
    sub('Adam - memory.md TAIL (recent entries)')
    safe_run(ssh, f'tail -30 {ADAM}/memory.md')
    sub('Eva - memory HEAD')
    safe_run(ssh, f'head -20 {EVA}/memory.yaml 2>/dev/null || head -20 {EVA}/memory.md 2>/dev/null || echo not_found')
    sub('Eva - memory TAIL')
    safe_run(ssh, f'tail -30 {EVA}/memory.yaml 2>/dev/null || tail -30 {EVA}/memory.md 2>/dev/null || echo not_found')

    banner('4. EPISODE SYSTEM (Eva v2)')
    sub('Eva - episodes.yaml raw (first 60 lines)')
    safe_run(ssh, f'head -60 {EVA}/episodes.yaml 2>/dev/null || echo not_found')
    sub('Eva - episodes.yaml raw (last 40 lines)')
    safe_run(ssh, f'tail -40 {EVA}/episodes.yaml 2>/dev/null || echo not_found')
    sub('Eva - episode count')
    safe_run(ssh, 'grep -c "^- " /opt/hivecore-v2/egons/eva_002/episodes.yaml 2>/dev/null || echo cannot_count')

    banner('5. BONDS / SOCIAL SYSTEM')
    sub('Adam - bonds.md')
    safe_run(ssh, f'cat {ADAM}/bonds.md 2>/dev/null || echo not_found')
    sub('Eva - bonds.yaml')
    safe_run(ssh, f'cat {EVA}/social/bonds.yaml 2>/dev/null || cat {EVA}/bonds.yaml 2>/dev/null || cat {EVA}/bonds.md 2>/dev/null || echo not_found')

    banner('6. WALLET / ECONOMY')
    sub('Adam - wallet.md')
    safe_run(ssh, f'cat {ADAM}/wallet.md 2>/dev/null || echo not_found')
    sub('Eva - wallet')
    safe_run(ssh, f'cat {EVA}/wallet.md 2>/dev/null || cat {EVA}/wallet.yaml 2>/dev/null || echo not_found')

    banner('7. DREAM SYSTEM')
    sub('Adam - dreams count + last dream')
    safe_run(ssh, 'echo Dream_file_count: && ls /opt/hivecore-v2/egons/adam_001/dreams/ 2>/dev/null | wc -l && echo --- && LAST=$(ls -t /opt/hivecore-v2/egons/adam_001/dreams/ 2>/dev/null | head -1) && echo File: $LAST && cat /opt/hivecore-v2/egons/adam_001/dreams/$LAST 2>/dev/null || echo no_dreams')
    sub('Eva - dreams directory')
    safe_run(ssh, 'echo Dream_file_count: && ls /opt/hivecore-v2/egons/eva_002/dreams/ 2>/dev/null | wc -l && echo --- && LAST=$(ls -t /opt/hivecore-v2/egons/eva_002/dreams/ 2>/dev/null | head -1) && echo File: $LAST && cat /opt/hivecore-v2/egons/eva_002/dreams/$LAST 2>/dev/null || echo no_dreams_for_Eva')

    banner('8. EXPERIENCE EXTRACTION (Eva v2)')
    sub('Eva - experience.yaml (first 120 lines)')
    safe_run(ssh, f'head -120 {EVA}/experience.yaml 2>/dev/null || echo not_found')
    sub('Eva - experience.yaml tail (last 40 lines)')
    safe_run(ssh, f'tail -40 {EVA}/experience.yaml 2>/dev/null || echo not_found')
    sub('Eva - experience.yaml line count')
    safe_run(ssh, f'wc -l {EVA}/experience.yaml 2>/dev/null || echo not_found')

    banner('9. EMOTIONAL STATE')
    sub('Adam - emotional markers (markers.md)')
    safe_run(ssh, f'cat {ADAM}/markers.md')
    sub('Eva - emotional_state.yaml')
    safe_run(ssh, f'cat {EVA}/emotional_state.yaml 2>/dev/null || echo not_found')
    sub('Eva - markers')
    safe_run(ssh, f'cat {EVA}/markers.yaml 2>/dev/null || cat {EVA}/markers.md 2>/dev/null || echo no_markers_file')

    banner('10. PULSE LOG (daily 08:00 schedule)')
    sub('journalctl - hivecore around 08:00 today')
    safe_run(ssh, 'journalctl -u hivecore --since "2026-02-24 07:55" --until "2026-02-24 08:05" --no-pager 2>/dev/null || echo no_entries')
    sub('crontab')
    safe_run(ssh, 'crontab -l 2>/dev/null || echo no_crontab')
    sub('systemd timers')
    safe_run(ssh, 'systemctl list-timers --all 2>/dev/null | head -20 || echo no_timers')
    sub('Scheduler config (first 50 lines)')
    safe_run(ssh, 'head -50 /opt/hivecore-v2/scheduler.py 2>/dev/null || echo no_scheduler')
    sub('Recent hivecore journal (last 40 lines)')
    safe_run(ssh, 'journalctl -u hivecore --no-pager -n 40 2>/dev/null || echo no_entries')

    banner('BONUS: FILE STRUCTURE OVERVIEW')
    sub('Adam directory')
    safe_run(ssh, f'find {ADAM} -type f | sort')
    sub('Eva directory')
    safe_run(ssh, f'find {EVA} -type f | sort')

    banner('VERIFICATION SUMMARY')
    checks = [
        '1.  Marker Decay',
        '2.  Inner Voice',
        '3.  Memory System',
        '4.  Episode System (Eva v2)',
        '5.  Bonds / Social',
        '6.  Wallet / Economy',
        '7.  Dream System',
        '8.  Experience Extraction',
        '9.  Emotional State',
        '10. Pulse Log / Scheduler',
    ]
    for c in checks:
        print(f'  [CHECKED]  {c}')

    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    print()
    print(f'  All subsystems queried. Review output above for live evidence.')
    print(f'  Verification completed at {ts} UTC')

    ssh.close()
    print()
    print('SSH connection closed. Done.')


if __name__ == '__main__':
    main()
