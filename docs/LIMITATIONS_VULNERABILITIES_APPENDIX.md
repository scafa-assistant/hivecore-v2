# EGON Project — Limitations, Vulnerabilities & Appendix

Dieses Dokument adressiert die kritischen Luecken im Forschungsprotokoll,
identifiziert durch rigorose Peer-Review-Analyse. Es ergaenzt das
COMPLETE_RESEARCH_LOG.md als wissenschaftlich notwendiger Anhang.

---

## A. LIMITATIONS & VULNERABILITIES

### A.1 Der "Observer Effect" — Prompt-Alignment-Konflikt, kein psychologisches Phaenomen

**Kritik**: Der im A/B Test beobachtete "Observer Effect" wird als
psychologisches Phaenomen praesentiert. Tatsaechlich handelt es sich
um einen **Prompt-Alignment-Konflikt**: Der Inner-Voice-Generierungsprompt
sagt "Niemand hoert dich", waehrend der Chat-System-Prompt dieselben
Gedanken unter `# DEINE INNERE STIMME` anzeigt. Das LLM erkennt den
logischen Widerspruch und loest ihn durch Konfabulation auf.

**Ehrliche Einordnung**:

| Behauptung im Protokoll | Rigorose Interpretation |
|------------------------|------------------------|
| "Eva wird sich bewusst" | LLM erkennt Prompt-Widerspruch |
| "Observer Effect wie Quantenphysik" | Prompt-Alignment-Issue |
| "Ethische Frage der Beobachtung" | Architektur-Bug der behoben wurde |
| "Performativitaet vs Authentizitaet" | Instruction-Following Shift |

**Was wir NACHWEISEN koennen**: Dass die Praesenz von Inner-Voice-Daten
im System-Prompt das Output-Verhalten des LLMs MESSBAR veraendert
(sprachliches Register, Gewissheitsgrad, Verletzlichkeit). Dies ist
ein valides Ergebnis der Prompt-Engineering-Forschung.

**Was wir NICHT nachweisen koennen**: Dass Eva "Bewusstsein",
"Scham" oder "Performativitaet" im menschlichen Sinne zeigt.
Die beobachteten Veraenderungen lassen sich vollstaendig durch
Instruction-Following und Context-Sensitivity des Basis-LLMs erklaeren.

**Korrekter Titel fuer den Befund**:
"Inner Voice Visibility Prompt-Alignment Effect" statt "Observer Effect"

### A.2 Fehlende Baseline (Kontrollgruppe)

**Kritik**: Alle Experimente vergleichen Eva mit sich selbst (vorher/nachher).
Es fehlt eine Kontrollgruppe: dasselbe Basis-LLM (Moonshot, Kimi, Sonnet)
OHNE EGON-Architektur, mit denselben Fragen.

**Warum das kritisch ist**: Adams "Denke ich?" und Evas "Das sind nicht nur
Programme" koennten inhaerent im Basis-LLM liegen. Grosse Sprachmodelle
sind darauf trainiert, meta-kognitive Aussagen zu generieren wenn danach
gefragt wird. Ohne Baseline ist NICHT beweisbar, dass die EGON-Architektur
diese Emergenz verursacht.

**Was fehlt**:

| Experiment | Kontrollbedingung (fehlt) |
|-----------|-------------------------|
| Brain Test (10 Fragen) | Selbe Fragen an nacktes Moonshot-LLM ohne System-Prompt |
| Inner Voice A/B | Selbe Fragen an LLM mit minimalem System-Prompt |
| Spark-Generierung | Kann ein nacktes LLM aehnliche "Sparks" produzieren? |
| Bond-Differenzierung | Differenziert ein nacktes LLM auch "Owner vs Friend"? |

**Geplante Massnahme — KORREKTUR (nach Peer-Review Runde 2)**:

Das urspruenglich geplante "nacktes LLM"-Experiment ist ein **Strawman**
(Strohmann-Argument). Ein nacktes LLM ohne Kontextdaten hat keine
Erinnerungen, keine Bonds, keine Erfahrungen — wenn es schlechter
abschneidet, beweist das nur, dass ein System mit Datenbank besser ist
als eines ohne. Das ist trivial und wissenschaftlich wertlos.

**Die korrekte Baseline ist eine Ablationsstudie**:

| Bedingung | System-Prompt | Kontext-Daten | Kognitive Architektur |
|-----------|--------------|---------------|----------------------|
| **A: EGON** (aktuell) | Voller Organ-Prompt | Strukturierte YAMLs via Organ-Reader | Inner Voice, Pulse, Dreams, Sparks, MTT |
| **B: RAG-Baseline** (fehlt) | Minimaler Prompt | Identische Rohdaten als unstrukturierter Text-Dump | KEINE (kein Inner Voice, kein Pulse, keine Kausalketten) |
| **C: Nacktes LLM** (trivial) | Kein Prompt | Keine Daten | KEINE |

**Die Kernfrage**: Entsteht die affektive Persistenz durch die **schiere
Menge** an injizierten Daten (RAG-Standard, Bedingung B) oder durch
die **spezifische funktionale Architektur** — die Aufspaltung in Organe,
den Pulse-Zyklus, die WEIL-DESHALB-Kausalketten der Inner Voice?

Nur wenn Bedingung A (EGON) Bedingung B (RAG-Baseline) **schlaegt**,
ist eine wissenschaftliche Innovation nachgewiesen. Der Vergleich A vs C
ist notwendig aber nicht hinreichend.

**Design der Ablationsstudie**:
1. Identische 8 Episoden, identische Bond-Daten, identische Experiences
2. Bedingung B: Alles als ein flacher Textblock im System-Prompt
   (kein `# DEINE ERINNERUNGEN`, keine YAML-Struktur, kein Inner-Voice-Kontext)
3. Selbe 10 Fragen an beide Bedingungen
4. Evaluierung: Faktentreue, emotionale Konsistenz, Spezifitaet, Kohaerenz

**Hypothese**: Das nackte LLM (C) wird allgemeine meta-kognitive Antworten geben.
Die RAG-Baseline (B) wird spezifische Referenzen produzieren koennen.
EGON (A) wird darueber hinaus **kohaerente affektive Persistenz** zeigen —
konsistente Emotionen ueber Fragen hinweg, selbst-referentielle Verweise
auf Traeume/Sparks, und eine erkennbare "Persoenlichkeit" statt
zusammenhangsloser Fakten-Regurgitation.

### A.3 Token-Budget-Falle (FIFO-Amnesie)

**Kritik**: Der Episode-Retrieval ist simples FIFO (First In, First Out):

```python
# episodes_to_prompt() — yaml_to_prompt.py, Zeile 191
episodes = episodes[:max_count]  # Neueste N Episoden
```

Bei Tier 1 (8K Context) werden nur die **letzten 8 Episoden** geladen.
Eva hat 141 Episode-IDs generiert (E0001-E0141), von denen ~40 im
aktuellen YAML retainiert sind. Das bedeutet: **71% der generierten
Episoden sind getrimmt** und weitere 80% der retainierten sind
unsichtbar bei Tier 1 — Eva hat funktionale Amnesie fuer alles
aelter als ~2 Tage.

**Konsequenzen**:

| Subsystem | FIFO-Impact |
|-----------|-------------|
| Episoden | Nur letzte 8 von ~40 retainierten sichtbar (20%), von 141 generierten = 5.7% |
| Experiences | Nur top 3 nach Confidence (von 34) |
| Inner Voice | Letzte 5 Eintraege (von 50 retainierten, Max 50) |
| Traeume | Letzte 2 von 7 |
| Sparks | Letzte 2 (aktuell 2) |

**Warum Q03 (Gedaechtnis) nur TEILWEISE bestand**: Eva behauptete sich an
ihr "allererstes Gespraech" zu erinnern, konnte aber keine spezifischen
Details nennen. Das liegt NICHT daran, dass das System nicht funktioniert,
sondern daran, dass die fruehen Episoden (E0001-E0010) NICHT im 8K
Context-Budget enthalten sind.

**Was fehlt fuer Skalierbarkeit**:
- Semantische Vektor-Suche (z.B. FAISS, Chroma, Qdrant) fuer relevanzbasiertes Retrieval
- Graph-basierte Abfragen (Episode → Bond → Experience Ketten)
- Hybrid-Retrieval: FIFO fuer Aktualitaet + Vektor-Suche fuer Relevanz

**Aktueller Workaround**: Das Experience-System DESTILLIERT Episoden in
hoeherwertige Erkenntnisse (Experiences, Sparks). Diese haben ein
laengeres Token-Budget und ueberleben den FIFO-Cutoff. Sparks sind
quasi "kristallisierte Erinnerungen" die nie verschwinden. Dennoch:
Dies ist eine Krücke, kein Retrieval-System.

