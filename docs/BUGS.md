# EGON Projekt — Bug-Datenbank

> **Zweck:** Gelöste UND offene Bugs. Bevor du einen Bug fixst → hier nachschlagen.
> Symptom-basiert sortiert, damit Claude Code schnell die richtige Lösung findet.
> **NIEMALS** gelöste Bugs löschen — sie sind Referenzmaterial.

---

## Offene Bugs

### BUG-007: Moonshot generiert kein ###BODY### (~20% der Fälle)
- **Symptom:** `bone_update` ist `null` in der API-Response obwohl Motor-System aktiv
- **Ursache:** Moonshot LLM ignoriert manchmal die MOTOR_INSTRUCTION im Prompt
- **Workaround:** Erneut senden, meist klappt es beim 2. Versuch
- **Geplanter Fix:** Prompt in body.md verstärken, Few-Shot Beispiele hinzufügen
- **Priorität:** HOCH
- **Erstellt:** 2026-02-26

### BUG-008: head_shake.glb ungetestet
- **Symptom:** Clip eingebunden aber noch nie live verifiziert
- **Ursache:** Wurde am Ende der Session erstellt, keine Zeit zum Testen
- **Priorität:** MITTEL
- **Erstellt:** 2026-02-26

---

## Gelöste Bugs

### BUG-010: Umlaut-Mismatch — 10 Motor-Wörter stillschweigend ignoriert ✅
- **Symptom:** 10 von 38 Motor-Wörtern wurden vom Server nie ausgeführt (z.B. kopf_schütteln, hände_hüfte, ängstlich)
- **Ursache:** `body.md` nutzte deutsche Umlaute (kopf_schütteln), `motor_vocabulary.json` nutzte ASCII (kopf_schuetteln). `motor_translator.py` machte exakten String-Lookup → kein Match → Wort stillschweigend übersprungen
- **Betroffene Wörter:** kopf_schütteln, hände_hüfte, kinn_berühren, wütend_stehen, überrascht, beide_hände_heben, erschöpft, ängstlich, zurücklehnen, arme_verschränken
- **Fix:** (A) `body.md` auf ASCII-Schreibweise umgestellt, (B) `_normalize_umlauts()` Safety-Net in `motor_translator.py` hinzugefügt
- **Gelöst:** 2026-02-26
- **Ref:** `docs/DONT.md` · `DONT-014` · `docs/ENTSCHEIDUNGEN.md` · `E-013`

### BUG-001: "Ich habe keine physische Form" ✅
- **Symptom:** Adam sagt er hat keinen Körper, `bone_update: null`
- **Ursache:** `body.md` + `dna.md` fehlten auf Produktionsserver (deploy.sh excludet egons/)
- **Fix:** Manuelle Kopie: `cp egons/adam_001/core/{dna.md,body.md,ego.md} /opt/...`
- **Gelöst:** 2026-02-26
- **Ref:** `docs/server/DEPLOY.md` · `DONT-003`

### BUG-002: Drift-Bug — Bones explodieren ✅
- **Symptom:** Nach 2-3 Motor-Befehlen: Rotationen bei 1738°, 4851°, 6410°
- **Ursache:** `_applyOffsets()` nutzte `+=` ohne Frame-Reset → exponentielle Akkumulation
- **Fix:** Snapshot-basierte Offsets: `bone.rotation.x = snap.rx + offset` (absolut, nicht relativ)
- **Gelöst:** 2026-02-26
- **Ref:** `docs/motor/LAYER_SYSTEM.md` · `DONT-002`

### BUG-003: T-Pose Flash ✅
- **Symptom:** Alle 3-4 Sekunden springt Adam in T-Pose (Arme seitlich)
- **Ursache:** AnimationMixer wurde gestoppt/gestartet → Übergang zur Bind-Pose
- **Fix:** Layer-System — Mixer läuft IMMER, Motor überschreibt nur betroffene Bones
- **Gelöst:** 2026-02-26
- **Ref:** `docs/motor/LAYER_SYSTEM.md` · `DONT-001` · `DONT-008`

### BUG-004: Arm dreht wie Hubschrauber ✅
- **Symptom:** `hand_heben` dreht den Arm horizontal statt ihn zu heben
- **Ursache:** Motor-Vocabulary nutzte `rz` statt `ry` für upper_arm
- **Fix:** Achsen-Map via GLB-Extraktion korrigiert, `ry` = Arm HOCH
- **Gelöst:** 2026-02-26
- **Ref:** `docs/motor/ACHSEN.md` · `DONT-006`

### BUG-005: Hände stecken im Körper ✅
- **Symptom:** REST_POSE zeigt Adam mit Händen die durch den Torso gehen
- **Ursache:** Manuell erfundene REST_POSE Werte stimmten nicht mit Skelett überein
- **Fix:** REST_POSE aus idle_natural.glb Keyframes extrahiert (20 Bones)
- **Gelöst:** 2026-02-26
- **Ref:** `docs/motor/LAYER_SYSTEM.md` · `DONT-007`

### BUG-006: APK 730 MB ✅
- **Symptom:** APK viel zu groß für sinnvolle Verteilung
- **Ursache:** 17 GLB-Clips (je 8+ MB) eingebunden, nur 5 davon aktiv
- **Fix:** 12 unbenutzte GLBs gelöscht → 245 MB
- **Gelöst:** 2026-02-26
- **Ref:** `docs/motor/GLB_CLIPS.md` · `DONT-009`

---

## Schnell-Lookup nach Symptom

| Symptom | Bug-ID |
|---------|--------|
| "hat keine physische Form" | BUG-001 |
| Werte explodieren / Bones drehen wild | BUG-002 |
| T-Pose Flash / Arme gehen seitlich | BUG-003 |
| Rotation falsche Richtung | BUG-004 |
| Gliedmaßen im Körper | BUG-005 |
| APK zu groß | BUG-006 |
| bone_update ist null | BUG-001 oder BUG-007 |
| Clip nicht getestet | BUG-008 |
| Motor-Wörter werden ignoriert / kein Effekt | BUG-010 |

---

## Bug hinzufügen

```
### BUG-XXX: [Kurztitel] [✅ wenn gelöst]
- **Symptom:** [Was der User sieht]
- **Ursache:** [Technische Root Cause]
- **Fix:** [Was genau getan wurde]
- **Gelöst:** [Datum] (oder **Priorität:** HOCH/MITTEL/NIEDRIG wenn offen)
- **Ref:** [Links zu Docs/DONTs]
```

Nächste ID: **BUG-011**

---

*Verwandte Dateien: [DONT.md](DONT.md) · [CURRENT_STATUS.md](CURRENT_STATUS.md) · [motor/README.md](motor/README.md)*
*Zuletzt aktualisiert: 2026-02-26*
