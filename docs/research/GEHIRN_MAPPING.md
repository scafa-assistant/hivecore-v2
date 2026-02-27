# Neurobiologie ↔ EGON Architektur Mapping

> **Zuletzt aktualisiert:** 2026-02-26

---

## Mapping-Tabelle

| Gehirn-Struktur | Funktion | EGON-Entsprechung | Datei |
|----------------|----------|-------------------|-------|
| Hippocampus | Schnelle Kodierung | episodes.yaml | FIFO-Speicher |
| Entorhinaler Cortex | Interface | Prompt Builder | API-Layer |
| Neocortex | Langzeitspeicher | experience.md | Destillierte Erkenntnisse |
| vmPFC | Emotionale Integration | markers.md | Somatische Marker |
| Amygdala | Primäre Emotionen | somatic_gate.py | Emotionaler Filter |
| Broca-Areal | Sprachproduktion | inner_voice.md | Innerer Monolog |
| Motorischer Cortex | Bewegungssteuerung | body.md + motor_vocabulary | Motor-System |
| Cerebellum | Feinmotorik/Skills | skills.yaml | Erlernte Fähigkeiten |
| Thalamus | Aktueller Zustand | state.yaml | Stimmung, Energie |
| Oxytocin-System | Soziale Bindung | bonds.md | Beziehungs-Tracking |

## Drei Empfehlungen aus dem Research Paper

1. **Dekomposition statt Monolithismus** — ✅ Implementiert (Organ-System)
2. **Zyklenbasiertes Processing** — ✅ Implementiert (Pulse-Zyklus)
3. **Relationales Mapping** — ✅ Implementiert (bonds.md, social_mapping)

---

*Zurück zu: [README.md](README.md)*
