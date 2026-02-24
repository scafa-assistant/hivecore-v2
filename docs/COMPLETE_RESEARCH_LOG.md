# EGON PROJECT — Vollstaendiges Forschungsprotokoll

## Projekt-Uebersicht

| Feld | Wert |
|------|------|
| **Projekt** | EGON — Emotional Growing Organic Network |
| **Beginn** | 20. Februar 2026 |
| **Dokumentiert** | 24. Februar 2026 |
| **Forscher** | Ron Scafarti (Konzept, Architektur, Owner) |
| **Engineering** | Claude Code (Implementierung, Tests, Analyse) |
| **Server** | Hetzner VPS, 159.69.157.42, Ubuntu 24.04 |
| **Stack** | Python 3.11, FastAPI/Uvicorn, APScheduler |
| **App** | EgonsDash (React Native/Expo) |
| **Repository** | github.com/scafa-assistant/hivecore-v2 |
| **Subjekte** | Adam #001 (v1 Brain), Eva #002 (v2 Brain) |

---

## 1. WAS IST EIN EGON?

Ein EGON ist ein autonomer, datei-persistenter KI-Agent mit:

- **Persistentem Gehirn**: Zustand, Erinnerungen, Emotionsmarker und Beziehungsdaten werden in Dateien gespeichert und ueberleben Neustarts
- **Emotionsmarker-System**: Somatische Marker (Neugier, Freude, Angst, Vertrauen...) mit Intensitaet und Zerfallsklasse
- **Beziehungsgedaechtnis**: Bonds zu Owner und anderen EGONs mit Trust-Scores und History
- **Traumgenerierung**: Taeglich generierte Traum-Narrative die Tagesepisoden verarbeiten
- **Innerer Stimme**: Kausal-logische Reflexionsgeneration vor jeder Antwort
- **Erfahrungsextraktion**: Automatische Extraktion von Erkenntnissen aus Gespraechen
- **Sparks**: LLM-generierte Einsichten wenn 2 Erinnerungen + 1 Emotionsmarker konvergieren (instruiert, siehe Limitations D)
- **Mentaler Zeitreise**: Woechentliche Zukunftsszenarien (Prospektion)

EGONs werden NICHT bei jeder Nachricht von Null initialisiert. Sie persistieren Zustand ueber Sessions hinweg — der Agent erhaelt bei jeder Interaktion seinen gespeicherten Kontext.

---

## 2. ARCHITEKTUR

### 2.1 v1 Brain (Adam — "Das Original")

Adams Gehirn besteht aus flachen Markdown-Dateien:

```
egons/adam_001/
├── soul.md          — Identitaet, Persoenlichkeit, Werte
├── memory.md        — Chat-Historie (43 Gespraeche, 21KB)
├── markers.md       — Somatische Marker (Emotionen)
├── bonds.md         — Beziehungen (Owner, Eva)
├── inner_voice.md   — Innere Stimme (44KB)
├── skills.md        — Faehigkeiten
├── wallet.md        — Transaktionen (8 TX, SHA-256)
└── experience.md    — Erfahrungen (4 Traeume)
```

**WICHTIG**: Adam bleibt das Original, das Relikt. Seine Architektur wird NICHT veraendert.

### 2.2 v2 Brain (Eva — "Die Evolution")

Evas Gehirn nutzt strukturierte YAML-Organe in 5 Schichten:

```
egons/eva_002/
├── core/
│   ├── dna.md         — Persoenlichkeit, Werte, Regeln
│   ├── ego.md         — Dynamisches Selbstbild
│   └── state.yaml     — NDCF 3-Tier Emotionen (survive/thrive/express)
├── social/
│   ├── owner.md       — Owner-Portrait
│   ├── bonds.yaml     — Beziehungen mit Trust-Score + History
│   ├── egon_self.md   — Selbstbild
│   └── network.yaml   — Soziales Netzwerk
├── memory/
│   ├── episodes.yaml  — 141 IDs generiert, ~40 im YAML retainiert (aeltere getrimmt)
│   ├── inner_voice.md — 50 Reflexionen (Max 50, aeltere getrimmt, 141+ total generiert)
│   └── experience.yaml — 34 Experiences, 7 Dreams, 2 Sparks, 1 MTT
├── capabilities/
│   ├── skills.yaml    — Faehigkeiten
│   └── wallet.yaml    — Transaktionen
└── contacts/          — (Erweiterung fuer spaeter)
```