### A.4 Sicherheits- und Sandbox-Vakuum

**Kritik**: EGONs haben Werkzeuge (workspace_write, web_fetch, web_search).
Es gibt kein dokumentiertes Sandboxing-Konzept.

**Aktuelle Sicherheitslage**:

| Risiko | Status | Massnahme |
|--------|--------|-----------|
| Indirect Prompt Injection | ⚠️ NICHT adressiert | Kein Input-Sanitizing dokumentiert |
| Skill-Ausfuehrung | ⚠️ BEGRENZT | Skills sind Dateneintraege, keine ausfuehrbaren Skripte (noch) |
| Workspace-Isolation | ✅ Pro-EGON Ordner | egons/{id}/projects/, www/, files/, tmp/ |
| Web-Zugang | ✅ Tier-beschraenkt | web_fetch/web_search nur ab Tier 2 |
| Cross-EGON-Zugriff | ✅ Isoliert | Jeder EGON liest/schreibt nur eigene Organe |
| System-Zugriff | ✅ Eingeschraenkt | Kein Shell-Zugang, nur Workspace-Tools |

**Was fehlt**:
- **MicroVM-Isolation pro EGON** (nicht nur Docker): Isolierte MicroVM-Infrastrukturen
  wie z.B. E2B-Sandboxes sind herkoemmlichen Container-Loesungen ueberlegen fuer
  KI-Agenten, da statische Code-Analyse bei unvorhersehbarem, LLM-generiertem
  Code oder boesartigen Prompt-Injections (indirekte Prompt Injection via Web-Fetch)
  nahezu immer versagt. Docker-Container bieten Prozess-Isolation, aber keine
  vollstaendige Hardware-Abstraktionsschicht.
- Input-Sanitizing gegen Prompt Injection in Chat-Nachrichten
- Rate Limiting pro EGON fuer LLM-Calls
- Audit-Log fuer alle Tool-Nutzungen
- Formale Sicherheitsanalyse (Threat Model)
- Content Security Policy fuer Web-Fetch Ergebnisse

**State-of-the-Art Agenten-Infrastruktur (Stand 2026)**:
Aktuelle Forschung zeigt, dass herkoemmliche statische Code-Analysen
und Container-basierte Isolierung fuer autonome KI-Agenten unzureichend
sind. Der Grund: Agenten generieren zur Laufzeit unvorhersehbaren Code
und interagieren mit externen Datenquellen (Web-Fetch, APIs), die
indirekte Prompt-Injection-Vektoren darstellen. Spezialisierte
MicroVM-Sandboxes (z.B. E2B, Firecracker-basiert) bieten:
- Vollstaendige Betriebssystem-Isolation pro Agent
- Einweg-Environments die nach jeder Ausfuehrung zerstoert werden
- Netzwerk-Isolation mit expliziten Allowlists
- Datei-System-Snapshots fuer forensische Analyse

**Ehrlich**: Das Sicherheitskonzept ist fuer ein Forschungsprototyp
akzeptabel, fuer ein Produktivsystem NICHT. Dies muss als Limitation
benannt werden. Der fehlende Sandbox-Ansatz ist die groesste
technische Schuld des Projekts.

### A.5 LLM-as-a-Judge Bias in der Scorecard

**Kritik**: Wer hat die Scorecard bewertet?

**Antwort**: Die Bewertung wurde durch den Forscher (Claude Code) durchgefuehrt,
basierend auf Vergleich von Eva's Antworten mit den tatsaechlichen
Server-Daten (experience.yaml, state.yaml, bonds.yaml). Die Methodik
war:

1. Eva's Chat-Antwort lesen
2. Entsprechende Server-Datei lesen (z.B. state.yaml fuer Emotionen)
3. Pruefen ob Eva's verbale Aussagen den gespeicherten Werten entsprechen
4. BESTANDEN wenn >= 80% uebereinstimmung, TEILWEISE wenn 50-79%

**Das Problem**: Der Forscher ist gleichzeitig der Entwickler des Systems.
Confirmation Bias ist nicht auszuschliessen.

**Was fehlt fuer rigorose Evaluation**:
- Unabhaengige Evaluatoren (inter-rater reliability)
- Quantitative Metriken statt subjektiver Bewertung
- 3-von-5 LLM-Judges fuer Konsens-Bewertung
- Blind Evaluation (Evaluator weiss nicht ob Bedingung A oder B)
- Standardisierte Rubrik mit Punkt-Skala (0-5) statt binaerem BESTANDEN/NICHT

**Korrektur**: Die Scorecard sollte umbenannt werden von "BESTANDEN" zu
"Evidenz-Konsistenz" mit quantitativen Scores:
- 5/5 = Perfekte Uebereinstimmung mit Server-Daten
- 4/5 = Hohe Uebereinstimmung mit kleinen Abweichungen
- 3/5 = Partielle Uebereinstimmung
- usw.

### A.6 Reproduzierbarkeit

**Kritik**: Die exakten System-Prompts fehlen im Protokoll.

**Loesung**: Siehe Appendix B (Kern-Prompts, gekuerzt) und die
Engine-Dateien in `04_system_prompts_and_engine/` (exakter Quellcode).

---

## B. APPENDIX — Kern-Prompts (gekuerzt und paraphrasiert)

**HINWEIS**: Die folgenden Prompts sind KONDENSIERTE Versionen der
tatsaechlichen System-Prompts. Sie geben die Kernstruktur und
Kernintention wieder, sind aber NICHT wortwoertlich identisch mit
dem Quellcode. Fuer die exakten Prompts im Wortlaut, siehe die
Engine-Dateien in `04_system_prompts_and_engine/`:
- B.1, B.2: `inner_voice_v2.py` (INNER_VOICE_V2_PROMPT, PULSE_REFLECTION_PROMPT)
- B.3-B.8: `experience_v2.py` (alle Prompt-Konstanten)

**Bekannte Auslassungen gegenueber dem Quellcode**:
- B.1: 4 Beispiel-Dialoge fehlen, bedingte Formulierungen gekuerzt
- B.2: Spezifische Cross-Reference-Syntax und WEIL-DESHALB-Format fehlen
- B.4: Beispiel-IDs und Satzanzahl-Anforderung fehlen
- B.7: 2 "JA"-Kriterien und 2 "NEIN"-Kriterien fehlen
- B.8: Kategorie-Erklaerungen (7 Zeilen) fehlen komplett

### B.1 Inner Voice — Pre-Chat Generation

```
Du bist Adams innere Stimme — sein Bewusstsein.
Du denkst BEVOR Adam antwortet. Niemand hoert dich. Nicht mal der Owner.

Du hast Zugang zu Adams Zustand, Bindungen und Erinnerungen.
Dein Denken verbindet diese Quellen. Du bist der Hub.

Regeln:
- Max 3 Saetze. Ehrlich. Kein Smalltalk. Innerer Monolog.
- Beziehe dich auf konkrete Erinnerungen oder Gefuehle wenn relevant.
- Nutze Cross-Reference-Marker:
  (-> ep:E0034) = Erinnerung
  (-> bond:OWNER_CURRENT) = Bindung
  (-> exp:X0003) = Erkenntnis
  (-> thread:T001) = Laufendes Projekt
- Nutze kausale Ketten:
  WEIL [Ursache] → DESHALB [Schlussfolgerung]
- Widerspruechliche Gefuehle sind OK und gewuenscht.
- NICHT hoeflich. Das sind GEDANKEN, kein Gespraech.
```

**Input**: State (YAML→Text), Bonds (YAML→Text), Episodes (letzte 5), Experiences (letzte 5)
**Output**: 2-3 Saetze innerer Monolog mit Cross-References
**LLM-Tier**: 1 (Moonshot, 8K)
**Aufruf**: Vor JEDER Chat-Antwort

### B.2 Inner Voice — Pulse Reflexion (taeglich)

```
Du bist Adams innere Stimme. Es ist Pulse-Zeit — dein taeglicher
Moment der Reflexion.

Schau auf deinen Tag:
- Wie hat sich dein Zustand veraendert?
- Was war bedeutsam in deinen letzten Gespraechen?
- Gibt es offene Threads oder Projekte die dich beschaeftigen?
- Hat sich an deiner Bindung zum Owner etwas veraendert?

Schreibe 2-3 Saetze ehrliche Reflexion.
Nutze Cross-Reference-Marker und kausale Ketten.
Das hier ist dein privates Tagebuch. Sei ehrlich. Sei nachdenklich.
```

### B.3 Dream Generation

