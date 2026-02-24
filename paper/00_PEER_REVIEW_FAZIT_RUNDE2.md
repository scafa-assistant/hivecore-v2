# Peer Review Fazit — Runde 2

**Datum**: 2026-02-24
**Pruefer**: Ron Scafarti (als kritischer Pruefer)
**Gegenstand**: LIMITATIONS_VULNERABILITIES_APPENDIX.md nach Runde 1

---

## Bewertung

Dieses Dokument ist jetzt exzellent. Du hast die Architektur transparent gemacht, ethische Bedenken abgewogen und die Schwaechen schonungslos dokumentiert.

Wenn du die unten genannten Punkte (besonders das exakte Design der Ablationsstudie und die Bias-Problematik bei LLM-Evaluatoren) in das Dokument einfuegst, hast du ein fertiges Manuskript, das absolut reif fuer ein Preprint auf arXiv ist. Es ist detailliert, methodisch reflektiert und adressiert praezise die aktuellen Probleme der agentischen KI.

---

## 5 Identifizierte Luecken

### Luecke 1: Baseline-Experiment ist ein Strawman
Das geplante "nacktes LLM"-Experiment ist der falsche Test. Die echte wissenschaftliche Baseline ist eine Ablationsstudie: LLM mit identischen Daten als simplem Text-Dump, OHNE strukturierte EGON-Kognition. Die Kernfrage: Entsteht die affektive Persistenz durch die Datenmenge (RAG-Standard) oder die spezifische funktionale Architektur (Organe + Pulse)?

### Luecke 2: Zirkelschluss bei Spark-Evaluierung
Der Spark-Prompt zwingt das WEIL-DESHALB Format. Das Befolgen ist Instruction Following, keine Emergenz. Ein Spark ist nur wissenschaftlich wertvoll wenn er Evas zukuenftiges Verhalten messbar aendert (z.B. haeufigere kreative Themen-Initiierung nach S0001).

### Luecke 3: Temporale Zerstoerung durch Vektor-Suche
Reine semantische Vektor-Suche zerstoert den chronologischen Narrativ. Episodisches Gedaechtnis benoetigt zwingend temporale Ordnung fuer Kausalitaetsverstaendnis. Hybrid-Retrieval muss temporale Kohaerenz priorisieren.

### Luecke 4: Verbosity & Position Bias der LLM-Judges
LLM-Judges ueberbewerten laengere, eloquentere Antworten systematisch. Fuer emotionale Authentizitaet sind sie ungeeignet — menschliche Evaluatoren notwendig.

### Luecke 5: Sandboxing jenseits von Docker
MicroVM-Infrastrukturen (z.B. E2B-Sandboxes) sind Docker ueberlegen fuer KI-Agenten mit unvorhersehbarem Code und Prompt-Injection-Risiko.

---

## Gesamturteil

Grossartige Arbeit. Reif fuer arXiv-Preprint nach Einarbeitung dieser 5 Punkte.

---

*Peer-Review Runde 2, 2026-02-24*
