# Task: Neuen GLB-Clip einbinden

> **Geschätzter Aufwand:** 30-60 Min
> **Benötigte Docs:** `motor/GLB_CLIPS.md` · `motor/ACHSEN.md` · `motor/LAYER_SYSTEM.md` · `app/README.md`
> **Benötigt neue APK:** JA

---

## Checkliste

### 1. GLB vorbereiten
- [ ] GLB-Datei bereitstellen (Quelle: Mixamo, ReadyPlayerMe, manuell)
- [ ] Prüfen: Ist das Skelett kompatibel mit Adam/Eva? (gleiche Bone-Names)
- [ ] Prüfen: Dateigröße (~8 MB pro Clip ist normal)
- [ ] **⚠️ DONT-009:** APK-Größe im Blick behalten (Ziel: <300 MB)

### 2. In App einbinden
- [ ] GLB-Datei kopieren nach: `C:\DEV\EgonsDash\assets\animations\`
- [ ] In `ChatAvatar.tsx` (oder Avatar-Loader) registrieren:
  - Import-Pfad hinzufügen
  - In Clip-Map eintragen (Name → GLB-Pfad)
- [ ] Trigger definieren: Wann soll der Clip abgespielt werden?
  - Motor-Wort mit `glb_fallback` → Clip wird statt Keyframes gespielt
  - Oder: Eigenständiger Trigger (z.B. sleeping, walking)

### 3. Layer-Integration prüfen
- [ ] **⚠️ DONT-001:** Mixer darf NICHT gestoppt werden
- [ ] Clip-Übergang: Wie wird vom idle_natural zum neuen Clip gewechselt?
- [ ] Rückkehr: Wie kommt Adam zurück zum idle_natural?
- [ ] Motor-Layer: Werden Motor-Offsets während des Clips deaktiviert?
- [ ] Ref: `docs/motor/LAYER_SYSTEM.md`

### 4. Testen
- [ ] APK bauen: `npx expo export && ./gradlew assembleRelease`
- [ ] Clip manuell triggern (z.B. via Nachricht)
- [ ] Prüfen: Kein T-Pose Flash beim Übergang?
- [ ] Prüfen: Kein Drift nach Clip-Ende?
- [ ] Prüfen: idle_natural übernimmt sauber danach?

### 5. Docs aktualisieren
- [ ] `docs/motor/GLB_CLIPS.md` — neuen Clip eintragen
- [ ] `docs/motor/VOKABULAR.md` — wenn Motor-Wort mit glb_fallback
- [ ] `docs/CURRENT_STATUS.md` — Clip-Anzahl + APK-Größe aktualisieren
- [ ] `docs/app/CHANGELOG.md` — neue APK-Version dokumentieren

### 6. Wenn es nicht funktioniert
- [ ] T-Pose Flash? → `docs/BUGS.md` BUG-003 + `DONT-001`
- [ ] Falsche Proportionen? → Skelett-Kompatibilität prüfen (Bone-Names)
- [ ] Clip spielt nicht? → Import-Pfad und Clip-Map prüfen

---

*Zurück zu: [INDEX.md](../INDEX.md) · [motor/GLB_CLIPS.md](../motor/GLB_CLIPS.md)*
