# APK Build-Anleitung — EgonsDash

> **Verwandte Dateien:** [README.md](README.md) · [../server/DEPLOY.md](../server/DEPLOY.md) · [../motor/GLB_CLIPS.md](../motor/GLB_CLIPS.md)
> **Zuletzt aktualisiert:** 2026-02-26

---

## Build-Schritte

```bash
# 1. Expo Bundle exportieren
cd C:\DEV\EgonsDash
npx expo export --platform android --clear

# 2. Build-Cache leeren (WICHTIG bei Asset-Aenderungen!)
# Ohne das bleiben alte GLBs im Build-Cache und die APK wird nicht kleiner
rm -rf android/app/build android/build

# 3. Gradle Build
cd android
./gradlew assembleRelease

# 4. APK kopieren
cp android/app/build/outputs/apk/release/app-release.apk "C:\DEV\APK-Archiv\EgonsDash-vX.X.X-NAME.apk"
```

---

## Version bumpen (vor dem Build)

- `app.json` → `"version": "2.3.8"`
- `android/app/build.gradle` → `versionCode 4` + `versionName "2.3.8"`
- Beide muessen uebereinstimmen (Expo liest app.json, Gradle liest build.gradle)

---

## Warum Build-Cache leeren?

Gradle cached Assets (GLBs, Texturen) im `android/app/build/` Ordner.
Wenn du GLBs loeschst oder aenderst, bleibt die alte Version im Cache.
Ergebnis: APK-Groesse aendert sich nicht, oder alte Animationen bleiben drin.
**Immer `rm -rf android/app/build android/build` bei Asset-Aenderungen!**

---

## Wenn rm -rf fehlschlaegt (Device busy)

Windows lockt manchmal Dateien. Dann mindestens die Key-Dirs loeschen:

```bash
rm -rf android/app/build/generated
rm -rf android/app/build/outputs
rm -rf android/app/build/intermediates/assets
rm -rf android/app/build/intermediates/merged_assets
```

---

## APK-Namenskonvention

`EgonsDash-v{VERSION}-{LABEL}.apk`
- VERSION = aus app.json (z.B. 2.3.8)
- LABEL = beschreibender Name (LAYER3, DEBUG2, RESTPOSE, etc.)

---

## APK-Groessen-Referenz

| Version | Clips | Groesse |
|---------|-------|---------|
| v2.2.3 (alle 20 Clips) | 20 | ~730 MB |
| v2.3.8 RESTPOSE | 3 | 229 MB |
| v2.3.8 LAYER2 | 6 | 253 MB |
| v2.3.8 LAYER3 | 7 | 262 MB |
| Pro GLB-Clip | — | ~8 MB (komprimiert) |

---

## Was braucht neue APK?

| Aenderung | Neue APK? |
|-----------|:---------:|
| Neue GLB-Clips (waving_left.glb, head_shake.glb, etc.) | ✅ |
| avatarState.ts Aenderungen | ✅ |
| ChatAvatar.tsx / skeletalRenderer.ts Aenderungen | ✅ |
| Jede Aenderung im App-Code | ✅ |
| motor_vocabulary.json Aenderungen | ❌ (nur Server) |
| body.md / dna.md Aenderungen | ❌ (nur Server) |

---

*Siehe auch: [../tasks/APK_BAUEN.md](../tasks/APK_BAUEN.md) · [../server/DEPLOY.md](../server/DEPLOY.md)*
*Zurück zu: [INDEX.md](../INDEX.md)*