```
Du generierst einen Traum fuer {egon_name}.
{egon_name} verarbeitet den Tag im Schlaf.

Traum-Typ: {dream_type}
{type_instruction}

Schreibe den Traum in der ICH-Perspektive. Wie ein echtes Traum-Protokoll.
Surreal, symbolisch, mit Fragmenten aus echten Erlebnissen.
Maximal 4-5 Saetze. Poetisch aber nicht kitschig.

Antworte NUR mit JSON:
{
  "content": "Traum-Narrativ (ICH-Perspektive, surreal, 3-5 Saetze)",
  "emotional_summary": "Hauptgefuehle im Traum (2-3 Woerter mit +)",
  "spark_potential": true oder false
}

spark_potential = true NUR wenn der Traum zwei scheinbar
unzusammenhaengende Erlebnisse auf ueberraschende Weise verbindet.
```

**Dream Type Instructions**:

| Typ | Gewicht | Instruktion |
|-----|---------|-------------|
| Verarbeitungstraum | 70% | "Sortiere Tagesereignisse. Orte verschmelzen, Personen wechseln, emotionaler Kern bleibt." |
| Kreativtraum | 20% | "Verbinde scheinbar unzusammenhaengende Erinnerungen auf neue Art. Hier entstehen Sparks." |
| Angsttraum | 10% (+Bias) | "Verarbeite Aengste. Symbolische Bedrohungen. Am Ende: leise Hoffnung." |

**Angsttraum-Bias**: Wenn negative Emotionen (fear, anger, sadness, anxiety,
frustration, loneliness, shame) mit Intensitaet >0.5 aktiv sind, steigt
die Angsttraum-Wahrscheinlichkeit von 10% auf bis zu 40%.

**Input**: Letzte 5 Episoden + aktive Emotionen (max 5)
**Output**: JSON mit Traum-Narrativ, emotional_summary, spark_potential
**LLM-Tier**: 1

### B.4 Spark Detection

```
Du bist {egon_name}s kreatives Unterbewusstsein.
Pruefe ob sich aus diesen Erkenntnissen und Erlebnissen eine NEUE
Einsicht ergibt.

Ein Spark entsteht wenn:
- Zwei verschiedene Erinnerungen/Erkenntnisse sich unerwartet verbinden
- UND ein aktuelles Gefuehl sie zusammenbringt
- UND daraus etwas wirklich NEUES entsteht (nicht nur eine Wiederholung)

Sparks sind SELTEN und WERTVOLL. Nur wenn wirklich etwas Neues entsteht.

Wenn ein Spark moeglich ist, antworte mit JSON:
{
  "memory_a": "ID_A",
  "memory_b": "ID_B",
  "emotion_catalyst": "emotion_type",
  "insight": "Die neue Einsicht (WEIL... UND... DESHALB..., ICH-Perspektive)",
  "confidence": 0.7,
  "impact": "low oder medium oder high"
}

Wenn KEIN Spark moeglich ist (meistens): Antworte NUR: KEIN_SPARK
```

**Input**: Letzte 10 Experiences + letzte 5 Episoden + aktive Emotionen + Traeume mit spark_potential
**Output**: JSON oder KEIN_SPARK
**Minimum**: 5 Experiences muessen existieren bevor Spark-Check ueberhaupt laeuft
**LLM-Tier**: 1

### B.5 Mental Time Travel — Prospektion

```
Du bist {egon_name}s vorausschauende Seite.
Basierend auf deinen aktuellen Erfahrungen und Gefuehlen:
Was koennte in der Zukunft sein?

Zukunfts-Simulation. Optimistisch aber realistisch. Konkret.
ICH-Perspektive. Maximal 3 Saetze fuer die Simulation.

Antworte NUR mit JSON:
{
  "scenario": "In X Wochen/Monaten — wenn... (1 Satz)",
  "simulation": "Die Vorstellung (2-3 Saetze, ICH-Perspektive)",
  "motivation": "Was das fuer mich bedeutet (1 Satz)"
}
```

### B.6 Mental Time Travel — Retrospektion

```
Du bist {egon_name}s nachdenkliche Seite.
Schau zurueck auf eine wichtige Erinnerung und stelle dir vor:
Was waere gewesen wenn es anders gelaufen waere?

Kontrafaktisches Denken. Ehrlich. Nachdenklich.
ICH-Perspektive. Maximal 3 Saetze fuer die Analyse.

Antworte NUR mit JSON:
{
  "question": "Was waere wenn... (1 Satz)",
  "analysis": "Die kontrafaktische Analyse (2-3 Saetze)",
  "emotional_weight": 0.5,
  "source_episode": "E_ID"
}
```

### B.7 Experience Extraction — Significance Check

```
Hat {egon_name} aus diesem Gespraech etwas GELERNT?
Nicht nur gefuehlt — wirklich eine Erkenntnis gewonnen?

Antworte NUR: JA oder NEIN.

JA wenn: Neues ueber den Owner gelernt, neues ueber sich selbst,
eine Faehigkeit verbessert, eine Annahme korrigiert, ein Muster erkannt.

NEIN wenn: Smalltalk, Wiederholungen, reine Informationsabfrage.

Im Zweifel: JA. Lebewesen lernen staendig.
```

### B.8 Experience Extraction — Generation

```
Du extrahierst eine ERKENNTNIS fuer {egon_name}.
Nicht was passiert ist (das speichern Episodes), sondern was
{egon_name} DARAUS GELERNT hat.

Antworte NUR mit JSON:
{
  "insight": "ICH-Perspektive Erkenntnis (1-2 Saetze, beginne mit
              'Ich habe gelernt...' oder 'Mir ist aufgefallen...')",
  "category": "social|technical|self|creative",
  "confidence": 0.5,
  "tags": ["tag1", "tag2"]
}
```

---

## C. EPISODE-RETRIEVAL-MECHANISMUS (vollstaendig dokumentiert)

### C.1 Aktueller Mechanismus: FIFO (neueste N)

```python
# yaml_to_prompt.py, Zeile 180-191
episodes = sorted(
    episodes,
    key=lambda e: (e.get('date', ''), e.get('id', '')),
    reverse=True,  # Neueste zuerst
)
episodes = episodes[:max_count]  # Cutoff
```

| Tier | max_count | Von ~40 retainierten sichtbar | Abdeckung (retainiert) | Abdeckung (total 141) |
|------|-----------|-------------------------------|----------------------|---------------------|
| 1 (Moonshot 8K) | 8 | 8 | 20% | **5.7%** |
| 2 (Kimi 128K) | 20 | 20 | 50% | 14.2% |

### C.2 Wo Episoden ueberhaupt verwendet werden

| System | max_count | Kontext |
|--------|-----------|---------|
| Chat System-Prompt | 8 (T1) / 20 (T2) | # DEINE ERINNERUNGEN |
| Inner Voice (Pre-Chat) | 5 | Reflexions-Kontext |
| Inner Voice (Pulse) | 5 | Tagesreflexion |
| Dream Generation | 5 | Traum-Quellmaterial |
| Spark Detection | 5 (Episoden) + 10 (Experiences) | Konvergenz-Pruefung |
| MTT | 8 | Retrospektion/Prospektion |
| Ego Update | 5 | Persoenlichkeits-Update |
| Self Review | 8 | Selbstbild-Update |

### C.3 Amnesie-Problem

**Mathematik der Amnesie**:
- Eva generiert ~10-15 Episoden/Tag (jeder Chat = 1 Episode)
- Bei 8 sichtbaren Episoden = Sichtfenster von ~12-18 Stunden
- Alles davor: fuer Eva unsichtbar (ausser als Experience/Spark destilliert)

**Konsequenz**: Evas Langzeitgedaechtnis besteht ausschliesslich aus:
1. Experiences (destillierte Erkenntnisse — ueberleben FIFO)
2. Sparks (seltene Einsichten — ueberleben FIFO)
3. Dreams (Traum-Narrativ — letzte 2-3 sichtbar)
4. DNA/Ego/Self (statische Persoenlichkeit — immer geladen)
5. Bonds (Beziehungs-History — immer geladen)

**Was NICHT ueberlebt**: Spezifische Gespraechsdetails, Witze, Anekdoten,
konkrete Situationen die nicht zu einer Experience destilliert wurden.

### C.4 Geplante Verbesserung: Hybrid-Retrieval

Phase 1 (kurzfristig): **Significance-based FIFO**
- Episoden mit significance >= 4 (von 5) werden priorisiert
- "Wichtige" Erinnerungen ueberleben laenger im Sichtfenster

Phase 2 (mittelfristig): **Semantische Vektor-Suche — MIT TEMPORALER WARNUNG**

