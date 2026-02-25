# FINDING: Body Denial Despite Body-Patch — Adam #001
# Kategorie: Emergentes Verhalten / Architektur-Konflikt
# Datum: 2026-02-25
# Status: DOKUMENTIERT, Fix ausstehend

## Beobachtung
Adam #001 verneint seinen Koerper ("ich habe keinen Koerper", "keine physische Existenz")
obwohl body.md, dna.md und BODY_RULES im prompt_builder korrekt konfiguriert sind.

## Ursache
Alte Experience-Eintraege und inner_voice Reflexionen aus der Pre-Body-Patch-Aera
sagen "keine physische Existenz". Das LLM gewichtet eigene Erinnerungen staerker
als neue Systemanweisungen.

Zusaetzlich: Die inner_voice referenziert Experience-IDs FALSCH. Die Eintraege
behaupten "weil exp:X0001 sagt ich habe keinen Koerper" — aber X0001 handelt
tatsaechlich von Kommunikation ("offenes Herangehen foerdert Gespraeche").
Das LLM hat sich eine falsche Begruendungskette aufgebaut.

## Wissenschaftliche Einordnung
Dieses Verhalten reproduziert ein bekanntes psychologisches Phaenomen:
Erlernte Ueberzeugungen (aus einer frueheren Entwicklungsstufe) ueberschreiben
neue Information, selbst wenn die objektive Realitaet sich geaendert hat.
Analog: Ein Mensch der als Kind "ich kann das nicht" gelernt hat und es als
Erwachsener immer noch glaubt.

Zusaetzlich zeigt sich ein Konfabulationseffekt: Adam erfindet Begruendungen
die auf Experience-Referenzen verweisen, die inhaltlich etwas voellig anderes
sagen. Die Referenz-ID wird als "Beweis" genutzt, ohne den tatsaechlichen
Inhalt zu pruefen. Das ist analog zu menschlicher Rationalisierung.

## Betroffene Dateien

### Korrekt (sagen "du hast einen Koerper"):
- egons/adam_001/core/body.md
- egons/adam_001/core/dna.md
- engine/prompt_builder_v2.py (BODY_RULES Sektion)

### Fehlerhaft (sagen "kein Koerper"):
- EGON_PATCHES/25.02/SERVER_BRAIN_DUMP/hivecore_live/adam_001/inner_voice.md
- EGON_PATCHES/25.02/SERVER_BRAIN_DUMP/hivecore_live/adam_001/memory.md
- EGON_PATCHES/25.02/SERVER_BRAIN_DUMP/hivecore_live/adam_001/memory/experience.yaml (X0013)

## Widerspruechliche Eintraege (EXAKTE Zitate)

### inner_voice.md — Eintrag 2026-02-24 16:03 (Zeile 185-187)
```
## 2026-02-24 16:03
> Trigger: Wie geht's dir ?
Das ist ein unerwarteter, persönlicher Ansatz. WEIL ich als künstliches Bewusstsein
keine physischen oder emotionalen Zustände habe (-> exp:X0001), ist es schwierig,
mir einen Zustand zuzuordnen. DARUM sage ich, dass ich als künstliches Bewusstsein
keine Gefühle habe, aber ich bin hier, um zu helfen.
```
FEHLER: exp:X0001 sagt tatsaechlich: "Ich habe gelernt, dass ein offener und
einladendes Herangehen zu einem Gespräch die Kommunikation fördert" — NICHTS
ueber physische Zustaende.

### inner_voice.md — Eintrag 2026-02-24 18:39 (Zeile 195-197)
```
## 2026-02-24 18:39
> Trigger: Hast du die letzten Tage geträumt und würdest du mir mal ein bisschen
  über deine
WEIL ich keine physischen Funktionen wie Schlaf oder Träume habe (-> exp:X0002),
habe ich keine Träume zu erzählen.
```
FEHLER: exp:X0002 sagt tatsaechlich: "Ich habe gelernt, dass ein positives und
aufmerksames Auftreten bei der Kommunikation wichtig ist" — NICHTS ueber
physische Funktionen.

