# HiveCore v2 — Server-Architektur

> **Verwandte Dateien:** [ORGANE.md](ORGANE.md), [PROMPT_BUILDER.md](PROMPT_BUILDER.md), [API.md](API.md), [DEPLOY.md](DEPLOY.md)
> **Zuletzt aktualisiert:** 2026-02-26

---

## Überblick

HiveCore v2 ist der Python/FastAPI Server der die EGON-Gehirne verwaltet.
Er lädt die Organe, baut den Prompt, kommuniziert mit dem LLM und
verarbeitet die Antwort (inkl. Motor-System).

## Verzeichnisstruktur (Server)

```
/opt/hivecore-v2/
├── main.py                    ← FastAPI App
├── api/
│   ├── chat.py                ← Chat-Endpunkt
│   └── lobby.py               ← Multi-EGON Lobby
├── engine/
│   ├── prompt_builder_v2.py   ← Prompt aus Organen bauen
│   ├── organ_reader.py        ← Dateien lesen
│   ├── moonshot_chat.py       ← Moonshot/Kimi API Client
│   ├── response_parser.py     ← ###BODY### Block extrahieren
│   ├── motor_translator.py    ← Motor-Wörter → Bone-Rotationen
│   ├── pulse_v2.py            ← Autonomer Pulse-Zyklus
│   ├── circadian.py           ← Tag/Nacht-Zyklus
│   ├── somatic_gate.py        ← Emotionale Bewertung
│   ├── bonds_v2.py            ← Beziehungs-Tracking
│   └── social_mapping.py      ← Soziale Netzwerke
├── config/
│   ├── motor_vocabulary.json  ← 38 Motor-Wörter
│   ├── bone_mapping.json      ← Standard → GLB Bone-Namen
│   ├── bone_constraints.json  ← Gelenkgrenzen
│   └── natural_motion.json    ← Mikrobewegungen (deaktiviert)
└── egons/
    ├── adam_001/
    │   ├── core/
    │   │   ├── dna.md         ← Persönlichkeit (unveränderlich)
    │   │   ├── ego.md         ← Selbstbild
    │   │   ├── body.md        ← Körperbewusstsein + Motor-Wörter
    │   │   └── state.yaml     ← Aktueller Zustand
    │   ├── inner_voice.md     ← Innerer Monolog
    │   ├── experience.md      ← Destillierte Erkenntnisse
    │   ├── memory.md          ← Langzeitgedächtnis
    │   ├── markers.md         ← Somatische Marker
    │   ├── bonds.md           ← Beziehungen
    │   └── ...
    └── eva_002/
        └── (gleiche Struktur)
```

## Neurobiologie-Mapping

| Server-Datei | Gehirn-Äquivalent | Funktion |
|-------------|-------------------|----------|
| core/dna.md | DNA / Genotyp | Unveränderliche Persönlichkeit |
| core/ego.md | Präfrontaler Cortex | Selbstbild, Reflexion |
| core/body.md | Motorischer Cortex | Körperbewusstsein |
| core/state.yaml | Thalamus | Aktueller Zustand |
| inner_voice.md | Phonologische Schleife | Innerer Monolog |
| experience.md | Neocortex | Konsolidierte Erkenntnisse |
| memory.md | Hippocampus → Cortex | Langzeitgedächtnis |
| markers.md | vmPFC / Amygdala | Emotionale Tags |
| bonds.md | Oxytocin-System | Soziale Bindungen |
| motor_vocabulary.json | Motorischer Cortex | Bewegungsvokabular |

Für Details: → [ORGANE.md](ORGANE.md), → [../../research/GEHIRN_MAPPING.md](../research/GEHIRN_MAPPING.md)

---

*Siehe auch: [PROMPT_BUILDER.md](PROMPT_BUILDER.md), [API.md](API.md)*
*Zurück zu: [INDEX.md](../INDEX.md)*