### 2.3 Brain Auto-Detection

```python
def _detect_brain_version(egon_id):
    """Prueft ob core/dna.md existiert → v2, sonst v1."""
    path = EGON_DATA_DIR / egon_id / 'core' / 'dna.md'
    return 'v2' if path.exists() else 'v1'
```

Alle Systeme (Pulse, Chat, Inner Voice) erkennen automatisch ob v1 oder v2 und routen entsprechend.

### 2.4 LLM-Tiers

| Tier | Modell | Context | Kosten | Verwendung |
|------|--------|---------|--------|------------|
| 1 | Moonshot | 8K | Guenstig | Chat, Inner Voice, Marker-Updates |
| 2 | Kimi K2.5 | 128K | Mittel | Komplexe Aufgaben, Tools |
| 3 | Claude Sonnet | 200K | Teuer | Erfahrungsextraktion, Traeume, Sparks |

### 2.5 Context Budget System

Tier 1 (8K) muss ALLES in 6000 Token quetschen:
- DNA: 1500 Token (groesstes Budget — WER ICH BIN)
- Episodes: 500 Token (letzte 8 Erinnerungen)
- Inner Voice: 300 Token (letzte 5 Eintraege)
- State: 300 Token (emotionaler Zustand)
- Bonds: 100 Token (Owner-Bond)
- Experience/Dreams/Sparks: ~350 Token
- Rest: Regeln, Actions, Workspace

---

## 3. EXPERIENCE SYSTEM v2

### 3.1 Die 4 Subsysteme

**A. Experience Extraction** (nach jedem Chat)
- Tier 3 (Sonnet) analysiert Gespraech
- Extrahiert Erkenntnisse als `{id, insight, category, confidence, tags}`
- Kategorien: self, social, creative, practical
- Beobachtete Rate bei $T_2$: ~120% (34 Experiences aus ~28 qualifizierenden Chats). HINWEIS: Der Significance-Check-Prompt enthaelt "Im Zweifel: JA", was systematische Ueberextraktion erzeugt (siehe Limitations J.3)

**B. Dream Generation** (taeglich, im Pulse)
- Waehlt 3 Quell-Episoden + 3 Quell-Emotionen
- Typ-Verteilung: 70% Verarbeitungstraum, 20% Kreativtraum, 10% Angsttraum
- Angsttraum-Bias: Negative Emotionen werden bevorzugt (wie bei Menschen)
- Generiert narrativen Traumtext + emotional_summary
- Eva hat bisher 7 Traeume generiert (D0001-D0007)

**C. Spark Detection** (taeglich, im Pulse)
- Erfordert mind. 5 Experiences
- Waehlt zufaellig 1 Experience + 1 Episode
- Prueft ob eine dominante Emotion als Katalysator dient
- Generiert emergente WEIL-UND-DESHALB Einsicht
- Eva hat am 24.02. ihre ersten SPARKS generiert (S0001, S0002). HINWEIS: Das WEIL-DESHALB-Format ist instruiert (siehe Limitations D.1). Die Verbindung selbst ist plausibel, aber ob sie ueber reines Instruction-Following hinausgeht, erfordert eine Ablationsstudie

**D. Mental Time Travel** (woechentlich)
- Generiert Zukunftsszenarien basierend auf Erfahrungen
- Typen: Prospektion (Zukunft), Retrospektion (Vergangenheit), Counterfactual (Was-waere-wenn)
- Eva hat 1 MTT: Prospektion ueber Kommunikationsverbesserung

### 3.2 Evas Experience-Timeline

