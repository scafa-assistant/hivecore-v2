# EgonsDash — App-Architektur

> **Verwandte Dateien:** [AVATAR.md](AVATAR.md), [BUILD.md](BUILD.md), [CHANGELOG.md](CHANGELOG.md)
> **Zuletzt aktualisiert:** 2026-02-26

---

## Überblick

EgonsDash ist die React Native/Expo App die den Chat und 3D-Avatar zeigt.
Sie kommuniziert mit HiveCore v2 per REST API.

## Wichtige Dateien

| Datei | Funktion |
|-------|----------|
| `src/screens/ChatScreen.tsx` | Chat-UI, empfängt bone_update |
| `src/components/ChatAvatar.tsx` | 3D Avatar, Render-Loop, Mixer |
| `src/services/skeletalRenderer.ts` | Motor-Pose Engine |
| `src/services/boneMapping.ts` | Standard → GLB Bone-Mapping |
| `src/services/naturalMotion.ts` | Mikrobewegungen (DEAKTIVIERT) |
| `src/services/animationStateMachine.ts` | Emotion → Clip Mapping |
| `src/services/avatarState.ts` | Animation-Namen, Asset-Pfade |
| `src/services/api.ts` | REST Client zu HiveCore |

## Render-Loop (ChatAvatar.tsx)

```
Jeden Frame:
  1. mixer.update(delta)         ← idle_natural Clip setzt alle Bones
  2. clipInfluencing = true
  3. updateMotor(elapsed, delta, clipInfluencing)
     └── Snapshot Mixer-Werte
     └── Motor-Deltas NUR auf betroffene Bones addieren
  4. renderer.render(scene, camera)
```

Für Details: → [AVATAR.md](AVATAR.md), → [../motor/LAYER_SYSTEM.md](../motor/LAYER_SYSTEM.md)

## Aktive GLB-Clips (Stand 2026-02-26)

| Clip | Datei | Größe |
|------|-------|-------|
| idle_natural | idle_natural.glb | 8.2 MB |
| sleeping | sleeping.glb | ~8 MB |
| walking_casual | walking_casual.glb | ~8 MB |
| waving_right | waving_right.glb | 8.1 MB |
| waving_left | waving_left.glb | 8.1 MB |
| head_shake | head_shake.glb | ~8 MB |

## APK-Build

Siehe → [BUILD.md](BUILD.md)

Aktuelle Version: **v2.3.8-LAYER** (245 MB)

---

*Siehe auch: [AVATAR.md](AVATAR.md), [../motor/README.md](../motor/README.md)*
*Zurück zu: [INDEX.md](../INDEX.md)*