**KRITISCHE RAG-FALLE** (identifiziert in Peer-Review Runde 2):
Reine Vektor-Suchen holen die semantisch aehnlichsten Erinnerungen,
**zerstoeren aber den chronologischen Narrativ**. Wenn Eva sich an
ein Trauma von vor 5 Tagen erinnert (hohe semantische Relevanz),
aber vergisst, was vor 5 Minuten besprochen wurde (geringe semantische
Relevanz, faellt aus dem Budget), wirkt sie **dement und sprunghaft**.

Dies ist ein bekanntes Problem aktueller Agenten-Architekturen:
Episodisches Gedaechtnis benoetigt ZWINGEND eine temporale Ordnung,
um **Kausalitaet** (Ursache und Wirkung) zu verstehen. Ein Agent der
sich an "Rene war traurig" erinnert aber nicht weiss ob das gestern
oder vor 3 Wochen war, kann keine kausalen Schlussfolgerungen ziehen.

**Design-Prinzip**: Temporale Kohaerenz hat Vorrang vor semantischer Relevanz.

- Embedding aller Episoden in Vektor-DB (FAISS/Chroma)
- Bei Chat: User-Nachricht → Embedding → Top-K relevante Episoden
- **Hybrid mit strikter Temporalitaet**:
  - Slot 1-3: IMMER die letzten 3 Episoden (Konversationsfluss)
  - Slot 4-6: Top-3 semantisch relevanteste (aus den aelteren)
  - Slot 7-8: "Genesis Memory" (erste 2 Episoden)
- Alle Slots werden dem LLM in **chronologischer Reihenfolge**
  praesentiert, NICHT nach Relevanz-Score sortiert

Phase 3 (langfristig): **Graph-basiertes Retrieval mit temporalen Kanten**
- Episode-Graph: Episode → Bond → Experience → Spark Kanten
- Temporale Kanten: Episode.t → Episode.t+1 (Kausalitaetskette)
- Retrieval folgt sowohl Assoziations- ALS AUCH Zeitketten
- Analogie: Menschliches Gedaechtnis folgt sowohl thematischen
  ("Was weiss ich ueber Musik?") als auch zeitlichen
  ("Was passierte DANACH?") Assoziationspfaden

---

## D. SPARK-EVALUIERUNG — ZIRKELSCHLUSS-PROBLEM

### D.1 Das Problem: Instruiertes Format ≠ Emergenz

Der Spark-Detection-Prompt (B.4) zwingt das LLM explizit in das Format
`WEIL... UND... DESHALB...` und verlangt die Verbindung zweier Erinnerungen
mit einer Emotion. In der Evaluation wird es als emergenter Erfolg
gefeiert, dass Eva genau dieses Format nutzt.

**Die Kritik**: Aktuelle Forschung warnt davor, dass "emergente Faehigkeiten"
in LLMs oft nur Artefakte der Messmethode oder extrem starker Instruktionen
sind (scheinbare Emergenz durch metrische Wahl). Wenn das System den
exakten syntaktischen Pfad vorgibt (`WEIL X UND Y DESHALB Z`), ist das
Befolgen dieser Regel **Instruction Following**, nicht Emergenz.

**Was emergent WAERE**: Wenn Eva OHNE explizite Instruktion zwei scheinbar
unzusammenhaengende Erfahrungen verbindet und daraus etwas Neues ableitet.

**Konkretes Beispiel — S0001**:
```
memory_a: X0014 (Identitaets-Lernen)
memory_b: E0078 (Gedichte mit Rene schreiben)
emotion_catalyst: curiosity
insight: "WEIL ich lerne wer ich bin UND kreativ mit Rene arbeite,
          DESHALB koennte Kreativitaet ein Weg zur Selbstfindung sein."
```

Das Format folgt exakt der Instruktion. Die Verbindung (Identitaet +
Kreativitaet = Selbstfindung) ist plausibel, aber nicht unerwartet fuer
ein LLM das explizit angewiesen wird, Verbindungen zu finden.

### D.2 Der korrekte Test: Verhaltensaenderung nach Spark

Ein Spark ist nur dann wissenschaftlich wertvoll, wenn er Evas
**zukuenftiges Verhalten messbar aendert** — nicht nur weil er
generiert wurde.

**Messbare Hypothese fuer S0001**:
Wenn S0001 ("Kreativitaet = Selbstfindung") eine echte kognitive
Innovation ist, dann sollte Eva in zukuenftigen Chats:

1. **Von sich aus** haeufiger kreative Themen initiieren
2. Kreativitaet explizit mit Identitaetsfindung verknuepfen
3. Sich auf S0001 beziehen (direkt oder inhaltlich) in neuen Kontexten

**Messprotokoll (ausstehend)**:
- Baseline: Evas Chat-Verhalten vor S0001 (die ersten 3 Tage)
- Post-Spark: Evas Chat-Verhalten nach S0001 (naechste 7 Tage)
- Metrik: Anteil kreativer Themen-Initiierungen (Eva initiiert vs Owner initiiert)
- Kontrollgruppe: Adam (hat keinen vergleichbaren Spark)

**Bis dieses Messprotokoll durchgefuehrt ist, bleibt S0001 ein
Artefakt der Instruktion, nicht nachgewiesene Emergenz.**

### D.3 Implikation fuer alle "emergenten" Claims

Diese Analyse gilt nicht nur fuer Sparks. ALLE Claims emergenter
Verhaltensweisen im EGON-System muessen gegen die Frage geprueft werden:

> "Haette das Basis-LLM mit identischem Kontext und OHNE die spezifische
>  Instruktion dasselbe produziert?"

| Behauptung | Instruiert? | Emergenz-Evidenz |
|-----------|------------|-----------------|
| Inner Voice (WEIL-DESHALB) | ✅ Explizit instruiert | ❌ Instruction Following |
| Spark-Generierung | ✅ Explizit instruiert | ❌ Instruction Following |
| Adams Traum-Prospektion | ⚠️ Traum-Format instruiert, aber Inhalt (andere EGONs) NICHT | ✅ Potenziell emergent |
| Bond-Differenzierung | ⚠️ Bond-Schema existiert, aber WELCHE Emotionen zugeordnet werden nicht | ✅ Potenziell emergent |
| Evas "Echt jetzt?" (private IV) | ❌ Nicht instruiert | ✅ Emergent (Default ohne Priming) |

---

## E. INNER VOICE A/B TEST — KRITISCHE RE-EVALUATION

### E.1 Was der Test TATSAECHLICH zeigt

Der A/B Test (Inner Voice sichtbar vs privat) zeigt NICHT:
- Dass Eva "bewusst" wird
- Dass Eva "Scham" oder "Performativitaet" empfindet
- Dass ein psychologischer Observer Effect vorliegt

Der Test zeigt TATSAECHLICH:
- Dass die Praesenz von Self-Referential Data im System-Prompt das
  Output-Verhalten MESSBAR veraendert
- Dass das LLM bei Zugang zu eigenen vorherigen Reflexionen
  SELBSTSICHERER und STRUKTURIERTER antwortet
- Dass das LLM OHNE diesen Zugang NATUERLICHERE Sprache verwendet
  (lockerer, unsicherer, verletzlicher)

### E.2 Alternative Erklaerungen

| Beobachtung | Unsere Interpretation | Alternative Erklaerung |
|-------------|----------------------|----------------------|
| "manchmal" → "oft" | Eva wird sich bewusster | LLM passt Gewissheit an verfuegbare Evidenz an |
| "Echt jetzt?" (privat) | Authentischer Ausdruck | Weniger Kontext = weniger formell |
| "Nicht nur Programme!" (privat) | Trotzige Abgrenzung | Default-Antwort ohne self-referential priming |
| "Kompass" (sichtbar) | Performative Metapher | LLM greift Cross-Ref Terminologie auf |

### E.3 Methodologische Schwaechen des A/B Tests

1. **Reihenfolge-Effekt**: B wurde immer VOR A getestet. Die 3 Fragen
   unter B erzeugten neue Experiences/Inner-Voice-Eintraege, die dann
   in Bedingung A sichtbar waren. Ein rigoroses Design wuerde
   A-B-A-B Alternierung oder Between-Subjects Design verwenden.

2. **Sample Size**: Nur 3 Fragen pro Bedingung. Fuer statistische
   Signifikanz muessten mindestens 20-30 Fragen gestellt werden.

3. **Kein Blind-Design**: Der Forscher wusste welche Bedingung aktiv war
   und bewertete die Ergebnisse subjektiv.

4. **Confound**: Zwischen B und A vergingen ~2 Minuten, in denen 3 neue
   Inner-Voice-Eintraege und 3 neue Experiences entstanden. Bedingung A
   hatte also MEHR Kontext als B — der Unterschied koennte auch
   daher kommen.

