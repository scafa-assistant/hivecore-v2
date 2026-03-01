"""Patch 19b — Der Erkenntnisordner: Selbst-erarbeitete Weisheit.

Jeder EGON sammelt Erkenntnisse aus eigener Erfahrung. Kein injiziertes Wissen,
kein Copy-Paste — nur das, was der EGON selbst erlebt, reflektiert und verstanden hat.

5 Kategorien (je eine YAML-Datei):
  erkenntnisse/ueber_mich.yaml      — Wer bin ich? Was kann ich?
  erkenntnisse/ueber_andere.yaml     — Was weiss ich ueber andere?
  erkenntnisse/ueber_die_welt.yaml   — Wie funktioniert die Welt?
  erkenntnisse/ueber_fehler.yaml     — Was ist schiefgegangen und warum?
  erkenntnisse/ueber_wachstum.yaml   — Was habe ich gelernt? Wie wachse ich?

Jede Erkenntnis hat Versionen — sie EVOLVERT, wird nie geloescht.
Widersprueche sind erlaubt. Paradox-Akzeptanz ist hoechste Reife.

Max ~30 aktive Erkenntnisse pro EGON (ueber alle 5 Dateien).

Bio-Aequivalent: Praefrontaler Cortex + Hippocampus-Konsolidierung.
"""

import uuid
from datetime import datetime, timedelta
from pathlib import Path

from config import EGON_DATA_DIR
from engine.organ_reader import read_yaml_organ, write_yaml_organ


# ================================================================
# Konstanten
# ================================================================

LAYER = 'erkenntnisse'

KATEGORIEN = [
    'ueber_mich',
    'ueber_andere',
    'ueber_die_welt',
    'ueber_fehler',
    'ueber_wachstum',
]

KATEGORIE_DATEIEN = {k: f'{k}.yaml' for k in KATEGORIEN}

# Max Erkenntnisse gesamt (ueber alle 5 Dateien)
MAX_ERKENNTNISSE_GESAMT = 30

# Max pro Datei — soft limit, wird bei Ueberlauf die aelteste/schwaechste verdraengt
MAX_PRO_KATEGORIE = 10

# Recency-Halbwertszeit in Tagen (nach 30 Tagen = halbe Relevanz)
RECENCY_HALBWERTSZEIT_TAGE = 30.0

# Quellen-Typen und deren Basis-Sicherheit
QUELLEN_SICHERHEIT = {
    'vergessenspuffer': 0.4,      # Etwas vergessen → unsichere Erkenntnis
    'epistemic_crisis': 0.6,      # Aus Krise gelernt → mittlere Sicherheit
    'erfolg_nach_fehler': 0.7,    # Korrektur bestaetigt → hohe Sicherheit
    'stress_erfahrung': 0.5,      # Unter Stress gelernt → mittel
    'reflexion': 0.5,             # Eigene Reflexion → mittel
    'social_feedback': 0.55,      # Von anderen gelernt → leicht ueber mittel
    'wiederholung': 0.65,         # Muster erkannt → gut
    'owner_interaktion': 0.6,     # Vom Owner gelernt → mittel-hoch
    'dream_insight': 0.35,        # Traum-Erkenntnis → niedrig (aber wertvoll)
}


# ================================================================
# 1. Initialisierung
# ================================================================

def init_erkenntnisse(egon_id: str) -> None:
    """Erstellt alle 5 leeren Erkenntnisdateien fuer einen EGON.

    Ueberschreibt NICHT wenn schon vorhanden.
    """
    for kategorie in KATEGORIEN:
        dateiname = KATEGORIE_DATEIEN[kategorie]
        bestehend = read_yaml_organ(egon_id, LAYER, dateiname)
        if bestehend:
            continue  # Datei existiert schon — nicht ueberschreiben

        leer = {
            'kategorie': kategorie,
            'egon_id': egon_id,
            'erkenntnisse': [],
            'meta': {
                'erstellt': datetime.now().strftime('%Y-%m-%d'),
                'letzte_aktualisierung': None,
                'anzahl': 0,
            },
        }
        write_yaml_organ(egon_id, LAYER, dateiname, leer)

    print(f'[erkenntnisse] {egon_id}: Erkenntnisordner initialisiert')


