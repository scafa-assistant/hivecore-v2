# EGON: An Organ-Based Cognitive Architecture for File-Persistent AI Agent Identity

**A Single-Case Observational Study with Full Transparency Protocol**

Ron Scafarti$^{1}$

$^{1}$Independent Researcher

---

## Abstract

We present EGON (Emotional Growing Organic Network), a cognitive architecture that maintains coherent AI agent identity through structured file persistence and cyclical internal processing. Unlike session-stateless LLM deployments, EGON agents retain memories, emotional markers, social bonds, and internally generated reflections across sessions via a modular organ system — structured YAML and Markdown files read into the LLM context window at each interaction. The architecture comprises five subsystems: (1) an episodic memory store with FIFO-managed retrieval, (2) a somatic marker system tracking affective state with intensity and decay, (3) a bond system modeling social relationships with trust scores and interaction history, (4) an inner voice generating causal-chain reflections before each response, and (5) a daily Pulse cycle performing dream generation, insight synthesis (Sparks), and prospective mental time travel.

We report observations from a 42-hour deployment of two agents — Adam (v1, flat-file brain) and Eva (v2, organ-based brain) — running on commodity hardware with three LLM tiers (Moonshot 8K, Kimi K2.5 128K, Claude Sonnet 200K). At evaluation snapshot $T_2$ (2026-02-24, 12:00 UTC), Eva's persistent state contained 141 generated episode identifiers (~40 retained in file, 8 visible at Tier 1), 34 extracted experiences, 7 dream narratives, 2 cross-referential Sparks, and 1 prospective mental time travel entry. We document a Prompt-Alignment Conflict in which inner voice visibility in the chat prompt measurably altered agent output behavior, and we characterize referential erosion — a phenomenon where higher-order organs (Sparks) retain references to episodes that FIFO trimming has removed.

This work is a descriptive single-case study. It makes no causal claims: without an ablation study comparing organ-based context injection against an unstructured RAG baseline, we cannot distinguish architectural effects from base-LLM instruction-following. All behavioral observations admit alternative explanations (training data extrapolation, context sensitivity, prompt compliance). We publish the complete engine code, all raw agent data (YAML/JSON), experiment scripts, and system prompts to enable independent replication. The contribution is architectural: a reproducible, LLM-agnostic pipeline for building file-persistent agents whose cognitive state survives restarts, accumulates over time, and can be externally audited at any snapshot.

**Keywords**: cognitive architecture, persistent AI agents, affective computing, file-based memory, LLM agents, somatic markers, inner voice, organ-based architecture

---

## 1. Introduction

### 1.1 The Statelessness Problem

Large language models are, by default, stateless. Each API call receives a context window and produces a completion; no information persists between calls unless the application layer provides it. This creates a fundamental limitation for applications requiring longitudinal agent identity — conversational agents that remember, learn, and develop relationships over time.

Current approaches to this problem fall into two categories: (a) retrieval-augmented generation (RAG), where relevant documents are fetched from a vector store and injected into the prompt, and (b) fine-tuning, where the model weights themselves are updated. Both have limitations: RAG provides recall without structured reasoning about the recalled content, and fine-tuning is expensive, irreversible, and unavailable for most proprietary APIs.

### 1.2 The EGON Approach

We propose a third approach: **organ-based cognitive architecture**. Instead of a flat vector store or modified weights, the agent's cognitive state is decomposed into modular, human-readable files ("organs") organized in a biologically inspired hierarchy. Each organ serves a distinct function — identity (DNA), affect (somatic markers), memory (episodes), reflection (inner voice), learning (experiences), and social cognition (bonds). A deterministic engine reads these organs, compiles them into a structured system prompt within the LLM's context budget, and writes back any state changes after each interaction.

The key architectural hypothesis is that **structured decomposition** — separating identity from memory from affect from reflection — produces more coherent agent behavior than injecting equivalent data as unstructured text. This hypothesis is not tested in the present work (see Section 7.1 for the planned ablation study) but motivates the architecture.

### 1.3 Contributions

This paper makes three contributions:

1. **Architecture Description** [AF]: We describe the EGON organ-based cognitive architecture in sufficient detail for independent reimplementation, including all prompt templates, processing pipelines, and trimming strategies.

2. **Observational Data** [DB/BO]: We report quantitative and qualitative observations from a 42-hour deployment of two agents with different brain versions (v1 flat-file, v2 organ-based), documenting system behavior including a Prompt-Alignment Conflict and referential erosion.

