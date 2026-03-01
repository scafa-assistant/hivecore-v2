# Motor-System — Vokabular-Referenz

> **Verwandte Dateien:** [ACHSEN.md](ACHSEN.md), [README.md](README.md), [GLB_CLIPS.md](GLB_CLIPS.md)
> **Zuletzt aktualisiert:** 2026-02-26
> **Quelle:** `config/motor_vocabulary.json` (v1.3, 38 Wörter)

---

## Wörter mit GLB-Fallback (Clip statt Motor-Keyframes)

| Wort | Clip | Status |
|------|------|--------|
| winken | waving_right | ✅ Funktioniert |
| winken_links | waving_left | ⚠️ Ungetestet |
| kopf_schuetteln | head_shake | ⚠️ Ungetestet |

## Wörter nach Kategorie

### Posture (Körperhaltungen)
| Wort | Bones | Status |
|------|-------|--------|
| stehen | (Bind-Pose Reset) | ✅ |
| sitzen | Hips, Spine, Beine | Ungetestet |

### Gesture (Gesten)
| Wort | Bones | Status |
|------|-------|--------|
| nicken | Head rx | ✅ Funktioniert |
| kopf_schuetteln | Head ry (GLB) | ⚠️ |
| winken | GLB waving_right | ✅ |
| winken_links | GLB waving_left | ⚠️ |
| zeigen | upper_arm_R, lower_arm_R | Ungetestet |
| hand_heben | upper_arm_R ry, lower_arm_R rz | ✅ Gefixt |
| beide_haende_heben | Beide Arme | ✅ Gefixt |
| kopf_drehen_rechts | Head ry:-25, neck ry:-10 | NEU, ungetestet |
| kopf_drehen_links | Head ry:+25, neck ry:+10 | NEU, ungetestet |

### Expression (Ausdruck)
| Wort | Bones | Status |
|------|-------|--------|
| kopf_neigen | Head rx, rz | ✅ |
| kopf_heben | Head rx:15 | ✅ |
| blick_senken | Head rx:-20 | Ungetestet |
| blick_rechts | eye_R, eye_L, Head | Ungetestet |
| blick_links | eye_R, eye_L, Head | Ungetestet |
| blick_wegdrehen | Head ry:35 | Ungetestet |

### Locomotion (Fortbewegung)
| Wort | Bones | Status |
|------|-------|--------|
| schritt_vor | Beine, Hips | Ungetestet |
| zurueckweichen | Beine, Hips, Spine | Ungetestet |

---

## Geplante Erweiterungen (~50-60 Wörter)

| Wort | Beschreibung | Priorität |
|------|-------------|-----------|
| schulter_zucken | Beide Shoulders hoch | Hoch |
| arme_ausbreiten | Beide Arme seitlich | Hoch |
| facepalm | Hand zum Gesicht | Mittel |
| verbeugen | Spine nach vorne | Mittel |
| klatschen | Hände zusammen (Sequence) | Niedrig |
| faust_ballen | Hand schließen | Niedrig |

---

*Siehe auch: [ACHSEN.md](ACHSEN.md), [GLB_CLIPS.md](GLB_CLIPS.md)*
*Zurück zu: [README.md](README.md)*
