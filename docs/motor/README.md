# Motor-System — Überblick

> **Verwandte Dateien:** [ACHSEN.md](ACHSEN.md), [VOKABULAR.md](VOKABULAR.md), [PIPELINE.md](PIPELINE.md), [LAYER_SYSTEM.md](LAYER_SYSTEM.md), [GLB_CLIPS.md](GLB_CLIPS.md)
> **Zuletzt aktualisiert:** 2026-02-26

---

## Was ist das Motor-System?

Das Motor-System gibt EGONs die Fähigkeit ihren 3D-Avatar zu bewegen.
Es ist das Äquivalent zum **motorischen Cortex** im menschlichen Gehirn.

## Drei Bewegungs-Ebenen

| Ebene | Beschreibung | Implementierung | Status |
|-------|-------------|-----------------|--------|
| **Unbewusst** | Atmen, Mikrobewegungen | idle_natural.glb Clip | ✅ Läuft |
| **Halbbewusst** | Gesten passend zur Antwort | LLM waehlt Motor-Wort + ###BODY### | ✅ ~100% (Few-Shot Primer) |
| **Bewusst** | Auf direkten Befehl | User sagt "wink mal" | ✅ Funktioniert |

## Pipeline (End-to-End)

```
User tippt Nachricht
       │
       ▼
  HiveCore Server
  ├── prompt_builder_v2.py lädt body.md
  ├── MOTOR_INSTRUCTION im Prompt
  ├── Moonshot LLM generiert Text + ###BODY### Block
  ├── response_parser.py extrahiert Body-Block
  ├── motor_translator.py → Bone-Rotationen
  └── API Response: { text, bone_update }
       │
       ▼
  EgonsDash App
  ├── ChatScreen.tsx empfängt bone_update
  ├── ChatAvatar.tsx leitet an Renderer
  ├── Prüft glb_fallback → Clip ODER Motor-Pose
  ├── skeletalRenderer.ts wendet Offsets an
  └── Avatar bewegt sich
```

Für Details: → [PIPELINE.md](PIPELINE.md)

## Aktive GLB-Clips

| Clip | Datei | Verwendung |
|------|-------|------------|
| idle_natural | idle_natural.glb | Default-Idle, Atmen |
| look_around | look_around.glb | Umherschauen |
| sleeping | sleeping.glb | Schlafzustand |
| walking_casual | walking_casual.glb | Fortbewegung |
| waving_right | waving_right.glb | Rechts winken |
| waving_left | waving_left.glb | Links winken |
| head_shake | head_shake.glb | Kopfschütteln |

Für Details: → [GLB_CLIPS.md](GLB_CLIPS.md)

## Motor-Vocabulary

Aktuell **38 Motor-Woerter** in `motor_vocabulary.json` (v1.4).
Kategorien: posture, gesture, expression, locomotion.

Für vollständige Liste: → [VOKABULAR.md](VOKABULAR.md)

## Key Files

### Backend (hivecore-v2)

| Datei | Zweck |
|-------|-------|
| `engine/prompt_builder.py` | Brain Version Dispatcher (v1/v2) |
| `engine/prompt_builder_v2.py` | MOTOR_INSTRUCTION Konstante, body.md Loading |
| `api/chat.py` | Few-Shot Primer, bone_update in ChatResponse |
| `config/motor_vocabulary.json` | 38 Motor-Woerter (v1.4), Bone-Rotationen + glb_fallback |
| `engine/response_parser.py` | Parst ###BODY### Blocks aus LLM Response |
| `engine/motor_translator.py` | Uebersetzt Motor-Woerter → Bone-Rotationen |

### App (EgonsDash)

| Datei | Zweck |
|-------|-------|
| `src/components/ChatAvatar.tsx` | 3D Avatar v2.4.3, Layer System, GLB-Fallback |
| `src/services/skeletalRenderer.ts` | Motor Pose Engine, REST_POSE, _postMixerSnapshot |
| `src/services/avatarState.ts` | 7 Animation Clips, GLB Asset requires |
| `src/services/boneMapping.ts` | Standard→GLB Bone Mapping (Spine REVERSED!) |
| `src/services/animationStateMachine.ts` | idle_natural/sleep/activity States |

---

## Bekannte Probleme (Stand 2026-02-26)

| Problem | Status | Details |
|---------|--------|---------|
| Kopf drehen links/rechts | Ungetestet | Motor-Woerter existieren, auf Geraet ungetestet |
| Hit-Rate | ✅ Gefixt | ~100% durch Few-Shot Primer in chat.py |
| Winken links | ✅ Gefixt | GLB-Fallback waving_left.glb |
| hand_heben | ✅ Gefixt | Achsen korrigiert (ry statt rz) |
| Drift-Bug | ✅ Gefixt | Snapshot-basierte Offsets |
| T-Pose Flash | ✅ Gefixt | Mixer laeuft permanent (Layer System) |

---

*Siehe auch: [../app/AVATAR.md](../app/AVATAR.md), [../server/PROMPT_BUILDER.md](../server/PROMPT_BUILDER.md)*
*Zurueck zu: [INDEX.md](../INDEX.md)*
