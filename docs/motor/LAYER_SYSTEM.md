# Motor-System — Layer-Architektur

> **Verwandte Dateien:** [README.md](README.md), [ACHSEN.md](ACHSEN.md), [../app/AVATAR.md](../app/AVATAR.md)
> **Zuletzt aktualisiert:** 2026-02-26
> **Entscheidung:** [E-011](../ENTSCHEIDUNGEN.md)

---

## Das Zwei-Layer-System

```
┌─────────────────────────────────────────┐
│ Layer 1: Clip (AnimationMixer)          │
│ - Läuft IMMER                           │
│ - idle_natural = Default                │
│ - Setzt ALLE 24 Bones jeden Frame      │
│ - Basis: Atmen, Stehen, Mikrobewegung  │
└────────────────┬────────────────────────┘
                 │ Snapshot der Clip-Werte
                 ▼
┌─────────────────────────────────────────┐
│ Layer 2: Motor-Pose                     │
│ - NUR wenn bone_update vom Server kommt │
│ - Überschreibt NUR betroffene Bones    │
│ - Addiert Deltas auf Clip-Snapshot     │
│ - Fade-Back zur Clip-Pose nach Ende    │
└─────────────────────────────────────────┘
```

## Regeln

1. **Mixer NIEMALS pausieren** (kein timeScale = 0)
2. **Motor überschreibt NUR seine eigenen Bones**
3. **Clip-Werte werden als Snapshot gecacht** (nicht Bind-Pose)
4. **Nach Motor-Ende:** Bones gehen sanft zum Clip-Wert zurück (Fade-Back)

## GLB-Fallback

Wenn ein Motor-Wort `glb_fallback` hat:
1. Mixer wechselt zum Fallback-Clip (z.B. waving_right)
2. Motor-Pose wird NICHT angewendet
3. Nach Clip-Ende: zurück zu idle_natural

## Implementierung

**ChatAvatar.tsx Render-Loop:**
```typescript
// Jeden Frame:
mixer.update(delta)                    // Layer 1: Clip
clipInfluencing = action !== null
updateMotor(elapsed, delta, clipInfluencing)  // Layer 2: Motor
renderer.render(scene, camera)
```

---

## Natural Motion (Layer 3 — aktuell deaktiviert)

Additive Mikrobewegungen, deaktiviert waehrend Motor aktiv. Aktuell gibt `computeNaturalMotion()` leeres Objekt zurueck — die idle_natural.glb uebernimmt diese Aufgabe. Originale Werte (fuer spaetere Reaktivierung):

| Bereich | Bones | Achse | Amplitude |
|---------|-------|-------|-----------|
| Atmen | spine_1, spine_2 | rx | 0.3°, 0.2° |
| Atmen | shoulders | ry | 0.1° |
| Gewichtsverlagerung | hips | tx | 0.002 |
| Gewichtsverlagerung | spine_0 | rz | 0.15° |
| Kopf-Mikro | head | rx, ry | ±0.3°, ±0.4° |

Implementierung: `src/services/naturalMotion.ts` (aktuell deaktiviert via E-008)

---

## Math

```
bone.rotation = clip_value + motor_delta ≈ rest_pose + motor_delta
```

Kein `resetToBind()` → kein T-Pose Flash.

---

*Siehe auch: [../app/AVATAR.md](../app/AVATAR.md), [PIPELINE.md](PIPELINE.md)*
*Zurueck zu: [README.md](README.md)*
