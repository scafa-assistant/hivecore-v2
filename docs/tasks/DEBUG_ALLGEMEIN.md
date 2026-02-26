# Task: Allgemeine Probleme debuggen

> **Geschaetzter Aufwand:** 10-30 Min
> **Benoetigte Docs:** [DEBUG_MOTOR.md](DEBUG_MOTOR.md) (fuer Motor-spezifische Bugs) · [../server/DEPLOY.md](../server/DEPLOY.md)
> **Erster Schritt:** IMMER erst in [BUGS.md](../BUGS.md) nachschlagen!

---

## Symptom-Uebersicht

| Was passiert? | Direkt zu... |
|--------------|-------------|
| APK-Groesse aendert sich nicht nach GLB-Loeschen | → Diagnose A |
| GLB-Fallback spielt nicht | → Diagnose B |
| Server startet nicht nach Deploy | → Diagnose C |
| Motor-spezifisches Problem (bone_update null, falsche Richtung, T-Pose, Drift) | → [DEBUG_MOTOR.md](DEBUG_MOTOR.md) |

---

## Diagnose A: APK-Groesse aendert sich nicht nach GLB-Loeschen

```
1. Build-Cache geleert?
   → rm -rf android/app/build android/build
   → Dann: npx expo export --platform android --clear
   → Dann: cd android && ./gradlew assembleRelease

2. GLB noch in avatarState.ts referenziert?
   → Auch wenn Datei geloescht: Metro bundled cached version
   → require() Zeile aus ADAM_ANIMATIONS/EVA_ANIMATIONS entfernen

3. --clear Flag bei expo export vergessen?
   → MUSS: npx expo export --platform android --clear

4. Wenn rm -rf fehlschlaegt (Device busy / Windows lock):
   → Mindestens Key-Dirs loeschen:
     rm -rf android/app/build/generated
     rm -rf android/app/build/outputs
     rm -rf android/app/build/intermediates/assets
     rm -rf android/app/build/intermediates/merged_assets
```

**Ref:** [../app/BUILD.md](../app/BUILD.md)

---

## Diagnose B: GLB-Fallback spielt nicht

```
1. Ist glb_fallback in motor_vocabulary.json gesetzt?
   → Wort nachschlagen: "glb_fallback": "clip_name"
   → Server deployed nach Aenderung?

2. Ist der Clip in avatarState.ts registriert?
   → ANIMATION_NAMES Array
   → ADAM_ANIMATIONS Record (require() Zeile)
   → EVA_ANIMATIONS Record (require() Zeile)

3. Existiert die GLB-Datei?
   → ls assets/3d/adam/{clip_name}.glb

4. Neue APK gebaut?
   → GLB-Aenderungen brauchen IMMER neue APK!
```

**Ref:** [../motor/GLB_CLIPS.md](../motor/GLB_CLIPS.md) · [../tasks/NEUER_GLB_CLIP.md](NEUER_GLB_CLIP.md)

---

## Diagnose C: Server startet nicht nach Deploy

```
1. Syntax-Fehler im Code?
   → ssh: journalctl -u hivecore --no-pager -n 20
   → Python Traceback → Fix in Code → git push → neu deployen

2. motor_vocabulary.json ungueltig (JSON-Fehler)?
   → ssh: python3 -c "import json; json.load(open('/opt/hivecore-v2/config/motor_vocabulary.json'))"
   → Fehler → JSON reparieren

3. venv/Requirements-Problem?
   → ssh: /opt/hivecore-v2/venv/bin/python -c "import fastapi"
   → ImportError → pip install im venv

4. Core-Dateien vergessen zu kopieren?
   → ssh: ls -la /opt/hivecore-v2/egons/adam_001/core/dna.md
   → FEHLT → manuell kopieren (siehe DEPLOY.md Schritt 5)
```

**Ref:** [../server/DEPLOY.md](../server/DEPLOY.md)

---

## Nach dem Fix

- [ ] Erneut testen
- [ ] `docs/BUGS.md` aktualisieren (neuer Bug oder geloesten markieren)
- [ ] `docs/CURRENT_STATUS.md` aktualisieren
- [ ] Falls neue Erkenntnis: `docs/DONT.md` Eintrag hinzufuegen

---

*Zurück zu: [INDEX.md](../INDEX.md) · [BUGS.md](../BUGS.md) · [DEBUG_MOTOR.md](DEBUG_MOTOR.md)*
