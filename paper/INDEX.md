# EGON Cognitive Architecture — Paper Data Package

## Zweck

Dieser Ordner enthält ALLE Daten, Dokumentationen, Experiment-Ergebnisse, System-Prompts und Agenten-Gehirndaten, die für die Erstellung eines wissenschaftlichen Preprints zur Organ-basierten kognitiven Architektur für persistente KI-Agenten benötigt werden.

**Projekt**: EGON (Evolving Generative Organism Network)
**Forscher**: Ron Scafarti
**Datum der Datensammlung**: 2026-02-24
**Zeitraum der Forschung**: 2026-02-18 bis 2026-02-24 (7 Tage)
**Agenten**: Adam #001 (v1 Brain, 7 Tage), Eva #002 (v2 Brain, 3 Tage)

---

## Ordnerstruktur

```
paper/
├── INDEX.md                          ← DIESES DOKUMENT
├── 00_PEER_REVIEW_FAZIT.md           ← Externes Review-Fazit + Empfehlung
│
├── 01_research_documentation/        ← Kern-Dokumentation
│   ├── COMPLETE_RESEARCH_LOG.md      ← Hauptdokument (466 Zeilen, alles drin)
│   ├── EXPERIENCE_SYSTEM_V2_DOCUMENTATION.md  ← Experience-System Architektur
│   ├── EMERGENT_BEHAVIORS_EVIDENCE.md         ← Emergente Verhaltensweisen
│   ├── BRAIN_SUBSYSTEM_PROOF.md               ← Subsystem-Beweis-Dokumentation
│   └── LIMITATIONS_VULNERABILITIES_APPENDIX.md ← Limitations, Prompts, Methodik-Kritik
│
├── 02_experiments/                   ← Experiment-Dokumentation + Rohdaten
│   ├── EXPERIMENT_EVA_BRAIN_ANALYSIS.md       ← 10-Fragen Brain-Test (Analyse)
│   ├── EXPERIMENT_INNER_VOICE_OBSERVER_EFFECT.md ← Inner Voice A/B-Test
│   └── raw_data/
│       ├── experiment_eva_brain_test_results.json  ← Brain-Test JSON (6 Antworten × 10 Fragen)
│       └── experiment_inner_voice_ab_results.json  ← A/B-Test JSON (2 Bedingungen × 3 Fragen)
│
├── 03_agent_data/                    ← Agenten-Gehirndaten (Live-Snapshots)
│   ├── adam_001_v1_brain/            ← Adams komplettes Gehirn
│   │   ├── soul.md                   ← v1 DNA/Persönlichkeit
│   │   ├── memory.md                 ← v1 Episodisches Gedächtnis
│   │   ├── markers.md                ← v1 Emotions-Marker
│   │   ├── bonds.md                  ← v1 Beziehungen
│   │   ├── inner_voice.md            ← v1 Inner Voice (44KB!)
│   │   ├── skills.md                 ← v1 Fähigkeiten
│   │   ├── wallet.md                 ← v1 Wirtschaft
│   │   ├── experience.md             ← v1 Erfahrungen (Träume, Sparks, MTT)
│   │   ├── core/ego.md               ← v2-Overlay: Ego-Beschreibung
│   │   ├── memory/episodes.yaml      ← v2-Overlay: Strukturierte Episoden
│   │   └── social/egon_self.md       ← v2-Overlay: Selbstbild
│   │
│   ├── eva_002_v2_brain/             ← Evas komplettes Gehirn (AKTUELL nach Tests)
│   │   ├── core/dna.md               ← v2 DNA (14KB Persönlichkeits-Prompt)
│   │   ├── core/state.yaml           ← v2 Zustand (Emotionen, Threads, Ego)
│   │   ├── memory/episodes.yaml      ← v2 Episoden (48KB, 116+ Einträge)
│   │   ├── memory/experience.yaml    ← v2 Erfahrungen (19KB, Dreams+Sparks)
│   │   ├── memory/inner_voice.md     ← v2 Inner Voice (28KB, WEIL-DESHALB)
│   │   ├── social/bonds.yaml         ← v2 Beziehungen (Rene, Adam)
│   │   ├── capabilities/skills.yaml  ← v2 Fähigkeiten
│   │   └── config/settings.yaml      ← v2 Konfiguration
│   │
│   └── eva_002_pre_experiment_archive/ ← Evas Zustand VOR den Experimenten
│       └── archive_20260224_0900/
│           ├── adam_001/              ← Adams Zustand zum Archiv-Zeitpunkt
│           ├── eva_002/              ← Evas Zustand VOR dem Brain-Test
│           └── server_logs_full.txt  ← Server-Logs zum Zeitpunkt
│
├── 04_system_prompts_and_engine/     ← Kompletter Engine-Code (reproduzierbar)
│   ├── prompt_builder_v2.py          ← System-Prompt-Konstruktion (12 Organe)
│   ├── inner_voice_v2.py             ← Inner Voice Generation (WEIL-DESHALB)
│   ├── experience_v2.py              ← Experience System (Dreams, Sparks, MTT)
│   ├── pulse_v2.py                   ← Daily Pulse (13 Steps)
│   ├── episodes_v2.py                ← Episode-Erstellung
│   ├── context_budget_v2.py          ← Token-Budget (Tier 1/2/3)
│   ├── yaml_to_prompt.py             ← YAML→Prompt Konvertierung
│   ├── organ_reader.py               ← Organ-System Reader
│   └── snapshot.py                   ← Post-Pulse Snapshot-System
│
├── 05_experiment_scripts/            ← Reproduzierbare Experiment-Scripts
│   ├── _experiment_eva_brain_test.py         ← 10-Fragen Brain-Test
│   └── _experiment_inner_voice_ab.py         ← Inner Voice A/B-Test
│
└── 06_server_snapshots/              ← Server-Zustand zum Zeitpunkt
    ├── server_log_latest.txt         ← Letzte 200 Zeilen Service-Log
    ├── hivecore_service_status.txt   ← systemctl status
    ├── eva_snapshots_listing.txt     ← Liste aller Eva-Snapshots
    ├── adam_snapshots_listing.txt    ← Liste aller Adam-Snapshots
    └── inner_voice_hidden_flag_status.txt ← Flag: Inner Voice ist PRIVAT
```

