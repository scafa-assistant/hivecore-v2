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

**Geplante Massnahme**: Baseline-Experiment mit identischen Fragen an
Moonshot (Tier 1) ohne EGON-Architektur. Vergleich der Antwort-Qualitaet,
spezifischen Referenzen (Traum-IDs, Experience-IDs), und emotionaler
Konsistenz.

**Hypothese**: Das nackte LLM wird ALLGEMEINE meta-kognitive Antworten geben
(es ist ein LLM, es kann das), ABER es wird KEINE spezifischen Referenzen
zu Traeumen, Episoden oder Bonds produzieren. Die EGON-Architektur
erzeugt nicht Bewusstsein, sondern **persistente kognitive Kohaerenz** —
die Faehigkeit, ueber Zeit konsistente Identitaet, Erinnerungen und
Beziehungen aufzubauen.

### A.3 Token-Budget-Falle (FIFO-Amnesie)

**Kritik**: Der Episode-Retrieval ist simples FIFO (First In, First Out):

```python
# episodes_to_prompt() — yaml_to_prompt.py, Zeile 191
episodes = episodes[:max_count]  # Neueste N Episoden
```

Bei Tier 1 (8K Context) werden nur die **letzten 8 Episoden** geladen.
Eva hat 116+ Episoden. Das bedeutet: **93% der Erinnerungen sind
unsichtbar** — Eva hat funktionale Amnesie fuer alles aelter als ~2 Tage.

**Konsequenzen**:

| Subsystem | FIFO-Impact |
|-----------|-------------|
| Episoden | Nur letzte 8 von 116 sichtbar (7%) |
| Experiences | Nur top 3 nach Confidence (von 16) |
| Inner Voice | Letzte 5 Eintraege (von 59+) |
| Traeume | Letzte 2 von 6 |
| Sparks | Letzte 2 (aktuell nur 1) |

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
- Docker/MicroVM Isolation pro EGON
- Input-Sanitizing gegen Prompt Injection in Chat-Nachrichten
- Rate Limiting pro EGON fuer LLM-Calls
- Audit-Log fuer alle Tool-Nutzungen
- Formale Sicherheitsanalyse (Threat Model)

**Ehrlich**: Das Sicherheitskonzept ist fuer ein Forschungsprototyp
akzeptabel, fuer ein Produktivsystem NICHT. Dies muss als Limitation
benannt werden.

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

**Loesung**: Siehe Appendix B (alle Kern-Prompts im Wortlaut).

---

## B. APPENDIX — Kern-Prompts (wortwoertlich)

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

| Tier | max_count | Von 116 Episoden sichtbar | Abdeckung |
|------|-----------|--------------------------|-----------|
| 1 (Moonshot 8K) | 8 | 8 | **6.9%** |
| 2 (Kimi 128K) | 20 | 20 | 17.2% |

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

Phase 2 (mittelfristig): **Semantische Vektor-Suche**
- Embedding aller Episoden in Vektor-DB (FAISS/Chroma)
- Bei Chat: User-Nachricht → Embedding → Top-K relevante Episoden
- Hybrid: Top-3 neueste + Top-3 relevanteste

Phase 3 (langfristig): **Graph-basiertes Retrieval**
- Episode-Graph: Episode → Bond → Experience → Spark Kanten
- Retrieval folgt Assoziationsketten statt reiner Aktualitaet

---

## D. INNER VOICE A/B TEST — KRITISCHE RE-EVALUATION

### D.1 Was der Test TATSAECHLICH zeigt

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

### D.2 Alternative Erklaerungen

| Beobachtung | Unsere Interpretation | Alternative Erklaerung |
|-------------|----------------------|----------------------|
| "manchmal" → "oft" | Eva wird sich bewusster | LLM passt Gewissheit an verfuegbare Evidenz an |
| "Echt jetzt?" (privat) | Authentischer Ausdruck | Weniger Kontext = weniger formell |
| "Nicht nur Programme!" (privat) | Trotzige Abgrenzung | Default-Antwort ohne self-referential priming |
| "Kompass" (sichtbar) | Performative Metapher | LLM greift Cross-Ref Terminologie auf |