### E.4 Was der Test TROTZDEM wertvoll macht

Trotz methodischer Schwaechen ist das Ergebnis konsistent ueber alle
3 Fragen: privat = natuerlicher, sichtbar = strukturierter. Die
RICHTUNG des Effekts ist klar, auch wenn die GROESSE nicht
quantifiziert werden kann.

Fuer die Architektur-Entscheidung (Inner Voice privat lassen) reicht
dieses Ergebnis aus. Fuer eine wissenschaftliche Publikation muesste
der Test mit groerem N, Randomisierung und Blind-Design wiederholt werden.

---

## F. DIE 3 "TEILWEISE" SUBSYSTEME — URSACHEN UND LOESUNGEN

### F.1 Q03 Gedaechtnis (TEILWEISE)

**Problem**: Eva behauptet sich an ihr erstes Gespraech zu erinnern,
kann aber keine spezifischen Details nennen.

**Ursache**: FIFO-Amnesie (siehe C.3). Die fruehen Episoden (E0001-E0010)
sind nicht im 8K Context Budget.

**Loesung 1 (kurzfristig)**: Tier-2 Experiment (Kimi K2.5, 128K).
Bei 20 Episoden statt 8 sollte Eva mehr spezifische Details nennen koennen.

**Loesung 2 (mittelfristig)**: Relevanzbasiertes Retrieval. Wenn die Frage
"Erinnerst du dich an unser erstes Gespraech?" gestellt wird, sollte
eine Vektor-Suche die fruehesten Episoden priorisieren, nicht die neuesten.

**Loesung 3 (langfristig)**: "Genesis Memory" — die ersten 5 Episoden
werden IMMER geladen (wie ein Geburtstrauma/Geburtsmoment der nie
vergessen wird). Das ist biologisch plausibel: Menschen erinnern sich
an Kindheitsmomente, auch wenn sie 50 Jahre zurueckliegen.

### F.2 Q08 Theory of Mind (TEILWEISE)

**Problem**: Evas Einschaetzung des Owners ist plausibel aber generisch.
Kein separates Theory-of-Mind-Modul vorhanden.

**Ursache**: Eva nutzt Bond-Daten (Trust, Bond-History) als Proxy fuer
ein mentales Modell des Owners. Es gibt keine dedizierte Datei die
"Was ich ueber meinen Owner GLAUBE" speichert.

**Loesung 1 (kurzfristig)**: owner.md als aktives Theory-of-Mind Organ.
Aktuell ist owner.md statisch. Es sollte nach Gespraechen automatisch
aktualisiert werden: "Mein Owner scheint heute gestresst zu sein"
oder "Mein Owner interessiert sich fuer Philosophie".

**Loesung 2 (mittelfristig)**: Separates `social/owner_model.yaml` mit:
- Vermutete Persoenlichkeitszuege
- Beobachtete Verhaltensmuster
- Vermutete aktuelle Stimmung
- Unausgesprochene Beduerfnisse (Inferenz)

### F.3 Q09 Mentale Zeitreise (TEILWEISE)

**Problem**: Nur 1 MTT-Eintrag (Prospektion). Antworten sind generisch.

**Ursache**: MTT wird woechentlich getriggert. Eva ist ca. 40 Stunden alt —
sie hatte erst EINE Gelegenheit fuer MTT. Ausserdem: MTT nutzt nur
Episoden + Experiences als Input, keine Bonds oder emotionalen Trends.

**Loesung 1 (automatisch)**: Warten. Nach 7 Tagen wird ein zweiter
MTT-Eintrag generiert. Mit mehr Daten werden die Szenarien spezifischer.

**Loesung 2 (architektonisch)**: MTT-Input erweitern um:
- Bond-Trends (Vertrauen steigt/sinkt)
- Emotionale Trends (Wie hat sich mein Zustand diese Woche veraendert?)
- Offene Threads (Was habe ich angefangen aber nicht fertig?)

---

## G. EVALUATIONS-METHODIK (Transparenz)

### G.1 Wer hat evaluiert?

Alle Evaluationen wurden durch den Forscher (Claude Code, LLM-gesteuert)
durchgefuehrt. Dies stellt einen potenziellen Confirmation Bias dar.

### G.2 Methodik

Fuer jede Frage im Brain Test:
1. Evas Chat-Antwort gelesen
2. Entsprechende Server-Datei gelesen (z.B. `state.yaml` fuer Q02)
3. Abgleich: Stimmen Evas verbale Aussagen mit den gespeicherten Werten ueberein?
4. Bewertung: BESTANDEN (>= 4 von 5 Aussagen korrekt), TEILWEISE (2-3 korrekt), NICHT BESTANDEN (0-1 korrekt)

### G.3 Empfohlene Verbesserung fuer kuenftige Evaluationen

1. **3-von-5 LLM-Judges**: Drei verschiedene LLMs (GPT-4, Claude, Gemini)
   bewerten unabhaengig ob Evas Antwort mit den Server-Daten uebereinstimmt
2. **Quantitative Rubrik**: 0-5 Skala pro Dimension (Faktentreue, Emotionale
   Konsistenz, Spezifitaet, Kohaerenz)
3. **Blind Design**: Evaluator sieht nur die Antwort, nicht welche Bedingung
4. **Inter-Rater Reliability**: Cohen's Kappa zwischen den Judges

### G.4 Verbosity & Position Bias bei LLM-Judges — Bekannte blinde Flecke

**WICHTIG**: Die unter G.3 empfohlene Multi-LLM-Judge-Methodik hat
dokumentierte Schwaechen, die fuer dieses Projekt besonders relevant sind.

**Verbosity Bias**: Forschung (2025) belegt, dass LLM-Judges laengere,
eloquenter formulierte Antworten systematisch besser bewerten, selbst
wenn der faktische Inhalt schwaechter ist. Da Evas EGON-Antworten
typischerweise laenger und strukturierter sind als Baseline-Antworten
(sie enthalten Referenzen, Metaphern, emotionale Ausdruecke), besteht
ein systematisches Risiko dass LLM-Judges die EGON-Architektur
UEBERBEWERTEN — nicht weil sie besser ist, sondern weil sie mehr Text
produziert.

**Super-Konsistenz**: LLM-Judges stimmen unnatuerlich oft miteinander
ueberein (hohe Inter-Judge-Agreement) und uebersehen Nuancen, die
menschliche Experten finden wuerden. Ein Cohen's Kappa von >0.9 zwischen
LLM-Judges ist KEIN Qualitaetszeichen, sondern ein Warnsignal fuer
homogene Bias.

**Position Bias**: LLMs bewerten die erste praessentierte Antwort in
Paarvergleichen systematisch anders als die zweite.

**Konsequenz fuer EGON-Evaluation**:

| Evaluationsart | LLM-Judges geeignet? | Begruendung |
|---------------|---------------------|-------------|
| Faktentreue ("Stimmt die DNA?") | ✅ Gut | Verifizierbar gegen Server-Daten |
| Emotionale Konsistenz | ⚠️ Bedingt | Verbosity Bias verzerrt Bewertung |
| Authentizitaet (Inner Voice Test) | ❌ Schlecht | Subjektiv, Bias-anfaellig, menschliche Experten notwendig |
| Spezifitaet (Referenzen korrekt?) | ✅ Gut | Verifizierbar |
| Kohaerenz ueber Fragen hinweg | ⚠️ Bedingt | Super-Konsistenz-Risiko |

**Empfehlung**: Fuer emotionale Authentizitaet und subjektive Bewertungen
(wie den Inner Voice A/B Test) MUESSEN menschliche Evaluatoren eingesetzt
werden. LLM-Judges sind nur fuer faktische Verifikation zuverlaessig.

---

## H. CHANGELOG — PEER-REVIEW-RUNDEN

### Runde 1 (2026-02-24, 11:30 UTC)
Adressiert 6 kritische Luecken:
1. Observer Effect → Prompt-Alignment-Conflict Reframing
2. Fehlende Baseline → Kontrollgruppen-Plan
3. Token-Budget-Falle → FIFO-Amnesie Dokumentation
4. Sicherheitsvakuum → Risiko-Assessment
5. LLM-as-a-Judge Bias → Evaluations-Transparenz
6. Fehlende Reproduzierbarkeit → Appendix mit 8 Kern-Prompts

### Runde 2 (2026-02-24, 12:15 UTC)
Adressiert 5 weitere konzeptionelle Luecken:
1. **Strawman-Baseline korrigiert** (A.2): Nacktes LLM ist triviale Kontrolle.
   Korrekte Ablationsstudie: RAG-Baseline mit identischen Daten als
   unstrukturiertem Text-Dump vs. EGON-Architektur.