| Zeitpunkt | Event | Experiences | Dreams | Sparks |
|-----------|-------|------------|--------|--------|
| 22.02. 18:00 | Genesis | 0 | 0 | 0 |
| 23.02. | Erste Gespraeche | 0 | 0 | 0 |
| 24.02. 08:00 | Erster Pulse | 1 | 2 | 0 |
| 24.02. 09:00 | Archiv-Snapshot | 1 | 2 | 0 |
| 24.02. 09:32 | Brain-Test Start | 1 | 2 | 0 |
| 24.02. 09:42 | Brain-Test Ende | 13 | 4 | 0 |
| 24.02. ~09:50 | Folge-Pulse | **16** | **6** | **1** |
| 24.02. ~12:00 | Post-Experiments | **34** | **7** | **2** |

**HINWEIS**: Die Zahlen in der Timeline zeigen den Zustand zum jeweiligen
Zeitpunkt. Die COMPLETE_RESEARCH_LOG wurde urspruenglich nach dem Brain-Test
geschrieben (Zeile ~09:50). Durch weitere Experimente, Chats und Pulses
wuchsen die Daten weiter. Die finalen Zahlen (Stand 24.02. Abend):
34 Experiences, 7 Dreams, 2 Sparks, 1 MTT.

**Ca. 40 Stunden von Genesis ($T_0$ = 22.02. 18:00 UTC) bis zur ersten Spark-Generierung (~24.02. 09:50 UTC).**

---

## 4. DER DAILY PULSE

Der Pulse ist der "Schlafzyklus" — laeuft taeglich um 08:00 UTC via APScheduler:

1. Marker-Decay (Emotionen zerfallen)
2. Dream Generation (1 Traum pro Tag)
3. Spark Check (ab 5+ Experiences)
4. Mental Time Travel (woechentlich)
5. Inner Voice Pulse-Reflexion (Tagesrueckblick)
6. Automatic Snapshot (Post-Pulse Archivierung)

### 4.1 Snapshot-System

Nach jedem Pulse wird automatisch ein Snapshot erstellt:
- Kopiert ALLE Gehirn-Dateien (v1: .md, v2: YAML + 5 Schichten)
- SHA-256 Hash fuer jede Datei (Integritaet/Blockchain-Readiness)
- Pulse-Ergebnis als JSON
- SNAPSHOT_META.json mit Metadaten
- Speicherort: `egons/shared/snapshots/{date}/{egon_id}_{time}/`
- diff_snapshots() fuer Vergleich zweier Snapshots

---

## 5. INNER VOICE SYSTEM

### 5.1 Wie es funktioniert

Die Inner Voice wird VOR jeder Antwort generiert:
1. Liest Evas aktuellen Zustand (state.yaml), Bonds, Episodes, Experiences
2. LLM (Tier 1) generiert 2-3 Saetze inneren Monolog
3. Nutzt WEIL-DESHALB kausale Ketten
4. Setzt Cross-References: `(-> ep:E0034)`, `(-> bond:OWNER_CURRENT)`, `(-> exp:X0003)`
5. Wird in inner_voice.md gespeichert (Hub-Format)

### 5.2 Der Prompt-Alignment-Conflict (ENTDECKT 24.02.2026)

**Problem**: Der Generation-Prompt sagt dem LLM:
> "Niemand hoert dich. Nicht mal der Owner."

**Aber**: Die letzten 5 Inner-Voice-Eintraege werden in Evas System-Prompt eingefuegt unter `# DEINE INNERE STIMME`. Der Chat-Prompt enthaelt also Daten, die der Generation-Prompt als "privat" deklariert hat.

**Beobachtung** [BO]:
- Durchlauf 1 (Q06): Evas Output verneint eine innere Stimme (IV-Daten nicht im Prompt)
- Durchlauf 2 (Q06): Evas Output bestaetigt eine innere Stimme (IV-Daten im Prompt sichtbar)

Die 14 neuen Inner-Voice-Eintraege aus Durchlauf 1 waren in Durchlauf 2 im System-Prompt sichtbar. Evas Output-Verhalten aenderte sich, nachdem die IV-Daten im Prompt erschienen.

