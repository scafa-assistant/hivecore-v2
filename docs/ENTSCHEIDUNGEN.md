# EGON Projekt — Entscheidungslog

> **Verwandte Dateien:** [TECH_STACK.md](TECH_STACK.md), [INDEX.md](INDEX.md)
> **Zuletzt aktualisiert:** 2026-02-26
> **Regel:** Neue Einträge OBEN hinzufügen (neueste zuerst). Alte NIE löschen.

---

## 2026-02-26

### E-013: ASCII-only Motor-Wort-Namen + Umlaut-Normalisierung als Safety-Net
- **Tags:** `#motor` `#server` `#bugfix`
- **Entscheidung:** Motor-Wort-Namen dürfen NUR ASCII enthalten (ue statt ü, ae statt ä, oe statt ö). Zusätzlich wurde `_normalize_umlauts()` in `motor_translator.py` als Safety-Net eingebaut
- **Grund:** `body.md` nutzte deutsche Umlaute, `motor_vocabulary.json` ASCII-Schreibweise. Exakter String-Lookup in `motor_translator.py` fand keinen Match → 10 von 38 Wörtern wurden stillschweigend ignoriert. Die Normalisierung fängt künftige Fälle ab, auch wenn body.md versehentlich wieder Umlaute enthält
- **Betrifft:** `body.md`, `motor_vocabulary.json`, `motor_translator.py`
- **Siehe:** [BUGS.md](BUGS.md) · BUG-010 · [DONT.md](DONT.md) · DONT-014

### E-012: GLB-Clips statt Motor-Keyframes für komplexe Gesten
- **Tags:** `#motor` `#glb` `#app`
- **Entscheidung:** Komplexe Gesten (Winken, Kopfschütteln) nutzen echte GLB-Animationen als `glb_fallback` statt manuell definierter Motor-Keyframes
- **Grund:** Motor-Keyframes mit manuellen Achsen-Werten sahen unnatürlich aus. GLB-Clips vom gleichen Skelett funktionieren garantiert korrekt
- **Betrifft:** `motor_vocabulary.json`, `avatarState.ts`, `ChatAvatar.tsx`
- **Siehe:** [motor/GLB_CLIPS.md](motor/GLB_CLIPS.md)

### E-011: Layer-System — Mixer läuft IMMER
- **Tags:** `#motor` `#app` `#architektur` `#breaking`
- **Entscheidung:** AnimationMixer läuft permanent (idle_natural als Base), Motor-Posen überschreiben nur betroffene Bones
- **Grund:** Mixer pausieren (timeScale=0) oder Weight-Manipulation führte zu T-Pose Flash und Konflikten
- **Betrifft:** `ChatAvatar.tsx` Render-Loop
- **Siehe:** [motor/LAYER_SYSTEM.md](motor/LAYER_SYSTEM.md)

### E-010: Ruhe-Pose aus Idle-GLB statt manueller Werte
- **Tags:** `#motor` `#achsen`
- **Entscheidung:** REST_POSE wird aus `idle_natural.glb` Keyframes extrahiert, nicht manuell definiert
- **Grund:** Manuelle Werte führten zu Händen im Körper. GLB-Werte sind verifiziert korrekt
- **Betrifft:** `skeletalRenderer.ts`

### E-009: Achsen-Korrektur — ry hebt den Arm, nicht rx
- **Tags:** `#motor` `#achsen` `#breaking`
- **Entscheidung:** Alle Arm-Motor-Wörter korrigiert: `upper_arm` Heben = ry, `lower_arm` Beugen = rz
- **Grund:** GLB-Extraktion zeigte dass die dominante Achse für Arm-Heben ry ist, nicht rx wie angenommen
- **Betrifft:** `motor_vocabulary.json` komplett
- **Siehe:** [motor/ACHSEN.md](motor/ACHSEN.md)

### E-008: Natural Motion deaktiviert, idle_natural GLB stattdessen
- **Tags:** `#motor` `#app`
- **Entscheidung:** `computeNaturalMotion()` gibt `{}` zurück. Mikrobewegungen kommen aus dem idle_natural Clip
- **Grund:** Natural Motion nutzte falsche Achsen und kollidierte mit dem Motor-System
- **Betrifft:** `naturalMotion.ts`, `ChatAvatar.tsx`

### E-007: 17 GLB-Clips gelöscht, 3+2 behalten
- **Tags:** `#app` `#glb` `#performance`
- **Entscheidung:** Nur idle_natural, sleeping, walking_casual, waving_right, waving_left behalten. Rest gelöscht
- **Grund:** APK-Größe (730MB → 245MB), Motor-System übernimmt expressive Gesten
- **Betrifft:** `assets/3d/adam/`, `avatarState.ts`, `animationStateMachine.ts`

### E-006: body.md als 13. Organ
- **Tags:** `#server` `#motor` `#architektur`
- **Entscheidung:** Neues Organ `core/body.md` das Adams Körperbewusstsein beschreibt
- **Grund:** LLM muss wissen dass es einen Körper hat um ###BODY### Blöcke zu generieren
- **Betrifft:** `prompt_builder_v2.py`, `egons/adam_001/core/body.md`

### E-005: deploy.sh excludet egons/ — manuelles Kopieren nötig
- **Tags:** `#server` `#deploy` `#breaking`
- **Entscheidung:** Core-Dateien (dna.md, body.md, ego.md) werden manuell nach /opt/ kopiert
- **Grund:** deploy.sh nutzt rsync --exclude egons/ um persönliche Daten zu schützen
- **Betrifft:** Deploy-Prozess

### E-004: Brain Version v2 (dna.md basiert)
- **Tags:** `#server` `#architektur`
- **Entscheidung:** v2 Brain mit dna.md statt v1 mit soul.md
- **Grund:** v2 unterstützt body.md, Motor-System, erweiterte Prompt-Pipeline
- **Betrifft:** `prompt_builder_v2.py`, `_detect_brain_version()`

### E-003: Moonshot als LLM für Adam
- **Tags:** `#server` `#llm`
- **Entscheidung:** Moonshot/Kimi API als primäres LLM
- **Betrifft:** `api/chat.py`, `engine/moonshot_chat.py`

### E-002: YAML + MD als Speicherformat
- **Tags:** `#server` `#architektur`
- **Entscheidung:** Organe in Markdown, State in YAML
- **Grund:** Menschenlesbar, versionierbar, LLM-freundlich

### E-001: Organ-basierte Dekomposition
- **Tags:** `#server` `#architektur`
- **Entscheidung:** EGON-Identität in separate "Organe" aufteilen (DNA, Ego, Memory, etc.)
- **Grund:** Biologische Analogie, modulare Wartbarkeit, Token-Budget-Management
- **Siehe:** [server/ORGANE.md](server/ORGANE.md)

---

*Siehe auch: [TECH_STACK.md](TECH_STACK.md), [server/README.md](server/README.md)*
*Zurück zu: [CLAUDE.md](../CLAUDE.md)*
