# Motor-System — Bone-Achsen-Map

> **Verwandte Dateien:** [VOKABULAR.md](VOKABULAR.md), [README.md](README.md)
> **Zuletzt aktualisiert:** 2026-02-26
> **Quelle:** Extrahiert aus GLB-Animationen (waving.glb, look_around.glb, idle.glb)
> **KRITISCH:** Diese Werte sind verifiziert. Bei neuen Motor-Wörtern IMMER diese Map nutzen.

---

## upper_arm_R (Rechter Oberarm)

| Achse | Richtung | Beschreibung |
|-------|----------|-------------|
| **ry positiv** | Arm HOCH | Hauptachse für Arm heben |
| **ry negativ** | Arm RUNTER | Arm senken |
| **rx negativ** | Leicht nach vorne | Sekundär beim Heben |
| **rx positiv** | Leicht nach hinten | |
| **rz positiv** | Arm nach HINTEN | |
| **rz negativ** | Arm nach VORNE | |

**Dominante Achse:** ry (verifiziert durch waving.glb: dry: +59.0)

## upper_arm_L (Linker Oberarm) — GESPIEGELT

| Achse | Richtung | Beschreibung |
|-------|----------|-------------|
| **ry negativ** | Arm HOCH | Gespiegelt! |
| **ry positiv** | Arm RUNTER | |
| **rx negativ** | Leicht nach vorne | GLEICH wie rechts |
| **rz negativ** | Arm nach HINTEN | Gespiegelt! |
| **rz positiv** | Arm nach VORNE | Gespiegelt! |

## lower_arm_R / lower_arm_L (Unterarme)

| Achse | Richtung | Beschreibung |
|-------|----------|-------------|
| **rz negativ (R)** | Ellenbogen BEUGEN | Hauptachse! |
| **rz positiv (L)** | Ellenbogen BEUGEN | Gespiegelt! |
| rx, ry | Minimal | Kaum relevant |

**Dominante Achse:** rz (verifiziert durch waving.glb: drz: -82.3)

## hand_R / hand_L (Hände)

| Achse | Richtung | Beschreibung |
|-------|----------|-------------|
| **rx negativ** | Handgelenk BEUGEN (runter) | Hauptachse |
| **rx positiv** | Handgelenk STRECKEN (hoch) | |
| **ry ±** | Hand SCHWENKEN (Winken) | Für Wink-Geste |
| **rz ±** | Hand DREHEN | |

## Head (Kopf)

| Achse | Richtung | Beschreibung |
|-------|----------|-------------|
| **rx positiv** | Kopf HOCH (nach oben schauen) | |
| **rx negativ** | Kopf RUNTER (nicken) | |
| **ry negativ** | Kopf nach RECHTS drehen | |
| **ry positiv** | Kopf nach LINKS drehen | |
| **rz positiv** | Kopf nach LINKS neigen | |
| **rz negativ** | Kopf nach RECHTS neigen | |

**Range:** rx: ±16°, ry: ±16°, rz: ±7° (aus look_around.glb)

## neck (Hals)

Gleiche Achsen wie Head, aber kleinere Werte (~40% von Head).
Immer zusammen mit Head bewegen für natürliches Aussehen.

## Spiegelungs-Regeln (Rechts → Links)

| Achse | Regel |
|-------|-------|
| **rx** | GLEICH (hoch/runter ist symmetrisch) |
| **ry** | INVERTIEREN (links/rechts spiegelt sich) |
| **rz** | INVERTIEREN (vor/zurück spiegelt sich) |

---

## Bone Mapping (WICHTIG: Spine-Nummerierung ist UMGEKEHRT!)

| Standard-Name | GLB-Bone | Achtung |
|---------------|----------|---------|
| spine_0 | Spine02 | NICHT Spine! |
| spine_1 | Spine01 | |
| spine_2 | Spine | |
| head | Head | |
| hips | Hips | |

Implementierung: `src/services/boneMapping.ts`

---

## GLB-Referenzwerte (Bind-Pose)

```
BP Hips rx:30.4 ry:11.4 rz:6.5
BP LeftShoulder rx:104.6 ry:-1.1 rz:-97.1
BP LeftArm rx:19.8 ry:22.1 rz:0.2
BP LeftForeArm rx:-26.4 ry:-25.2 rz:-0.2
BP RightShoulder rx:104.6 ry:-1.1 rz:95.1
BP RightArm rx:20.5 ry:-22.3 rz:1.1
BP RightForeArm rx:-26.5 ry:25.7 rz:-0.6
BP Head rx:38.1 ry:-0.1 rz:-0.5
BP neck rx:6.7 ry:0.2 rz:-0.3
```

---

*Siehe auch: [VOKABULAR.md](VOKABULAR.md), [GLB_CLIPS.md](GLB_CLIPS.md)*
*Zurück zu: [README.md](README.md)*