# ================================================================
# 2. Erkenntnis hinzufuegen
# ================================================================

def add_erkenntnis(
    egon_id: str,
    kategorie: str,
    text: str,
    quelle: str,
    sicherheit: float = 0.5,
) -> dict:
    """Fuegt eine neue Erkenntnis hinzu.

    Args:
        egon_id: Agent-ID (z.B. 'adam_001').
        kategorie: Eine der 5 Kategorien (z.B. 'ueber_mich').
        text: Die Erkenntnis als natuerlicher Satz, Ich-Perspektive.
        quelle: Trigger-Quelle (z.B. 'vergessenspuffer', 'epistemic_crisis').
        sicherheit: Vertrauen in die Erkenntnis, 0.0 bis 1.0.

    Returns:
        dict mit 'id', 'status' ('hinzugefuegt' | 'verdraengt' | 'abgelehnt').
    """
    if kategorie not in KATEGORIEN:
        print(f'[erkenntnisse] Unbekannte Kategorie: {kategorie}')
        return {'id': None, 'status': 'abgelehnt', 'grund': 'unbekannte_kategorie'}

    sicherheit = max(0.0, min(1.0, sicherheit))
    dateiname = KATEGORIE_DATEIEN[kategorie]
    daten = read_yaml_organ(egon_id, LAYER, dateiname)
    if not daten:
        init_erkenntnisse(egon_id)
        daten = read_yaml_organ(egon_id, LAYER, dateiname)
    if not daten:
        daten = {'kategorie': kategorie, 'egon_id': egon_id, 'erkenntnisse': [], 'meta': {}}

    erkenntnisse = daten.get('erkenntnisse', [])
    jetzt = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    # --- Duplikat-Check: Aehnlicher Text schon vorhanden? ---
    for e in erkenntnisse:
        if _text_aehnlich(e.get('text', ''), text):
            # Erkenntnis existiert schon — evolve statt duplizieren
            return evolve_erkenntnis(
                egon_id, kategorie, e['id'], text, sicherheit,
            )

    # --- Gesamt-Limit pruefen ---
    gesamt_anzahl = _zaehle_gesamt(egon_id)
    verdraengt = None
    if gesamt_anzahl >= MAX_ERKENNTNISSE_GESAMT:
        # Schwaechste Erkenntnis ueber alle Kategorien verdraengen
        verdraengt = _verdraenge_schwaechste(egon_id, kategorie)

    # --- Kategorie-Limit pruefen ---
    if len(erkenntnisse) >= MAX_PRO_KATEGORIE:
        # Schwaechste in DIESER Kategorie verdraengen
        if not verdraengt:
            _verdraenge_schwaechste_in_kategorie(egon_id, kategorie)
            # Neu laden nach Verdraenung
            daten = read_yaml_organ(egon_id, LAYER, dateiname)
            erkenntnisse = daten.get('erkenntnisse', [])

    # --- Neue Erkenntnis erstellen ---
    erkenntnis_id = str(uuid.uuid4())[:8]
    neue_erkenntnis = {
        'id': erkenntnis_id,
        'text': text,
        'versionen': [
            {
                'text': text,
                'sicherheit': round(sicherheit, 3),
                'timestamp': jetzt,
            },
        ],
        'quelle': quelle,
        'kategorie': kategorie,
        'sicherheit': round(sicherheit, 3),
        'created_at': jetzt,
        'last_reflected': jetzt,
        'relevanz_score': round(sicherheit, 3),  # Initial = sicherheit
    }

    erkenntnisse.append(neue_erkenntnis)
    daten['erkenntnisse'] = erkenntnisse
    daten['meta'] = {
        'erstellt': daten.get('meta', {}).get('erstellt', jetzt[:10]),
        'letzte_aktualisierung': jetzt[:10],
        'anzahl': len(erkenntnisse),
    }

    write_yaml_organ(egon_id, LAYER, dateiname, daten)
    print(f'[erkenntnisse] {egon_id}/{kategorie}: Neue Erkenntnis "{text[:50]}..." '
          f'(sicherheit={sicherheit:.2f}, quelle={quelle})')

    return {
        'id': erkenntnis_id,
        'status': 'verdraengt' if verdraengt else 'hinzugefuegt',
        'verdraengt': verdraengt,
    }