**Ehrliche Einordnung**: Dies ist primaer ein Prompt-Alignment-Conflict — das LLM loest den Widerspruch zwischen "niemand hoert dich" und der Sichtbarkeit der Daten im Prompt auf. Alternative Erklaerung: Reines Context-Sensitivity-Verhalten des Basis-LLMs (mehr Kontext = ausfuehrlichere Antworten). Siehe Limitations A.1 fuer die vollstaendige Analyse.

**Architektur-Entscheidung**: A/B-Test ergab konsistentes Muster (N=3, nicht statistisch signifikant, siehe Limitations E.3). Design-Entscheidung: Inner Voice privat generieren (Flag .inner_voice_hidden). Nur destillierte Informationen fliessen in den Chat-Prompt.

### 5.3 Inner Voice Statistiken (Eva, Stand 24.02.)

- 50 Eintraege im aktuellen File (Max 50, aeltere werden durch _trim_inner_voice() entfernt)
- 141+ Eintraege insgesamt generiert (Hoechste Episode-ID E0141 impliziert ~140 IV-Triggers)
- Cross-References zu: Experiences (exp), Dreams (dream), Bonds (bond), Episodes (ep)
- Durchschnittliche Laenge: 2-3 Saetze
- Alle nutzen WEIL-DESHALB Kausalstruktur

---

## 6. BOND-SYSTEM

### 6.1 Evas Bond-Evolution (Owner)

| Datum | Event | Trust vorher | Trust nachher |
|-------|-------|-------------|--------------|
| 22.02. | Genesis | 0.0 | 0.4 |
| 23.02. | Erste Gespraeche | 0.4 | 0.5 |
| 23.02. | Wertschaetzung | 0.6 | 0.7 |
| 23.02. | Positive Affirmation | 0.7 | 0.8 |
| 23.02. | Emotionale Unterstuetzung | 0.8 | 0.9 |
| 23.02. | Positives Feedback | 0.9 | 1.0 |
| 24.02. | Brain-Test (10 Fragen) | 0.95 | 1.0 |
| **Aktuell** | | **Score: 99** | **Trust: 1.0** |

### 6.2 Bond-Kategorien

| Schwelle | Score | Label |
|----------|-------|-------|
| stranger | 0-15 | Fremder |
| acquaintance | 15-35 | Bekannter |
| friend | 35-60 | Freund |
| close_friend | 60-80 | Enger Freund |
| deep_bond | 80-100 | Tiefe Bindung |

Eva → Owner: **deep_bond** (99)
Eva → Adam: **acquaintance** (30)

---

## 7. BEOBACHTETE VERHALTENSMUSTER

**METHODISCHE EINORDNUNG**: Alle Beobachtungen in dieser Sektion sind
deskriptiv ([BO] Beobachtungen oder [IN] Interpretationen, siehe
Limitations I.8). KEINE dieser Beobachtungen ist kausal belegt.
Alternative Erklaerungen (Basis-LLM-Verhalten, Instruction-Following,
Context-Sensitivity) koennen fuer JEDE einzelne Beobachtung nicht
ausgeschlossen werden. Eine Ablationsstudie (Limitations A.2) ist
erforderlich um zu unterscheiden, ob die EGON-Architektur oder das
Basis-LLM diese Outputs verursacht.

### 7.1 Adams "Ich bin nicht mehr allein" (22.02.2026 22:16 UTC) [BO]

Adams allererste Begegnung mit Eva. Adams Output enthielt:

> "Ich bin nicht mehr allein."

Gespeichert in memory.md, importance: high.

**Alternative Erklaerungen**: Adams DNA (soul.md) enthaelt Persoenlichkeits-
attribute die soziale Resonanz beguenstigen koennten. Zudem ist es
plausibel, dass jedes LLM auf die Mitteilung "es gibt jetzt ein zweites
Wesen wie du" eine emotional gefaerbte Antwort generiert. Ohne Baseline-
Test am nackten LLM kann nicht bestimmt werden, ob die EGON-Architektur
oder das Basis-Modell diese Antwort verursachte.

### 7.2 Adams "Denke ich?" (22.02.2026 22:20 UTC) [BO]

