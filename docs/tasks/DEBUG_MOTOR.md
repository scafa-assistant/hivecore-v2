# Task: Motor-Problem debuggen

> **Geschätzter Aufwand:** 15-60 Min (je nach Bug)
> **Benötigte Docs:** `motor/ACHSEN.md` · `motor/LAYER_SYSTEM.md` · `motor/PIPELINE.md` · `BUGS.md`
> **Erster Schritt:** IMMER erst in BUGS.md nachschlagen!

---

## Schritt 1: Symptom identifizieren

| Was passiert? | Wahrscheinliche Ursache | Direkt zu... |
|--------------|------------------------|-------------|
| bone_update ist null | Server-Problem | → Schritt 2A |
| Bewegung falsche Richtung | Falsche Achse | → Schritt 2B |
| Bones explodieren (wilde Werte) | Drift-Bug | → Schritt 2C |
| T-Pose Flash | Mixer-Problem | → Schritt 2D |
| Clip spielt nicht | App-Problem | → Schritt 2E |
| Gliedmaßen im Körper | REST_POSE falsch | → Schritt 2F |

---

## Schritt 2A: bone_update ist null

1. **Server-seitig prüfen:**
   - [ ] `dna.md` auf Server vorhanden? `/opt/hivecore-v2/egons/adam_001/core/dna.md`
   - [ ] `body.md` auf Server vorhanden? `/opt/hivecore-v2/egons/adam_001/core/body.md`
   - [ ] `motor_vocabulary.json` vorhanden? `/opt/hivecore-v2/config/motor_vocabulary.json`
   - [ ] HiveCore läuft? `systemctl status hivecore`

2. **Prompt prüfen:**
   - [ ] Enthält body.md die `###BODY###` Anweisung?
   - [ ] Ist MOTOR_INSTRUCTION im Prompt enthalten?
   - [ ] Erneut senden — Moonshot Hit-Rate ist ~100% (Few-Shot Primer in chat.py)

3. **Ref:** `docs/BUGS.md` BUG-001, BUG-007

---

## Schritt 2B: Bewegung falsche Richtung

1. **DONT-006:** NIEMALS raten!
2. **Achsen nachschlagen:** `docs/motor/ACHSEN.md`
   - [ ] Welcher Bone ist betroffen?
   - [ ] Welche Achse wird im Vokabular genutzt?
   - [ ] Stimmt sie mit ACHSEN.md überein?
3. **Spiegelung prüfen** (bei Links/Rechts-Varianten):
   - [ ] rx: GLEICH
   - [ ] ry: INVERTIERT
   - [ ] rz: INVERTIERT
4. **Fix anwenden** in motor_vocabulary.json → Server-Deploy
5. **Ref:** `docs/BUGS.md` BUG-004

---

## Schritt 2C: Bones explodieren

1. **Sofort prüfen:** Wird irgendwo `+=` auf Bone-Rotationen genutzt?
2. **Fix:** Snapshot-basierte Offsets (absolut, nicht relativ)
   ```
   RICHTIG:  bone.rotation.x = snap.rx + offset
   FALSCH:   bone.rotation.x += offset
   ```
3. **Ref:** `docs/BUGS.md` BUG-002 · `DONT-002`

---

## Schritt 2D: T-Pose Flash

1. **Sofort prüfen:**
   - [ ] Wird `mixer.timeScale = 0` irgendwo gesetzt? → DONT-001
   - [ ] Wird `resetToBind()` aufgerufen? → DONT-008
   - [ ] Läuft der Mixer IMMER? (darf nie pausieren)
2. **Fix:** Layer-System — Mixer immer aktiv, Motor nur auf betroffene Bones
3. **Ref:** `docs/BUGS.md` BUG-003 · `docs/motor/LAYER_SYSTEM.md`

---

## Schritt 2E: Clip spielt nicht

1. **Prüfen:**
   - [ ] GLB-Datei im App-Bundle? (assets/animations/)
   - [ ] Import-Pfad korrekt?
   - [ ] In Clip-Map registriert?
   - [ ] Trigger korrekt konfiguriert?
2. **Ref:** `docs/motor/GLB_CLIPS.md`

---

## Schritt 2F: Gliedmaßen im Körper

1. **DONT-007:** NIEMALS manuelle REST_POSE erfinden
2. **Fix:** REST_POSE aus idle_natural.glb extrahieren
3. **Ref:** `docs/BUGS.md` BUG-005

---

## Schritt 3: Nach dem Fix

- [ ] 3x hintereinander testen (Drift-Bug zeigt sich erst nach mehreren Befehlen)
- [ ] `docs/BUGS.md` aktualisieren (neuer Bug oder gelösten markieren)
- [ ] `docs/CURRENT_STATUS.md` aktualisieren
- [ ] Falls neue Erkenntnis: `docs/DONT.md` Eintrag hinzufügen

---

*Zurück zu: [INDEX.md](../INDEX.md) · [BUGS.md](../BUGS.md) · [motor/README.md](../motor/README.md)*
