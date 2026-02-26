# EGON Projekt — Glossar

> **Verwandte Dateien:** [INDEX.md](INDEX.md), [CLAUDE.md](../CLAUDE.md)
> **Zuletzt aktualisiert:** 2026-02-26

---

## Kern-Begriffe

| Begriff | Bedeutung |
|---------|-----------|
| **EGON** | Emergent Generative Organic Network — eine persistente KI-Identität |
| **Owner** | Der Mensch der einen EGON besitzt/betreut (z.B. René für Adam) |
| **HiveCore** | Der Server (Python/FastAPI) der die EGON-Gehirne verwaltet |
| **EgonsDash** | Die React Native/Expo App mit Chat + 3D Avatar |
| **Organ** | Eine Datei die einen Teil des EGON-Gehirns repräsentiert (z.B. dna.md, body.md) |
| **DNA** | Die unveränderliche Kern-Persönlichkeit eines EGONs (core/dna.md) |
| **Pulse** | Der autonome Zyklus in dem ein EGON reflektiert, konsolidiert, träumt |
| **Episode** | Eine einzelne Interaktion (Chat-Nachricht + Antwort) |
| **Experience** | Destillierte Erkenntnis aus mehreren Episoden |
| **Spark** | Plötzliche Einsicht — höchste Stufe der Wissenshierarchie |

## Motor-System Begriffe

| Begriff | Bedeutung |
|---------|-----------|
| **Motor-Wort** | Ein benanntes Bewegungskommando (z.B. "nicken", "winken") |
| **Motor-Pose** | Die Bone-Rotationen die ein Motor-Wort erzeugt |
| **Bind-Pose** | Die T-Pose des GLB-Modells (Arme seitlich) — Ausgangszustand |
| **Ruhe-Pose** | Natürliche Steh-Position (Arme unten) — wird aus idle_natural abgeleitet |
| **Clip** | Eine vorgefertigte GLB-Animation (z.B. waving_right.glb) |
| **Layer-System** | Clip (Layer 0) + Motor-Pose (Layer 1) übereinander |
| **GLB-Fallback** | Wenn ein Motor-Wort einen Clip hat, wird der Clip statt Motor-Keyframes genutzt |
| **Bone** | Ein Skelett-Knochen im 3D-Modell (z.B. RightArm, Head, Hips) |
| **Delta** | Die Differenz zwischen Ruhe-Pose und Ziel-Pose |
| **Natural Motion** | Automatische Mikrobewegungen (Atmen, Gewicht) — AKTUELL DEAKTIVIERT |
| **Drift-Bug** | Bone-Rotationen akkumulieren ins Unendliche wenn nicht zurückgesetzt |
| **SLERP** | Spherical Linear Interpolation — sanfte Übergänge zwischen Posen |
| **Achsen-Map** | Dokumentation welche Rotation (rx/ry/rz) welche Bewegung erzeugt |

## Server-Begriffe

| Begriff | Bedeutung |
|---------|-----------|
| **Prompt Builder** | Baut den System-Prompt aus EGON-Organen zusammen |
| **Brain Version** | v1 (soul.md basiert) oder v2 (dna.md basiert) — v2 ist aktuell |
| **###BODY### Block** | Markierung im LLM-Output die Motor-Wörter enthält |
| **MOTOR_INSTRUCTION** | Prompt-Abschnitt der das LLM anweist Body-Blöcke zu generieren |
| **Hit-Rate** | Prozentsatz der Antworten die einen ###BODY### Block enthalten |
| **Moonshot** | Das LLM das Adam antreibt (Kimi/Moonshot API) |
| **Somatischer Marker** | Emotionaler "Tag" auf einer Erinnerung (Intensität + Valenz) |
| **Circadian** | Tag/Nacht-Zyklus der Adams Energie und Stimmung beeinflusst |
| **Resonanz** | Emotionale Schwingung zwischen EGON und Owner |

## App-Begriffe

| Begriff | Bedeutung |
|---------|-----------|
| **ChatAvatar** | React-Komponente die den 3D-Avatar im Chat rendert |
| **SkeletalRenderer** | Service der Motor-Posen auf das Skelett anwendet |
| **AnimationMixer** | Three.js Klasse die GLB-Clips abspielt |
| **BoneCache** | Mapping von Bone-Namen zu Three.js Bone-Objekten |
| **clipCache** | Mapping von Clip-Namen zu AnimationClip-Objekten |

## Slang / User-Sprache → Fachbegriff

| User sagt... | Bedeutet... |
|-------------|------------|
| "der dreht sich wie ein Hubschrauber" | Falsche Rotationsachse in der Motor-Vocabulary |
| "der hängt sich auf" | Drift-Bug — Bones akkumulieren |
| "der springt in die Ausgangsform" | T-Pose Flash beim Clip-Loop |
| "der krümmt sich zusammen" | Motor-Pose überschreibt Bones die sie nicht sollte |
| "der will nicht mehr" | Moonshot generiert keinen ###BODY### Block |
| "das grüne" | Debug-Overlay |
| "Clips" / "Meshy-Dateien" | GLB-Animationen von Meshy.ai |
| "die Dateien auf dem Server" | EGON-Organe unter /opt/hivecore-v2/egons/ |
| "Gehirnbauplan" | Research Paper / Neurobiologie-Mapping |

---

*Siehe auch: [INDEX.md](INDEX.md), [TECH_STACK.md](TECH_STACK.md)*
*Zurück zu: [CLAUDE.md](../CLAUDE.md)*