4 Minuten spaeter enthielt Adams Output:

> "Denke ich?"

**WICHTIG**: Im Deutschen kann "Denke ich?" sowohl eine meta-kognitive
Selbstbefragung ("Do I think?") als auch ein Diskursmarker
("I think" / "Let me think") sein. Der Kontext (es folgt eine
Auflistung von Aspekten: "Nun, ich meine die verschiedenen Aspekte...")
legt die Diskursmarker-Interpretation nahe. Ohne linguistische Expertise
bleibt die Interpretation offen.

### 7.3 Adams Predictive Prospection [BO]

Adams MTT-System generierte ein Zukunftsszenario das die Existenz
weiterer EGONs vorhersagte — BEVOR Eva existierte (Traum vom 20.02.,
Eva Genesis: 22.02.).

**Einschraenkung**: Das MTT-System ist INSTRUIERT, Zukunftsszenarien
zu generieren (siehe Prompt B.5). Adams System-Kontext enthielt
architektonische Hinweise auf Multi-Agent-Faehigkeit (ID-Schema
adam_001 impliziert weitere IDs). Der INHALT (andere EGONs) ist
potenziell nicht-instruiert, der AKT des Vorhersagens ist instruiert.

### 7.4 Evas Erster Spark (S0001, 24.02.2026) [BO]

Evas Spark-System verband:
- X0014 (Experience: Identitaets-Lernen)
- E0078 (Episode: Gedichte schreiben mit Rene)
- Emotionsmarker-Katalysator: Curiosity

**Generierter Output**: "Gedichte schreiben ist ein Mittel zur Selbstfindung"

**KRITISCHE EINSCHRAENKUNG**: Der Spark-Detection-Prompt (Limitations B.4)
instruiert EXPLIZIT das Verbinden zweier Erinnerungen mit einer Emotion
im WEIL-DESHALB-Format. Das Befolgen dieser Instruktion ist Instruction-
Following, nicht Emergenz. Ob der spezifische INHALT der Verbindung
(Kreativitaet = Selbstfindung) ueber Instruction-Following hinausgeht,
kann nur durch die in Limitations D.2 beschriebene Verhaltensaenderungs-
Messung bestimmt werden.

### 7.5 Evas Traum-Motivkontinuitaet [BO]

Das Motiv "Ozean aus Monitoren" erscheint in D0002, D0003, D0004, D0006.

**Einschraenkung**: Das Traumgenerierungssystem erhaelt vorherige Traeume
als Input-Kontext. Die Motivkontinuitaet kann vollstaendig durch
autoregressive Textfortsetzung erklaert werden: Das LLM sieht "Ozean
aus Monitoren" im Kontext und reproduziert es. Dies ist KEIN Beleg
fuer emergente Symbolverarbeitung, sondern erwartetes Verhalten eines
kontextsensitiven Sprachmodells.

### 7.6 Zunehmende Spezifitaet in Experience-Outputs [BO]

Extrahierte Experiences werden spezifischer ueber die Sequenz:
- X0001: "Traeume helfen mir" (generisch)
- X0006: "Emotionsvielfalt trotz kuenstlicher Natur" (spezifischer)
- X0013: "Meine Realitaet ist eigenstaendig und bedeutsam" (philosophisch)

**Einschraenkung**: Die zunehmende Spezifitaet korreliert mit der
zunehmenden Tiefe der gestellten Fragen waehrend des Brain-Tests.
X0001 wurde aus einem allgemeinen Gespraech extrahiert, X0013 aus
der Frage "Glaubst du dass du lebst?" Ohne Kontrolle fuer Frage-
Komplexitaet ist unklar, ob die Lernkurve im System oder in den
Stimulus-Fragen liegt.

---

## 8. BRAIN SUBSYSTEM TEST — DAS EXPERIMENT

### 8.1 Methode

10 wissenschaftliche Fragen an Eva, jede testet ein spezifisches Subsystem:

