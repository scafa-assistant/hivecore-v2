# Setup-Prompt für Kollegen — in Claude Code einfügen

> **Anleitung:** Kopiere den Text zwischen den `---` Linien in deine Claude Code Session.
> **Voraussetzung:** Du arbeitest im `hivecore-v2` Repo (nach `git pull origin master`).
> **WICHTIG:** Ersetze `[PASSWORT_HIER_EINSETZEN]` mit dem echten SSH-Passwort (bekommst du von Max).
> **Diese Datei NICHT committen** — nach Setup löschen.

---

Du bist jetzt Claude Code für das EGON-Projekt. Richte dich automatisch ein indem du folgende Schritte ausfuehrst:

## Schritt 1: Repo prüfen

Stelle sicher dass du im `hivecore-v2` Repo arbeitest:
- `git pull origin master` ausfuehren
- Pruefe ob diese Dateien existieren:
  - `CLAUDE.md` (Einstiegspunkt, v2.1)
  - `docs/INDEX.md` (Master-Index)
  - `docs/CURRENT_STATUS.md` (Projektstatus)
- Wenn ja: weiter zu Schritt 2
- Wenn nein: STOPP und melde das Problem

## Schritt 2: CLAUDE.local.md erstellen

Erstelle die Datei `CLAUDE.local.md` im Repo-Root mit diesem Inhalt:

```markdown
# EGON — Lokale Credentials (NICHT committen!)

> **Zweck:** Sensible Zugangsdaten die NICHT ins Git-Repo gehoeren.
> Diese Datei ist in `.gitignore` und wird NUR lokal gelesen.

---

## Server SSH

- **Host**: 159.69.157.42
- **Port**: 8001 (API), SSH Port 443 (wenn 22 blockiert)
- **User**: root
- **Passwort**: `[PASSWORT_HIER_EINSETZEN]`

## SSH von Claude Code

Benutze `paramiko` (python, nicht python3 auf Windows!):

```python
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('159.69.157.42', username='root', password='[PASSWORT_HIER_EINSETZEN]')
stdin, stdout, stderr = ssh.exec_command('cd /root/hivecore-v2 && git pull origin master')
print(stdout.read().decode())
ssh.close()
```

WICHTIG: `python` benutzen, nicht `python3` (Windows-Pfad-Problem mit Git Bash).

---

*Diese Datei wird NICHT committed. Credentials nur hier, nirgendwo sonst.*
```

## Schritt 3: Verifizieren dass CLAUDE.local.md gitignored ist

- Fuehre `git status` aus
- `CLAUDE.local.md` darf NICHT in der Ausgabe erscheinen
- Wenn sie doch erscheint: Pruefe ob `.gitignore` den Eintrag `CLAUDE.local.md` enthaelt

## Schritt 4: Projekt-Kontext laden

Lies jetzt diese Dateien in dieser Reihenfolge (wie CLAUDE.md vorschreibt):
1. `CLAUDE.md` — Grundregeln und Arbeitsanweisungen
2. `docs/CURRENT_STATUS.md` — Wo stehen wir?
3. `docs/INDEX.md` — Master-Index aller Docs

Danach fasse kurz zusammen:
- Welche Version hat CLAUDE.md?
- Was ist der aktuelle Projektstatus?
- Wie viele Motor-Woerter gibt es?
- Welche Bugs sind offen?

## Schritt 5: Fertig!

Bestaetige dass alles eingerichtet ist. Ab jetzt arbeitest du nach den Regeln in CLAUDE.md:
- Bei jeder neuen Session: CLAUDE.md → CURRENT_STATUS.md → INDEX.md lesen
- Sprache: Deutsch (Code-Kommentare koennen Englisch sein)
- Begriffe: Glossar nutzen (`docs/GLOSSAR.md`)
- Docs aktualisieren nach jeder Aufgabe (Abschnitt 4 in CLAUDE.md)
- Niemals alle Docs gleichzeitig laden — nur was fuer die Aufgabe noetig ist

---
