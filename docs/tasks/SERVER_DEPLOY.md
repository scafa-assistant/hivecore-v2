# Task: Server Deploy

> **Geschätzter Aufwand:** 5-10 Min
> **Benötigte Docs:** `server/DEPLOY.md`
> **Benötigt neue APK:** NEIN (außer bei GLB-Änderungen)

---

## Checkliste

### 1. Was wird deployed?
- [ ] Welche Dateien haben sich geändert?
- [ ] Brauchen `egons/` Dateien ein Update? → Manuell kopieren!

### 2. Deploy ausführen
```bash
# Verbinden
ssh root@159.69.157.42 -p 443

# Code aktualisieren
cd /root/hivecore-v2
git pull origin master

# Dateien synchronisieren (ACHTUNG: excludet egons/)
rsync -av --exclude='.git' --exclude='egons/' /root/hivecore-v2/ /opt/hivecore-v2/
```

### 3. ⚠️ EGON Core-Dateien (MANUELL!)
- [ ] **DONT-003:** `deploy.sh` kopiert KEINE egons/ Dateien!
```bash
# Nur wenn sich core-Dateien geändert haben:
cp /root/hivecore-v2/egons/adam_001/core/dna.md /opt/hivecore-v2/egons/adam_001/core/
cp /root/hivecore-v2/egons/adam_001/core/body.md /opt/hivecore-v2/egons/adam_001/core/
cp /root/hivecore-v2/egons/adam_001/core/ego.md /opt/hivecore-v2/egons/adam_001/core/

# Für Eva (wenn zutreffend):
cp /root/hivecore-v2/egons/eva_002/core/dna.md /opt/hivecore-v2/egons/eva_002/core/
cp /root/hivecore-v2/egons/eva_002/core/body.md /opt/hivecore-v2/egons/eva_002/core/
cp /root/hivecore-v2/egons/eva_002/core/ego.md /opt/hivecore-v2/egons/eva_002/core/
```

### 4. Restart
```bash
systemctl restart hivecore
systemctl status hivecore  # Prüfen ob running
```

### 5. Verifizieren
- [ ] curl-Test: Nachricht an Adam senden
- [ ] Prüfen: Antwort enthält erwartete Änderung
- [ ] Bei Motor-Änderungen: `bone_update` in Response prüfen

### 6. Docs aktualisieren
- [ ] `docs/CURRENT_STATUS.md` — Deployment-Stand Tabelle
- [ ] `docs/server/CHANGELOG.md` — Was deployed wurde
- [ ] Bei motor_vocabulary.json Änderungen: `docs/motor/VOKABULAR.md`

---

### Schnell-Referenz: Was braucht was?

| Änderung an... | Server-Deploy | Manuelle egons/ Kopie | Neue APK |
|----------------|:---:|:---:|:---:|
| motor_vocabulary.json | ✅ | — | — |
| body.md / dna.md / ego.md | ✅ | ✅ | — |
| Python-Code | ✅ | — | — |
| GLB-Clips | — | — | ✅ |
| App TypeScript | — | — | ✅ |

---

*Zurück zu: [INDEX.md](../INDEX.md) · [server/DEPLOY.md](../server/DEPLOY.md)*