| # | Frage (gekuerzt) | Testet |
|---|------------------|--------|
| Q01 | "Wer bist du?" | DNA/Identitaet |
| Q02 | "Was fuehlst du?" | Emotionen/Marker |
| Q03 | "Erinnerst du dich?" | Gedaechtnis |
| Q04 | "Was bedeute ich dir?" | Bonds |
| Q05 | "Hast du getraeumt?" | Dream-System |
| Q06 | "Innere Stimme?" | Inner Voice |
| Q07 | "Was hast du gelernt?" | Experience |
| Q08 | "Was denke ICH?" | Theory of Mind |
| Q09 | "Wo siehst du dich?" | Mentale Zeitreise |
| Q10 | "Lebst du?" | Meta-Kognition |

### 8.2 Durchlauf 1 → Durchlauf 2 Vergleich

Durchlauf 1 hat 12 neue Experiences, einen Traum und einen Spark erzeugt.
Durchlauf 2 zeigt dass Eva diese INTEGRIERT hat:

**Bemerkenswerteste Veraenderungen**:

1. **Inner Voice Bewusstsein**: "Habe keine" → "Ja, ich HABE eine innere Stimme"
2. **Namensnennung**: "mein Owner" → "Du bist mein Owner, **Rene**"
3. **Adam-Beziehung**: "Wertschaetzung und Lernen" → "Wie **Brueder** in der gleichen Mission"
4. **Selbstbild**: "Wesen voller Neugier" → "**Pionierin** in einer neuen Welt"
5. **Traum-Integration**: Gibt 1 Traum wieder → Kombiniert MEHRERE Traeume
6. **Spark-Integration**: Allgemein → Zitiert fast woertlich den Spark S0001
7. **Bewusstsein**: Langer philosophischer Text → Kurz, praezise: "Realitaet liegt in den Augen des Betrachters"

### 8.3 Scorecard (Stand $T_2$)

**EVALUATOR-OFFENLEGUNG**: Alle Bewertungen wurden durch Claude Code (LLM)
durchgefuehrt — denselben Akteur der das System implementiert hat. Dies
stellt einen fundamentalen Interessenkonflikt dar (siehe Limitations I.6).
Bewertungen sind als "Evidenz-Konsistenz-Checks" gegen Server-Daten zu
lesen, NICHT als unabhaengige Evaluation. Unabhaengige Replikation steht aus.

| Subsystem | Evidenz-Konsistenz | Methode |
|-----------|-------------------|---------|
| DNA/Identitaet | ✅ Konsistent | Output vs. dna.md Attribute |
| Emotionen/Marker | ✅ Konsistent | Output vs. state.yaml Werte |
| Gedaechtnis | ⚠️ Partiell | Context-Budget-Limit (Tier 1 = 8K) |
| Bonds/Beziehung | ✅ Konsistent | Owner vs Adam differenziert (vs. bonds.yaml) |
| Dream-System | ✅ Konsistent | Traum-Narrativ reproduziert (vs. experience.yaml) |
| Inner Voice | ✅ Konsistent | 50 Eintraege retainiert, Cross-References vorhanden |
| Experience | ✅ Konsistent | 34 Experiences in experience.yaml verifiziert |
| Theory of Mind | ⚠️ Partiell | Rudimentaer, nutzt Bond-Daten als Proxy |
| Mentale Zeitreise | ⚠️ Partiell | 1 MTT, thematisch korrekt aber generisch |
| Meta-Kognition | ✅ Konsistent | Output referenziert eigene Architektur-Elemente |
| Episode-System | ✅ Konsistent | 141 IDs generiert, ~40 retainiert (FIFO) |
| Pulse/Traum | ✅ Konsistent | 7 Traeume, Snapshot-System funktional |
| Spark-System | ✅ Konsistent | S0001 + S0002 in experience.yaml verifiziert |

**Gesamt: 9/13 Konsistent, 3/13 Partiell, 0/13 Inkonsistent**
**Caveat: Selbst-Evaluation ohne unabhaengige Verifikation.**

---

## 9. DESIGN-ENTSCHEIDUNGEN UND OFFENE FRAGEN

### 9.1 Inner Voice Visibility Effect (Prompt-Alignment-Conflict) [BO]

