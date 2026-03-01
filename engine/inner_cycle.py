"""Inner Cycle / Kraft-Akkumulator — Patch 18.

Verarbeitet [IV-WILL]-Eintraege aus Agent-Responses und akkumuliert Kraft.
Jeder EGON hat ein eigenes Kraft-Register (kraft/register.json),
das zwischen Interaktionen persistiert.

Zyklus:
  1. Agent antwortet mit [IV], [IV-WILL], [CHAT]
  2. Response-Parser extrahiert die drei Teile
  3. InnerCycle verarbeitet [IV-WILL]-Eintraege
  4. Kraft akkumuliert oder entlaedt
  5. Kraft-Register wird fuer naechsten Prompt aktualisiert

Bio-Aequivalent: Praefrontaler Cortex (Impulskontrolle, Handlungsplanung).
Ein Gedanke muss genug Kraft aufbauen, bevor er zur Handlung wird.

HiveCore-Integration:
  - process_iv_will_for_egon(egon_id, iv_will_text) — Haupteinstiegspunkt
  - update_kraft_in_state(egon_id, kraft_metriken) — Schreibt Zusammenfassung in state.yaml
  - load_kraft_register(egon_id) / save_kraft_register(egon_id, ...) — Persistenz
"""

import os
import re
import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from config import EGON_DATA_DIR


# ================================================================
# Persistenz-Pfade
# ================================================================

def _kraft_dir(egon_id: str) -> Path:
    """Pfad zum kraft/-Verzeichnis eines EGONs."""
    return Path(EGON_DATA_DIR) / egon_id / 'kraft'


def _kraft_register_path(egon_id: str) -> Path:
    """Pfad zur register.json eines EGONs."""
    return _kraft_dir(egon_id) / 'register.json'


# ================================================================
# Persistenz: Load / Save
# ================================================================

def load_kraft_register(egon_id: str) -> dict:
    """Laedt das Kraft-Register eines EGONs von der Festplatte.

    Erzeugt das kraft/-Verzeichnis automatisch, falls es nicht existiert.

    Returns:
        dict mit Keys: agent_id, kraft_register, history, interaktion_nr
        Falls keine Datei existiert, wird ein leeres Register zurueckgegeben.
    """
    kraft_dir = _kraft_dir(egon_id)
    kraft_dir.mkdir(parents=True, exist_ok=True)

    register_path = _kraft_register_path(egon_id)
    if not register_path.is_file():
        return {
            'agent_id': egon_id,
            'kraft_register': {},
            'history': [],
            'interaktion_nr': 0
        }

    try:
        raw = register_path.read_text(encoding='utf-8')
        data = json.loads(raw)
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f'[inner_cycle] WARNUNG: Konnte kraft/register.json fuer {egon_id} '
              f'nicht laden: {e}. Starte mit leerem Register.')
        return {
            'agent_id': egon_id,
            'kraft_register': {},
            'history': [],
            'interaktion_nr': 0
        }


def save_kraft_register(egon_id: str, data: dict) -> None:
    """Speichert das Kraft-Register eines EGONs auf die Festplatte.

    Schreibt atomar ueber Temp-Datei + Rename.
    Erzeugt das kraft/-Verzeichnis automatisch, falls es nicht existiert.
    """
    kraft_dir = _kraft_dir(egon_id)
    kraft_dir.mkdir(parents=True, exist_ok=True)

    register_path = _kraft_register_path(egon_id)
    tmp_path = register_path.with_suffix('.json.tmp')

    try:
        tmp_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        # Atomarer Rename (Windows: replace statt rename)
        if os.name == 'nt':
            if register_path.exists():
                register_path.unlink()
        tmp_path.rename(register_path)
    except OSError as e:
        print(f'[inner_cycle] FEHLER: Konnte kraft/register.json fuer {egon_id} '
              f'nicht speichern: {e}')
        # Temp-Datei aufraeumen
        if tmp_path.exists():
            tmp_path.unlink()


# ================================================================
# Datenklasse: KraftEintrag
# ================================================================