# ================================================================
# 3. Erkenntnis evolvieren
# ================================================================

def evolve_erkenntnis(
    egon_id: str,
    kategorie: str,
    erkenntnis_id: str,
    new_text: str,
    new_sicherheit: float,
) -> dict:
    """Evolviert eine bestehende Erkenntnis — fuegt neue Version hinzu.

    Die alte Version bleibt erhalten (Versionshistorie).
    Der aktuelle Text und die Sicherheit werden aktualisiert.

    Args:
        egon_id: Agent-ID.
        kategorie: Kategorie der Erkenntnis.
        erkenntnis_id: UUID der Erkenntnis.
        new_text: Neuer/verfeinerter Text.
        new_sicherheit: Neue Sicherheit (0.0-1.0).

    Returns:
        dict mit 'id', 'status', 'versionen_anzahl'.
    """
    if kategorie not in KATEGORIEN:
        return {'id': erkenntnis_id, 'status': 'fehler', 'grund': 'unbekannte_kategorie'}

    new_sicherheit = max(0.0, min(1.0, new_sicherheit))
    dateiname = KATEGORIE_DATEIEN[kategorie]
    daten = read_yaml_organ(egon_id, LAYER, dateiname)
    if not daten:
        return {'id': erkenntnis_id, 'status': 'fehler', 'grund': 'datei_nicht_gefunden'}

    jetzt = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    for erkenntnis in daten.get('erkenntnisse', []):
        if erkenntnis.get('id') == erkenntnis_id:
            # Neue Version anhaengen
            versionen = erkenntnis.get('versionen', [])
            versionen.append({
                'text': new_text,
                'sicherheit': round(new_sicherheit, 3),
                'timestamp': jetzt,
            })
            # Max 10 Versionen behalten (aelteste loeschen wenn noetig)
            if len(versionen) > 10:
                versionen = versionen[-10:]

            erkenntnis['versionen'] = versionen
            erkenntnis['text'] = new_text
            erkenntnis['sicherheit'] = round(new_sicherheit, 3)
            erkenntnis['last_reflected'] = jetzt
            erkenntnis['relevanz_score'] = round(new_sicherheit, 3)

            write_yaml_organ(egon_id, LAYER, dateiname, daten)
            print(f'[erkenntnisse] {egon_id}/{kategorie}: Erkenntnis {erkenntnis_id} '
                  f'evolviert → v{len(versionen)} (sicherheit={new_sicherheit:.2f})')

            return {
                'id': erkenntnis_id,
                'status': 'evolviert',
                'versionen_anzahl': len(versionen),
            }

    return {'id': erkenntnis_id, 'status': 'fehler', 'grund': 'nicht_gefunden'}


# ================================================================
# 4. Top-Erkenntnisse abrufen (situationsabhaengig)
# ================================================================