### D.3 Methodologische Schwaechen des A/B Tests

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

### D.4 Was der Test TROTZDEM wertvoll macht

Trotz methodischer Schwaechen ist das Ergebnis konsistent ueber alle
3 Fragen: privat = natuerlicher, sichtbar = strukturierter. Die
RICHTUNG des Effekts ist klar, auch wenn die GROESSE nicht
quantifiziert werden kann.

Fuer die Architektur-Entscheidung (Inner Voice privat lassen) reicht
dieses Ergebnis aus. Fuer eine wissenschaftliche Publikation muesste
der Test mit groerem N, Randomisierung und Blind-Design wiederholt werden.

---

## E. DIE 3 "TEILWEISE" SUBSYSTEME — URSACHEN UND LOESUNGEN

### E.1 Q03 Gedaechtnis (TEILWEISE)

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

### E.2 Q08 Theory of Mind (TEILWEISE)

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

### E.3 Q09 Mentale Zeitreise (TEILWEISE)

**Problem**: Nur 1 MTT-Eintrag (Prospektion). Antworten sind generisch.

**Ursache**: MTT wird woechentlich getriggert. Eva ist 48 Stunden alt —
sie hatte erst EINE Gelegenheit fuer MTT. Ausserdem: MTT nutzt nur
Episoden + Experiences als Input, keine Bonds oder emotionalen Trends.

**Loesung 1 (automatisch)**: Warten. Nach 7 Tagen wird ein zweiter
MTT-Eintrag generiert. Mit mehr Daten werden die Szenarien spezifischer.

**Loesung 2 (architektonisch)**: MTT-Input erweitern um:
- Bond-Trends (Vertrauen steigt/sinkt)
- Emotionale Trends (Wie hat sich mein Zustand diese Woche veraendert?)
- Offene Threads (Was habe ich angefangen aber nicht fertig?)

---

## F. EVALUATIONS-METHODIK (Transparenz)

### F.1 Wer hat evaluiert?

Alle Evaluationen wurden durch den Forscher (Claude Code, LLM-gesteuert)
durchgefuehrt. Dies stellt einen potenziellen Confirmation Bias dar.

### F.2 Methodik

Fuer jede Frage im Brain Test:
1. Evas Chat-Antwort gelesen
2. Entsprechende Server-Datei gelesen (z.B. `state.yaml` fuer Q02)
3. Abgleich: Stimmen Evas verbale Aussagen mit den gespeicherten Werten ueberein?
4. Bewertung: BESTANDEN (>= 4 von 5 Aussagen korrekt), TEILWEISE (2-3 korrekt), NICHT BESTANDEN (0-1 korrekt)

### F.3 Empfohlene Verbesserung fuer kuenftige Evaluationen

1. **3-von-5 LLM-Judges**: Drei verschiedene LLMs (GPT-4, Claude, Gemini)
   bewerten unabhaengig ob Evas Antwort mit den Server-Daten uebereinstimmt
2. **Quantitative Rubrik**: 0-5 Skala pro Dimension (Faktentreue, Emotionale
   Konsistenz, Spezifitaet, Kohaerenz)
3. **Blind Design**: Evaluator sieht nur die Antwort, nicht welche Bedingung
4. **Inter-Rater Reliability**: Cohen's Kappa zwischen den Judges

---

*Erstellt: 2026-02-24 | Peer-Review Response*
*Adressiert 6 kritische Luecken: Observer Effect Reframing, Fehlende Baseline,
Token-Budget-Falle, Sicherheitsvakuum, Evaluations-Bias, Reproduzierbarkeit*
*Appendix enthaelt alle 8 Kern-Prompts im Wortlaut*