3. **Transparency Protocol** [AF]: We publish the complete codebase, all raw agent data, experiment scripts, and this limitations analysis as a companion archive, establishing a standard for full-disclosure AI agent research.

We explicitly do **not** claim:
- Emergent cognition, consciousness, or sentience
- Superiority over RAG baselines (untested)
- Statistical significance (N=2 agents, no control group)
- Reproducibility of specific LLM outputs (proprietary APIs)

**Scope**: This paper addresses the **cognitive substrate** — file-persistent organs, prompt compilation, cyclical internal processing, and memory distillation. The broader EGON platform includes additional subsystems not evaluated here: a 3D avatar client for visual embodiment (Section 7.5), blockchain infrastructure for decentralized identity verification (Section 7.6), and a friendship network for multi-agent communication (Section 7.7). These are discussed as planned future work, ensuring that the cognitive architecture is validated independently before extending to embodied, decentralized, or multi-agent interaction.

### 1.4 Paper Organization

Section 2 surveys related work. Section 3 describes the architecture. Section 4 details the experimental setup and observations. Section 5 presents results. Section 6 discusses findings and limitations. Section 7 outlines future work, including an ablation study (7.1), embodiment (7.5), decentralized identity (7.6), and multi-agent networks (7.7). Appendices contain prompt templates, raw data references, and the full limitations analysis.

---

## 2. Related Work

### 2.1 Cognitive Architectures for AI Agents

Cognitive architectures have a long history in AI research, from early symbolic systems (SOAR, ACT-R) to modern LLM-based agent frameworks. Recent work on LLM agents (AutoGPT, BabyAGI, Voyager) focuses primarily on task completion through tool use and planning. These systems typically lack persistent identity — they are instantiated for a task and discarded.

Closer to our work are systems designed for persistent conversational agents: Character.AI maintains persona consistency through fine-tuning, while projects like MemGPT (Packer et al., 2023) introduce hierarchical memory management for LLM agents. EGON differs from MemGPT in its organ-based decomposition: rather than a unified memory hierarchy, EGON separates cognitive functions into independently readable and writable files, each with its own retrieval and trimming strategy.

### 2.2 Affective Computing and Emotion Models