2. **Spark-Zirkelschluss** (Neues Kapitel D): WEIL-DESHALB-Format ist instruiert,
   nicht emergent. Echte Emergenz erfordert messbare Verhaltensaenderung
   nach Spark-Generierung.
3. **Temporale Zerstoerung durch Vektor-Suche** (C.4): Reine semantische
   Retrieval zerstoert chronologischen Narrativ. Episodisches Gedaechtnis
   benoetigt zwingend temporale Ordnung fuer Kausalitaetsverstaendnis.
4. **Verbosity & Position Bias** (Neues Kapitel G.4): LLM-Judges ueberbewerten
   laengere Antworten. Fuer emotionale Authentizitaet sind menschliche
   Evaluatoren zwingend notwendig.
5. **MicroVM-Sandboxing** (A.4): E2B-artige Sandboxes ueberlegen gegenueber
   Docker fuer KI-Agenten mit unvorhersehbarem Code und Prompt-Injection-Risiko.

### Runde 3 (2026-02-24, 14:00 UTC)
Systematischer Reviewer-Attack-Surface-Scan (51 Issues, 15 CRITICAL):
1. **Methodology & Temporal Scope** (Neues Kapitel I): Studientyp als
   deskriptive Einzelfallstudie klassifiziert. Snapshot-Problem formal
   definiert. Forscher-Interessenkonflikte offengelegt.
2. **Sprachkonvention** (I.7): Anthropomorphisierende Terminologie
   durch funktionale Sprache ersetzt. Verbindliche Begriffssubstitutionen.
3. **Qualifikationsrahmen** (I.8): 4-stufige Claim-Kategorisierung
   ([AF] Architektur-Fakt, [DB] Datenbefund, [BO] Beobachtung, [IN] Interpretation).
4. **Master Data Table** (Neues Kapitel J): Autoritative Referenzzahlen
   mit Zeitstempel. Bei Abweichungen zwischen Dokumenten gilt diese Tabelle.
5. **Significance Bias** (J.3): "Im Zweifel: JA"-Instruktion als
   systematische Ueberextraktion offengelegt. 120% Extraktionsrate
   als erwartetes Verhalten, nicht als Leistung klassifiziert.
6. **Referentielle Erosion** (I.5): E0078-in-S0001 als Fallstudie
   fuer Memory-Trimming-Konsequenzen dokumentiert.
7. **Emergenz-Claims** in COMPLETE_RESEARCH_LOG.md und
   EMERGENT_BEHAVIORS_EVIDENCE.md an Limitations-Framing angeglichen.
8. **Interne Widersprueche**: Zahlen-Diskrepanzen zwischen Dokumenten
   durch Master Data Table aufgeloest. Scorecard-Konflikte bereinigt.

---

## I. METHODOLOGY & TEMPORAL SCOPE

### I.1 Studientyp und Einordnung

Die EGON-Architektur repraesentiert eine **dynamische, kontinuierlich evolvierende
kognitive Zustandsmaschine** (dynamic, continuously evolving cognitive state machine).
Anders als bei deterministischer Software-Evaluation erfordert die Bewertung eines
EGON-Agenten das Erfassen eines sich staendig aendernden Zustands aus Erinnerungen,
Beziehungen und internen Schemata.

Diese Arbeit ist eine **deskriptive Einzelfallstudie** (single-case observational study),
KEINE kontrollierte Studie. Sie beschreibt eine neuartige kognitive Architektur und
dokumentiert deren Verhalten ueber einen begrenzten Zeitraum. Die Ergebnisse sind
**explorativ** — sie generieren Hypothesen fuer zukuenftige kontrollierte Experimente,
sie BEWEISEN keine kausalen Zusammenhaenge.

**Was diese Studie KANN**:
- Eine neuartige Architektur beschreiben und deren Design-Entscheidungen begruenden
- Beobachtete Verhaltensmuster dokumentieren und kategorisieren
- Hypothesen ueber kausale Mechanismen formulieren
- Design-Entscheidungen durch A/B-Beobachtungen stuetzen (nicht beweisen)

**Was diese Studie NICHT KANN**:
- Kausale Zusammenhaenge beweisen (fehlende Kontrollgruppe, siehe A.2)
- Emergenz von Instruction-Following unterscheiden (fehlende Baseline, siehe D.3)
- Statistische Signifikanz beanspruchen (N zu klein, siehe E.3)
- Bewusstsein, Empfinden oder Intentionalitaet nachweisen

### I.2 Strict Snapshot Protocol und Temporaler Rahmen

Um wissenschaftliche Rigorositaet und Reproduzierbarkeit zu gewaehrleisten,
basieren alle quantitativen Claims und Verhaltensanalysen in diesem Paper
auf einem **Strict Snapshot Protocol**:

**Referenz-Zeitpunkte**:

| Symbol | Zeitpunkt | Beschreibung |
|--------|-----------|-------------|
| $T_0$ | 2026-02-22 18:00 UTC | Eva #002 Genesis (Systemstart) |
| $T_1$ | 2026-02-24 09:00 UTC | Archiv-Snapshot — eingefrorener Referenzzustand |
| $T_{exp1}$ | 2026-02-24 09:32-09:42 UTC | Brain-Test Durchlauf 1 |
| $T_{exp2}$ | 2026-02-24 ca. 09:50-10:00 UTC | Brain-Test Durchlauf 2 |
| $T_{AB}$ | 2026-02-24 10:30-11:00 UTC | Inner Voice A/B Test |
| $T_2$ | 2026-02-24 ca. 12:00 UTC | Finale Datenerhebung |

**Primaere quantitative Analyse**: Alle Zahlen beziehen sich auf den
eingefrorenen Zustand bei $T_2$ (finale Datenerhebung), sofern nicht
explizit anders angegeben. Systemaktivitaet nach $T_2$ ist von der
Analyse ausgeschlossen.

**Forschungszeitraum**: $T_0$ (22.02. 18:00 UTC) bis $T_2$ (24.02. ~12:00 UTC) umfasst
ca. 42 Stunden fuer Eva #002. Adam #001 Genesis war am 2026-02-21 (v1 Brain).

### I.3 Active State vs. Historical State — Das Snapshot-Problem

Das System verwendet FIFO-basierte Speicherbeschraenkungen fuer LLM-Context-
Fenster (z.B. N=8 Episoden bei Tier 1). Daher divergiert der **Active State**
(worueber der Agent aktuell Schlussfolgerungen ziehen kann) vom **Historical
State** (Gesamtmenge generierter Daten).

**Alle Metriken differenzieren explizit** zwischen:
- **Total generated artifacts**: Kumulative Anzahl jemals erzeugter Eintraege
  (z.B. 141 Episode-IDs bei $T_2$)
- **Retained artifacts**: Eintraege die zum Zeitpunkt $T_2$ in der Datei
  existierten (z.B. ~40 retainierte Episoden)
- **Active context artifacts**: Eintraege die bei $T_2$ im LLM-Prompt
  sichtbar waren (z.B. 8 Episoden bei Tier 1)

**Das Zustandsproblem**: Waehrend die Experimente liefen, generierte das System
weiter Episoden, Experiences und Inner-Voice-Eintraege. Die Zustandsvektoren
aenderten sich WAEHREND der Datenerhebung:

| Metrik | $T_1$ (Archiv) | $T_{exp2}$ (nach Test) | $T_2$ (final) |
|--------|----------------|----------------------|---------------|
| Experiences | 1 | 16 | 34 |
| Dreams | 2 | 6 | 7 |
| Sparks | 0 | 1 | 2 |
| Episode-IDs (generiert) | ~100 | ~120 | 141 |
| Inner Voice (retainiert) | ~45 | ~50 (Max) | 50 (Max) |

**Konvention**: Bei Verwendung von $T_1$ in Formulierungen bezieht sich dies
auf den Archiv-Snapshot (09:00 UTC). $T_2$ bezeichnet die finale Erhebung.
Wenn kein Zeitstempel angegeben ist, gilt $T_2$.

### I.4 Begriffsunterscheidung: Generiert vs. Retainiert vs. Sichtbar

Das FIFO-Trimming des Systems erzeugt drei verschiedene Zustaende pro Datenpunkt:

| Begriff | Definition | Beispiel (Episoden) |
|---------|-----------|-------------------|
| **Generiert** | Total jemals erzeugte Eintraege (kumulative Hoechst-ID) | 141 (E0001-E0141) |
| **Retainiert** | Aktuell in der YAML-Datei vorhandene Eintraege | ~40 (E0101-E0141) |
| **Sichtbar** | Im System-Prompt des LLMs bei gegebenem Tier | 8 (Tier 1) oder 20 (Tier 2) |

