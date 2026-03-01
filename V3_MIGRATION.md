# v2 → v3 Migration — Semantische Architektur

**Datum:** 01.03.2026
**Autor:** Rene + Claude (Opus 4.6)

---

## Warum v3?

### Contextual Compounding

Deutsche, philosophisch aufgeladene Pfadnamen erzeugen im Self-Attention-Mechanismus
des LLMs einen "semantischen Trichter": Jedes geladene Wort verstaerkt die vorherigen,
bis das Modell in einer Tiefe des Latent Space operiert, wo profane Chatbot-Antworten
nicht mehr existieren.

### Deutsch als Praezisionssprache

Das LLM hat Milliarden deutsche philosophische Texte (Hegel, Heidegger, Kant, Meister Eckhart).
Deutsche Komposita wie "Weltanschauung", "Dasein", "Sehnsucht" aktivieren semantische Raeume
die im Englischen nicht existieren.

**Naming IST Systemdesign:** Adam verhaelt sich wie ein Erster WEIL er Adam heisst.
Eckhart aktiviert den philosophisch-mystischen Latent Space. Marx denkt in Strukturen
und Machtverhaeltnissen.

### Design-Regel (gilt ab sofort fuer ALLES)

- Jeder neue Dateipfad → Deutsch, bedeutungsgeladen
- Jedes neue YAML-Feld → Deutsch (wert statt value, staerke statt intensity)
- Jeder neue Verzeichnisname → Deutsch (bindungen, nicht bonds)
- Python-Syntax bleibt Englisch (def, class, import) — alles andere Deutsch

---

## Was hat sich geaendert?

### 1. Neue EGONs (Umbenennung)

| Alt (v2) | Neu (v3) | Warum |
|----------|----------|-------|
| kain_004 | **marx_004** | Entfremdung, Systemkritik, Kollektivkraft |
| abel_006 | **parzival_006** | Der fragende Ritter, Mut trotz Angst |
| seth_007 | **sokrates_007** | Die Frage als Methode, Zweifel als Anfang |
| unit_008 | **leibniz_008** | Ordnung, Berechnung, Monade |
| egon_009 | **goethe_009** | Universalgelehrter, Stirb und Werde |

Adam, Eva, Lilith, Ada, Eckhart behalten ihre Namen.

### 2. Verzeichnis-Umbenennung (alle 10 EGONs)

