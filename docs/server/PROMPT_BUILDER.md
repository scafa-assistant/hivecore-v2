# Prompt Builder Pipeline

> **Zuletzt aktualisiert:** 2026-02-26
> **Verwandte Dateien:** [motor/PIPELINE.md](../motor/PIPELINE.md) · [ENTSCHEIDUNGEN.md](../ENTSCHEIDUNGEN.md)

---

## Brain Version Detection

`engine/prompt_builder.py` entscheidet welches Brain geladen wird:

```
Existiert egons/{id}/core/dna.md?
  JA  → v2 Brain → prompt_builder_v2.py → LÄDT body.md + MOTOR_INSTRUCTION
  NEIN → v1 Brain → prompt_builder.py (legacy) → KEIN body.md!
```

**KRITISCH:** Ohne `dna.md` auf dem Runtime-Pfad (`/opt/hivecore-v2/egons/adam_001/core/`) wird das v1-Brain geladen. Das v1-Brain kennt KEIN body.md und generiert KEINEN ###BODY### Block.

## Prompt-Aufbau (v2 Brain)

```
1. System-Prompt:
   - dna.md (Persönlichkeit, Identität) — KEIN Budget-Limit
   - ego.md (Selbstbild) — KEIN Budget-Limit
   - body.md (Motor-Instruktionen) — KEIN Budget-Limit
   - MOTOR_INSTRUCTION (Konstante in prompt_builder_v2.py)
   - Organe (soul, memory, markers, bonds, etc.) — mit Token-Budget

2. Chat-History (letzte N Messages)

3. Few-Shot Primer (wenn History LEER):
   - Injiziert ein Beispiel-Paar in chat.py
   - User: "Hallo, wie geht es dir?"
   - Assistant: "[Antwort mit ###BODY### Block]"
   - Zweck: Zeigt Moonshot das erwartete Format
   - Hit-Rate: von ~50% auf ~100% gestiegen
```

## MOTOR_INSTRUCTION (Konstante)

Definiert in `engine/prompt_builder_v2.py`. Erklärt dem LLM:
- Dass es ###BODY### Blöcke generieren MUSS
- Format: `###BODY###{"words":["wort1","wort2"],"intensity":0.7}###END_BODY###`
- Welche Wörter verfügbar sind (aus motor_vocabulary.json)
- Wann welche Gesten passend sind

## Few-Shot Primer

**Location:** `api/chat.py` → `inject_few_shot_primer()`

**Wann:** Nur bei leerer Chat-History (erste Nachricht eines Gesprächs)

**Warum nötig:** Moonshot folgt Format-Instruktionen aus dem System-Prompt nur ~50% der Zeit. Ein konkretes Beispiel-Paar steigert die Compliance auf ~100%.

**Ablauf:**
1. User sendet erste Nachricht
2. chat.py prüft: History leer?
3. JA → injiziert Example-Pair VOR der User-Message
4. Moonshot sieht das Beispiel und reproduziert das Format

---

*Zurück zu: [INDEX.md](../INDEX.md)*