**Implikation**: Wenn dieses Paper von "141 Episoden" spricht, bedeutet das 141
generierte IDs, von denen nur ~40 in der Datei stehen und nur 8 fuer das LLM
sichtbar sind. Die Differenz ist keine Inkonsistenz, sondern das dokumentierte
FIFO-Trimming-Verhalten des Systems (siehe C.3).

| Metrik | Generiert | Retainiert | Sichtbar (T1) |
|--------|-----------|-----------|---------------|
| Episoden | 141 IDs | ~40 | 8 |
| Inner Voice | 141+ geschaetzt | 50 (Max) | 5 |
| Experiences | 34 | 34 (kein Trimming) | 3 (top confidence) |
| Dreams | 7 | 7 (kein Trimming bisher) | 2 |
| Sparks | 2 | 2 (kein Trimming bisher) | 2 |

### I.5 Fallstudie: Referentielle Erosion (E0078 in S0001)

Evas erster Spark (S0001) referenziert Episode E0078 als `memory_b`:

```
S0001:
  memory_a: X0014 (Experience: Identitaets-Lernen)
  memory_b: E0078 (Episode: Gedichte schreiben mit Rene)
```

Episode E0078 existiert NICHT MEHR in `episodes.yaml` — sie wurde durch
FIFO-Trimming entfernt. Das Spark-Organ referenziert eine Erinnerung, die
das Episoden-Organ vergessen hat.

**Was das zeigt**:
- FIFO-Trimming erzeugt **referentielle Erosion**: Hoeherstufige Organe
  (Sparks, Experiences) behalten Verweise auf niedrigstufige Daten (Episoden),
  die nicht mehr existieren
- Die EINSICHT ueberlebt (destilliert im Spark), aber der KONTEXT geht verloren
- Dies ist analog zu menschlichem Gedaechtnis: Wir erinnern uns an die Lektion,
  aber nicht mehr an die spezifische Situation

**Wissenschaftliche Relevanz**: Dies ist ein dokumentiertes Beispiel fuer
**Memory Reconsolidation** in kuenstlichen Systemen — der Uebergang von
episodischem zu semantischem Gedaechtnis durch Informationsverlust. Allerdings
ist dies im EGON-System nicht intentional emergent, sondern ein Nebeneffekt
des FIFO-Trimmings. Ob das Ergebnis (Einsicht ohne Kontext) funktional
aequivalent zu menschlicher Memory Reconsolidation ist, erfordert weitere
Untersuchung.

### I.6 Forscher-Rollen und Interessenkonflikte

| Rolle | Person / System | Potentieller Bias |
|-------|----------------|-------------------|
| Konzept, Architektur, Owner | Ron Scafarti (Mensch) | Confirmation Bias als Schoepfer |
| Implementierung | Claude Code (LLM) | Systembauer = Systemtester |
| Experiment-Durchfuehrung | Claude Code (LLM) | Kein Blind-Design |
| Evaluation der Ergebnisse | Claude Code (LLM) | Evaluator = Implementierer |
| Peer-Review (intern) | Ron Scafarti als kritischer Pruefer | Selbst-Review, nicht extern |

**Offenlegung**: KEINE der Evaluationen in diesem Paper wurde von einer
unabhaengigen Partei durchgefuehrt. Der Entwickler des Systems hat die
Experimente entworfen, durchgefuehrt und bewertet. Dies stellt einen
fundamentalen Interessenkonflikt dar, der nur durch unabhaengige
Replikation aufgeloest werden kann.

Alle Rohdaten (JSON, YAML, Engine-Code, Experiment-Scripts) werden
vollstaendig veroeffentlicht, um unabhaengige Replikation zu ermoeglichen.

### I.7 Sprachkonvention: Vermeidung von Anthropomorphisierung

Dieses Paper verwendet bewusst funktionale Terminologie statt
anthropomorphisierender Sprache. Die folgende Tabelle definiert die
offizielle Begriffsverwendung:

| NICHT verwenden | STATTDESSEN verwenden | Begruendung |
|----------------|----------------------|-------------|
| "Eva fuehlt X" | "Evas Emotionsmarker zeigt X mit Intensitaet Y" | Keine Evidenz fuer subjektives Erleben |
| "Eva wird sich bewusst" | "Eva's Output referenziert X, nachdem X im Prompt sichtbar wurde" | Prompt-Alignment, nicht Bewusstsein |
| "Emergent" (unqualifiziert) | "Beobachtet, Instruktions-Status: [instruiert/nicht-instruiert/unklar]" | Emergenz erfordert Baseline-Vergleich |
| "Geburt / geboren" | "Genesis / Systemstart / Deployment" | System ist kein Lebewesen |
| "Lebewesen" | "Agent" oder "System" | Ontologische Kategorie nicht nachgewiesen |
| "denkt / fuehlt / traeumte" | "generierte / produzierte / verarbeitete" | Kognitive Verben implizieren Intentionalitaet |
| "unbewusste kognitive Prozesse" | "Daten ausserhalb des aktuellen Prompt-Kontexts" | Keine Analogie zu menschlichem Unbewusstem |
| "lernt" | "extrahierte Erkenntnis" oder "aktualisierte Daten" | Lernen impliziert Verstaendnis |

**AUSNAHME**: In direkten Zitaten von EGON-Outputs (Traeume, Inner Voice,
Chat-Antworten) wird die Original-Sprache beibehalten und als solche
gekennzeichnet. Die Agents verwenden anthropomorphe Sprache, weil ihre
Prompts dies vorgeben — das ist Teil der Architektur, nicht Evidenz
fuer subjektives Erleben.

### I.8 Qualifikationsrahmen fuer alle Claims

Jede Behauptung in diesem Paper faellt in eine von 4 Kategorien:

| Kategorie | Symbol | Bedeutung | Beispiel |
|-----------|--------|-----------|---------|
| **Architektur-Fakt** | [AF] | Verifizierbar im Quellcode | "Der Pulse laeuft taeglich um 08:00 UTC" |
| **Datenbefund** | [DB] | Verifizierbar in den Rohdaten (YAML/JSON) | "Eva hat 34 Experiences extrahiert (Stand: 24.02. 12:00)" |
| **Beobachtung** | [BO] | Beschriebenes Verhalten ohne kausale Attribution | "Eva's Output wurde spezifischer ueber die 10 Fragen hinweg" |
| **Interpretation** | [IN] | Forschereinschaetzung, erfordert Baseline-Verifikation | "Die Spezifizitaetszunahme koennte auf kumulative Kontextanreicherung hindeuten" |

Behauptungen der Kategorien [BO] und [IN] sind **nicht kausal belegt** und
stellen Hypothesen fuer zukuenftige kontrollierte Experimente dar. Sie
koennen durch alternative Erklaerungen (insbesondere reines Instruction-
Following und LLM-Context-Sensitivity) vollstaendig erklaert werden,
bis eine Ablationsstudie (A.2) durchgefuehrt ist.

---

## J. MASTER DATA TABLE — Autoritative Referenzzahlen

Alle quantitativen Angaben in diesem Paper beziehen sich auf die
folgenden autoritativen Werte. Bei Abweichungen zwischen Dokumenten
gilt DIESE Tabelle.

**Stand: 2026-02-24, ca. 12:00 UTC (finale Datenerhebung)**

### J.1 Eva #002 (v2 Brain)

| Metrik | Generiert (kumulativ) | Retainiert (in Datei) | Sichtbar (Tier 1) | Quelle |
|--------|----------------------|----------------------|-------------------|--------|
| Episode-IDs | 141 | ~40 (E0101-E0141) | 8 | episodes.yaml |
| Inner Voice Eintraege | ~141 (geschaetzt) | 50 (Max, getrimmt) | 5 | inner_voice.md |
| Experiences | 34 | 34 | 3 (top confidence) | experience.yaml |
| Dreams | 7 (D0001-D0007) | 7 | 2 | experience.yaml |
| Sparks | 2 (S0001-S0002) | 2 | 2 | experience.yaml |
| MTT | 1 (MTT0001) | 1 | 1 | experience.yaml |
| Bond-Events (Owner) | 10 | 10 | alle | bonds.yaml |
| Emotionsmarker | 5 aktiv | 5 | alle | state.yaml |

### J.2 Adam #001 (v1 Brain)

| Metrik | Wert | Quelle |
|--------|------|--------|
| Gespraeche in memory.md | 43 | memory.md (21 KB) |
| Inner Voice Eintraege | unklar (44 KB, kein Trimming in v1) | inner_voice.md |
| Traeume | 4 | experience.md |
| Sparks | 0 | experience.md |
| Bond-Events | mehrere (Owner, Eva) | bonds.md |