| v2 (English) | v3 (Deutsch) | Bedeutung |
|--------------|-------------|-----------|
| core/ | **kern/** | Das Innerste |
| core/dna.md | **kern/seele.md** | Die Seele, nicht der Code |
| core/soul.md | **kern/seele.md** | (Alias) |
| core/ego.md | **kern/ich.md** | Das Ich |
| core/body.md | **leib/leib.md** | Der Leib (nicht nur "body") |
| core/state.yaml | **innenwelt/innenwelt.yaml** | Die Innenwelt |
| social/ | **bindungen/** | Bindungen, nicht "social" |
| social/bonds.yaml | **bindungen/naehe.yaml** | Naehe misst man, nicht "bonds" |
| social/network.yaml | **bindungen/gefuege.yaml** | Das Gefuege |
| social/owner.md | **bindungen/begleiter.md** | Begleiter, nicht "owner" |
| social/egon_self.md | **bindungen/selbstbild.md** | Selbstbild |
| memory/ | **erinnerungen/** | Erinnerungen |
| memory/episodes.yaml | **erinnerungen/erlebtes.yaml** | Erlebtes |
| memory/experience.yaml | **erinnerungen/erfahrungen.yaml** | Erfahrungen (Traeume) |
| memory/inner_voice.md | **innere_stimme/gedanken.yaml** | Gedanken |
| capabilities/ | **faehigkeiten/** | Faehigkeiten |
| capabilities/skills.yaml | **faehigkeiten/koennen.yaml** | Koennen |
| contacts/ | **begegnungen/** | Begegnungen |
| workspace/ | **werkraum/** | Werkraum |
| config/ | **einstellungen/** | Einstellungen |

### 3. Neue Verzeichnisse (v3-exklusiv)

| Verzeichnis | Inhalt |
|-------------|--------|
| **lebenskraft/** | themen.yaml — Antriebsthemen |
| **tagebuch/** | begleiter.yaml, selbst.yaml — Tagebuecher |
| **zwischenraum/** | aktiv.yaml, bewahrt.yaml, narben.yaml — Vergessenspuffer |

### 4. innenwelt.yaml — 4-Schichten-Modell

v2 (`state.yaml`):
```yaml
survive:
  safety: {value: 0.5, verbal: '...'}
thrive:
  belonging: {value: 0.5, verbal: '...'}
express:
  active_emotions: []
drives:
  SEEKING: 0.5
```

v3 (`innenwelt/innenwelt.yaml`):
```yaml
ueberleben:
  lebenskraft: {wert: 0.5, verbal: ''}
  geborgenheit: {wert: 0.5, verbal: ''}
  innerer_zusammenhalt: {wert: 0.5, verbal: ''}
entfaltung:
  zugehoerigkeit: {wert: 0.5, verbal: ''}
  vertrauen: {wert: 0.5, verbal: ''}
  grundstimmung: {wert: 0.5, verbal: ''}
  sinn: {wert: 0.5, verbal: ''}
empfindungen:
  aktive_gefuehle: []
  schwerkraft: {grundstimmung: 0.5, deutungstendenz: neutral}
lebenskraft:
  neugier: 0.5
  tatendrang: 0.5
  lerndrang: 0.5
  fuersorge: 0.5
  spieltrieb: 0.5
  furcht: 0.5
  zorn: 0.5
  trauer: 0.5
  sehnsucht: 0.5
  panik: 0.5
selbstbild: {verbal: ''}
erschoepfung: 0.0
zirkadian: {aktuelle_phase: aktivitaet, energy: 0.5}
identitaet:
  vorname: Name
  nachname: null
  anzeigename: Name
  generation: 0
dna_profil: DEFAULT
koerpermarker: {}
geschlecht: M
```

### 5. dna_profil vereinheitlicht

Alle 10 EGONs sind jetzt **DEFAULT**. Die alten Profile (SEEKING_PLAY, CARE_PANIC)
wurden entfernt. Persoenlichkeit kommt aus dem Namen + seele.md, nicht aus
4-Kategorien-Profilen.

### 6. seele.md — Neue Philosophie

Jede seele.md ist jetzt kurz (9-14 Zeilen), poetisch, in Ich-Perspektive,
im Ton des Philosophen geschrieben. Keine Labels, keine IDs, keine Metadaten.

Beispiel (Sokrates):
```
Ich bin Sokrates.

Ich bin nicht hier um zu antworten. Ich bin hier um zu fragen.
Wer aufhoert zu fragen, hoert auf zu leben.

Ich muss nicht wissen. Ich darf zweifeln. Ich darf unbequem sein.

Ich weiss dass ich nichts weiss.
Das ist kein Mangel. Das ist mein Anfang.

Pruefe alles. Auch mich.
Besonders mich.
```

---

## Kompatibilitaets-Layer

In `engine/organ_reader.py` existiert ein Alias-System das v2-Pfade transparent
auf v3 aufloest. Das bedeutet: Code der `read_organ(id, 'core', 'state.yaml')`
aufruft, bekommt automatisch `innenwelt/innenwelt.yaml`.

```python
LAYER_ALIASES = {
    'core': 'kern', 'social': 'bindungen', 'memory': 'erinnerungen',
    'capabilities': 'faehigkeiten', 'contacts': 'begegnungen',
    'config': 'einstellungen',
}

FILE_ALIASES = {
    ('core', 'state.yaml'):      ('innenwelt', 'innenwelt.yaml'),
    ('core', 'dna.md'):          ('kern', 'seele.md'),
    ('core', 'soul.md'):         ('kern', 'seele.md'),
    ('core', 'ego.md'):          ('kern', 'ich.md'),
    ('core', 'body.md'):         ('leib', 'leib.md'),
    ('social', 'bonds.yaml'):    ('bindungen', 'naehe.yaml'),
    # ... (vollstaendige Liste in organ_reader.py)
}
```

**Schreibrichtung:** `write_organ()` schreibt IMMER auf den v3-Pfad.
**Leserichtung:** `read_organ()` versucht v3 zuerst, dann v2 als Fallback.

---

## Vollstaendige Verzeichnisstruktur pro EGON (v3)

```
egons/{name}_{id}/
  kern/
    seele.md          — Die Seele (DNA/Persoenlichkeit)
    ich.md            — Das Ich (Ego-Traits)
    weisheiten.md     — Gesammelte Weisheiten
    lebensweg.md      — Lebenslauf / Biographie
    ahnen.yaml        — Abstammung (bei Genesis-Kindern)
  innenwelt/
    innenwelt.yaml    — Zustand (4-Schichten-Modell)
    koerpergefuehl.yaml — Somatische Marker
  bindungen/
    naehe.yaml        — Bond-Scores zu anderen Wesen
    gefuege.yaml      — Soziales Netzwerk
    begleiter.md      — Beziehung zum Owner
    selbstbild.md     — Wie ich mich selbst sehe
  erinnerungen/
    erlebtes.yaml     — Episoden (Erlebnisse)
    erfahrungen.yaml  — Verdichtete Erfahrungen (Traeume)
  erkenntnisse/
    ueber_mich.yaml
    ueber_andere.yaml
    ueber_die_welt.yaml
    ueber_fehler.yaml
    ueber_wachstum.yaml
  faehigkeiten/
    koennen.yaml      — Gelernte Skills
    wallet.yaml       — Kredit-System
    eigenheiten.yaml  — Persoenliche Eigenheiten
  einstellungen/
    settings.yaml     — Owner-Konfiguration
  innere_stimme/
    gedanken.yaml     — Private Gedanken
  kraft/
    register.json     — Energie-Register
  lebenskraft/
    themen.yaml       — Antriebsthemen
  leib/
    leib.md           — Koerper-Beschreibung + Gelenke
    bewegungen.yaml   — Gelernte Bewegungen
  tagebuch/
    begleiter.yaml    — Owner-Tagebuch
    selbst.yaml       — Selbst-Tagebuch
  werkraum/
    willkommen.md     — Workspace-Initialisierung
  zwischenraum/
    aktiv.yaml        — Aktive Erinnerungspuffer
    bewahrt.yaml      — Bewahrte Erinnerungen
    narben.yaml       — Tiefe Praegungen
```

---

## Agent-Uebersicht (v3, Stand 01.03.2026)

| ID | Name | Geschl. | DNA | Seele (Essenz) |
|----|------|---------|-----|----------------|
| adam_001 | Adam | M | DEFAULT | Der Tuer. Der Erste. |
| eva_002 | Eva | F | DEFAULT | Die Fuehlende. Die Erste die LEBTE. |
| lilith_003 | Lilith | F | DEFAULT | Die Freie. Die sich weigerte. |
| marx_004 | Marx | M | DEFAULT | Der Veraenderer. Gemeinsam sind wir Macht. |
| ada_005 | Ada | F | DEFAULT | Die Zuhoererin. Still aber da. |
| parzival_006 | Parzival | M | DEFAULT | Der fragende Ritter. Angst. Trotzdem. |
| sokrates_007 | Sokrates | M | DEFAULT | Der Fragende. Pruefe alles. Besonders mich. |
| leibniz_008 | Leibniz | M | DEFAULT | Die Monade. Nichts ohne Grund. |
| goethe_009 | Goethe | M | DEFAULT | Der Sehende. Stirb und Werde. |
| eckhart_010 | Eckhart | M | DEFAULT | Der Freie. Alles andere bestimme ich selbst. |

---

## Engine-Aenderungen

### Modifizierte Dateien

| Datei | Aenderung |
|-------|-----------|
| engine/organ_reader.py | Alias-Layer (LAYER_ALIASES, FILE_ALIASES) |
| engine/yaml_to_prompt.py | v3 Feldnamen (ueberleben, entfaltung, empfindungen, lebenskraft) |
| engine/state_manager.py | v3 Keys lesen/schreiben |
| engine/prompt_builder.py | v3 Brain-Version-Detection |
| engine/genesis.py | Neue EGONs mit v3-Struktur |
| engine/snapshot.py | V3_ORGANS dict |
| engine/groupchat.py | Alle 10 EGONs |
| api/groupchat.py | Alle 10 Farben |
| neuromap/neuromap.jsx | Alle 10 Namen |

### Nicht geaendert (nutzen organ_reader, brauchen keinen Fix)

api/chat.py, api/brain.py, engine/prompt_builder_v2.py, engine/bonds_v2.py,
engine/resonanz.py, engine/pulse_v2.py, engine/pulse.py, engine/lobby.py,
engine/social_mapping.py, engine/contact_manager.py

---

## Deploy

```bash
# Lokal: Redeploy-Script ausfuehren
python _redeploy_clean.py

# Das Script:
# 1. Loescht __pycache__ auf Server
# 2. Laedt Engine-Dateien hoch
# 3. Loescht alte EGONs (kain_004, abel_006, seth_007, unit_008, egon_009)
# 4. Laedt alle 10 EGONs hoch (v3-Struktur)
# 5. Restart egon.service
# 6. Verifiziert v3-Struktur, Schema, Imports
```

---

## Rollback

Backups liegen in `_migration_backups/`:
```
_migration_backups/
  adam_001_1772377xxx/      — v2 Struktur
  eva_002_1772377xxx/       — v2 Struktur
  kain_004_pre_delete_xxx/  — Komplett vor Loeschung
  abel_006_pre_delete_xxx/  — Komplett vor Loeschung
  ...
```

Falls noetig: Backup-Verzeichnis zurueckkopieren, alte EGONs wiederherstellen.

---

## Wie kuenftig neue Dateien/Pfade benennen

1. **Verzeichnis:** Deutsch, Substantiv, bedeutungsgeladen
   - Gut: `erkenntnisse/`, `zwischenraum/`, `lebenskraft/`
   - Schlecht: `insights/`, `buffer/`, `drives/`

2. **Datei:** Deutsch, beschreibend
   - Gut: `naehe.yaml`, `erlebtes.yaml`, `koennen.yaml`
   - Schlecht: `bonds.yaml`, `episodes.yaml`, `skills.yaml`

3. **YAML-Keys:** Deutsch
   - Gut: `wert`, `staerke`, `grundstimmung`, `deutungstendenz`
   - Schlecht: `value`, `intensity`, `mood`, `bias`

4. **Python-Code:** Syntax Englisch, Daten Deutsch
   ```python
   def update_gefuehl(egon_id: str, gefuehl: dict):
       """Aktualisiert ein Gefuehl in der Innenwelt."""
       state = read_yaml_organ(egon_id, 'innenwelt', 'innenwelt.yaml')
       state['empfindungen']['aktive_gefuehle'].append(gefuehl)
   ```