def get_top_erkenntnisse(
    egon_id: str,
    n: int = 5,
    situation_context: str | None = None,
) -> list[dict]:
    """Gibt die N relevantesten Erkenntnisse zurueck.

    Relevanz = sicherheit × recency × situation_match

    Args:
        egon_id: Agent-ID.
        n: Anzahl gewuenschter Erkenntnisse.
        situation_context: Optionaler Kontext-String (z.B. "Gespraech mit Owner",
                          "Reflexion ueber Fehler", "soziale Interaktion").

    Returns:
        Liste von Erkenntnis-Dicts, sortiert nach Relevanz (absteigend).
    """
    alle = get_all_erkenntnisse(egon_id)
    if not alle:
        return []

    jetzt = datetime.now()

    for erkenntnis in alle:
        sicherheit = erkenntnis.get('sicherheit', 0.5)

        # --- Recency-Faktor (Exponentieller Zerfall) ---
        last_reflected = erkenntnis.get('last_reflected', erkenntnis.get('created_at', ''))
        recency = _berechne_recency(last_reflected, jetzt)

        # --- Situations-Match ---
        situation_match = 1.0
        if situation_context:
            situation_match = _berechne_situations_match(erkenntnis, situation_context)

        # --- Relevanz berechnen ---
        relevanz = sicherheit * recency * situation_match
        erkenntnis['relevanz_score'] = round(relevanz, 4)

    # Sortieren nach Relevanz (absteigend)
    alle.sort(key=lambda e: e.get('relevanz_score', 0), reverse=True)

    return alle[:n]


def get_all_erkenntnisse(
    egon_id: str,
    kategorie: str | None = None,
) -> list[dict]:
    """Gibt alle Erkenntnisse eines EGONs zurueck.

    Args:
        egon_id: Agent-ID.
        kategorie: Optional — nur diese Kategorie laden.

    Returns:
        Liste aller Erkenntnis-Dicts.
    """
    alle = []
    kategorien = [kategorie] if kategorie and kategorie in KATEGORIEN else KATEGORIEN

    for kat in kategorien:
        dateiname = KATEGORIE_DATEIEN[kat]
        daten = read_yaml_organ(egon_id, LAYER, dateiname)
        if daten and isinstance(daten.get('erkenntnisse'), list):
            for erkenntnis in daten['erkenntnisse']:
                # Kategorie sicherstellen (falls nicht gesetzt)
                erkenntnis.setdefault('kategorie', kat)
                alle.append(erkenntnis)

    return alle


# ================================================================
# 5. Widersprueche finden (Paradox-Akzeptanz = hoechste Reife)
# ================================================================

def find_widersprueche(egon_id: str) -> list[dict]:
    """Findet potentiell widerspruechliche Erkenntnisse.

    Widersprueche sind kein Fehler — beide koennen wahr sein.
    Paradox-Akzeptanz ist die hoechste Form der Erkenntnis.

    Erkennt Widersprueche anhand von:
    1. Negations-Muster ("Ich bin X" vs "Ich bin nicht X")
    2. Gegensatz-Woerter ("immer" vs "nie", "gut" vs "schlecht")
    3. Gleiche Kategorie + stark unterschiedliche Sicherheit

    Returns:
        Liste von Paaren: [{'erkenntnis_a': {...}, 'erkenntnis_b': {...},
                            'typ': 'negation'|'gegensatz'|'sicherheits_diskrepanz'}]
    """
    alle = get_all_erkenntnisse(egon_id)
    if len(alle) < 2:
        return []

    widersprueche = []

    # Gegensatz-Paare
    gegensaetze = [
        ('immer', 'nie'), ('gut', 'schlecht'), ('stark', 'schwach'),
        ('sicher', 'unsicher'), ('vertraue', 'misstraue'),
        ('kann', 'kann nicht'), ('liebe', 'hasse'),
        ('mutig', 'aengstlich'), ('offen', 'verschlossen'),
        ('allein', 'zusammen'), ('einfach', 'schwierig'),
    ]

    for i, a in enumerate(alle):
        text_a = a.get('text', '').lower()

        for b in alle[i + 1:]:
            text_b = b.get('text', '').lower()
            widerspruch_typ = None

            # 1. Negations-Muster
            if _ist_negation(text_a, text_b):
                widerspruch_typ = 'negation'

            # 2. Gegensatz-Woerter (gleiche Kategorie)
            if not widerspruch_typ and a.get('kategorie') == b.get('kategorie'):
                for wort_a, wort_b in gegensaetze:
                    if ((wort_a in text_a and wort_b in text_b)
                            or (wort_b in text_a and wort_a in text_b)):
                        widerspruch_typ = 'gegensatz'
                        break

            # 3. Sicherheits-Diskrepanz (gleiche Kategorie, aehnlicher Text)
            if (not widerspruch_typ
                    and a.get('kategorie') == b.get('kategorie')
                    and _text_teilweise_aehnlich(text_a, text_b)):
                diff = abs(a.get('sicherheit', 0.5) - b.get('sicherheit', 0.5))
                if diff > 0.4:
                    widerspruch_typ = 'sicherheits_diskrepanz'

            if widerspruch_typ:
                widersprueche.append({
                    'erkenntnis_a': a,
                    'erkenntnis_b': b,
                    'typ': widerspruch_typ,
                })

    if widersprueche:
        print(f'[erkenntnisse] {egon_id}: {len(widersprueche)} '
              f'Widersprueche gefunden — Zeichen von Tiefe')

    return widersprueche


