# Task: Neues Motor-Wort hinzufügen

> **Geschätzter Aufwand:** 10-20 Min
> **Benötigte Docs:** `motor/ACHSEN.md` · `motor/VOKABULAR.md` · `server/DEPLOY.md`
> **Benötigt neue APK:** NEIN (nur Server-Deploy)

---

## Checkliste

### 1. Achsen bestimmen
- [ ] Welcher Bone? → `docs/motor/ACHSEN.md` öffnen
- [ ] Welche Achse (rx/ry/rz)? → Verifizierte Werte aus ACHSEN.md nutzen
- [ ] Welche Richtung (positiv/negativ)? → ACHSEN.md Kommentare lesen
- [ ] **⚠️ DONT-006:** NIEMALS Achsen raten — nur GLB-verifizierte Werte

### 2. Eintrag in motor_vocabulary.json
- [ ] Datei öffnen: `/opt/hivecore-v2/config/motor_vocabulary.json`
- [ ] Neues Wort im richtigen Format:
```json
{
  "wort_name": {
    "label": "wort_name",
    "bones": {
      "bone_name": {
        "rx": 0, "ry": 0, "rz": 0
      }
    },
    "duration": 0.8,
    "easing": "easeInOut"
  }
}
```
- [ ] Bei Links/Rechts-Varianten: Spiegelungs-Regeln beachten (rx gleich, ry/rz invertiert)

### 3. Testen
- [ ] Server deployen: `systemctl restart hivecore`
- [ ] curl-Test: Nachricht senden die die Geste auslösen sollte
- [ ] Prüfen: Kommt das Motor-Wort im `bone_update.words[]`?
- [ ] Prüfen: Sieht die Bewegung in der App korrekt aus?

### 4. Docs aktualisieren
- [ ] `docs/motor/VOKABULAR.md` — neues Wort eintragen
- [ ] `docs/CURRENT_STATUS.md` — Motor-Wort-Anzahl aktualisieren
- [ ] Falls neue Achsen-Erkenntnis: `docs/motor/ACHSEN.md` ergänzen

### 5. Wenn es nicht funktioniert
- [ ] `bone_update` ist null? → `docs/BUGS.md` BUG-007 (Hit-Rate Problem)
- [ ] Bewegung falsche Richtung? → `docs/BUGS.md` BUG-004 (Achsen prüfen)
- [ ] Bones explodieren? → `docs/BUGS.md` BUG-002 (Drift-Bug)

---

*Zurück zu: [INDEX.md](../INDEX.md) · [motor/VOKABULAR.md](../motor/VOKABULAR.md)*
