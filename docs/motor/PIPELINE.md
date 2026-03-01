# Motor-System — Pipeline (End-to-End)

> **Verwandte Dateien:** [README.md](README.md), [LAYER_SYSTEM.md](LAYER_SYSTEM.md), [../server/PROMPT_BUILDER.md](../server/PROMPT_BUILDER.md)
> **Zuletzt aktualisiert:** 2026-02-26

---

## Datenfluss

```
1. USER TIPPT NACHRICHT
   │
   ▼
2. HIVECORE SERVER
   ├── prompt_builder_v2.py
   │   ├── Lädt body.md (Organ)
   │   └── Hängt MOTOR_INSTRUCTION an
   ├── Moonshot LLM generiert:
   │   ├── Text-Antwort
   │   └── ###BODY###{"words":["winken"],"intensity":0.8}###END_BODY###
   ├── response_parser.py extrahiert Body-Block
   ├── motor_translator.py
   │   ├── Liest motor_vocabulary.json
   │   ├── Wendet intensity Skalierung an
   │   └── Gibt Bone-Rotationen zurück
   └── API Response: { text, bone_update }
   │
   ▼
3. EGONSDASH APP
   ├── ChatScreen.tsx empfängt bone_update
   ├── setLatestBoneUpdate(bone_update)
   ├── ChatAvatar.tsx useEffect → boneUpdate
   │   ├── Prüft glb_fallback
   │   │   ├── JA → switchAnimation(fallback)
   │   │   └── NEIN → applyBoneUpdate(boneUpdate)
   └── skeletalRenderer.ts
       ├── _postMixerSnapshot() → cached Clip-Werte
       ├── _computeMotorPose() → berechnet Offsets
       └── _applyOffsets() → setzt Bone-Rotationen
```

## bone_update Format (API → App)

```json
{
  "words": ["nicken", "kopf_neigen"],
  "intensity": 0.7,
  "reason": "Zeige Interesse",
  "animations": [
    {
      "word": "nicken",
      "type": "sequence",
      "duration_ms": 600,
      "easing": "ease_in_out",
      "loopable": false,
      "blendable": true,
      "glb_fallback": null,
      "keyframes": [{"t": 0, "bones": {...}}, {"t": 0.5, "bones": {...}}]
    }
  ]
}
```

---

## Fehlerquellen

| Stelle | Symptom | Ursache |
|--------|---------|---------|
| Schritt 2 | bone_update = null | Moonshot generiert keinen ###BODY### Block |
| Schritt 2 | body.md nicht geladen | dna.md fehlt → Brain v1 → kein body.md |
| Schritt 3 | Keine Bewegung | GLB-Fallback Clip nicht geladen |
| Schritt 3 | Wilde Rotation | Falsche Achsen in motor_vocabulary.json |
| Schritt 3 | Drift | Bones nicht zurückgesetzt nach Motor-Ende |

---

*Zurück zu: [README.md](README.md)*
