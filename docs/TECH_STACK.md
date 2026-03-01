# EGON Projekt — Tech Stack

> **Verwandte Dateien:** [ENTSCHEIDUNGEN.md](ENTSCHEIDUNGEN.md), [INDEX.md](INDEX.md)
> **Zuletzt aktualisiert:** 2026-02-26

---

## Server (HiveCore v2)

| Komponente | Technologie | Version | Notizen |
|-----------|-------------|---------|---------|
| Runtime | Python | 3.11+ | Auf Hetzner VPS |
| Framework | FastAPI | - | REST API |
| LLM | Moonshot (Kimi) | - | Hit-Rate ~80% für ###BODY### |
| Datenformat | MD + YAML | - | Organe: .md, State: .yaml |
| Hosting | Hetzner VPS | Ubuntu 24.04 | 159.69.157.42 |
| Service | systemd | - | `hivecore` Unit |
| SSH | Port 443 | - | Port 22 oft blockiert |
| Repo | GitHub | - | scafa-assistant/hivecore-v2 |

## App (EgonsDash)

| Komponente | Technologie | Version | Notizen |
|-----------|-------------|---------|---------|
| Framework | React Native + Expo | - | TypeScript |
| 3D Rendering | Three.js (expo-three) | - | GLTFLoader für GLBs |
| 3D Format | GLB | - | Von Meshy.ai generiert |
| Build | Gradle (Android) | 8.14.3 | `assembleRelease` |
| State | React Hooks | - | useState, useRef, useEffect |
| API Client | fetch | - | REST zu HiveCore |
| Ziel-OS | Android | 8-16 | Hauptziel: Android 15 |

## Motor-System

| Komponente | Technologie | Datei | Notizen |
|-----------|-------------|-------|---------|
| Vocabulary | JSON | motor_vocabulary.json | 38 Wörter (v1.3) |
| Bone-Mapping | JSON | bone_mapping.json | Standard → GLB Namen |
| Constraints | JSON | bone_constraints.json | Gelenkgrenzen |
| Natural Motion | JSON | natural_motion.json | AKTUELL DEAKTIVIERT |
| Skeleton | JSON | skeleton_standard.json | 22 Standard-Bones |
| GLB-Clips | GLB | assets/3d/adam/*.glb | idle_natural, waving_right, etc. |

## 3D Assets

| Quelle | Typ | Notizen |
|--------|-----|---------|
| Meshy.ai | GLB Export | Biped-Skelett, ~8-15 MB pro Animation |
| Blender | GLB Nachbearbeitung | Für Decimation/Optimierung |

## Externe Dienste

| Dienst | Zweck | Notizen |
|--------|-------|---------|
| Moonshot/Kimi | LLM für Adam/Eva | Chinesischer Anbieter, gute Qualität |
| Meshy.ai | 3D-Modell + Animation Generierung | GLB-Export |
| GitHub | Code-Repository | Zwei Repos: EgonsDash + hivecore-v2 |
| Hetzner | Server-Hosting | VPS in Deutschland |

---

*Siehe auch: [ENTSCHEIDUNGEN.md](ENTSCHEIDUNGEN.md), [server/README.md](server/README.md), [app/README.md](app/README.md)*
*Zurück zu: [CLAUDE.md](../CLAUDE.md)*