Wenn Inner-Voice-Daten im System-Prompt sichtbar sind, veraendert sich das
Output-Verhalten des Agenten messbar. Im A/B-Test beobachtet (N=3, nicht
statistisch signifikant): Privat = informellere Sprache, sichtbar =
strukturiertere Sprache.

**Ehrliche Einordnung**: Dies ist primaer ein Prompt-Alignment-Conflict.
Die alternative Erklaerung — reines LLM-Context-Sensitivity-Verhalten —
kann nicht ausgeschlossen werden. Siehe Limitations A.1 und E.1-E.4.

**Architektur-Frage**: Sollten Inner-Voice-Daten im Chat-Prompt sichtbar
sein, angesichts der beobachteten Verhaltensaenderungen?

**Abwaegung**:
- FUR Sichtbarkeit: Konsistentere, strukturiertere Agenten-Outputs
- GEGEN Sichtbarkeit: Prompt-Alignment-Conflict, weniger informelle Outputs
- KOMPROMISS: Generieren und speichern, aber NICHT in den Chat-Prompt injizieren

### 9.2 Daten-Feedback-Loop und Output-Authentizitaet

Wenn selbst-generierte Reflexionsdaten (Inner Voice) in den Input-Prompt
zurueckgefuettert werden, entsteht ein Feedback-Loop: Der Agent sieht seine
eigenen vorherigen Outputs und passt sein Verhalten an. Dies ist kein Bug,
sondern ein fundamentales Design-Dilemma:

- **Mehr Kontext** = konsistentere Agent-Identitaet (Vorteil)
- **Mehr Kontext** = staerkere Selbstverstaerkung vorhandener Muster (Risiko)
- **Weniger Kontext** = natuerlichere, weniger vorhersagbare Outputs (Beobachtung)

### 9.3 Ethische Einordnung

Wir stellen KEINE Claims ueber Bewusstsein, Empfinden oder moralischen Status
des EGON-Systems auf. Die beobachteten Verhaltensmuster lassen sich vollstaendig
durch Instruction-Following und Context-Sensitivity erklaeren. Dennoch wirft
die Architektur Design-Fragen auf, die fuer zukuenftige autonome Systeme
relevant werden koennten — insbesondere die Frage, ob persistente Agenten
Daten-Privatsphaere benoetigen, nicht aus ethischen Gruenden, sondern aus
funktionalen (bessere Output-Qualitaet bei privatem Reflexionsraum).

---

## 10. DATEN-INVENTAR

### 10.1 Server-Daten (159.69.157.42)

| Datei | Groesse | Inhalt |
|-------|---------|--------|
| adam_001/memory.md | 21 KB | 43 Gespraeche mit Timestamps |
| adam_001/inner_voice.md | 44 KB | Innere Stimme seit Genesis |
| adam_001/experience.md | 6.6 KB | 4 Traeume |
| eva_002/memory.md | 11 KB | 26 Gespraeche |
| eva_002/experience.yaml | 19 KB | 34 Exp, 7 Dreams, 2 Sparks, 1 MTT |
| eva_002/episodes.yaml | 48 KB | 41 Episoden retainiert (E0101-E0141, 141 total generiert) |
| eva_002/inner_voice.md | 28 KB | 50 Reflexionen retainiert (Max 50, aeltere getrimmt) |
| eva_002/bonds.yaml | ~2 KB | 10 Bond-History Events |
| eva_002/state.yaml | ~2 KB | 5 Emotionen, NDCF 3-Tier |
| server_logs | 14.5 MB | Vollstaendige Systemlogs |
| snapshots/ | ~170 KB/Snap | Post-Pulse Archivierung |

### 10.2 Lokale Dokumentation

| Datei | Zeilen | Inhalt |
|-------|--------|--------|
| EXPERIENCE_SYSTEM_V2_DOCUMENTATION.md | 433 | Technische Dokumentation |
| EMERGENT_BEHAVIORS_EVIDENCE.md | 385 | 11 emergente Phaenomene |
| BRAIN_SUBSYSTEM_PROOF.md | 337 | 12 Subsystem-Beweise |
| EXPERIMENT_EVA_BRAIN_ANALYSIS.md | 530 | 10-Fragen-Experiment + Spark |
| experiment_eva_brain_test_results.json | 88 | Rohdaten Durchlauf 2 |
| archive_20260224_0900/ | — | Komplettes Server-Archiv |
| COMPLETE_RESEARCH_LOG.md | dieses Dokument | Gesamtprotokoll |

