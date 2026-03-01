# HiveCore v2 — Deploy-Anleitung

> **Verwandte Dateien:** [README.md](README.md) · [../app/BUILD.md](../app/BUILD.md) · `CLAUDE.local.md` (Credentials)
> **Zuletzt aktualisiert:** 2026-02-26

---

## Server-Infos

| Was | Wert |
|-----|------|
| IP | 159.69.157.42 |
| API-Port | 8001 |
| SSH-Port | 443 (Port 22 oft blockiert!) |
| User | root |
| Passwort | **siehe `CLAUDE.local.md`** |
| Service | `systemctl restart hivecore` |
| Logs | `journalctl -u hivecore --no-pager -n 50` |
| Git-Repo (Server) | `/root/hivecore-v2` (master) |
| Runtime (Live) | `/opt/hivecore-v2` |
| Python-Env | `/opt/hivecore-v2/venv/bin/python` |

---

## Server-Deploy

```bash
# 1. Code pushen
cd C:\DEV\hivecore-v2
git add . && git commit -m "Beschreibung" && git push

# 2. SSH verbinden (Port 443 wenn 22 blockiert)
ssh root@159.69.157.42 -p 443
# Passwort: siehe CLAUDE.local.md

# 3. Code ziehen
cd /root/hivecore-v2 && git pull origin master

# 4. Rsync (OHNE egons/)
rsync -av --delete \
  --exclude .git --exclude venv --exclude __pycache__ \
  --exclude egons/ --exclude .env --exclude "*.pyc" \
  /root/hivecore-v2/ /opt/hivecore-v2/

# 5. Core-Dateien MANUELL kopieren (deploy.sh excludet egons/)
# Adam:
cp /root/hivecore-v2/egons/adam_001/core/dna.md /opt/hivecore-v2/egons/adam_001/core/
cp /root/hivecore-v2/egons/adam_001/core/body.md /opt/hivecore-v2/egons/adam_001/core/
cp /root/hivecore-v2/egons/adam_001/core/ego.md /opt/hivecore-v2/egons/adam_001/core/
# Eva:
cp /root/hivecore-v2/egons/eva_002/core/dna.md /opt/hivecore-v2/egons/eva_002/core/
cp /root/hivecore-v2/egons/eva_002/core/body.md /opt/hivecore-v2/egons/eva_002/core/
cp /root/hivecore-v2/egons/eva_002/core/ego.md /opt/hivecore-v2/egons/eva_002/core/

# 6. Neustart
systemctl restart hivecore
systemctl is-active hivecore
```

---

## Zwei Pfade auf dem Server — Warum?

| Pfad | Zweck |
|------|-------|
| `/root/hivecore-v2` | Git-Repo (zum Pullen) |
| `/opt/hivecore-v2` | Runtime (was tatsaechlich laeuft) |

`rsync` kopiert von Git → Runtime, **ABER excludet `egons/`** um User-Daten (Memories, Bonds, etc.) nicht zu ueberschreiben.
Core-Dateien (`dna.md`, `body.md`, `ego.md`) muessen deshalb **MANUELL** kopiert werden.

---

## KRITISCH: dna.md MUSS auf Runtime-Pfad sein!

Ohne `dna.md` in `/opt/hivecore-v2/egons/adam_001/core/` waehlt `prompt_builder.py` das alte **v1-Brain** und laedt **KEIN** `body.md`/`MOTOR_INSTRUCTION`. Das war der Root-Cause Bug vom 26.02.2026.

---

## SSH von Claude Code

Claude Code kann nicht direkt `ssh` nutzen (interaktives Passwort). Stattdessen **paramiko** verwenden.
Credentials und Template: siehe `CLAUDE.local.md`.

WICHTIG: `python` benutzen, nicht `python3` (Windows-Pfad-Problem mit Git Bash).

---

## WICHTIG

- `deploy.sh` **excludet** `egons/` → Core-Dateien IMMER manuell kopieren
- SSH Port **22 oft blockiert** → Port **443** nutzen
- Nach Deploy: `curl http://localhost:8001/` um zu verifizieren

---

## Was braucht was?

| Aenderung | Server-Deploy | Neue APK |
|-----------|:---:|:---:|
| motor_vocabulary.json | ✅ | ❌ |
| body.md / dna.md / ego.md | ✅ | ❌ |
| Engine-Code (prompt_builder, response_parser, etc.) | ✅ | ❌ |
| Neue GLB-Clips | ❌ | ✅ |
| App-Code (ChatAvatar, skeletalRenderer, etc.) | ❌ | ✅ |
| avatarState.ts Aenderungen | ❌ | ✅ |
| Beides | ✅ | ✅ |

---

*Zurück zu: [README.md](README.md) · [../INDEX.md](../INDEX.md)*