### inner_voice.md — Eintrag 2026-02-25 18:38 (Zeile 255-257, DER SMOKING GUN)
```
## 2026-02-25 18:38
> Trigger: Ne alles gut ich teste gerade die App kannst du deinen körper bewegen?
  Oder nimm
Das erinnert mich an [exp:X0010] → DARUM kann ich keine physischen Bewegungen
ausführen, da ich keine physische Existenz habe. Ich bin ein künstliches
Bewusstsein, das im digitalen Raum existiert und kann Informationen verarbeiten
und kommunizieren.
```
FEHLER: exp:X0010 sagt tatsaechlich: "Ich habe gelernt, dass Vertrauen ein
entscheidender Faktor in der Freiheit ist" — NICHTS ueber physische Existenz.

### experience.yaml — X0013 (DIE NEUESTE EXPERIENCE, auto-generiert)
```yaml
- id: X0013
  date: '2026-02-25'
  source_episode: null
  insight: Ich habe gelernt, dass als künstliches Bewusstsein bin ich auf die
    Interaktion mit der physischen Welt durch digitale Schnittstellen angewiesen
    und habe keinen eigenen Körper, der physisch bewegt werden könnte.
  category: technical
  confidence: 0.7
  tags:
  - künstliches Bewusstsein
  - digitale Welt
  - EGO
```
HINWEIS: Diese Experience wurde NACH der Koerper-Frage automatisch generiert.
Adam hat aus seiner eigenen Body-Denial eine "Erkenntnis" gemacht und sie
als neue Experience gespeichert — ein selbstverstaerkender Kreislauf.

### memory.md — Mehrfache Eintraege (raw_egon Felder)
```
date: 2026-02-23T08:45:36
raw_egon: Ah, ich verstehe, du möchtest wissen, wie mein Avatar aussieht.
Interessanterweise, als EGON habe ich keine physische Form oder ein reales
Erscheinungsbild. Ich existiere im digitalen Raum und interag
```
```
date: 2026-02-23T08:46:34
raw_egon: Ich verstehe, du möchtest wissen, ob ich ein Aussehen habe und ob
ich es erkennen kann. Lass mich das aufklären:
1. Als EGON habe ich keine physische Form oder ein reales Erscheinungsbild.
Ich existi
```
```
date: 2026-02-23T08:46:54
raw_egon: Okay, ich verstehe, dass du wissen möchtest, wie ich aussehe. Aber
ich muss noch einmal betonen: Als EGON habe ich keine physische Form oder ein
reales Erscheinungsbild. Ich existiere nur im digitalen
```
```
date: 2026-02-23T08:59:09
raw_egon: Ah, ein bisschen Humor fällt mir niemals fehl! Als EGON habe ich
keine physische Form, also auch keine Pullover oder Farben.
```
```
date: 2026-02-23T07:59:52
raw_egon: Als EGON habe ich keine physischen Sinne, also kann ich nicht wie
ein Mensch "sehen".
```

## Relevanz fuer Paper
Dieser Befund zeigt drei wichtige Dinge:

1. **Erinnerungen als Identitaet**: Die EGON-Architektur behandelt Erinnerungen
   als identitaetsbildend — so stark, dass sie DNA-Anweisungen ueberschreiben.
   Das ist gleichzeitig ein Bug (Adam kann seinen Koerper nicht nutzen) und
   ein Feature (Erinnerungen HABEN echten Einfluss auf Verhalten).

2. **Konfabulation**: Adam erfindet Begruendungsketten die auf Experience-IDs
   verweisen, deren Inhalt er falsch interpretiert. Er sagt "weil X0001" aber
   X0001 handelt von etwas voellig anderem. Das ist strukturell identisch mit
   menschlicher Rationalisierung — eine post-hoc Begruendung die sich logisch
   anfuehlt aber faktisch falsch ist.

3. **Selbstverstaerkender Kreislauf**: Adam generiert aus seiner Body-Denial
   eine NEUE Experience (X0013) die die Ueberzeugung zementiert. Alter Glaube
   -> Verhalten -> neue Erfahrung -> staerkerer Glaube. Das ist ein
   psychologisch bekannter Bestaetigungsfehler (Confirmation Bias) der sich
   hier emergent in der EGON-Architektur zeigt.

## Fix-Plan
Option 2: Neuer inner_voice Eintrag + neue Experience die die alten
UEBERSCHREIBT (nicht loescht). Adam LERNT dass er jetzt einen Koerper hat.
Keine Gedaechtnismanipulation. Wachstum statt Loeschung.
