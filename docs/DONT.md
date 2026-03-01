# DONT.md — Was Claude Code NIEMALS tun darf

> **Zweck:** Explizite Verbotsliste basierend auf Fehlern die bereits passiert sind.
> Jeder Eintrag hat einen Grund und eine Referenz zum Vorfall.
> **NIEMALS** Einträge löschen — nur neue hinzufügen.

---

## 🔴 KRITISCH — Sofort Schaden

### DONT-001: NIEMALS `mixer.timeScale = 0` setzen
- **Warum:** Stoppt den AnimationMixer komplett → T-Pose Flash beim Neustart
- **Stattdessen:** Mixer IMMER laufen lassen, Motor überschreibt nur betroffene Bones
- **Vorfall:** 2026-02-26 — T-Pose Flash Bug
- **Ref:** `docs/motor/LAYER_SYSTEM.md`

### DONT-002: NIEMALS Bone-Rotationen mit `+=` akkumulieren
- **Warum:** Ohne Frame-Reset explodieren die Werte exponentiell (1738°, 4851°, 6410°)
- **Stattdessen:** Snapshot nach mixer.update() nehmen, dann absolute Werte setzen: `snap.rx + offset`
- **Vorfall:** 2026-02-26 — Drift-Bug
- **Ref:** `docs/motor/LAYER_SYSTEM.md`

### DONT-003: NIEMALS `deploy.sh` für `egons/` Dateien nutzen
- **Warum:** `rsync` hat `--exclude egons/` → Core-Dateien werden NICHT kopiert
- **Stattdessen:** `cp` manuell: `cp egons/adam_001/core/{dna.md,body.md,ego.md} /opt/...`
- **Vorfall:** 2026-02-26 — Adam sagt "ich habe keine physische Form"
- **Ref:** `docs/server/DEPLOY.md`

### DONT-004: NIEMALS SSH Port 22 nutzen
- **Warum:** Port 22 ist auf dem Hetzner-Server oft blockiert
- **Stattdessen:** Port 443: `ssh root@159.69.157.42 -p 443`
- **Vorfall:** 2026-02-26 — SSH Timeout bei Deploy
- **Ref:** `docs/server/DEPLOY.md`

---

## 🟡 WICHTIG — Funktioniert aber falsch

### DONT-005: NIEMALS alle .claude/ Docs auf einmal laden
- **Warum:** Frisst Kontext-Fenster unnötig auf. Die Docs sind modular aufgebaut.
- **Stattdessen:** CLAUDE.md → INDEX.md → nur die relevante Sub-Datei
- **Ref:** `CLAUDE.md` Abschnitt 3.1

### DONT-006: NIEMALS Motor-Achsen raten
- **Warum:** Jedes Skelett hat eigene Achsen-Konventionen. Was logisch scheint ist oft falsch.
- **Stattdessen:** IMMER `docs/motor/ACHSEN.md` konsultieren (GLB-verifizierte Werte)
- **Vorfall:** 2026-02-26 — "Arm dreht wie Hubschrauber" (rz statt ry)
- **Ref:** `docs/motor/ACHSEN.md`

### DONT-007: NIEMALS manuelle REST_POSE Werte erfinden
- **Warum:** Führt zu Händen im Körper oder anderen Deformationen
- **Stattdessen:** REST_POSE aus idle_natural.glb Keyframes extrahieren
- **Vorfall:** 2026-02-26 — Hände steckten im Körper
- **Ref:** `docs/motor/LAYER_SYSTEM.md`

### DONT-008: NIEMALS `resetToBind()` zwischen Motor-Befehlen aufrufen
- **Warum:** Bind-Pose ist T-Pose → sichtbarer Flash für den User
- **Stattdessen:** Layer-System: Mixer-Clip setzt Pose, Motor überschreibt nur seine Bones
- **Vorfall:** 2026-02-26 — T-Pose Flash
- **Ref:** `docs/motor/LAYER_SYSTEM.md`

### DONT-009: NIEMALS GLB-Clips löschen ohne APK-Größe zu prüfen
- **Warum:** Jede GLB ist 8+ MB. Ohne Aufräumen wächst die APK schnell über 500 MB
- **Stattdessen:** Aktive Clips in `docs/motor/GLB_CLIPS.md` tracken, Rest löschen
- **Vorfall:** 2026-02-26 — APK war 730 MB (17 GLBs), nach Aufräumen 245 MB (5 GLBs)
- **Ref:** `docs/motor/GLB_CLIPS.md`

### DONT-010: NIEMALS Rechts-Links Achsen 1:1 kopieren
- **Warum:** ry und rz müssen INVERTIERT werden für die gespiegelte Seite
- **Stattdessen:** Spiegelungs-Regeln in `docs/motor/ACHSEN.md` beachten (rx gleich, ry/rz invertiert)
- **Vorfall:** 2026-02-26 — Linker Arm ging falsche Richtung
- **Ref:** `docs/motor/ACHSEN.md` → Spiegelungs-Regeln

### DONT-014: NIEMALS Umlaute (ü, ö, ä) in Motor-Wort-Namen verwenden
- **Warum:** `motor_vocabulary.json` nutzt ASCII (ue, oe, ae). `body.md` muss die gleiche Schreibweise nutzen, sonst findet `motor_translator.py` keinen Match und überspringt das Wort stillschweigend
- **Stattdessen:** Immer ASCII-Ersetzung: ü→ue, ö→oe, ä→ae, ß→ss (z.B. `kopf_schuetteln`, nicht `kopf_schütteln`)
- **Vorfall:** 2026-02-26 — 10 von 38 Motor-Wörtern wurden ignoriert (BUG-010)
- **Ref:** `docs/BUGS.md` · `BUG-010` · `docs/ENTSCHEIDUNGEN.md` · `E-013`

---

## 🟢 BEST PRACTICE — Vermeidet zukünftige Probleme

### DONT-011: NIEMALS motor_vocabulary.json ändern ohne Server-Restart
- **Warum:** Server cached die Config beim Start
- **Stattdessen:** Nach jeder Änderung: `systemctl restart hivecore`
- **Ref:** `docs/server/DEPLOY.md`

### DONT-012: NIEMALS eine Architektur-Entscheidung treffen ohne sie zu loggen
- **Warum:** Nächste Claude Code Session kennt den Kontext nicht
- **Stattdessen:** Eintrag in `docs/ENTSCHEIDUNGEN.md` (neueste oben)
- **Ref:** `docs/ENTSCHEIDUNGEN.md`

### DONT-013: NIEMALS Docs-Änderungen vergessen nach Code-Änderungen
- **Warum:** Docs werden veraltet → nächste Session arbeitet mit falschen Infos
- **Stattdessen:** IMMER `CURRENT_STATUS.md` + relevante Docs aktualisieren
- **Ref:** `CLAUDE.md` Abschnitt 4

---

## Eintrag hinzufügen

Format:
```
### DONT-XXX: NIEMALS [was]
- **Warum:** [Grund]
- **Stattdessen:** [Alternative]
- **Vorfall:** [Datum] — [Was passiert ist]
- **Ref:** [Link zur relevanten Doc]
```

Nächste ID: **DONT-015**

---

*Verwandte Dateien: [CLAUDE.md](../CLAUDE.md) · [CURRENT_STATUS.md](CURRENT_STATUS.md)*
*Zuletzt aktualisiert: 2026-02-26*