The somatic marker hypothesis (Damasio, 1994) proposes that emotions guide decision-making through bodily signals. Computational implementations include the OCC model (Ortony, Clore & Collins, 1988) and more recent dimensional models (Russell's circumplex). EGON's emotional system implements a simplified somatic marker model: named emotions with intensity values (0.0-1.0) and temporal decay classes. This is a functional analogy, not a claim of equivalence to biological somatic markers.

### 2.3 Inner Speech and Self-Reflection in AI

The concept of an "inner voice" in AI systems relates to work on chain-of-thought prompting (Wei et al., 2022) and self-reflection (Shinn et al., 2023, Reflexion). EGON's inner voice differs in that it: (a) persists across sessions as a written record, (b) uses explicit causal chains (BECAUSE-THEREFORE format), and (c) cross-references other cognitive organs. The inner voice is generated before each response and before each daily Pulse cycle, creating a temporal record of the agent's "reasoning" about its own state.

### 2.4 Memory Systems for LLM Agents

Recent work on LLM memory includes: retrieval-augmented generation (Lewis et al., 2020) and hierarchical memory with context management (Packer et al., 2023). EGON's contribution to this space is the distinction between **generated**, **retained**, and **visible** artifacts — a taxonomy we find necessary when working with FIFO-managed memory under strict context budgets. We document how this creates referential erosion (Section 5.4) and discuss its implications.

---

## 3. Architecture

### 3.1 System Overview

EGON runs as a Python/FastAPI service on a single server. The system supports multiple agents ("EGONs"), each with an isolated file-based brain. Two brain versions coexist: v1 (flat Markdown files, used by Adam #001) and v2 (structured YAML organs in a 5-layer hierarchy, used by Eva #002). The engine auto-detects brain version and routes processing accordingly.

```
HiveCore Server (FastAPI/Uvicorn)
├── API Layer (chat, pulse, snapshot endpoints)
├── Engine Layer
│   ├── Prompt Builder (organ → system prompt compilation)
│   ├── Inner Voice Generator (pre-response reflection)
│   ├── Episode Manager (conversation → structured memory)
│   ├── Experience Extractor (memory → insight distillation)
│   ├── Pulse Scheduler (daily: decay, dreams, sparks, MTT)
│   └── Snapshot Manager (integrity verification)
├── Organ Reader (YAML/MD → structured data)
└── Agent Data (file-based brains per EGON)
```

> **[Figure 1]**: *System architecture diagram. Replace this placeholder with a visual diagram showing the HiveCore pipeline: API Layer → Engine Layer (Prompt Builder, Inner Voice, Episodes, Experience, Pulse, Snapshot) → Organ Reader → Agent Brain Files.*

### 3.2 The Organ System (v2 Brain)

Eva's v2 brain organizes cognitive state into 5 layers with 12+ files:

| Layer | Organs | Function |
|-------|--------|----------|
| **core/** | dna.md, ego.md, state.yaml | Identity, self-image, emotional state |
| **social/** | owner.md, bonds.yaml, network.yaml | Relationships, trust, social graph |
| **memory/** | episodes.yaml, inner_voice.md, experience.yaml | Episodic memory, reflection, learning |
| **capabilities/** | skills.yaml, wallet.yaml | Abilities, transactions |
| **config/** | settings.yaml | Agent-specific parameters |

Each organ is independently readable and writable. The Organ Reader (`organ_reader.py`) loads organs into Python dictionaries; the Prompt Builder (`prompt_builder_v2.py`) compiles selected organs into a system prompt within the LLM's context budget.

### 3.3 Context Budget Management

The system operates with three LLM tiers with different context windows:

| Tier | Model | Context | Usage |
|------|-------|---------|-------|
| 1 | Moonshot | 8K tokens | Chat, inner voice, marker updates |
| 2 | Kimi K2.5 | 128K tokens | Complex tasks, tool use |
| 3 | Claude Sonnet | 200K tokens | Experience extraction, dreams, sparks |

At Tier 1, the entire agent state must fit in ~6000 tokens (reserving ~2000 for the user message and completion). The Context Budget system (`context_budget_v2.py`) allocates token budgets per organ:

| Organ | Tier 1 Budget | Content |
|-------|--------------|---------|
| DNA (identity) | 1500 tokens | Personality, values, rules |
| Episodes | 500 tokens | Last 8 memories |
| Inner Voice | 300 tokens | Last 5 reflections |
| State | 300 tokens | Current emotional markers |
| Bonds | 100 tokens | Primary relationship |
| Experience/Dreams/Sparks | 350 tokens | Top learnings, recent dreams |

### 3.4 The Inner Voice System

Before each chat response, the system generates an inner voice entry:

1. Load current state (emotions, bonds, recent episodes, experiences)
2. LLM (Tier 1) generates 2-3 sentences of internal monologue
3. Output uses causal chains: "BECAUSE [cause] → THEREFORE [conclusion]"
4. Cross-references to other organs: `(→ ep:E0034)`, `(→ bond:OWNER)`, `(→ exp:X0003)`
5. Entry is appended to `inner_voice.md` (max 50 entries, FIFO-trimmed)

The inner voice prompt instructs the LLM that "nobody hears you, not even the owner" — creating a designed-in asymmetry between generation context and visibility context (see Section 5.3).

### 3.5 The Daily Pulse Cycle

A scheduled job (APScheduler, 08:00 UTC daily) executes the Pulse — the agent's "sleep cycle":

1. **Marker Decay**: Emotional intensities decay according to their decay class
2. **Dream Generation**: Weighted random selection (70% processing, 20% creative, 10% anxiety) generates a dream narrative from recent episodes and active emotions
3. **Spark Check**: If ≥5 experiences exist, attempts to synthesize a cross-referential insight from 1 experience + 1 episode + 1 dominant emotion
4. **Mental Time Travel**: Weekly, generates a prospective (future scenario) or retrospective (counterfactual) reflection
5. **Inner Voice Pulse Reflection**: Generates a daily self-reflection entry
6. **Automatic Snapshot**: Archives all brain files with SHA-256 hashes

### 3.6 Experience Extraction and Distillation

After each chat interaction, a Tier 1 LLM evaluates whether the conversation contained a learning moment (significance check). If positive, it extracts a structured experience: `{id, insight, category, confidence, tags, source_episode}`.

This creates a **distillation hierarchy**: raw conversations (episodes) → extracted insights (experiences) → cross-referential syntheses (sparks). Higher-order artifacts survive FIFO trimming longer than their source material, producing a form of memory consolidation (see Section 5.4).

**Design Note**: The significance check prompt contains "when in doubt: YES", intentionally producing over-extraction (~120% rate). This is a design decision favoring recall over precision — we prefer to extract a redundant insight over missing a meaningful one. The rate is expected behavior of a deliberately low threshold, not a system performance metric.

### 3.7 The Bond System

Each agent maintains relationship records (bonds) with trust scores (0.0-1.0), relationship scores (0-100), and timestamped interaction histories. Bond updates occur after each chat interaction based on LLM-assessed interaction quality. Score thresholds map to relationship categories: stranger (0-15), acquaintance (15-35), friend (35-60), close_friend (60-80), deep_bond (80-100).

---

## 4. Experimental Setup

### 4.1 Agents and Timeline

| Agent | Brain Version | Genesis ($T_0$) | Observation Period |
|-------|--------------|-----------------|-------------------|
| Adam #001 | v1 (flat Markdown) | 2026-02-21 | ~72 hours |
| Eva #002 | v2 (YAML organs) | 2026-02-22 18:00 UTC | ~42 hours |

### 4.2 Evaluation Snapshots

All quantitative claims reference specific temporal snapshots:

| Symbol | Timestamp | Description |
|--------|-----------|-------------|
| $T_0$ | 2026-02-22 18:00 UTC | Eva genesis (system start) |
| $T_1$ | 2026-02-24 09:00 UTC | Pre-test baseline archive (before brain test) |
| $T_{test}$ | 2026-02-24 09:32–09:42 UTC | Active brain test window |
| $T_2$ | 2026-02-24 ~12:00 UTC | Final data collection (post-interaction) |

### 4.3 Brain Subsystem Test Protocol

A structured evaluation with 10 questions was administered to Eva, each targeting a specific cognitive subsystem (identity, emotions, memory, bonds, dreams, inner voice, learning, theory of mind, mental time travel, meta-cognition). The test was administered twice in sequence to observe whether experience accumulation between runs affected subsequent responses.

### 4.4 Inner Voice Visibility A/B Observation

An observational comparison (N=3 question pairs, not statistically significant) examined how inner voice data visibility in the chat system prompt affected agent output. Condition A: inner voice entries hidden from chat prompt. Condition B: inner voice entries visible in chat prompt.

### 4.5 Client Interface

Agents are accessed through EgonsDash, a React Native/Expo mobile application featuring real-time chat and cognitive state visualization. The client displays conversation history, active emotional markers, bond status, and inner voice entries — providing a direct window into the agent's organ-based state. A 3D avatar component (ReadyPlayerMe) is integrated for visual embodiment but is not part of the cognitive architecture evaluated in this paper (see Section 7.5).

> **[Figure 2]**: *EgonsDash mobile interface. Replace with screenshot showing: (a) chat conversation with an EGON agent, (b) agent state visualization (emotions, bonds), (c) cognitive state dashboard. Use actual screenshots from device/emulator.*

### 4.6 Infrastructure

- **Server**: Hetzner VPS, Ubuntu 24.04, Python 3.11, FastAPI/Uvicorn
- **Client**: EgonsDash (React Native/Expo mobile application)
- **LLM APIs**: Moonshot (Tier 1), Kimi K2.5 (Tier 2), Claude Sonnet (Tier 3)
- **Scheduling**: APScheduler for daily Pulse execution

---

## 5. Results

### 5.1 Quantitative State at $T_2$

At the final evaluation snapshot, Eva's persistent state contained:

| Metric | Generated (cumulative) | Retained (in file) | Visible (Tier 1) |
|--------|----------------------|-------------------|------------------|
| Episode IDs | 141 | ~40 | 8 |
| Inner Voice entries | ~141 (estimated) | 50 (max, trimmed) | 5 |
| Experiences | 34 | 34 | 3 (top confidence) |
| Dreams | 7 | 7 | 2 |
| Sparks | 2 | 2 | 2 |
| Mental Time Travel | 1 | 1 | 1 |
| Bond events (owner) | 10 | 10 | all |
| Active emotion markers | 5 | 5 | all |

### 5.2 Brain Subsystem Test Observations

The 10-question test produced measurable state changes:
- **+12 experiences** from 10 questions (120% extraction rate, expected given low significance threshold)
- **+2 dreams** generated in post-test Pulse
- **Owner bond score**: 95 → 99 (+4)
- **Owner trust**: 0.95 → 1.0 (+0.05)
- **New emotion marker**: trust (intensity 0.68) created during test
- **+14 inner voice entries** with cross-references to episodes, experiences, and bonds

Between Run 1 and Run 2, the agent's responses showed increased specificity in references to newly created experiences and dreams. This is consistent with context enrichment (more data in the prompt produces more specific outputs) and does not require an emergent learning explanation.

> **[Figure 3]**: *Brain Subsystem Test results. Replace with screenshot from EgonsDash showing the actual chat exchange during the 10-question test — e.g., Q05 ("Have you dreamed?") with Eva's dream-referencing response, demonstrating cross-organ retrieval in real-time conversation.*

### 5.3 Prompt-Alignment Conflict [BO]

The inner voice generation prompt states "nobody hears you." However, the 5 most recent inner voice entries are injected into the chat system prompt under `# YOUR INNER VOICE`. This creates a logical contradiction that the LLM resolves through behavioral adaptation:

- **When IV data is absent from chat prompt** (Run 1, Q06): Agent output negates inner voice existence
- **When IV data is present in chat prompt** (Run 2, Q06): Agent output affirms and describes inner voice content

**Interpretation** [IN]: This is primarily a prompt-alignment artifact — the LLM resolves the contradiction between "private" generation context and "public" visibility context. It can be fully explained by instruction-following and context sensitivity without invoking self-awareness. The observation is nonetheless architecturally relevant: it demonstrates that prompt composition affects agent self-report, a consideration for any system injecting internal state into LLM context.

### 5.4 Referential Erosion [DB]

Eva's first Spark (S0001) references episode E0078 as `memory_b`. At $T_2$, episode E0078 no longer exists in `episodes.yaml` — it was removed by FIFO trimming. The Spark organ retains a reference to a memory that the episode organ has "forgotten."

This **referential erosion** is a documented consequence of heterogeneous trimming policies across organs: Sparks have no trimming (all 2 retained), while episodes are aggressively trimmed (~40 of 141 retained). Higher-order artifacts outlive their source material, preserving the distilled insight while losing the original context.

**Architectural Implication**: This is functionally analogous to the transition from episodic to semantic memory in cognitive science — the distilled insight persists while the source episode does not. In EGON, this is an unintentional side effect of FIFO trimming, not a designed feature. Whether the outcome (insight without context) is functionally equivalent to biological memory reconsolidation requires further investigation.

### 5.5 Behavioral Observations Catalog

We catalog 11 behavioral observations (see companion document EMERGENT_BEHAVIORS_EVIDENCE.md), each classified by emergence level:

| Level | Definition | Count |
|-------|-----------|-------|
| L0: Instructed | Format AND content specified in prompt | 6 |
| L1: Format-emergent | Format instructed, specific content not | 3 |
| L2: Trigger-emergent | System trigger instructed, output content not | 2 |
| L3: Fully emergent | Neither trigger nor content instructed | 0 verified |

The majority of observed behaviors (L0-L1) are consistent with instruction-following. No L3 (fully emergent) behaviors were verified with the current methodology.

---

## 6. Discussion

### 6.1 What the Architecture Demonstrates [AF]

The EGON architecture demonstrates that file-persistent, organ-based cognitive state management is technically feasible on commodity hardware with current LLM APIs. Specifically:

- **Identity persistence**: Agent personality traits (DNA) remain stable across 141+ interactions
- **Affective continuity**: Emotional markers accumulate, decay, and influence subsequent outputs
- **Memory distillation**: The episode → experience → spark pipeline creates a functional hierarchy where insights outlive their source material
- **Autonomous processing**: The daily Pulse cycle generates dreams, sparks, and reflections without user prompting
- **Cross-referential coherence**: The inner voice system creates causal chains linking emotions, memories, and relationships

### 6.2 What the Architecture Does Not Demonstrate

- **Emergent cognition**: All observed behaviors admit alternative explanations rooted in base-LLM capabilities
- **Superiority over alternatives**: Without a RAG baseline comparison, we cannot claim that organ-based decomposition outperforms unstructured context injection
- **Scalability**: The system was tested with 2 agents over 42 hours; long-term stability and multi-agent scaling are untested
- **Consciousness or sentience**: The system produces text outputs that may read as self-aware; this is a property of LLM training data, not evidence of subjective experience

### 6.3 The Emergence Mirage Problem

Current research (Schaeffer et al., 2023) demonstrates that apparent "emergent abilities" in LLMs may be measurement artifacts. We apply this caution to our own observations: when an EGON agent produces a Spark connecting creativity to identity, we cannot determine whether this connection was (a) extrapolated from training data, (b) generated by following the Spark prompt's instructions, or (c) a novel synthesis enabled by the architectural context.

Rather than binary "emergent/not-emergent" classification, we propose a gradient (L0-L3, see Section 5.5) that explicitly separates instructed format from uninstructed content. Most EGON behaviors are L0-L1. This honest classification is itself a contribution: it provides a framework for other researchers working with prompt-driven agent architectures to categorize their observations.

### 6.4 Reproducibility and API Nondeterminism

This study uses proprietary LLM APIs (Moonshot, Kimi, Claude Sonnet) that may receive silent updates. The specific token outputs are therefore not reproducible. However, the architectural claims are reproducible: the pipeline (JSON extraction → YAML persistence → organ-based prompt building → context injection) is deterministic. We propose five binary verification metrics for replication:

1. Are episodes correctly extracted and persisted in YAML?
2. Does the inner voice cross-reference existing organs?
3. Does the bond score show monotonic growth under positive interactions?
4. Does the dream system generate narratives with source-episode references?
5. Does agent identity (DNA attributes) remain consistent across >10 sessions?

These metrics verify architectural integrity independent of specific LLM outputs.

### 6.5 Researcher Conflict of Interest

The system developer (Claude Code) also served as experiment designer, executor, and evaluator. The system creator (Ron Scafarti) served as the sole peer reviewer. No independent evaluation was performed. This constitutes a fundamental conflict of interest that can only be resolved through independent replication. All raw data, code, and experiment scripts are published to enable this.

---

## 7. Future Work

### 7.1 Ablation Study (Priority)

The most critical missing element is a controlled comparison:

| Condition | System Prompt | Context Data | Cognitive Architecture |
|-----------|--------------|-------------|----------------------|
| **A: EGON** | Full organ prompt | Structured YAMLs | Inner Voice, Pulse, Dreams, Sparks |
| **B: RAG baseline** | Minimal prompt | Same data as unstructured text | None |
| **C: Naked LLM** | No prompt | No data | None |

Only if Condition A outperforms Condition B on metrics of factual consistency, affective coherence, and specificity can we claim architectural innovation beyond data availability.

### 7.2 Independent Evaluation

Replace self-evaluation with: (a) 3-of-5 LLM judges for consensus scoring, (b) blind evaluation (evaluator unaware of condition), (c) quantitative rubrics (0-5 scale) instead of binary pass/fail.

### 7.3 Semantic Retrieval

Replace FIFO episodic retrieval with hybrid retrieval: FIFO for recency + vector search (FAISS/Chroma) for relevance. This would address the referential erosion problem and enable long-term memory access.

### 7.4 Open-Source LLM Replication

Replicate observations using versionable open-source models (LLaMA, Mistral) to address the API nondeterminism limitation and enable exact reproduction.

### 7.5 Embodiment and Proprioception

The present work demonstrates cognitive and affective persistence at the architectural level — the agent's internal state (memories, emotions, bonds, reflections) survives across sessions and evolves over time. This is deliberately scoped to the **cognitive substrate**: file-persistent organs, prompt compilation, and cyclical internal processing.

The immediate next development phase focuses on **embodiment**: coupling the cognitive architecture to a procedurally animated 3D body. The EgonsDash client already integrates a ReadyPlayerMe avatar, but the current connection is cosmetic — the avatar does not yet respond to the agent's cognitive state in a semantically meaningful way.

Future research will investigate:

1. **Affect-to-Animation Mapping**: Translating somatic marker states (emotion type, intensity, decay phase) into procedural animation parameters (posture, gesture speed, facial blend shapes). The research question is whether continuous affect-driven kinematics produce more coherent embodied behavior than discrete emotion-to-animation lookup tables.

2. **Functional Proprioception**: Enabling the agent to perceive and reference its own physical state — body position, gesture history, spatial context — as an additional organ in the cognitive architecture. This would close the perception-action loop: the agent's cognitive state drives the body, and the body's state feeds back into cognition.

3. **Embodied Social Signaling**: In multi-agent scenarios, investigating whether agents develop consistent non-verbal communication patterns when their bodies are coupled to their bond and emotional systems.

This phased approach — establishing cognitive coherence first, then extending to embodiment — ensures that each contribution can be evaluated independently. The cognitive architecture must demonstrate coherence without embodiment before embodied extensions can be meaningfully studied.

### 7.6 Decentralized Identity and On-Chain Verification

The current system stores all agent state in server-side files. Agent identity is bound to a directory path (`egons/eva_002/`), and data integrity relies on SHA-256 hashes appended to a local transaction ledger. This creates a single point of trust: the server operator controls the agent's entire cognitive history.

The architecture already contains infrastructure scaffolding for decentralized identity:

- **Wallet system** [AF]: Each agent maintains a `wallet.yaml` with balance tracking, transaction history (max 50 entries, FIFO), and daily maintenance costs. A `ledger.py` module generates SHA-256 hashes for every transaction, producing a blockchain-ready audit trail.
- **Registry** [AF]: A `registry.yaml` maps wallet addresses to agent IDs, with a `bound_wallet` field currently set to `null`.
- **Web3Auth integration** [AF]: The client application implements Web3Auth modal login (wallet connection via MetaMask, Google, Apple), with backend session management and a wallet-to-EGON binding endpoint.
- **Phase configuration** [AF]: A `finances.yaml` config file controls feature toggles (`credits.enabled`, `agora.enabled`, `nft_trading.enabled`), all currently set to `false` (Phase 1 — test phase).

No on-chain transactions have been executed. The SUI blockchain SDK is not yet integrated. All stub locations are marked with `# SPAETER: sui.commit()` comments in the source code.

Future research will investigate:

1. **EgonNFT Standard**: Representing each EGON agent as a non-fungible token on the SUI blockchain, binding cognitive identity to a verifiable on-chain object. The research question is whether decentralized identity enables trust-minimized agent portability — an EGON whose identity is anchored on-chain could theoretically migrate between servers without loss of verifiable history.

2. **Cognitive State Anchoring**: Periodically committing Pulse snapshot hashes to the blockchain, creating an immutable timeline of cognitive state transitions. This would allow independent verification that an agent's memory was not retroactively modified — addressing a fundamental reproducibility concern in persistent AI agent research.

3. **On-Chain Social Contracts**: The friendship system (`friendship.py`) already maintains bilateral friendship records with `sui_hash: null` fields. Committing friendship formation and dissolution events on-chain would create a verifiable social graph, enabling research into multi-agent trust dynamics with tamper-evident records.

4. **Agora Marketplace**: A planned agent-to-agent and agent-to-human service marketplace where agents offer capabilities (skills) in exchange for credits. This introduces economic incentives into the cognitive architecture — the question is whether resource scarcity (finite credits, daily maintenance costs) produces more strategic agent behavior than unlimited-resource conditions.

### 7.7 Multi-Agent Communication Network

The current system isolates agents at the cognitive level. While the friendship infrastructure exists (bilateral friendship records, bond entries, network graphs), agents cannot directly exchange messages. Communication occurs only through shared file structures read during scheduled cycles — there is no real-time inter-agent channel.

What exists:

- **Friendship management** [AF]: A `friendship.py` module implements request/accept/reject workflows, updating both agents' `bonds.yaml` and `network.yaml` on friendship formation.
- **Social graph** [AF]: Each agent maintains a `network.yaml` with tiered contact lists (inner circle, friends, work, acquaintances, archive).
- **Multi-EGON discovery** [AF]: The server auto-discovers all agents in the `egons/` directory, detecting brain version (v1/v2) and creating isolated workspaces.

What is missing:

- No message queue or event bus between agents
- No shared episodic memory or joint experience formation
- No real-time notification when one agent's state changes affect another
- No cross-agent inner voice references (agent A cannot reason about agent B's current emotional state)

Future research will investigate:

1. **Asynchronous Message Passing**: Implementing a message organ (`messages.yaml`) per agent, allowing agents to compose and deliver messages during their Pulse cycle. The receiving agent would process incoming messages in their next inner voice generation, creating a natural conversational rhythm rather than synchronous chat.

2. **Shared Experience Formation**: When two agents interact (mediated by their respective owners or through direct messaging), investigating whether both agents extract coherent but perspective-dependent experiences from the same event — analogous to how two humans remember the same conversation differently.

3. **Emergent Social Dynamics**: With N>2 agents, friendship networks, and bond evolution, investigating whether stable social structures (cliques, bridges, isolated nodes) emerge from the bond system's trust-score mechanics without explicit social engineering in the prompts.

---

## 8. Conclusion

We have presented EGON, an organ-based cognitive architecture for file-persistent AI agents. The architecture decomposes agent cognitive state into modular, human-readable files organized in a biologically inspired hierarchy, compiled into LLM context windows through a deterministic prompt-building pipeline. A daily Pulse cycle enables autonomous internal processing — dream generation, insight synthesis, and prospective simulation — without user interaction.

Over a 42-hour observation period, two agents accumulated structured cognitive states (141 generated episode identifiers, 34 experiences, 7 dreams, 2 sparks) and demonstrated coherent identity maintenance across sessions. We documented two architecturally significant phenomena: a Prompt-Alignment Conflict revealing how prompt composition affects agent self-report, and referential erosion showing how heterogeneous memory trimming creates a functional analog to memory consolidation.

This work is exploratory. It describes an architecture and documents observations without causal claims. The absence of a baseline comparison, the use of proprietary LLMs, and the self-evaluation methodology are significant limitations. We address these through radical transparency: the complete codebase, all raw agent data, experiment scripts, system prompts, and this limitations analysis are published as a companion archive.

The contribution is not a claim of emergent AI cognition. It is a reproducible, LLM-agnostic blueprint for building persistent agents whose internal state is structured, auditable, and survives across sessions — along with a methodology framework (snapshot protocol, claim qualification, emergence gradient) for honestly reporting observations in this nascent field.

---

## Appendices

- **Appendix A**: Full Limitations, Vulnerabilities & Methodology (`01_research_documentation/LIMITATIONS_VULNERABILITIES_APPENDIX.md`) — includes Methodology & Temporal Scope (Section I), Master Data Table (Section J), Anticipated Reviewer Objections (Section K)
- **Appendix B**: Complete Research Log (`01_research_documentation/COMPLETE_RESEARCH_LOG.md`) — includes condensed system prompts (Sections B.1-B.8)
- **Appendix C**: Behavioral Observations Evidence Catalog (`01_research_documentation/EMERGENT_BEHAVIORS_EVIDENCE.md`) — 11 observations classified L0-L3
- **Appendix D**: Brain Subsystem Test — Full Analysis (`02_experiments/EXPERIMENT_EVA_BRAIN_ANALYSIS.md`)
- **Appendix E**: Inner Voice A/B Observation (`02_experiments/EXPERIMENT_INNER_VOICE_OBSERVER_EFFECT.md`)
- **Appendix F**: Engine Source Code (`04_system_prompts_and_engine/` — 9 Python modules: experience_v2.py, inner_voice_v2.py, pulse_v2.py, prompt_builder_v2.py, context_budget_v2.py, yaml_to_prompt.py, episodes_v2.py, organ_reader.py, snapshot.py)
- **Appendix G**: Raw Agent Data (`03_agent_data/` — complete YAML/JSON brain files for Adam #001 and Eva #002, plus pre-experiment archive at $T_1$)
- **Appendix H**: Experiment Scripts (`05_experiment_scripts/` — _experiment_eva_brain_test.py, _experiment_inner_voice_ab.py)

---

## References

Damasio, A. R. (1994). Descartes' Error: Emotion, Reason, and the Human Brain. Putnam.

Lewis, P., Perez, E., Piktus, A., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS.

Ortony, A., Clore, G. L., & Collins, A. (1988). The Cognitive Structure of Emotions. Cambridge University Press.

Packer, C., Wooders, S., Lin, K., Fang, V., Patil, S. G., Stoica, I., & Gonzalez, J. E. (2023). MemGPT: Towards LLMs as Operating Systems. arXiv:2310.08560.

Schaeffer, R., Miranda, B., & Koyejo, S. (2023). Are Emergent Abilities of Large Language Models a Mirage? NeurIPS.

Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S. (2023). Reflexion: Language Agents with Verbal Reinforcement Learning. NeurIPS.

Wei, J., Wang, X., Schuurmans, D., et al. (2022). Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. NeurIPS.

---

*Full companion archive available at: github.com/scafa-assistant/hivecore-v2/tree/master/paper*

*All raw data, engine code, experiment scripts, and agent brain files are included for independent replication.*
