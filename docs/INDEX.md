# EGON Projekt — Master-Index

> **Zweck:** Zentrale Übersicht aller Dokumentationsdateien.
> Claude Code: Lies diese Datei um die richtige Detail-Datei für deine Aufgabe zu finden.
> **Stand:** 2026-02-26 (v2.1)

---

## Verzeichnisstruktur

```
.claude/
├── CLAUDE.md                          ← Einstiegspunkt (Grundregeln)
├── CLAUDE.local.md                    ← Credentials (NICHT in Git!)
├── docs/
│   ├── INDEX.md                       ← DU BIST HIER
│   ├── CURRENT_STATUS.md             ← 🔴 Aktueller Projektstatus (immer zuerst!)
│   ├── DONT.md                        ← 🔴 Was NICHT tun (Verbotsliste)
│   ├── BUGS.md                        ← 🔴 Bug-Datenbank (gelöst + offen)
│   ├── GLOSSAR.md                     ← Projektbegriffe (Markdown, lesbar)
│   ├── glossar.yaml                   ← Projektbegriffe (YAML, maschinenlesbar)
│   ├── TECH_STACK.md                  ← Technologie-Entscheidungen
│   ├── ENTSCHEIDUNGEN.md              ← Architektur-Entscheidungslog
│   ├── KONVENTIONEN.md                ← Code-Style & Naming
│   │
│   ├── tasks/                         ← 📋 Schritt-für-Schritt Anleitungen
│   │   ├── NEUE_SESSION.md            ← Kontext-Übergabe bei neuer Session
│   │   ├── NEUES_MOTOR_WORT.md        ← Motor-Wort hinzufügen
│   │   ├── NEUER_GLB_CLIP.md          ← GLB-Animation einbinden
│   │   ├── SERVER_DEPLOY.md           ← Server deployen
│   │   ├── APK_BAUEN.md              ← Android APK bauen
│   │   ├── DEBUG_MOTOR.md             ← Motor-Problem diagnostizieren
│   │   └── DEBUG_ALLGEMEIN.md         ← APK/GLB/Server-Probleme diagnostizieren
│   │
│   ├── sessions/                      ← 📝 Session-Logs
│   │   └── SESSION_2026-02-26.md      ← Erste Session (Motor-Debug)
│   │
│   ├── server/                        ← HiveCore v2 (Gehirn)
│   │   ├── README.md                  ← Architektur-Überblick
│   │   ├── ORGANE.md                  ← Alle EGON-Organe erklärt
│   │   ├── PROMPT_BUILDER.md          ← Prompt-Pipeline (v2 Brain, Few-Shot Primer)
│   │   ├── API.md                     ← REST API Endpunkte [TODO]
│   │   ├── DEPLOY.md                  ← Deploy-Anleitung
│   │   └── CHANGELOG.md              ← Server-Änderungslog [TODO]
│   │
│   ├── app/                           ← EgonsDash (Körper)
│   │   ├── README.md                  ← App-Architektur
│   │   ├── AVATAR.md                  ← 3D Avatar System [TODO]
│   │   ├── SCREENS.md                 ← Screen-Übersicht [TODO]
│   │   ├── BUILD.md                   ← Build-Anleitung (APK bauen, Cache, Groessen)
│   │   └── CHANGELOG.md              ← App-Änderungslog [TODO]
│   │
│   ├── motor/                         ← Body Motor System
│   │   ├── README.md                  ← Motor-System Überblick
│   │   ├── ACHSEN.md                  ← Bone-Achsen-Map (GLB-verifiziert) ⚠️
│   │   ├── VOKABULAR.md              ← Motor-Wörter Referenz
│   │   ├── PIPELINE.md               ← End-to-End Datenfluss
│   │   ├── LAYER_SYSTEM.md           ← Clip + Motor Layer Architektur
│   │   └── GLB_CLIPS.md              ← Registrierte GLB-Animationen
│   │
│   ├── overlay/                       ← Living Overlay
│   │   └── README.md                  ← Overlay-Konzept & Status
│   │
│   └── research/                      ← Forschung & Paper
│       ├── README.md                  ← Studiendesign-Überblick
│       ├── GEHIRN_MAPPING.md          ← Neurobiologie ↔ EGON Mapping
│       └── EGON_VERGLEICH.md          ← Adam vs Eva vs #003 vs #004
```

---

## Schnell-Navigation nach Aufgabentyp

| Wenn du... | Lies zuerst... | Task-Template? |
|-----------|---------------|----------------|
| Eine neue Session startest | `CURRENT_STATUS.md` → `DONT.md` | `tasks/NEUE_SESSION.md` ✅ |
| Motor-Wörter ändern willst | `motor/VOKABULAR.md` → `motor/ACHSEN.md` | `tasks/NEUES_MOTOR_WORT.md` ✅ |
| Einen Motor-Bug fixen willst | `BUGS.md` → `motor/LAYER_SYSTEM.md` | `tasks/DEBUG_MOTOR.md` ✅ |
| Ein APK/GLB/Server-Problem hast | `BUGS.md` → relevanter Bereich | `tasks/DEBUG_ALLGEMEIN.md` ✅ |
| Server deployen willst | `server/DEPLOY.md` | `tasks/SERVER_DEPLOY.md` ✅ |
| APK bauen willst | `app/BUILD.md` | `tasks/APK_BAUEN.md` ✅ |
| Neue GLB-Animation einbinden willst | `motor/GLB_CLIPS.md` → `app/AVATAR.md` | `tasks/NEUER_GLB_CLIP.md` ✅ |
| Einen Bug im Avatar fixen willst | `BUGS.md` → `app/AVATAR.md` → `motor/LAYER_SYSTEM.md` | — |
| Prompt/Body.md ändern willst | `server/PROMPT_BUILDER.md` → `motor/PIPELINE.md` | — |
| Einen neuen EGON anlegen willst | `server/ORGANE.md` → `server/README.md` | — |
| Architektur-Entscheidung treffen willst | `ENTSCHEIDUNGEN.md` → `TECH_STACK.md` | — |
| Einen Begriff nicht verstehst | `GLOSSAR.md` (oder `glossar.yaml`) | — |
| Wissen willst was NICHT tun | `DONT.md` | — |
| Einen alten Bug nachschlagen willst | `BUGS.md` | — |
| Letzte Session nachlesen willst | `sessions/SESSION_YYYY-MM-DD.md` | — |

---

## Cross-Referenz-Regeln

Jede Datei enthält am Anfang:
- **Verwandte Dateien:** Links zu Dateien die oft zusammen gelesen werden
- **Zuletzt aktualisiert:** Datum der letzten Änderung

Jede Datei enthält am Ende:
- **Siehe auch:** Weiterführende Dateien
- **Aktualisiert von:** Wer/was die letzte Änderung ausgelöst hat

---

## Dateien nach Priorität

🔴 **Immer lesen:** CLAUDE.md → CURRENT_STATUS.md → INDEX.md
🟡 **Bei Problemen:** DONT.md → BUGS.md → relevantes Task-Template
🟢 **Bei Bedarf:** Bereichs-spezifische Docs (motor/, server/, app/, etc.)

---

*Zurück zu: [CLAUDE.md](../CLAUDE.md)*