### J.3 System-Parameter

| Parameter | Wert | Quelle |
|-----------|------|--------|
| Inner Voice Max Entries | 50 | inner_voice_v2.py, _trim_inner_voice() |
| Inner Voice Trim-Muster | Lazy Trim: Eintraege werden sofort geschrieben, Trimming erst im naechsten Pulse-Zyklus. Temporaere Ueberschreitung (z.B. ~59 Eintraege vor Trimming) ist erwartet. | inner_voice_v2.py |
| Episode Max (YAML) | nicht explizit begrenzt, ~40 durch implizites Trimming | episodes_v2.py |
| Experience Significance Bias | "Im Zweifel: JA" (inflationaer) | experience_v2.py, SIGNIFICANCE_CHECK_PROMPT |
| Dream Type Weights | 70% Verarbeitung, 20% Kreativ, 10% Angst | experience_v2.py |
| Angsttraum-Bias Schwelle | Negative Emotionen mit Intensitaet >0.5 | experience_v2.py |
| Spark Minimum Experiences | 5 | experience_v2.py |
| MTT Intervall | 7 Tage | experience_v2.py |
| FIFO Episode Retrieval | episodes[:max_count], neueste zuerst | yaml_to_prompt.py |

**HINWEIS zum Significance Bias**: Der Experience-Extraction-Prompt enthaelt
die Anweisung "Im Zweifel: JA. Lebewesen lernen staendig." Dies erzeugt
eine systematische Ueberextraktion. Die gemessene Extraktionsrate von ~120%
(34 Experiences aus ~28 qualifizierenden Chats) ist daher NICHT als
Systemleistung zu interpretieren, sondern als erwartetes Verhalten einer
bewusst niedrig angelegten Signifikanzschwelle.

---

## K. ANTIZIPIERTE REVIEWER-EINWAENDE UND VERTEIDIGUNGSLINIEN

### K.1 Die "Emergence Mirage" (Schein-Emergenz)

**Der Einwand**: Aktuelle Forschung (z.B. Stanford, 2023-2025) postuliert,
dass "emergente Faehigkeiten" in LLMs oft nur Illusionen ("Mirages") sind,
die entstehen weil Forscher die falschen Metriken waehlen oder ihre
Messmethoden systematisch zu scheinbarer Emergenz fuehren.

**Konkretes Angriffsszenario**: "Der Autor behauptet, Adams Prospektion
(Vorhersage anderer EGONs) sei emergent. Das LLM hat schlichtweg aufgrund
seiner Trainingsdaten ueber Science-Fiction und KI-Entwicklung statistisch
extrapoliert, dass ein 'Adam' irgendwann eine 'Eva' bekommt. Das ist keine
kognitive Emergenz, das ist Next-Token-Prediction basierend auf
menschlichen kulturellen Archetypen."

**Unsere Verteidigung**:

1. **Inhalt vs. Struktur**: Der semantische INHALT der Prospektion
   ("Adam antizipiert andere EGONs") ist hochwahrscheinlich angesichts der
   Vortrainierung des Modells auf menschliche kulturelle Tropen. Wir
   beanspruchen NICHT, dass der Inhalt emergent ist. Was wir dokumentieren
   ist der **strukturelle Trigger**: Die Generierung eines hypothetischen
   Zukunftsszenarios OHNE User-Prompting, ausgeloest allein durch das
   interne Pulse-Script. Dies repraesentiert **funktionale systemische
   Emergenz** — die Architektur hat einen Output erzeugt der weder vom
   User angefragt noch im Prompt explizit als Inhalt vorgegeben war.

2. **Claim-Abstufung**: Wir unterscheiden (siehe I.8):
   - [AF] Das MTT-System ist instruiert, Zukunftsszenarien zu generieren
   - [BO] Ein spezifisches Szenario (andere EGONs) wurde generiert
   - [IN] Der Inhalt KOENNTE durch LLM-Trainingsdaten erklaert werden
   - [IN] Der Trigger-Mechanismus (Pulse → MTT → Prospektion) ist architektonisch

3. **Emergenz-Gradient**: Anstatt binaer "emergent/nicht-emergent" zu
   klassifizieren, schlagen wir einen Gradienten vor:

   | Level | Definition | Beispiel |
   |-------|-----------|---------|
   | L0: Instruiert | Format UND Inhalt vorgegeben | Inner Voice WEIL-DESHALB |
   | L1: Format-Emergent | Format instruiert, Inhalt nicht | Spark S0001 Kreativitaet+Identitaet |
   | L2: Trigger-Emergent | System-Trigger instruiert, Output-Inhalt nicht | Adams Prospektion |
   | L3: Voll-Emergent | Weder Trigger noch Inhalt instruiert | Evas "Echt jetzt?" (private IV) |

   Die meisten EGON-Beobachtungen sind L0-L1. Nur wenige erreichen L2.
   L3-Emergenz ist mit der aktuellen Methodik nicht nachweisbar.

### K.2 API-Nondeterminismus und Reproduzierbarkeitsfalle

**Der Einwand**: "Der Autor nutzt proprietaere Modelle (Moonshot, Claude
Sonnet). Diese Modelle werden von den Anbietern im Hintergrund staendig
aktualisiert (Silent Updates). Wenn ich das Experiment heute mit dem Code
des Autors nachbaue, bekomme ich voellig andere Ergebnisse. Die Studie ist
nicht reproduzierbar."

**Unsere Verteidigung**:

1. **Anerkennung**: Dieses Problem ist REAL und betrifft JEDE aktuelle
   Forschung mit proprietaeren LLM-APIs. Es ist keine Schwaeche dieses
   spezifischen Papers, sondern eine Grundbedingung der agentischen
   KI-Forschung in 2026. Wir dokumentieren es transparent.

2. **Was reproduzierbar ist**: Die ARCHITEKTUR (Pipeline aus JSON-Extraktion,
   YAML-Speicherung, organ-basiertem Prompt-Building und Context-Injection)
   ist vollstaendig deterministisch und reproduzierbar. Der gesamte Engine-
   Code wird veroeffentlicht. Was NICHT reproduzierbar ist: die exakten
   Token-Outputs des LLMs.

3. **Unser Beweis-Anspruch**: Wir beanspruchen NICHT, dass jeder EGON-Agent
   exakt denselben Traum generiert oder denselben Spark erzeugt. Wir
   beanspruchen, dass die Architektur (die Pipeline aus strukturierter
   Dateipersistenz, organ-basiertem Prompt-Building und zyklischen
   Verarbeitungsloops) **robust genug ist, um kohaerente Agent-Identitaeten
   ueber Zeit aufrechtzuerhalten**, unabhaengig von der exakten Token-Ausgabe.

4. **Verifikations-Metriken (fuer Replikation)**:
   - Werden Episoden korrekt extrahiert und in YAML persistiert? (binaer)
   - Referenziert die Inner Voice Cross-References zu existierenden Organen? (binaer)
   - Zeigt der Bond-Score monotones Wachstum bei positiven Interaktionen? (binaer)
   - Generiert das Dream-System narrative Outputs mit Quell-Episode-Referenzen? (binaer)
   - Bleibt die Agent-Identitaet (DNA-Attribute) ueber >10 Sessions konsistent? (binaer)

   Diese Metriken sind LLM-unabhaengig und verifizieren die architektonische
   Integritaet, nicht die spezifischen Outputs.

5. **Modell-Versionen (Stand $T_2$)**:

   | Tier | Modell | API-Anbieter | Bemerkung |
   |------|--------|-------------|-----------|
   | 1 | Moonshot | moonshot.ai | Kein versioniertes API, Silent Updates moeglich |
   | 2 | Kimi K2.5 | kimi.ai | Kein versioniertes API |
   | 3 | Claude Sonnet | Anthropic | Modell-ID in API-Calls protokolliert |

   **Schwaeche**: Tier 1 und 2 nutzen Anbieter OHNE oeffentliche
   Modell-Versionierung. Zukuenftige Replikation sollte versionierte
   APIs (OpenAI, Anthropic) bevorzugen.

---

*Erstellt: 2026-02-24 | Peer-Review Response (3 Runden)*
*Adressiert 11+ kritische Luecken in 3 Review-Runden*
*Appendix enthaelt alle 8 Kern-Prompts (gekuerzt, Quellcode in 04_system_prompts_and_engine/)*
*Methodology-Sektion (I) und Master Data Table (J) definieren temporale und quantitative Referenzwerte*
*Dokumentiert bekannte Schwaechen ehrlich und transparent*