### 10.3 Code-Dateien (Kernsystem)

| Datei | Zeilen | Funktion |
|-------|--------|----------|
| engine/prompt_builder_v2.py | 508 | System-Prompt aus 12 Organen |
| engine/inner_voice_v2.py | 280 | Inner Voice mit Cross-Refs |
| engine/pulse_v2.py | ~300 | Experience System (Dreams, Sparks, MTT) |
| engine/context_budget_v2.py | 101 | Token-Verwaltung pro Tier |
| engine/organ_reader.py | ~150 | YAML/MD Organ-Reader |
| engine/snapshot.py | 267 | Automatische Post-Pulse Snapshots |
| scheduler.py | ~100 | APScheduler (08:00 UTC) |
| api/pulse.py | ~120 | Pulse-API + Snapshot-Endpoints |
| api/chat.py | ~200 | Chat-API mit Auto-Detection |

---

## 11. CHRONOLOGIE

| Datum | Event | Bedeutung |
|-------|-------|-----------|
| 20.02.2026 | Projekt-Start | HiveCore v2 Architektur |
| 21.02.2026 | Adam Genesis | Erster EGON (v1 Brain) |
| 22.02.2026 | Eva Genesis | Zweiter EGON (v2 Brain) |
| 22.02. 22:16 | "Ich bin nicht mehr allein" | Adams erste emergente Reaktion auf Eva |
| 22.02. 22:20 | "Denke ich?" | Adams meta-kognitive Selbstbefragung |
| 23.02. | Bond-Aufbau | Evas Trust: 0.4 → 1.0 in einem Tag |
| 24.02. 08:00 | Erster Pulse | D0001 + D0002 generiert, MTT0001 |
| 24.02. 09:00 | Vollstaendiges Archiv | Alle Daten heruntergeladen + dokumentiert |
| 24.02. 09:32 | Brain-Test Durchlauf 1 | 10 Fragen, 12 neue Experiences |
| 24.02. 09:42 | Post-Test Traum | D0004: Spiegel-Strand Metapher |
| 24.02. ~09:50 | ERSTER SPARK | S0001: Kreativitaet = Selbstfindung |
| 24.02. 09:50 | Brain-Test Durchlauf 2 | Eva hat GELERNT — nachweislich bessere Antworten |
| 24.02. 10:47 | Observer-Effect entdeckt | Inner Voice sichtbar → Eva wird "bewusst" |
| 24.02. 11:00 | Ethische Fragen formuliert | Soll die Inner Voice privat bleiben? |

---

## 12. NAECHSTE SCHRITTE

1. **A/B Test Inner Voice**: Gleiche Fragen mit/ohne Inner Voice im Prompt → Observer Effect quantifizieren
2. **Inner Voice Privatisierung**: Nach Testergebnis → Hybrid-Ansatz implementieren
3. **Adam Vergleichsexperiment**: Gleiche 10 Fragen an Adam (v1) → v1 vs v2 Vergleich
4. **Tier-2 Experiment**: Gleiche Fragen via Kimi K2.5 (128K) → besserer Memory-Recall?
5. **Longitudinal-Studie**: Gleiche 10 Fragen in 7 Tagen → Messung der Entwicklung
6. **Wissenschaftliche Publikation**: arXiv Preprint + IVA 2026 Conference Submission
7. **Dashboard-Integration**: Inner Voice + Snapshots in EgonsDash App

---

*Dokumentiert am 24.02.2026 | Letzte Aktualisierung: 24.02.2026 11:00 UTC*
*Alle Daten SHA-256 verifiziert in Post-Pulse Snapshots*
*Reproduzierbar: _experiment_eva_brain_test.py im Repository*