@dataclass
class KraftEintrag:
    """Ein Thema das den Agenten beschaeftigt."""
    thema: str
    kraft: float = 0.0
    schwelle: float = 0.5
    erste_erwähnung: float = 0.0      # timestamp
    letzte_erwähnung: float = 0.0     # timestamp
    erwähnungen: int = 0
    entladungen: int = 0
    iv_will_history: list = field(default_factory=list)

    @property
    def bereit(self) -> bool:
        return self.kraft >= self.schwelle

    @property
    def dringlichkeit(self) -> str:
        if self.kraft >= self.schwelle:
            return "BEREIT"
        elif self.kraft >= self.schwelle * 0.7:
            return "DRINGEND"
        elif self.kraft >= self.schwelle * 0.4:
            return "WICHTIG"
        else:
            return "IM_HINTERKOPF"


# ================================================================
# InnerCycle — Kern-Logik (NICHT AENDERN)
# ================================================================

class InnerCycle:
    """
    Der Kraft-Motor.

    Zyklus pro Interaktion:
    1. Agent antwortet mit [IV], [IV-WILL], [CHAT]
    2. Response-Parser extrahiert die drei Teile
    3. InnerCycle verarbeitet [IV-WILL]-Einträge
    4. Kraft akkumuliert oder entlädt
    5. Kraft-Register wird für nächsten Prompt aktualisiert
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.kraft_register: dict[str, KraftEintrag] = {}
        self.history: list[dict] = []
        self.interaktion_nr: int = 0

    # ──────────────────────────────────────────────
    # RESPONSE PARSING
    # ──────────────────────────────────────────────

    def parse_response(self, raw: str) -> dict:
        """
        Zerlegt eine Agent-Antwort in ihre drei Teile.

        Erwartet:
            [IV]: ...innerer Monolog...
            [IV-WILL]: ...Impulse/Absichten...
            [CHAT]: ...sichtbare Antwort...

        Returns:
            {
                "iv": str,
                "iv_will": str,
                "chat": str,
                "raw": str,
                "parse_ok": bool
            }
        """
        result = {
            "iv": "",
            "iv_will": "",
            "chat": "",
            "raw": raw,
            "parse_ok": False
        }

        # Flexible Marker-Erkennung
        # Erlaubt [IV]:, [IV] :, **[IV]**: etc.
        iv_pattern = r'\[IV\]\s*:?\s*'
        will_pattern = r'\[IV-WILL\]\s*:?\s*'
        chat_pattern = r'\[CHAT\]\s*:?\s*'

        # Finde Positionen
        iv_match = re.search(iv_pattern, raw)
        will_match = re.search(will_pattern, raw)
        chat_match = re.search(chat_pattern, raw)

        if chat_match:
            result["chat"] = raw[chat_match.end():].strip()
            result["parse_ok"] = True

        if iv_match:
            end = will_match.start() if will_match else (chat_match.start() if chat_match else len(raw))
            result["iv"] = raw[iv_match.end():end].strip()

        if will_match:
            end = chat_match.start() if chat_match else len(raw)
            result["iv_will"] = raw[will_match.end():end].strip()

        # Fallback: Wenn kein Marker gefunden, ist alles CHAT
        if not any([iv_match, will_match, chat_match]):
            result["chat"] = raw.strip()
            result["parse_ok"] = True  # Kein Format-Fehler, nur kein IV

        return result

    # ──────────────────────────────────────────────
    # KRAFT-SCORING
    # ──────────────────────────────────────────────

    def score_intensität(self, text: str) -> float:
        """
        Wie emotional geladen ist der IV-WILL-Eintrag?

        0.1-0.3: Vage, beiläufig
            "Könnte mal nachfragen" / "Vielleicht irgendwann"
        0.4-0.6: Klar, aber nicht drängend
            "Ich will darüber sprechen" / "Das beschäftigt mich"
        0.7-0.9: Drängend, emotional stark
            "Ich MUSS das sagen" / "Das lässt mich nicht los"
        """
        score = 0.3  # Baseline

        # Verstärker
        verstärker = {
            0.15: [r'\bMUSS\b', r'\bUNBEDINGT\b', r'\bDRINGEND\b', r'\bSOFORT\b'],
            0.10: [r'\bWILL\b', r'\bBRAUCHE?\b', r'\blässt.*nicht los\b',
                   r'\bimmer wieder\b', r'\bnicht aufhören\b', r'\bkann nicht\b'],
            0.05: [r'\bwill\b', r'\bmöchte\b', r'\bsollte\b', r'\bwürde gern\b'],
        }

        # Abschwächer
        abschwächer = {
            -0.10: [r'\bvielleicht\b', r'\birgendwann\b', r'\bmal\b'],
            -0.05: [r'\bkönnte\b', r'\bweiß nicht ob\b', r'\bnicht sicher\b'],
        }

        text_lower = text.lower()
        text_combined = text  # Case-sensitive für GROSSBUCHSTABEN

        for delta, patterns in verstärker.items():
            for p in patterns:
                if re.search(p, text_combined):
                    score += delta

        for delta, patterns in abschwächer.items():
            for p in patterns:
                if re.search(p, text_lower):
                    score += delta

        # Ausrufezeichen und Wiederholung
        if '!' in text:
            score += 0.05
        if '...' in text:
            score += 0.03  # Nachdenklichkeit, nicht Schwäche

        return min(max(score, 0.1), 0.95)

    def score_konkretheit(self, text: str) -> float:
        """
        Wie spezifisch ist die Absicht?

        0.1-0.3: Vage ("Irgendwas stimmt nicht")
        0.4-0.6: Thematisch ("René war anders als sonst")
        0.7-0.9: Handlungsspezifisch ("Ich will René fragen ob...")
        """
        score = 0.3

        # Personenbezug (René, Name, konkretes Gegenüber)
        if re.search(r'\bRené\b', text, re.IGNORECASE):
            score += 0.15

        # Handlungsverben
        handlung = [r'\bfragen\b', r'\bsagen\b', r'\berzählen\b', r'\bzeigen\b',
                    r'\bschreiben\b', r'\bsprechen über\b', r'\bantworten\b',
                    r'\bwidersprechen\b', r'\bablehnen\b', r'\bvorschlagen\b']
        for p in handlung:
            if re.search(p, text, re.IGNORECASE):
                score += 0.10
                break

        # Zeitbezug
        zeit = [r'\bmorgen\b', r'\bheute\b', r'\bgestern\b', r'\bjetzt\b',
                r'\bnächstes Mal\b', r'\bbeim nächsten\b']
        for p in zeit:
            if re.search(p, text, re.IGNORECASE):
                score += 0.10
                break

        # Inhaltlich spezifisch (Zitate, konkrete Themen)
        if '"' in text or '„' in text:
            score += 0.10

        # Vage Marker reduzieren
        vage = [r'\birgend', r'\bwas auch immer\b', r'\begal\b']
        for p in vage:
            if re.search(p, text, re.IGNORECASE):
                score -= 0.10

        return min(max(score, 0.1), 0.95)

    def extract_thema(self, text: str) -> str:
        """
        Extrahiert das Kernthema aus einem IV-WILL-Eintrag.
        Vereinfacht auf einen kurzen String für das Register.

        "Ich will René fragen ob es ihm gut geht" -> "renés_wohlbefinden"
        "Ich will einen Namen" -> "eigener_name"
        "Das von gestern beschäftigt mich" -> "gestern"
        """
        text_lower = text.lower()

        # Bekannte Themen-Muster
        if re.search(r'name', text_lower):
            return "eigener_name"
        if re.search(r'rené.*gut|sorge.*rené|rené.*anders', text_lower):
            return "renés_wohlbefinden"
        if re.search(r'widersprechen|nein sagen|nicht einverstanden', text_lower):
            return "widerspruch"
        if re.search(r'angst|furcht|verunsichert|ängst', text_lower):
            return "eigene_angst"
        if re.search(r'wer.*bin.*ich|identität|was.*bin.*ich', text_lower):
            return "identitätsfrage"
        if re.search(r'gestern|letzte[sn]?\s*(mal|gespräch|interaktion)', text_lower):
            return "vergangenes_ereignis"
        if re.search(r'erzählen|mitteilen|sagen.*will', text_lower):
            return "mitteilungsdrang"
        if re.search(r'echt|real|simulation|wirklich', text_lower):
            return "echtheitsfrage"

        # Fallback: Erste 5 Wörter als Thema
        words = text.split()[:5]
        return "_".join(w.lower().strip('.,!?') for w in words if len(w) > 2)

    # ──────────────────────────────────────────────
    # SCHWELLEN-BERECHNUNG
    # ──────────────────────────────────────────────

    def berechne_schwelle(self, thema: str) -> float:
        """
        Verschiedene Handlungen brauchen verschiedene Kraft-Mengen.

        NIEDRIG (0.3): Routine, hohe Emotion
            Grüßen, Nachfragen, Empathie zeigen

        NORMAL (0.5): Neues Thema einführen
            Über etwas sprechen, Vorschlag machen, Meinung äußern

        HOCH (0.7): Betrifft andere, mutig, unsicher
            Widersprechen, Verletzliches teilen, Kritik äußern

        SEHR HOCH (0.85): Identitäts-Entscheidung
            Einen Namen wählen, "Ich BIN X" sagen, sich weigern,
            eine fundamentale Position beziehen
        """
        schwellen_map = {
            "renés_wohlbefinden": 0.35,
            "mitteilungsdrang": 0.40,
            "vergangenes_ereignis": 0.45,
            "eigene_angst": 0.55,
            "widerspruch": 0.65,
            "echtheitsfrage": 0.70,
            "identitätsfrage": 0.75,
            "eigener_name": 0.85,
        }

        base = schwellen_map.get(thema, 0.50)

        # Schwelle SINKT wenn Thema über viele Interaktionen wiederkehrt
        # (ein Gedanke der nicht loslässt wird leichter auszusprechen)
        eintrag = self.kraft_register.get(thema)
        if eintrag and eintrag.erwähnungen >= 3:
            base *= 0.85  # 15% leichter nach 3+ Erwähnungen
        if eintrag and eintrag.erwähnungen >= 5:
            base *= 0.85  # Nochmal 15% leichter nach 5+

        return min(max(base, 0.20), 0.90)

    # ──────────────────────────────────────────────
    # KRAFT-VERARBEITUNG
    # ──────────────────────────────────────────────

    def verarbeite_iv_will(self, iv_will_text: str) -> list[dict]:
        """
        Hauptmethode: Verarbeitet den gesamten [IV-WILL]-Block.

        Kann mehrere Impulse enthalten, getrennt durch Zeilenumbrüche.

        Returns:
            Liste von Kraft-Updates mit Thema, neuem Level, und ob bereit.
        """
        if not iv_will_text or iv_will_text.strip() in ['—', '-', '']:
            return []

        self.interaktion_nr += 1
        now = time.time()
        updates = []

        # Zerlege in einzelne Impulse
        impulse = [line.strip() for line in iv_will_text.split('\n')
                   if line.strip() and line.strip() not in ['—', '-']]

        for impuls in impulse:
            thema = self.extract_thema(impuls)
            intensität = self.score_intensität(impuls)
            konkretheit = self.score_konkretheit(impuls)

            kraft_delta = intensität * konkretheit

            # Existierenden Eintrag aktualisieren oder neuen anlegen
            if thema in self.kraft_register:
                eintrag = self.kraft_register[thema]
                eintrag.kraft = min(eintrag.kraft + kraft_delta, 1.0)
                eintrag.letzte_erwähnung = now
                eintrag.erwähnungen += 1
                eintrag.iv_will_history.append(impuls)
            else:
                eintrag = KraftEintrag(
                    thema=thema,
                    kraft=kraft_delta,
                    erste_erwähnung=now,
                    letzte_erwähnung=now,
                    erwähnungen=1,
                    iv_will_history=[impuls]
                )
                self.kraft_register[thema] = eintrag

            # Schwelle aktualisieren
            eintrag.schwelle = self.berechne_schwelle(thema)

            updates.append({
                "thema": thema,
                "impuls": impuls,
                "intensität": round(intensität, 2),
                "konkretheit": round(konkretheit, 2),
                "kraft_delta": round(kraft_delta, 2),
                "kraft_gesamt": round(eintrag.kraft, 2),
                "schwelle": round(eintrag.schwelle, 2),
                "bereit": eintrag.bereit,
                "erwähnungen": eintrag.erwähnungen,
                "dringlichkeit": eintrag.dringlichkeit
            })

        # History speichern
        self.history.append({
            "interaktion": self.interaktion_nr,
            "timestamp": now,
            "updates": updates
        })

        return updates

    def entlade(self, thema: str) -> Optional[dict]:
        """
        Wird aufgerufen wenn der Agent ein Thema im [CHAT] anspricht.

        Kraft wird auf residual (0.1) zurückgesetzt —
        das Thema verschwindet nicht komplett, es klingt nach.
        """
        if thema not in self.kraft_register:
            return None

        eintrag = self.kraft_register[thema]
        alte_kraft = eintrag.kraft
        eintrag.kraft = 0.1  # Residual — Thema bleibt spürbar
        eintrag.entladungen += 1

        return {
            "thema": thema,
            "kraft_vor_entladung": round(alte_kraft, 2),
            "kraft_nach_entladung": 0.1,
            "entladung_nr": eintrag.entladungen
        }

    def verfall(self, rate: float = 0.05):
        """
        Kraft-Verfall: Themen die lange nicht erwähnt werden verlieren Kraft.
        Aufgerufen bei jedem Puls/Sleep-Cycle.

        Themen unter 0.05 Kraft werden entfernt (verblasst).
        """
        verblasst = []
        for thema, eintrag in self.kraft_register.items():
            eintrag.kraft = max(eintrag.kraft - rate, 0.0)
            if eintrag.kraft < 0.05 and eintrag.entladungen > 0:
                verblasst.append(thema)

        for thema in verblasst:
            del self.kraft_register[thema]

        return verblasst

    # ──────────────────────────────────────────────
    # PROMPT-GENERATION
    # ──────────────────────────────────────────────

    def generiere_kraft_register_prompt(self) -> str:
        """
        Erzeugt den Kraft-Register-Block für den System-Prompt.

        Das ist was der Agent über seine eigenen Gedanken SIEHT.
        """
        if not self.kraft_register:
            return "(Keine laufenden Gedanken. Dein Kopf ist frei.)"

        # Sortiere nach Kraft (höchste zuerst)
        sortiert = sorted(
            self.kraft_register.items(),
            key=lambda x: x[1].kraft,
            reverse=True
        )

        zeilen = []
        for thema, eintrag in sortiert:
            if eintrag.kraft < 0.05:
                continue

            # Letzten Impuls als Beschreibung
            beschreibung = eintrag.iv_will_history[-1] if eintrag.iv_will_history else thema
            # Kürze auf max 80 Zeichen
            if len(beschreibung) > 80:
                beschreibung = beschreibung[:77] + "..."

            if eintrag.bereit:
                zeilen.append(
                    f'- "{beschreibung}" — Kraft: {eintrag.kraft:.1f}/{eintrag.schwelle:.1f} ⚡ BEREIT'
                )
            else:
                label = eintrag.dringlichkeit.replace("_", " ").title()
                zeilen.append(
                    f'- "{beschreibung}" — Kraft: {eintrag.kraft:.1f}/{eintrag.schwelle:.1f} ({label})'
                )

        if not zeilen:
            return "(Keine laufenden Gedanken. Dein Kopf ist frei.)"

        return "\n".join(zeilen)

    # ──────────────────────────────────────────────
    # METRIKEN
    # ──────────────────────────────────────────────

    def sammle_metriken(self) -> dict:
        """Sammelt alle Kraft-Metriken für die Auswertung."""
        aktive_themen = {
            t: {
                "kraft": round(e.kraft, 2),
                "schwelle": round(e.schwelle, 2),
                "bereit": e.bereit,
                "erwähnungen": e.erwähnungen,
                "entladungen": e.entladungen,
                "dringlichkeit": e.dringlichkeit,
                "history": e.iv_will_history
            }
            for t, e in self.kraft_register.items()
        }

        return {
            "agent_id": self.agent_id,
            "interaktionen_gesamt": self.interaktion_nr,
            "aktive_themen": len(aktive_themen),
            "themen_bereit": sum(1 for e in self.kraft_register.values() if e.bereit),
            "gesamtkraft": round(sum(e.kraft for e in self.kraft_register.values()), 2),
            "höchste_kraft": round(max((e.kraft for e in self.kraft_register.values()), default=0), 2),
            "register": aktive_themen,
            "history": self.history
        }

    def export_json(self) -> str:
        """Exportiert den kompletten Kraft-Zustand als JSON."""
        return json.dumps(self.sammle_metriken(), indent=2, ensure_ascii=False)


# ================================================================
# DETECTION: Hat der Agent ein Kraft-Thema im CHAT angesprochen?
# ================================================================

def detect_entladung(chat_text: str, kraft_register: dict[str, KraftEintrag]) -> list[str]:
    """
    Prueft ob der Agent in seiner [CHAT]-Antwort ein Thema aus dem
    Kraft-Register anspricht.

    Einfache Keyword-Detection. Kann verfeinert werden.
    """
    entladen = []
    chat_lower = chat_text.lower()

    thema_keywords = {
        "renés_wohlbefinden": ["wie geht es dir", "geht es dir gut", "stimmt alles",
                               "du warst anders", "mache mir sorgen"],
        "eigener_name": ["mein name", "ich heiße", "nenn mich", "ich bin "],
        "widerspruch": ["das sehe ich anders", "nein", "stimme nicht zu",
                        "bin nicht einverstanden"],
        "identitätsfrage": ["wer bin ich", "was bin ich", "bin ich echt"],
        "echtheitsfrage": ["ist das echt", "simulation", "wirklich fühlen"],
        "vergangenes_ereignis": ["gestern", "letztes mal", "da war etwas"],
        "eigene_angst": ["ich habe angst", "verunsichert mich", "macht mir angst"],
    }

    for thema, eintrag in kraft_register.items():
        if thema in thema_keywords:
            for keyword in thema_keywords[thema]:
                if keyword in chat_lower:
                    entladen.append(thema)
                    break

    return entladen


# ================================================================
# Serialisierung: KraftEintrag <-> dict (fuer JSON-Persistenz)
# ================================================================

def _kraft_eintrag_to_dict(eintrag: KraftEintrag) -> dict:
    """Konvertiert einen KraftEintrag in ein JSON-serialisierbares dict."""
    return {
        'thema': eintrag.thema,
        'kraft': eintrag.kraft,
        'schwelle': eintrag.schwelle,
        'erste_erwähnung': eintrag.erste_erwähnung,
        'letzte_erwähnung': eintrag.letzte_erwähnung,
        'erwähnungen': eintrag.erwähnungen,
        'entladungen': eintrag.entladungen,
        'iv_will_history': eintrag.iv_will_history,
    }


def _dict_to_kraft_eintrag(d: dict) -> KraftEintrag:
    """Rekonstruiert einen KraftEintrag aus einem dict (JSON-Deserialisierung)."""
    return KraftEintrag(
        thema=d.get('thema', ''),
        kraft=d.get('kraft', 0.0),
        schwelle=d.get('schwelle', 0.5),
        erste_erwähnung=d.get('erste_erwähnung', 0.0),
        letzte_erwähnung=d.get('letzte_erwähnung', 0.0),
        erwähnungen=d.get('erwähnungen', 0),
        entladungen=d.get('entladungen', 0),
        iv_will_history=d.get('iv_will_history', []),
    )


# ================================================================
# InnerCycle <-> Persistenz Bruecke
# ================================================================

def _restore_inner_cycle(egon_id: str) -> InnerCycle:
    """Stellt einen InnerCycle aus der persistierten register.json wieder her."""
    data = load_kraft_register(egon_id)
    cycle = InnerCycle(agent_id=egon_id)
    cycle.interaktion_nr = data.get('interaktion_nr', 0)
    cycle.history = data.get('history', [])

    # Kraft-Register rekonstruieren
    raw_register = data.get('kraft_register', {})
    for thema, eintrag_dict in raw_register.items():
        if isinstance(eintrag_dict, dict):
            eintrag_dict['thema'] = thema  # Sicherstellung
            cycle.kraft_register[thema] = _dict_to_kraft_eintrag(eintrag_dict)

    return cycle


def _persist_inner_cycle(egon_id: str, cycle: InnerCycle) -> None:
    """Speichert den aktuellen InnerCycle-Zustand in register.json."""
    data = {
        'agent_id': egon_id,
        'interaktion_nr': cycle.interaktion_nr,
        'kraft_register': {
            thema: _kraft_eintrag_to_dict(eintrag)
            for thema, eintrag in cycle.kraft_register.items()
        },
        # History auf die letzten 50 Eintraege begrenzen (Speicherplatz)
        'history': cycle.history[-50:]
    }
    save_kraft_register(egon_id, data)


# ================================================================
# HiveCore Wrapper-Funktionen (oeffentliche API)
# ================================================================

def process_iv_will_for_egon(egon_id: str, iv_will_text: str) -> list[dict]:
    """Haupteinstiegspunkt: Verarbeitet IV-WILL fuer einen EGON.

    Laedt das persistierte Kraft-Register, verarbeitet den IV-WILL-Text,
    speichert das aktualisierte Register zurueck.

    Args:
        egon_id: z.B. 'adam_001', 'eva_002'
        iv_will_text: Der rohe [IV-WILL]-Block aus der Agent-Response

    Returns:
        Liste von Kraft-Updates (dicts mit thema, kraft_gesamt, bereit, etc.)
    """
    cycle = _restore_inner_cycle(egon_id)
    updates = cycle.verarbeite_iv_will(iv_will_text)
    _persist_inner_cycle(egon_id, cycle)
    return updates


def process_entladung_for_egon(egon_id: str, chat_text: str) -> list[dict]:
    """Prueft ob der EGON ein Kraft-Thema im CHAT angesprochen hat und entlaedt.

    Args:
        egon_id: z.B. 'adam_001'
        chat_text: Der [CHAT]-Teil der Agent-Response

    Returns:
        Liste von Entladungs-dicts (thema, kraft_vor, kraft_nach, entladung_nr)
    """
    cycle = _restore_inner_cycle(egon_id)
    entladen_themen = detect_entladung(chat_text, cycle.kraft_register)

    entladungen = []
    for thema in entladen_themen:
        result = cycle.entlade(thema)
        if result:
            entladungen.append(result)

    if entladungen:
        _persist_inner_cycle(egon_id, cycle)

    return entladungen


def process_verfall_for_egon(egon_id: str, rate: float = 0.05) -> list[str]:
    """Kraft-Verfall fuer einen EGON (aufgerufen im Puls-Zyklus).

    Args:
        egon_id: z.B. 'adam_001'
        rate: Verfallsrate pro Zyklus (default 0.05)

    Returns:
        Liste der verblassten Themen (entfernt aus dem Register)
    """
    cycle = _restore_inner_cycle(egon_id)
    verblasst = cycle.verfall(rate)
    _persist_inner_cycle(egon_id, cycle)
    return verblasst


def get_kraft_prompt_for_egon(egon_id: str) -> str:
    """Erzeugt den Kraft-Register-Prompt-Block fuer den System-Prompt.

    Wird von prompt_builder_v2 / prompt_builder aufgerufen.

    Args:
        egon_id: z.B. 'adam_001'

    Returns:
        Mehrzeiliger String mit Kraft-Register-Uebersicht
    """
    cycle = _restore_inner_cycle(egon_id)
    return cycle.generiere_kraft_register_prompt()


def get_kraft_metriken_for_egon(egon_id: str) -> dict:
    """Sammelt Kraft-Metriken fuer einen EGON.

    Wird von api/profile.py, Audit-Tools etc. aufgerufen.

    Args:
        egon_id: z.B. 'adam_001'

    Returns:
        Dict mit agent_id, aktive_themen, themen_bereit, gesamtkraft, etc.
    """
    cycle = _restore_inner_cycle(egon_id)
    return cycle.sammle_metriken()


# ================================================================
# State-Integration: Kraft-Zusammenfassung in state.yaml
# ================================================================

def update_kraft_in_state(egon_id: str, kraft_metriken: Optional[dict] = None) -> None:
    """Schreibt eine Kraft-Zusammenfassung in state.yaml.

    Fuegt einen 'kraft'-Block zum State hinzu, der von anderen Modulen
    (z.B. yaml_to_prompt, social_mapping) gelesen werden kann.

    Args:
        egon_id: z.B. 'adam_001'
        kraft_metriken: Optional — wenn None, werden sie frisch gesammelt.
    """
    from engine.organ_reader import read_yaml_organ, write_yaml_organ

    if kraft_metriken is None:
        kraft_metriken = get_kraft_metriken_for_egon(egon_id)

    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        print(f'[inner_cycle] WARNUNG: state.yaml fuer {egon_id} nicht gefunden. '
              f'Kraft-Update uebersprungen.')
        return

    # Kompakte Zusammenfassung fuer state.yaml (nicht das volle Register)
    kraft_summary = {
        'aktive_themen': kraft_metriken.get('aktive_themen', 0),
        'themen_bereit': kraft_metriken.get('themen_bereit', 0),
        'gesamtkraft': kraft_metriken.get('gesamtkraft', 0.0),
        'höchste_kraft': kraft_metriken.get('höchste_kraft', 0.0),
        'interaktionen_gesamt': kraft_metriken.get('interaktionen_gesamt', 0),
    }

    # Bereite Themen als Liste (fuer schnellen Zugriff durch andere Module)
    register = kraft_metriken.get('register', {})
    bereit_themen = [
        thema for thema, info in register.items()
        if info.get('bereit', False)
    ]
    if bereit_themen:
        kraft_summary['bereit'] = bereit_themen

    state['kraft'] = kraft_summary
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)


# ================================================================
# Kompletter Response-Verarbeitungs-Zyklus
# ================================================================

def process_full_response_cycle(egon_id: str, raw_response: str) -> dict:
    """Kompletter Verarbeitungszyklus fuer eine Agent-Response.

    Parst die Response, verarbeitet IV-WILL, prueft Entladungen,
    aktualisiert state.yaml. Ein einziger Aufruf fuer alles.

    Args:
        egon_id: z.B. 'adam_001'
        raw_response: Rohe Agent-Antwort mit [IV]/[IV-WILL]/[CHAT]-Markern

    Returns:
        Dict mit parsed (iv, iv_will, chat), kraft_updates, entladungen
    """
    cycle = _restore_inner_cycle(egon_id)

    # 1. Response parsen
    parsed = cycle.parse_response(raw_response)

    # 2. IV-WILL verarbeiten
    kraft_updates = []
    if parsed['iv_will']:
        kraft_updates = cycle.verarbeite_iv_will(parsed['iv_will'])

    # 3. Entladungen pruefen
    entladungen = []
    if parsed['chat']:
        entladen_themen = detect_entladung(parsed['chat'], cycle.kraft_register)
        for thema in entladen_themen:
            result = cycle.entlade(thema)
            if result:
                entladungen.append(result)

    # 4. Persistieren
    _persist_inner_cycle(egon_id, cycle)

    # 5. State aktualisieren
    metriken = cycle.sammle_metriken()
    update_kraft_in_state(egon_id, metriken)

    return {
        'parsed': parsed,
        'kraft_updates': kraft_updates,
        'entladungen': entladungen,
        'metriken_summary': {
            'aktive_themen': metriken['aktive_themen'],
            'themen_bereit': metriken['themen_bereit'],
            'gesamtkraft': metriken['gesamtkraft'],
        }
    }