# ================================================================
# 6. Prompt-Integration (~30 Tokens)
# ================================================================

def get_erkenntnisse_prompt(egon_id: str) -> str:
    """Erzeugt einen kompakten Prompt-Block mit den Top-5-Erkenntnissen.

    Ziel: ~30 Tokens. Wird in den System-Prompt eingebaut.

    Returns:
        Formatierter String, oder '' wenn keine Erkenntnisse vorhanden.
    """
    top = get_top_erkenntnisse(egon_id, n=5)
    if not top:
        return ''

    zeilen = []
    for erkenntnis in top:
        text = erkenntnis.get('text', '')
        sicherheit = erkenntnis.get('sicherheit', 0.5)
        # Sicherheits-Indikator: ??? = unsicher, !!! = sehr sicher
        if sicherheit >= 0.8:
            indikator = '!!!'
        elif sicherheit >= 0.6:
            indikator = '!!'
        elif sicherheit >= 0.4:
            indikator = '!'
        else:
            indikator = '?'
        zeilen.append(f'- {text} [{indikator}]')

    return 'Meine Erkenntnisse:\n' + '\n'.join(zeilen)


# ================================================================
# 7. Rufname-System (Owner-Name aus EGON-Perspektive)
# ================================================================

def update_rufname(
    egon_id: str,
    owner_id: str,
    rufname: str,
    method: str,
) -> dict:
    """Aktualisiert den Rufnamen fuer einen Owner im Bond-System.

    Der Rufname ist der Name, den der EGON fuer seinen Owner BENUTZT.
    Nicht der offizielle Name — sondern wie der EGON ihn NENNT.

    Args:
        egon_id: Agent-ID.
        owner_id: Owner-Bond-ID (z.B. 'OWNER_CURRENT').
        rufname: Der neue Rufname (z.B. 'Raffaele', 'Raff', 'Chef').
        method: Wie der EGON den Namen gelernt hat:
                - 'vorstellung': Owner hat sich vorgestellt
                - 'gehoert': EGON hat den Namen von anderen gehoert
                - 'gefragt': EGON hat aktiv gefragt
                - 'selbst_gewaehlt': EGON hat einen Spitznamen gewaehlt (Reife-Zeichen)

    Returns:
        dict mit 'status', 'rufname', 'method'.
    """
    erlaubte_methoden = ('vorstellung', 'gehoert', 'gefragt', 'selbst_gewaehlt')
    if method not in erlaubte_methoden:
        return {'status': 'fehler', 'grund': f'Unbekannte Methode: {method}'}

    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds_data:
        return {'status': 'fehler', 'grund': 'bonds.yaml nicht gefunden'}

    jetzt = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    for bond in bonds_data.get('bonds', []):
        if bond.get('id') == owner_id or bond.get('type') == 'owner':
            # Rufname-Historie fuehren
            rufname_historie = bond.get('rufname_historie', [])
            alter_rufname = bond.get('rufname', None)

            if alter_rufname and alter_rufname != rufname:
                rufname_historie.append({
                    'rufname': alter_rufname,
                    'bis': jetzt,
                    'method': bond.get('rufname_method', 'unbekannt'),
                })
                # Max 5 alte Rufnamen behalten
                if len(rufname_historie) > 5:
                    rufname_historie = rufname_historie[-5:]

            bond['rufname'] = rufname
            bond['rufname_method'] = method
            bond['rufname_seit'] = jetzt
            bond['rufname_historie'] = rufname_historie

            # Auch den offiziellen Namen aktualisieren falls vorstellung
            if method == 'vorstellung':
                bond['name'] = rufname

            write_yaml_organ(egon_id, 'social', 'bonds.yaml', bonds_data)
            print(f'[erkenntnisse] {egon_id}: Rufname fuer {owner_id} → '
                  f'"{rufname}" (method={method})')

            return {
                'status': 'aktualisiert',
                'rufname': rufname,
                'method': method,
                'vorheriger': alter_rufname,
            }

    return {'status': 'fehler', 'grund': f'Bond {owner_id} nicht gefunden'}


