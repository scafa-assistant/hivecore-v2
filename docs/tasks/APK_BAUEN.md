# Task: APK bauen

> **Geschätzter Aufwand:** 10-20 Min
> **Benötigte Docs:** `app/BUILD.md` · `app/README.md`
> **Wann nötig:** Bei GLB-Clip Änderungen, App-Code Änderungen, UI-Änderungen

---

## Checkliste

### 1. Vor dem Build
- [ ] Alle Code-Änderungen gespeichert
- [ ] Debug-Overlay deaktiviert (kein grünes Debug-Panel in Produktion)
- [ ] Nicht-benutzte GLBs gelöscht? (DONT-009, Ziel: <300 MB APK)
- [ ] Aktive GLBs prüfen: `docs/motor/GLB_CLIPS.md`

### 2. Build
```bash
cd C:\DEV\EgonsDash

# Cache leeren (bei Problemen)
rm -rf android/app/build

# Export
npx expo export --platform android --clear

# APK bauen
cd android
./gradlew assembleRelease
```

### 3. APK archivieren
- [ ] APK kopieren nach: `C:\DEV\APK-Archiv\`
- [ ] Dateiname-Konvention: `egonsdash_YYYY-MM-DD_vX.X.apk`
- [ ] Größe prüfen (Ziel: <300 MB)

### 4. Docs aktualisieren
- [ ] `docs/CURRENT_STATUS.md` — APK-Datum + Größe
- [ ] `docs/app/CHANGELOG.md` — Was geändert wurde
- [ ] `docs/motor/GLB_CLIPS.md` — falls Clips geändert

---

*Zurück zu: [INDEX.md](../INDEX.md) · [app/BUILD.md](../app/BUILD.md)*