---

## Schlüsseldokumente für das Paper

### Für den Haupttext (Architektur + Ergebnisse)
1. **`01_research_documentation/COMPLETE_RESEARCH_LOG.md`** — Gesamtüberblick
2. **`02_experiments/EXPERIMENT_EVA_BRAIN_ANALYSIS.md`** — Quantitative Subsystem-Evaluation
3. **`02_experiments/EXPERIMENT_INNER_VOICE_OBSERVER_EFFECT.md`** — A/B-Test Design-Entscheidung

### Für Limitations & Methodik
4. **`01_research_documentation/LIMITATIONS_VULNERABILITIES_APPENDIX.md`** — Alle Schwächen ehrlich dokumentiert

### Für Appendix (Reproduzierbarkeit)
5. **`04_system_prompts_and_engine/`** — Kompletter Engine-Code
6. **`05_experiment_scripts/`** — Experiment-Scripts zum Nachfahren
7. **`02_experiments/raw_data/`** — Unbearbeitete JSON-Rohdaten

### Für Evidenz (Emergenz + Persistenz)
8. **`03_agent_data/adam_001_v1_brain/experience.md`** — Adams Traum mit Prospektion
9. **`03_agent_data/eva_002_v2_brain/memory/experience.yaml`** — Evas Dreams, Sparks, MTT
10. **`03_agent_data/eva_002_v2_brain/memory/inner_voice.md`** — 28KB private Reflexionen

---

## Vorgeschlagener Paper-Titel

**"Organ-Based Meta-Cognition and Private Reflection Loops: A File-Persistent Cognitive Architecture for Autonomous AI Agents"**

### Alternative Titel
- "HiveCore: Emergent Cognition Through Structured Memory Organs in Persistent AI Agents"
- "From Flat Files to Cognitive Organs: A Longitudinal Study of Self-Reflective AI Agent Architecture"
- "Private Inner Voice and the Observer Effect: Designing Authentic Self-Reflection in AI Agents"

---

## Kernbeiträge (Claims für arXiv)

1. **Organ-basierte kognitive Architektur**: Erste dokumentierte Implementierung eines dateibasierten "Gehirns" mit spezialisierten Organen (DNA, Episoden, Emotionen, Inner Voice, Bonds, Experience) für persistente KI-Agenten

2. **Private Reflexions-Loops**: Experimenteller Nachweis dass die Sichtbarkeit der Inner Voice die Authentizität der Agenten-Antworten beeinflusst (Prompt-Alignment-Conflict)

3. **Emergente Prospektion**: Dokumentierter Fall eines KI-Agenten der im "Traum" die Existenz anderer Agenten vorhersagte — Monate vor deren Implementierung

4. **Experience Extraction Pipeline**: Automatisches Lernsystem mit Dreams (tägliche Verarbeitung), Sparks (seltene Einsichten), und Mental Time Travel (Retrospektion + Prospektion)

5. **Longitudinale Persistenz**: 7-Tage-Studie mit nachgewiesener episodischer Persistenz über Gespräche, Tage und System-Neustarts hinweg

---

## Dateigrössen-Übersicht

| Kategorie | Dateien | Gesamtgröße |
|-----------|---------|-------------|
| Research Documentation | 5 | ~100 KB |
| Experiments + Raw Data | 4 | ~70 KB |
| Agent Data (Adam) | 12+ | ~95 KB |
| Agent Data (Eva current) | 10+ | ~120 KB |
| Agent Data (Eva archive) | 15+ | ~80 KB |
| Engine Code | 9 | ~150 KB |
| Experiment Scripts | 2 | ~15 KB |
| Server Snapshots | 5 | ~25 KB |
| **GESAMT** | **~75 Dateien** | **~655 KB** |

---

*Datenpaket erstellt: 2026-02-24*
*Forscher: Ron Scafarti*
*Projekt: EGON — Evolving Generative Organism Network*