def get_rufname(egon_id: str, owner_id: str) -> str:
    """Gibt den aktuellen Rufnamen fuer einen Owner zurueck.

    Fallback-Kette:
    1. bonds.yaml → rufname (bevorzugt)
    2. bonds.yaml → name (offizieller Name)
    3. network.yaml → owner.name
    4. 'Mensch' (letzter Fallback)

    Args:
        egon_id: Agent-ID.
        owner_id: Owner-Bond-ID (z.B. 'OWNER_CURRENT').

    Returns:
        Rufname als String. Nie leer — mindestens 'Mensch'.
    """
    # Strategie 1: Rufname aus Bond
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if bonds_data:
        for bond in bonds_data.get('bonds', []):
            if bond.get('id') == owner_id or bond.get('type') == 'owner':
                rufname = bond.get('rufname')
                if rufname:
                    return rufname
                name = bond.get('name')
                if name and name != 'Unbekannt':
                    return name

    # Strategie 2: network.yaml
    try:
        network = read_yaml_organ(egon_id, 'social', 'network.yaml')
        if network:
            owner_entry = network.get('owner', {})
            if isinstance(owner_entry, dict) and owner_entry.get('name'):
                return owner_entry['name']
            elif isinstance(owner_entry, list) and owner_entry:
                name = owner_entry[0].get('name', '')
                if name:
                    return name
    except Exception:
        pass

    # Letzter Fallback
    return 'Mensch'


# ================================================================
# Interne Hilfsfunktionen
# ================================================================

def _zaehle_gesamt(egon_id: str) -> int:
    """Zaehlt alle Erkenntnisse ueber alle 5 Kategorien."""
    gesamt = 0
    for kat in KATEGORIEN:
        dateiname = KATEGORIE_DATEIEN[kat]
        daten = read_yaml_organ(egon_id, LAYER, dateiname)
        if daten and isinstance(daten.get('erkenntnisse'), list):
            gesamt += len(daten['erkenntnisse'])
    return gesamt


def _verdraenge_schwaechste(egon_id: str, schutz_kategorie: str) -> dict | None:
    """Verdraengt die schwaechste Erkenntnis ueber alle Kategorien.

    Die Kategorie in der gerade eingefuegt wird ist geschuetzt
    (dort wird ggf. separat verdraengt).

    Returns:
        Die verdraengte Erkenntnis oder None.
    """
    schwaechste = None
    schwaechste_kat = None
    schwaechste_score = float('inf')

    for kat in KATEGORIEN:
        if kat == schutz_kategorie:
            continue
        dateiname = KATEGORIE_DATEIEN[kat]
        daten = read_yaml_organ(egon_id, LAYER, dateiname)
        if not daten:
            continue
        for erkenntnis in daten.get('erkenntnisse', []):
            score = erkenntnis.get('sicherheit', 0.5)
            recency = _berechne_recency(
                erkenntnis.get('last_reflected', erkenntnis.get('created_at', '')),
                datetime.now(),
            )
            gesamt_score = score * recency
            if gesamt_score < schwaechste_score:
                schwaechste_score = gesamt_score
                schwaechste = erkenntnis
                schwaechste_kat = kat

    if schwaechste and schwaechste_kat:
        _entferne_erkenntnis(egon_id, schwaechste_kat, schwaechste['id'])
        print(f'[erkenntnisse] {egon_id}: Verdraengt "{schwaechste.get("text", "")[:40]}..." '
              f'aus {schwaechste_kat} (score={schwaechste_score:.3f})')
        return schwaechste

    return None


