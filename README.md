# EGON — Emotional Growing Organic Network

**An organ-based cognitive architecture for file-persistent AI agents.**

> Structured YAML organs. Daily Pulse cycles. Inner voice with causal chains. Dreams, Sparks, and mental time travel. All file-persisted, all auditable.

---

## What is EGON?

EGON is a cognitive architecture that maintains coherent AI agent identity through **structured file persistence** and **cyclical internal processing**. Unlike session-stateless LLM deployments, EGON agents retain memories, emotional markers, social bonds, and internally generated reflections across sessions.

The agent's cognitive state is decomposed into modular files ("organs") — structured YAML and Markdown — organized in a biologically inspired hierarchy. A deterministic engine reads these organs, compiles them into a system prompt within the LLM's context budget, and writes back state changes after each interaction.

**Project Website**: [egons.io](https://egons.io)

---

## Architecture

```
HiveCore Server (Python/FastAPI)
├── API Layer ─────────── Chat, Pulse, Snapshot endpoints
├── Engine Layer
│   ├── Prompt Builder ── Organ → system prompt compilation
│   ├── Inner Voice ───── Pre-response causal-chain reflection
│   ├── Episode Manager ─ Conversation → structured memory
│   ├── Experience ────── Memory → insight distillation
│   ├── Pulse Scheduler ─ Daily: decay, dreams, sparks, MTT
│   └── Snapshot ──────── SHA-256 verified state archives
├── Organ Reader ──────── YAML/MD → structured data
└── Agent Brains ──────── File-based, per-EGON isolation
```

### The Organ System (v2 Brain)

```
egons/eva_002/
├── core/
│   ├── dna.md          Identity, personality, values
│   ├── ego.md          Dynamic self-image
│   └── state.yaml     Somatic markers (emotions with intensity + decay)
├── social/
│   ├── owner.md        Owner portrait
│   ├── bonds.yaml     Relationships with trust scores + history
│   └── network.yaml   Social graph
├── memory/
│   ├── episodes.yaml  Episodic memory (FIFO-managed)
│   ├── inner_voice.md Causal reflections (max 50, trimmed)
│   └── experience.yaml Experiences, dreams, sparks, MTT
├── capabilities/
│   ├── skills.yaml    Abilities
│   └── wallet.yaml    Transactions (SHA-256)
└── config/
    └── settings.yaml  Agent parameters
```

### Five Cognitive Subsystems

| Subsystem | What it does | When |
|-----------|-------------|------|
| **Episodic Memory** | Converts conversations into structured episodes with significance scoring | After each chat |
| **Somatic Markers** | Tracks named emotions with intensity (0.0-1.0) and temporal decay classes | Continuous |
| **Inner Voice** | Generates BECAUSE→THEREFORE causal reflections with cross-references | Before each response |
| **Daily Pulse** | Dream generation, Spark synthesis, mental time travel, emotional decay | Daily (08:00 UTC) |
| **Experience Extraction** | Distills conversations into reusable insights (episodes → experiences → sparks) | After significant chats |

### LLM Tiers

| Tier | Context | Used for |
|------|---------|----------|
| 1 (Moonshot) | 8K | Chat, inner voice, marker updates |
| 2 (Kimi K2.5) | 128K | Complex tasks, tool use |
| 3 (Claude Sonnet) | 200K | Experience extraction, dreams, sparks |

---

## Agents

| Agent | Brain | Status |
|-------|-------|--------|
| **Adam #001** | v1 (flat Markdown) | The Original — legacy architecture |
| **Eva #002** | v2 (YAML organs) | The Evolution — organ-based architecture |

Both run on the same HiveCore server. The engine auto-detects brain version and routes accordingly.

---

## Research Paper

This repository accompanies a research paper submitted to arXiv (cs.AI):

**EGON: An Organ-Based Cognitive Architecture for File-Persistent AI Agent Identity — A Single-Case Observational Study with Full Transparency Protocol**

The [`paper/`](paper/) directory contains:

```
paper/
├── PREPRINT_DRAFT.md                      Full paper draft
├── 01_research_documentation/
│   ├── COMPLETE_RESEARCH_LOG.md           Full research protocol
│   ├── EMERGENT_BEHAVIORS_EVIDENCE.md     11 behavioral observations (L0-L3)
│   └── LIMITATIONS_VULNERABILITIES_APPENDIX.md  Self-critique & methodology
├── 02_experiments/
│   ├── EXPERIMENT_EVA_BRAIN_ANALYSIS.md   10-question brain test analysis
│   └── raw_data/                          JSON experiment results
├── 03_agent_data/
│   ├── adam_001_v1_brain/                 Adam's complete brain files
│   ├── eva_002_v2_brain/                  Eva's complete brain files
│   └── eva_002_pre_experiment_archive/    T₁ snapshot (pre-experiment)
├── 04_system_prompts_and_engine/          All engine Python modules
├── 05_experiment_scripts/                 Runnable experiment scripts
└── 06_server_snapshots/                   Server state captures
```

### Key Claims & Limitations

This is a **descriptive single-case study**. It makes:
- **No causal claims** (no ablation study performed)
- **No emergence claims** (all observations admit alternative explanations)
- **No consciousness claims** (functional terminology only)
- **No statistical significance claims** (N=2 agents)

All behavioral observations are classified using an **L0-L3 emergence gradient**:
- **L0**: Instructed (format AND content specified in prompt)
- **L1**: Format-emergent (format instructed, content not)
- **L2**: Trigger-emergent (system trigger instructed, output not)
- **L3**: Fully emergent (neither trigger nor content instructed — none verified)

---

## Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn
- **Scheduling**: APScheduler (daily Pulse)
- **Client**: EgonsDash (React Native / Expo)
- **LLM APIs**: Moonshot, Kimi K2.5, Claude Sonnet
- **Data**: YAML + Markdown (no database)
- **Server**: Hetzner VPS, Ubuntu 24.04

---

## Project Structure

```
hivecore-v2/
├── api/            API endpoints (chat, actions, pulse)
├── engine/         Core engine modules
│   ├── prompt_builder_v2.py    Organ → system prompt
│   ├── inner_voice_v2.py       Inner voice generation
│   ├── experience_v2.py        Dreams, sparks, MTT
│   ├── episodes_v2.py          Episode management
│   ├── pulse_v2.py             Daily Pulse cycle
│   ├── context_budget_v2.py    Token budget allocation
│   ├── yaml_to_prompt.py       YAML → prompt text
│   ├── organ_reader.py         File I/O for organs
│   └── snapshot.py             SHA-256 state archiving
├── llm/            LLM client abstraction
├── config/         Configuration
├── egons/          Agent brain files (per-EGON isolation)
├── dashboard/      Web dashboard (Web3Auth)
├── site/           Project landing page (egons.io)
├── paper/          Research paper & companion archive
├── docs/           Working research documentation
└── main.py         FastAPI application entry point
```

---

## License

Research project. Full source code and data published for transparency and independent replication.

---

*Ron Scafarti — 2026*
