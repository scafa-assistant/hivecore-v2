# Motor-System — GLB-Clips Referenz

> **Verwandte Dateien:** [VOKABULAR.md](VOKABULAR.md), [../app/AVATAR.md](../app/AVATAR.md)
> **Zuletzt aktualisiert:** 2026-02-26

---

## Aktive Clips in der App

| Clip-Name | Datei | Größe | Verwendung | glb_fallback von |
|-----------|-------|-------|------------|-------------------|
| idle_natural | idle_natural.glb | 8.2 MB | Default-Idle | - |
| look_around | look_around.glb | ~8 MB | Umherschauen | - |
| sleeping | sleeping.glb | ~8 MB | Schlafzustand | schlafen |
| walking_casual | walking_casual.glb | ~8 MB | Fortbewegung | laufen |
| waving_right | waving_right.glb | 8.1 MB | Rechts winken | "winken" |
| waving_left | waving_left.glb | 8.1 MB | Links winken | "winken_links" |
| head_shake | head_shake.glb | ~8 MB | Kopfschütteln | "kopf_schuetteln" |

## Gelöschte Clips (seit v2.3.8)

angry, checkout, confused, dancing, excited, finger_wag, gesture,
hand_on_hip, look_around, pain, phone_action, phone_call, running,
thumbs_up, walking, walking_funny, walking_slow, waving (original)

## Neue Clips hinzufügen

1. GLB nach `C:\DEV\EgonsDash\assets\3d\adam\` kopieren
2. In `avatarState.ts`: ANIMATION_NAMES + ADAM_ANIMATIONS + EVA_ANIMATIONS
3. In `motor_vocabulary.json`: Motor-Wort mit `glb_fallback: "clip_name"`
4. Server deployen (vocabulary) + neue APK bauen (GLB)

## GLB-Quellen

| Quelle | Pfad |
|--------|------|
| Meshy.ai Exporte | `C:\DEV\Avatar-glb\` |
| Git-History | `git show HEAD~N:assets/...` |

---

*Zurück zu: [README.md](README.md)*