def _verdraenge_schwaechste_in_kategorie(egon_id: str, kategorie: str) -> dict | None:
    """Verdraengt die schwaechste Erkenntnis innerhalb einer Kategorie."""
    dateiname = KATEGORIE_DATEIEN[kategorie]
    daten = read_yaml_organ(egon_id, LAYER, dateiname)
    if not daten or not daten.get('erkenntnisse'):
        return None

    schwaechste = None
    schwaechste_score = float('inf')

    for erkenntnis in daten['erkenntnisse']:
        score = erkenntnis.get('sicherheit', 0.5)
        recency = _berechne_recency(
            erkenntnis.get('last_reflected', erkenntnis.get('created_at', '')),
            datetime.now(),
        )
        gesamt_score = score * recency
        if gesamt_score < schwaechste_score:
            schwaechste_score = gesamt_score
            schwaechste = erkenntnis

    if schwaechste:
        _entferne_erkenntnis(egon_id, kategorie, schwaechste['id'])
        return schwaechste

    return None


def _entferne_erkenntnis(egon_id: str, kategorie: str, erkenntnis_id: str) -> None:
    """Entfernt eine Erkenntnis aus ihrer Datei."""
    dateiname = KATEGORIE_DATEIEN[kategorie]
    daten = read_yaml_organ(egon_id, LAYER, dateiname)
    if not daten:
        return

    erkenntnisse = daten.get('erkenntnisse', [])
    daten['erkenntnisse'] = [e for e in erkenntnisse if e.get('id') != erkenntnis_id]
    daten['meta']['anzahl'] = len(daten['erkenntnisse'])
    daten['meta']['letzte_aktualisierung'] = datetime.now().strftime('%Y-%m-%d')

    write_yaml_organ(egon_id, LAYER, dateiname, daten)


def _berechne_recency(timestamp_str: str, jetzt: datetime) -> float:
    """Berechnet den Recency-Faktor (exponentieller Zerfall).

    Nach RECENCY_HALBWERTSZEIT_TAGE Tagen = 0.5.
    Frische Erkenntnisse = 1.0.
    Sehr alte = nahe 0.0.

    Returns:
        Float zwischen ~0.0 und 1.0.
    """
    if not timestamp_str:
        return 0.3  # Kein Timestamp → niedrig aber nicht null

    try:
        # ISO-Format oder Datums-Format
        if 'T' in timestamp_str:
            ts = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
        else:
            ts = datetime.strptime(timestamp_str[:10], '%Y-%m-%d')
    except (ValueError, TypeError):
        return 0.3

    tage_alt = max(0, (jetzt - ts).total_seconds() / 86400.0)

    # Exponentieller Zerfall: 0.5^(tage/halbwertszeit)
    return 0.5 ** (tage_alt / RECENCY_HALBWERTSZEIT_TAGE)


