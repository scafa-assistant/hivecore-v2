# EGON Projekt — Claude Code Arbeitsanweisungen

> **Version:** 2.1 | **Stand:** 2026-02-26
> **Zweck:** Diese Datei ist der Einstiegspunkt für Claude Code.
> Sie enthält Grundregeln und verweist auf Detail-Dokumente.
> **NIEMALS** alle Dateien gleichzeitig laden — nur das was für die aktuelle Aufgabe nötig ist.

---

## 0. ERSTE SCHRITTE — BEI JEDER SESSION

> **⚡ Lies diese drei Dateien in dieser Reihenfolge:**
> 1. Diese Datei (`CLAUDE.md`) — hast du gerade
> 2. [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md) — wo stehen wir?
> 3. [`docs/INDEX.md`](docs/INDEX.md) — welche Detail-Datei brauchst du?
>
> **Dann prüfe:**
> - Gibt es ein Task-Template? → [`docs/tasks/`](docs/tasks/)
> - Was darf ich NICHT tun? → [`docs/DONT.md`](docs/DONT.md)
> - Wurde dieses Problem schon gelöst? → [`docs/BUGS.md`](docs/BUGS.md)

---

## 1. PROJEKT-ÜBERBLICK

EGON (Emergent Generative Organic Network) ist ein System für persistente KI-Identitäten.
Jeder EGON hat ein "Gehirn" (Server-Dateien), einen "Körper" (3D-Avatar in der App)
und eine "Seele" (DNA, Persönlichkeit, Erinnerungen).

**Aktive EGONs:** Adam #001, Eva #002
**Geplant:** #003 (Baseline), #004 (Kontrast)

---

## 2. WO FINDE ICH WAS — INDEX

> **Regel:** Lies ZUERST `docs/INDEX.md` um die richtige Detail-Datei zu finden.
> Lade NUR die Dateien die für die aktuelle Aufgabe relevant sind.

| Datei | Inhalt |
|-------|--------|
| [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md) | **Aktueller Projektstatus** ← IMMER zuerst lesen |
| [docs/INDEX.md](docs/INDEX.md) | **Master-Index** aller Dokumentationsdateien |
| [docs/DONT.md](docs/DONT.md) | **Verbotsliste** — Was NICHT tun (aus Fehlern gelernt) |
| [docs/BUGS.md](docs/BUGS.md) | **Bug-Datenbank** — Gelöste + offene Bugs |
| [docs/GLOSSAR.md](docs/GLOSSAR.md) | Projektbegriffe (lesbar) |
| [docs/glossar.yaml](docs/glossar.yaml) | Projektbegriffe (maschinenlesbar) |
| [docs/TECH_STACK.md](docs/TECH_STACK.md) | Alle Technologie-Entscheidungen |
| [docs/ENTSCHEIDUNGEN.md](docs/ENTSCHEIDUNGEN.md) | Log aller Architektur-Entscheidungen |
| [docs/KONVENTIONEN.md](docs/KONVENTIONEN.md) | Code-Style, Naming, Commit-Regeln |

### Task-Templates (Schritt-für-Schritt Anleitungen)

| Template | Wann nutzen |
|----------|------------|
| [docs/tasks/NEUE_SESSION.md](docs/tasks/NEUE_SESSION.md) | Bei jeder neuen Claude Code Session |
| [docs/tasks/NEUES_MOTOR_WORT.md](docs/tasks/NEUES_MOTOR_WORT.md) | Neues Motor-Wort hinzufügen |
| [docs/tasks/NEUER_GLB_CLIP.md](docs/tasks/NEUER_GLB_CLIP.md) | GLB-Animation einbinden |
| [docs/tasks/SERVER_DEPLOY.md](docs/tasks/SERVER_DEPLOY.md) | Server deployen |
| [docs/tasks/APK_BAUEN.md](docs/tasks/APK_BAUEN.md) | Android APK bauen |
| [docs/tasks/DEBUG_MOTOR.md](docs/tasks/DEBUG_MOTOR.md) | Motor-Problem diagnostizieren |
| [docs/tasks/DEBUG_ALLGEMEIN.md](docs/tasks/DEBUG_ALLGEMEIN.md) | APK/GLB/Server-Probleme diagnostizieren |

### Detail-Dokumentation (nach Bereich)

| Bereich | Datei | Beschreibung |
|---------|-------|-------------|
| Server/Gehirn | [docs/server/README.md](docs/server/README.md) | HiveCore v2 Architektur |
| App | [docs/app/README.md](docs/app/README.md) | EgonsDash App Architektur |
| Motor-System | [docs/motor/README.md](docs/motor/README.md) | Body Motor System |
| Forschung | [docs/research/README.md](docs/research/README.md) | Paper & Studiendesign |
| Overlay | [docs/overlay/README.md](docs/overlay/README.md) | Living Overlay System |

---

## 3. GRUNDREGELN FÜR CLAUDE CODE

### 3.1 Kontext-Management
- **NICHT** alle Docs auf einmal lesen → Kontext-Fenster schonen
- **IMMER** zuerst `docs/INDEX.md` lesen → richtige Sub-Datei finden
- **NUR** die Dateien laden die für die aktuelle Aufgabe nötig sind
- Bei Unsicherheit: Frag den User welcher Bereich betroffen ist

### 3.2 Arbeitsablauf
1. User gibt Aufgabe
2. Lies diese CLAUDE.md (hast du gerade)
3. Lies `docs/CURRENT_STATUS.md` (wo stehen wir?)
4. Prüfe `docs/tasks/` — gibt es ein Template für diese Aufgabe?
5. Prüfe `docs/BUGS.md` — wurde dieses Problem schon gelöst?
6. Prüfe `docs/DONT.md` — was darf ich NICHT tun?
7. Lies `docs/INDEX.md` um die relevante Detail-Datei zu finden
8. Lies NUR die relevante Detail-Datei(en)
9. Führe die Aufgabe aus
10. **Aktualisiere die Docs** (siehe Abschnitt 4)

### 3.3 Kommunikation
- Sprache: **Deutsch** (Code-Kommentare können Englisch sein)
- Begriffe: Nutze das **GLOSSAR** (`docs/GLOSSAR.md`)
- Wenn der User Slang benutzt → im Glossar nachschlagen

### 3.4 Dateipfade
| Was | Pfad |
|-----|------|
| App-Code | `C:\DEV\EgonsDash\` |
| Server-Code | `C:\DEV\hivecore-v2\` |
| Produktionsserver | `159.69.157.42` (SSH Port 443, User: root) |
| APK-Archiv | `C:\DEV\APK-Archiv\` |
| GLB-Assets | `C:\DEV\Avatar-glb\` |
| Adam Server-Daten | `/opt/hivecore-v2/egons/adam_001/` |
| Eva Server-Daten | `/opt/hivecore-v2/egons/eva_002/` |

### 3.5 Deploy-Prozess

> **Credentials:** SSH-Passwort steht in `CLAUDE.local.md` (lokal, nicht in Git).
> **Details:** Vollstaendige Anleitung in `docs/server/DEPLOY.md`.

```
SERVER:
  git push → ssh root@159.69.157.42 -p 443 (Passwort: CLAUDE.local.md)
  cd /root/hivecore-v2 && git pull origin master
  rsync (--exclude egons/) → /opt/hivecore-v2/
  cp egons/{adam,eva}/core/{dna.md,body.md,ego.md} → /opt/...
  systemctl restart hivecore

APP:
  cd C:\DEV\EgonsDash
  npx expo export --platform android --clear
  rm -rf android/app/build android/build (bei Asset-Aenderungen!)
  cd android && ./gradlew assembleRelease
  APK → C:\DEV\APK-Archiv\
```

### 3.6 Bekannte Fallstricke
- `deploy.sh` **excludet** den `egons/` Ordner → Core-Dateien MANUELL kopieren
- SSH Port **22 oft blockiert** → Port **443** nutzen
- Moonshot LLM `###BODY###` Hit-Rate **~100%** (durch Few-Shot Primer in chat.py)
- `motor_vocabulary.json` Änderungen brauchen **nur Server-Deploy**, keine neue APK
- GLB-Clips Änderungen brauchen **neue APK**

---

## 4. DOCS AKTUALISIEREN — SELBSTPFLEGE

> **WICHTIG:** Nach jeder abgeschlossenen Aufgabe die relevanten Docs aktualisieren.
> **Single Source of Truth:** Alles geteilte Wissen steht in `docs/` (im Git-Repo).
> **Credentials:** Stehen NUR in `CLAUDE.local.md` (lokal, nicht in Git).
> **Auto-Memory:** `memory/MEMORY.md` ist nur ein schlanker Index + Current State.

### Was wann aktualisieren

| Event | Aktualisiere |
|-------|-------------|
| **Motor-Wort geaendert/hinzugefuegt** | `docs/CURRENT_STATUS.md` + `docs/motor/VOKABULAR.md` |
| **Bug gefixt** | `docs/BUGS.md` (geloest) + `docs/CURRENT_STATUS.md` |
| **Architektur-Entscheidung** | `docs/ENTSCHEIDUNGEN.md` (Problem, Alternativen, Warum) |
| **Server deployed** | `docs/CURRENT_STATUS.md` |
| **APK gebaut** | `docs/CURRENT_STATUS.md` |
| **Neuer GLB-Clip** | `docs/motor/GLB_CLIPS.md` |
| **Fehler gemacht** | `docs/DONT.md` + `docs/tasks/DEBUG_MOTOR.md` oder `DEBUG_ALLGEMEIN.md` |
| **Neuer Bug gefunden** | `docs/BUGS.md` (neuer Eintrag) |
| **Session beendet** | `docs/CURRENT_STATUS.md` + `memory/MEMORY.md` (Current State) |

### Wie aktualisieren
1. Datum hinzufuegen (Format: `YYYY-MM-DD`)
2. Kurze Beschreibung was geaendert wurde
3. Cross-Referenzen pruefen (verweist eine andere Datei hierauf?)
4. **NIEMALS** alte Eintraege loeschen — nur neue hinzufuegen
5. `docs/ENTSCHEIDUNGEN.md` immer MIT Begruendung (Warum, nicht nur Was)

---

## 5. NOTFALL-REFERENZ

| Problem | Lösung |
|---------|--------|
| SSH Port 22 blockiert | Port 443 nutzen |
| APK zu groß | Build-Cache leeren: `rm -rf android/app/build` |
| bone_update ist null | `body.md` + `dna.md` auf Server prüfen |
| Motor-Pose dreht wild | Achsen-Map prüfen: `docs/motor/ACHSEN.md` |
| Drift-Bug (Bones explodieren) | Snapshot-basierte Offsets prüfen (skeletalRenderer.ts) |
| Moonshot generiert kein ###BODY### | Few-Shot Primer in chat.py prüfen (History leer?) |
| T-Pose Flash | Mixer muss IMMER laufen — KEIN resetToBind(), KEIN timeScale=0 |

---

*Diese Datei ist der Ausgangspunkt. Für Details → `docs/INDEX.md`*