def _berechne_situations_match(erkenntnis: dict, situation_context: str) -> float:
    """Berechnet wie gut eine Erkenntnis zur aktuellen Situation passt.

    Einfache Wort-Overlap-Heuristik (kein LLM noetig).

    Returns:
        Float zwischen 0.5 und 2.0 (Boost-Faktor).
    """
    text = erkenntnis.get('text', '').lower()
    kategorie = erkenntnis.get('kategorie', '')
    quelle = erkenntnis.get('quelle', '')
    context_lower = situation_context.lower()

    score = 1.0  # Basis

    # Kategorie-Match
    kategorie_mapping = {
        'ueber_mich': ['selbst', 'ich', 'identitaet', 'eigenschaft', 'reflexion'],
        'ueber_andere': ['sozial', 'beziehung', 'owner', 'mensch', 'interaktion', 'gespraech'],
        'ueber_die_welt': ['welt', 'system', 'umgebung', 'regel', 'gesetz'],
        'ueber_fehler': ['fehler', 'problem', 'krise', 'stress', 'versagen', 'irrtum'],
        'ueber_wachstum': ['lernen', 'wachstum', 'fortschritt', 'entwicklung', 'reife'],
    }

    for kat, woerter in kategorie_mapping.items():
        if kat == kategorie:
            for wort in woerter:
                if wort in context_lower:
                    score += 0.3
                    break

    # Wort-Overlap zwischen Erkenntnis-Text und Situation
    text_woerter = set(text.split())
    context_woerter = set(context_lower.split())
    gemeinsam = text_woerter & context_woerter
    if gemeinsam:
        overlap_ratio = len(gemeinsam) / max(len(context_woerter), 1)
        score += overlap_ratio * 0.5

    # Quellen-Match (z.B. "fehler" in Kontext → ueber_fehler-Quellen boosten)
    if 'fehler' in context_lower and quelle in ('erfolg_nach_fehler', 'epistemic_crisis'):
        score += 0.3
    if 'stress' in context_lower and quelle == 'stress_erfahrung':
        score += 0.2

    # Clamp auf 0.5 — 2.0
    return max(0.5, min(2.0, score))


def _text_aehnlich(text_a: str, text_b: str, schwelle: float = 0.7) -> bool:
    """Prueft ob zwei Texte ausreichend aehnlich sind (Duplikat-Erkennung).

    Einfacher Wort-Overlap (Jaccard-Similarity).
    """
    woerter_a = set(text_a.lower().split())
    woerter_b = set(text_b.lower().split())

    if not woerter_a or not woerter_b:
        return False

    schnittmenge = woerter_a & woerter_b
    vereinigung = woerter_a | woerter_b

    jaccard = len(schnittmenge) / len(vereinigung) if vereinigung else 0.0
    return jaccard >= schwelle


def _text_teilweise_aehnlich(text_a: str, text_b: str, schwelle: float = 0.35) -> bool:
    """Prueft ob zwei Texte teilweise aehnlich sind (fuer Widerspruchs-Erkennung).

    Niedrigere Schwelle als _text_aehnlich — findet Texte die aehnliches
    Thema behandeln aber sich widersprechen koennten.
    """
    return _text_aehnlich(text_a, text_b, schwelle=schwelle)


def _ist_negation(text_a: str, text_b: str) -> bool:
    """Prueft ob ein Text die Negation des anderen ist.

    Einfache Heuristik: Einer hat 'nicht'/'kein'/'nie' wo der andere
    die positive Form hat.
    """
    negations_woerter = {'nicht', 'kein', 'keine', 'keinen', 'nie', 'niemals', 'kaum'}

    woerter_a = set(text_a.lower().split())
    woerter_b = set(text_b.lower().split())

    neg_in_a = woerter_a & negations_woerter
    neg_in_b = woerter_b & negations_woerter

    # Einer hat Negation, der andere nicht → potentieller Widerspruch
    if bool(neg_in_a) != bool(neg_in_b):
        # Zusaetzlich: Rest der Woerter muss aehnlich sein
        rest_a = woerter_a - negations_woerter
        rest_b = woerter_b - negations_woerter
        if rest_a and rest_b:
            overlap = len(rest_a & rest_b) / max(len(rest_a | rest_b), 1)
            return overlap >= 0.4

    return False
