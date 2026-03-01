"""Brain API — Neuro-Map Endpoints fuer das Frontend.

Stellt die strukturellen Gehirn-Daten bereit die Patch 16
(Neuroplastizitaet) im Backend generiert:

- /brain/snapshot:     Kompletter Faden-Zustand (alle Kategorien)
- /brain/events:       Polling fuer neue Events seit Timestamp
- /brain/bonds:        Alle Bonds als Liste mit Typ, Staerke, Narben
- /brain/interactions: Chat-Histories + Bond-Daten aller Partner
- /brain/regions:      Regionen-Nutzung (Aktivitaets-Heatmap)
- /brain/region/{name}: Deep-Dive — ALLE Organ-Daten einer Region

UX-Konzept: Toggle im Chat-Screen oben rechts:
  Body-Modus (3D Avatar) <-> Brain-Modus (Neuro-Map)
  Beides ist die Kulisse HINTER dem Chat.
"""

import os
import json
from datetime import datetime
from fastapi import APIRouter, Query
from typing import Optional
from config import EGON_DATA_DIR
from engine.organ_reader import read_yaml_organ, read_organ, read_md_organ

router = APIRouter()


# ================================================================
# 1. Brain Snapshot — Kompletter Faden-Zustand
# ================================================================

@router.get('/egon/{egon_id}/brain/snapshot')
async def get_brain_snapshot(egon_id: str):
    """Kompletter Faden-Zustand fuer die Neuro-Map Visualisierung.

    Returns alle Faeden (anatomisch, bond, lebensfaden, praegung,
    metacognition) mit Dicke, Farbe, Opacity und Metadaten.

    Frontend nutzt dies beim Laden / Toggle auf Brain-Modus.
    """
    try:
        from engine.neuroplastizitaet import baue_struktur_snapshot
        snapshot = baue_struktur_snapshot(egon_id)
        return snapshot
    except ImportError:
        return {'error': 'neuroplastizitaet module not available', 'faeden': []}
    except Exception as e:
        return {'error': str(e), 'faeden': []}


# ================================================================
# 2. Brain Events — Polling fuer Live-Updates
# ================================================================

@router.get('/egon/{egon_id}/brain/events')
async def get_brain_events(
    egon_id: str,
    since: float = Query(0, description='Unix-Timestamp — nur Events danach'),
    clear: bool = Query(False, description='Buffer nach Abruf leeren'),
):
    """Neue strukturelle Events seit Timestamp.

    Frontend pollt alle 200ms waehrend Brain-Modus aktiv.
    Events: STRUKTUR_NEU, _UPDATE, _FADE, _TEMP, _ENTFERNT, _SNAPSHOT.

    ?since=1740000000    → Nur Events nach diesem Unix-Timestamp
    ?clear=true          → Buffer leeren nach Abruf (einmal-Konsum)
    """
    try:
        from engine.neuroplastizitaet import event_buffer_peek, event_buffer_pop
        if clear:
            events = event_buffer_pop(egon_id)
            if since > 0:
                events = [e for e in events if e.get('timestamp_unix', 0) > since]
        else:
            events = event_buffer_peek(egon_id, seit_ts=since)
        return {
            'egon_id': egon_id,
            'events': events,
            'count': len(events),
        }
    except ImportError:
        return {'egon_id': egon_id, 'events': [], 'count': 0}
    except Exception as e:
        return {'egon_id': egon_id, 'events': [], 'count': 0, 'error': str(e)}


# ================================================================
# Helper: Owner-Name aus network.yaml aufloesen
# ================================================================

def _resolve_owner_name(egon_id: str) -> str:
    """Holt den tatsaechlichen Owner-Namen.

    Zeigt 'René' statt 'Owner' — der EGON kennt seinen Menschen beim Namen.

    Strategie (Fallback-Kette):
    1. network.yaml → owner.name
    2. Owner-Bond (type=owner) → name-Feld
    3. Adam's network.yaml (Adam kennt den Owner immer)
    """
    # Strategie 1: Eigene network.yaml
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

    # Strategie 2: Owner-Bond in bonds.yaml hat evtl. ein name-Feld
    try:
        bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml') or {}
        for bond in bonds_data.get('bonds', []):
            if isinstance(bond, dict) and bond.get('type') == 'owner' and bond.get('name'):
                return bond['name']
    except Exception:
        pass

    # Strategie 3: Adam (adam_001) kennt den Owner immer
    if egon_id != 'adam_001':
        try:
            adam_net = read_yaml_organ('adam_001', 'social', 'network.yaml')
            if adam_net:
                owner_entry = adam_net.get('owner', {})
                if isinstance(owner_entry, dict) and owner_entry.get('name'):
                    return owner_entry['name']
        except Exception:
            pass

    return 'Bezugsmensch'


# ================================================================
# 3. Bonds — Alle Beziehungen als Liste
# ================================================================

@router.get('/egon/{egon_id}/brain/bonds')
async def get_brain_bonds(egon_id: str):
    """Alle Bonds eines EGONs mit Typ, Staerke, Farbe und Narben.

    Erweitert um Neuro-Map Informationen (Faden-Dicke, Farbe)
    die das Frontend direkt zum Rendern verwenden kann.
    """
    try:
        from engine.neuroplastizitaet import BOND_FARBEN, _clamp

        bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml') or {}
        bonds = bonds_data.get('bonds', [])
        result = []

        for bond in bonds:
            if not isinstance(bond, dict):
                continue
            partner_id = bond.get('id', bond.get('partner_id', 'unbekannt'))
            score = bond.get('score', 0)
            staerke = score / 100.0 if score > 1 else score
            bond_typ = bond.get('bond_typ', 'bekannt')
            trust = bond.get('trust', 0.5)
            familiarity = bond.get('familiarity', 0.0)
            hat_narbe = bond.get('hat_narbe', False)

            # Attachment Style (falls vorhanden)
            attachment = bond.get('attachment_style', 'undefined')

            # Letzte Interaktion
            last = bond.get('last_interaction', '')

            # Bond-History (letzte 5 Eintraege)
            history = bond.get('bond_history', [])[-5:]

            # Neuro-Map Faden-Daten
            faden_dicke = _clamp(staerke * 0.8, 0.05, 0.8)
            faden_farbe = BOND_FARBEN.get(bond_typ, BOND_FARBEN['bekannt'])
            faden_opacity = _clamp(0.3 + staerke * 0.7, 0.1, 0.9)

            # Partner-Name auflösen
            # Person-Bonds haben ein 'name'-Feld (z.B. "Vivian"), EGON-Bonds nutzen naming.py
            # Owner-Bonds: Tatsaechlichen Owner-Namen aus network.yaml holen
            bond_name_field = bond.get('name', '').strip().strip('<>')
            entity_type = bond.get('type', 'egon')
            if entity_type == 'owner':
                # Owner-Bond: Echten Namen zeigen, nicht "Owner"
                partner_name = _resolve_owner_name(egon_id)
            elif entity_type == 'person' and bond_name_field:
                partner_name = bond_name_field
            elif partner_id.startswith('person_') and bond_name_field:
                partner_name = bond_name_field
            else:
                try:
                    from engine.naming import get_display_name
                    partner_name = get_display_name(partner_id, 'voll')
                except Exception:
                    parts = partner_id.split('_')
                    partner_name = parts[0].title() if parts else partner_id

            # Farbe basiert auf Entity-Typ
            if entity_type == 'owner':
                faden_farbe = '#ffd700'
            elif entity_type == 'person':
                faden_farbe = '#fb923c'
            # else: bleibt BOND_FARBEN (Standard fuer EGONs)

            # Observations (was der Owner ueber die Person gesagt hat)
            observations = bond.get('observations', [])

            # Kontakt-Status (pending/verified) aus contact_card laden
            contact_status = 'verified'
            if entity_type == 'person':
                try:
                    from engine.contact_manager import get_contact
                    card = get_contact(egon_id, partner_name)
                    contact_status = card.get('status', 'verified')
                except Exception:
                    pass

            result.append({
                'partner_id': partner_id,
                'partner_name': partner_name,
                'bond_typ': bond_typ,
                'score': score,
                'staerke': round(staerke, 3),
                'trust': round(trust, 3),
                'familiarity': round(familiarity, 3),
                'attachment_style': attachment,
                'hat_narbe': hat_narbe,
                'last_interaction': last,
                'emotional_debt': bond.get('emotional_debt', 0),
                'history': history,
                'observations': observations,
                'bond_type': entity_type,  # egon/person/owner
                'contact_status': contact_status,  # pending/verified
                # Neuro-Map Rendering
                'faden': {
                    'faden_id': f'bond_{partner_id}',
                    'dicke': round(faden_dicke, 3),
                    'farbe': faden_farbe,
                    'opacity': round(faden_opacity, 3),
                    'von': 'amygdala',
                    'nach': 'praefrontal',
                },
            })

        # Sortiere nach Score (staerkste zuerst)
        result.sort(key=lambda b: b['score'], reverse=True)

        return {
            'egon_id': egon_id,
            'bonds': result,
            'total': len(result),
            'staerkster_bond': result[0]['partner_name'] if result else None,
        }
    except Exception as e:
        return {'egon_id': egon_id, 'bonds': [], 'total': 0, 'error': str(e)}


# ================================================================
# 4. Interactions — Chat-Histories + Bonds aller Partner
# ================================================================

@router.get('/egon/{egon_id}/brain/interactions')
async def get_brain_interactions(egon_id: str):
    """Alle Interaktionen eines EGONs: Chats + Social Maps + Bonds.

    Kombiniert fuer jeden Partner:
    - Chat-History (letzte N Nachrichten)
    - Bond-Daten (Score, Trust, Typ)
    - Social Map (Eindruck, emotionale Bewertung)

    So kann das Frontend eine komplette Interaktions-Uebersicht zeigen.
    """
    try:
        # 1. Bonds laden
        bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml') or {}
        bonds = bonds_data.get('bonds', [])

        # 2. Chat-Histories von Disk laden
        egon_chat_dir = os.path.join(EGON_DATA_DIR, 'shared', 'egon_chats')
        disk_histories = {}
        try:
            if os.path.isdir(egon_chat_dir):
                for filename in os.listdir(egon_chat_dir):
                    if filename.endswith('.json') and egon_id in filename:
                        key = filename[:-5].replace('--', ':')
                        parts = key.split(':')
                        partner = parts[1] if parts[0] == egon_id else parts[0]
                        try:
                            with open(os.path.join(egon_chat_dir, filename), 'r',
                                      encoding='utf-8') as f:
                                msgs = json.load(f)
                            disk_histories[partner] = msgs
                        except Exception:
                            pass
        except Exception:
            pass

        # 3. Alle Partner sammeln (aus Bonds + Chat-Histories)
        all_partners = set()
        for bond in bonds:
            if isinstance(bond, dict):
                pid = bond.get('id', bond.get('partner_id', ''))
                if pid and pid != 'OWNER_CURRENT':
                    all_partners.add(pid)
        for partner in disk_histories:
            all_partners.add(partner)

        # 4. Pro Partner: Bond + Social Map + Chat zusammenfuehren
        interactions = []
        for partner_id in sorted(all_partners):
            # Bond-Daten
            bond = None
            for b in bonds:
                if isinstance(b, dict) and b.get('id', b.get('partner_id', '')) == partner_id:
                    bond = b
                    break

            # Social Map
            social_map = None
            try:
                sm = read_yaml_organ(egon_id, 'skills/memory/social_mapping',
                                     f'ueber_{partner_id}.yaml')
                if sm:
                    social_map = {
                        'erster_eindruck': sm.get('mein_eindruck', {}).get('erster_eindruck', ''),
                        'aktueller_eindruck': sm.get('mein_eindruck', {}).get('aktueller_eindruck', ''),
                        'emotionale_bewertung': sm.get('emotionale_bewertung', {}),
                        'interaktionen_gesamt': sm.get('identitaet', {}).get('interaktionen_gesamt', 0),
                    }
            except Exception:
                pass

            # Chat-History (letzte 10 Messages)
            chat = disk_histories.get(partner_id, [])
            recent_chat = chat[-10:] if chat else []

            # Partner-Name
            try:
                from engine.naming import get_display_name
                partner_name = get_display_name(partner_id, 'voll')
            except Exception:
                partner_name = partner_id.split('_')[0].title() if '_' in partner_id else partner_id

            interactions.append({
                'partner_id': partner_id,
                'partner_name': partner_name,
                'bond': {
                    'score': bond.get('score', 0) if bond else 0,
                    'trust': bond.get('trust', 0) if bond else 0,
                    'bond_typ': bond.get('bond_typ', 'unbekannt') if bond else 'kein_bond',
                    'last_interaction': bond.get('last_interaction', '') if bond else '',
                    'attachment_style': bond.get('attachment_style', 'undefined') if bond else 'undefined',
                } if bond or True else None,
                'social_map': social_map,
                'recent_chat': [
                    {'role': m.get('role', '?'), 'content': m.get('content', '')[:200]}
                    for m in recent_chat
                ],
                'chat_message_count': len(chat),
            })

        # Sortiere: Meiste Interaktionen zuerst
        interactions.sort(key=lambda x: x['chat_message_count'], reverse=True)

        return {
            'egon_id': egon_id,
            'interactions': interactions,
            'total_partners': len(interactions),
        }
    except Exception as e:
        return {'egon_id': egon_id, 'interactions': [], 'total_partners': 0, 'error': str(e)}


# ================================================================
# 5. Regions — Regionen-Nutzung (Heatmap-Daten)
# ================================================================

@router.get('/egon/{egon_id}/brain/regions')
async def get_brain_regions(egon_id: str):
    """Regionen-Nutzungs-Daten fuer eine Aktivitaets-Heatmap.

    Zeigt welche Hirnregionen wie aktiv waren (Zaehler pro Zyklus).
    Frontend kann damit Regionen heller/dunkler faerben.
    """
    try:
        from engine.neuroplastizitaet import ALLE_REGIONEN, _regionen_nutzung

        state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}
        neuro = state.get('neuroplastizitaet', {})

        # Persistierte Nutzung (aus state.yaml)
        gespeichert = neuro.get('regionen_nutzung', {})

        # In-memory Nutzung (noch nicht geflusht)
        inmemory = dict(_regionen_nutzung.get(egon_id, {}))

        # Kombinieren
        combined = {}
        for r in ALLE_REGIONEN:
            combined[r] = gespeichert.get(r, 0) + inmemory.get(r, 0)

        # Max fuer Normalisierung
        max_nutzung = max(combined.values()) if combined else 1

        regionen = []
        for r in ALLE_REGIONEN:
            count = combined.get(r, 0)
            regionen.append({
                'region': r,
                'nutzung': count,
                'intensitaet': round(count / max_nutzung, 3) if max_nutzung > 0 else 0,
            })

        # Sortiere nach Nutzung
        regionen.sort(key=lambda x: x['nutzung'], reverse=True)

        # Pruning-Stats
        pruning = neuro.get('pruning', {})
        faden_stats = neuro.get('faden_statistik', {})

        return {
            'egon_id': egon_id,
            'regionen': regionen,
            'aktivste_region': regionen[0]['region'] if regionen else None,
            'pruning': pruning,
            'faden_statistik': faden_stats,
        }
    except Exception as e:
        return {'egon_id': egon_id, 'regionen': [], 'error': str(e)}


# ================================================================
# 6. DNA-Morphologie — Welche Regionen sind von Natur aus staerker
# ================================================================

@router.get('/egon/{egon_id}/brain/dna')
async def get_brain_dna(egon_id: str):
    """DNA-abhaengige Gehirn-Morphologie.

    Zeigt welche Verbindungen aufgrund der DNA (Drives) von Natur
    aus dicker/duenner sind. Fuer den "Fingerabdruck" des Gehirns.
    """
    try:
        from engine.neuroplastizitaet import dna_morphologie_modifikatoren

        mods = dna_morphologie_modifikatoren(egon_id)
        state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}
        drives = state.get('drives', {})
        dna_profile = state.get('dna_profile', 'DEFAULT')

        # Dominant Drives finden
        dominant = sorted(
            [(k, v) for k, v in drives.items() if isinstance(v, (int, float))],
            key=lambda x: x[1], reverse=True
        )[:3]

        return {
            'egon_id': egon_id,
            'dna_profile': dna_profile,
            'dominant_drives': [{'drive': d[0], 'value': round(d[1], 3)} for d in dominant],
            'morphologie_modifikatoren': mods,
            'beschreibung': _dna_beschreibung(mods),
        }
    except Exception as e:
        return {'egon_id': egon_id, 'error': str(e)}


def _dna_beschreibung(mods: dict) -> str:
    """Menschenlesbarer Text ueber die DNA-Morphologie."""
    if not mods:
        return 'Ausgewogene Gehirn-Architektur (DEFAULT-Profil).'

    teile = []
    for faden_id, mod in mods.items():
        bonus = mod.get('dicke_bonus', 0)
        # Faden-ID zerlegen: "anat_thalamus_praefrontal" -> "Thalamus → Präfrontal"
        parts = faden_id.replace('anat_', '').split('_')
        von = parts[0].title() if parts else '?'
        nach = parts[1].title() if len(parts) > 1 else '?'

        if bonus > 0:
            teile.append(f'{von}->{nach} verstaerkt (+{bonus:.0%})')
        elif bonus < 0:
            teile.append(f'{von}->{nach} abgeschwaecht ({bonus:.0%})')

    return '. '.join(teile) + '.' if teile else ''


# ================================================================
# 7. Decision-Log — Kalibrierungs-Sperren (Patch 17)
# ================================================================

@router.get('/egon/{egon_id}/brain/decisions')
async def get_brain_decisions(
    egon_id: str,
    since: float = Query(0, description='Unix-Timestamp — nur Eintraege danach'),
):
    """Decision-Log: Welche Kalibrierungs-Sperren haben gegriffen.

    Zeigt welche der 4 Patch-17-Sperren wann ausgeloest wurden:
    - homoestase: Notfall-Bremse (PANIC/RAGE > 0.95)
    - thalamus: Emotion-Floor-Upgrade (max_emotion > 0.75 -> Pfad C)
    - metacognition: Ueberflutet-Sperre (max_drive > 0.85)
    - decay: Flashbulb-Nacht-Rettung (marker > 0.85)

    Nuetzlich fuer Debugging: Warum hat ein EGON 'komisch' reagiert?
    """
    try:
        from engine.kalibrierung import get_decision_log
        entries = get_decision_log(egon_id, seit_ts=since)
        return {
            'egon_id': egon_id,
            'decisions': entries,
            'count': len(entries),
        }
    except ImportError:
        return {'egon_id': egon_id, 'decisions': [], 'count': 0,
                'error': 'kalibrierung module not available'}
    except Exception as e:
        return {'egon_id': egon_id, 'decisions': [], 'count': 0,
                'error': str(e)}


# ================================================================
# 8. Diary Debug — Owner Diary + Self Diary Eintraege
# ================================================================

@router.get('/egon/{egon_id}/brain/prompt-debug')
async def get_prompt_debug(egon_id: str):
    """DEBUG: Zeigt den System-Prompt wie er aktuell gebaut wird.

    Hilft zu pruefen ob Diary, Contacts, etc. korrekt injiziert werden.
    """
    try:
        from engine.prompt_builder import build_system_prompt
        prompt = build_system_prompt(
            egon_id, message_count=1,
            conversation_type='owner_chat')

        # Suche nach Diary-Sektionen
        has_owner_diary = 'WAS BEI MEINEM OWNER' in prompt
        has_self_diary = 'MEIN EIGENES LEBEN' in prompt
        has_contacts = 'PERSONEN AUS GESPRAECHEN' in prompt
        has_follow_up = 'WICHTIGE OFFENE THEMEN' in prompt

        return {
            'egon_id': egon_id,
            'prompt_length': len(prompt),
            'has_owner_diary': has_owner_diary,
            'has_self_diary': has_self_diary,
            'has_contacts': has_contacts,
            'has_follow_up': has_follow_up,
            'prompt_sections': [
                line for line in prompt.split('\n')
                if line.startswith('# ') or line.startswith('!! ')
            ],
            'diary_section': _extract_section(prompt, 'WAS BEI MEINEM OWNER'),
            'self_diary_section': _extract_section(prompt, 'MEIN EIGENES LEBEN'),
        }
    except Exception as e:
        return {'error': str(e)}


def _extract_section(prompt: str, heading: str) -> str:
    """Extrahiert eine Sektion aus dem Prompt (bis zum naechsten # Heading)."""
    if heading not in prompt:
        return ''
    start = prompt.index(heading)
    rest = prompt[start:]
    # Finde naechstes Heading
    lines = rest.split('\n')
    section = [lines[0]]
    for line in lines[1:]:
        if line.startswith('# ') and not line.startswith('# WAS') and not line.startswith('# MEIN'):
            break
        section.append(line)
    return '\n'.join(section)[:1000]


@router.get('/egon/{egon_id}/brain/diary')
async def get_diary(egon_id: str, limit: int = Query(10, ge=1, le=50)):
    """Gibt Owner Diary + Self Diary Eintraege zurueck.

    Debugging-Endpoint: Zeigt was der EGON sich gemerkt hat.
    """
    result = {
        'egon_id': egon_id,
        'owner_diary': {'entries': [], 'count': 0},
        'self_diary': {'entries': [], 'count': 0},
    }

    # Owner Diary
    try:
        owner = read_yaml_organ(egon_id, 'social', 'owner_diary.yaml')
        if owner and owner.get('entries'):
            entries = owner['entries'][-limit:]
            result['owner_diary'] = {
                'entries': entries,
                'count': len(owner['entries']),
            }
    except Exception as e:
        result['owner_diary']['error'] = str(e)

    # Self Diary
    try:
        self_d = read_yaml_organ(egon_id, 'social', 'self_diary.yaml')
        if self_d and self_d.get('entries'):
            entries = self_d['entries'][-limit:]
            result['self_diary'] = {
                'entries': entries,
                'count': len(self_d['entries']),
            }
    except Exception as e:
        result['self_diary']['error'] = str(e)

    return result


# ================================================================
# 9. Region Detail — Deep-Dive in einzelne Hirnregionen
# ================================================================

# Farben fuer Emotions-Nodes
_EMOTION_COLORS = {
    'joy': '#fbbf24', 'excitement': '#f59e0b', 'anger': '#ef4444',
    'fear': '#a855f7', 'sadness': '#3b82f6', 'surprise': '#ec4899',
    'pride': '#f97316', 'gratitude': '#10b981', 'curiosity': '#06b6d4',
    'love': '#e91e63', 'anxiety': '#a78bfa', 'loneliness': '#6366f1',
    'caution': '#eab308', 'warmth': '#f472b6', 'confusion': '#8b5cf6',
}

# Farben fuer Drive-Nodes
_DRIVE_COLORS = {
    'SEEKING': '#fbbf24', 'PLAY': '#4ade80', 'CARE': '#f472b6',
    'PANIC': '#ef4444', 'RAGE': '#dc2626', 'FEAR': '#a855f7',
    'LUST': '#e91e63', 'LEARNING': '#06b6d4', 'ACTION': '#f59e0b',
    'GRIEF': '#6366f1',
}


@router.get('/egon/{egon_id}/brain/region/{region_name}')
async def get_brain_region_detail(egon_id: str, region_name: str):
    """Deep-Dive: Gibt ALLE Organ-Daten einer spezifischen Hirnregion zurueck.

    Jede Region liefert sub_nodes (die einzelnen Datenpunkte) und
    optionale connections (interne Verbindungen).

    region_name: bonds | praefrontal | amygdala | hippocampus |
                 thalamus | hypothalamus | hirnstamm | neokortex |
                 insula | cerebellum
    """
    loaders = {
        'bonds': _load_bonds_detail,
        'praefrontal': _load_praefrontal_detail,
        'amygdala': _load_amygdala_detail,
        'hippocampus': _load_hippocampus_detail,
        'thalamus': _load_thalamus_detail,
        'hypothalamus': _load_hypothalamus_detail,
        'hirnstamm': _load_hirnstamm_detail,
        'neokortex': _load_neokortex_detail,
        'insula': _load_insula_detail,
        'cerebellum': _load_cerebellum_detail,
    }
    loader = loaders.get(region_name)
    if not loader:
        return {'error': f'Unbekannte Region: {region_name}',
                'gueltige_regionen': list(loaders.keys())}
    try:
        return await loader(egon_id)
    except Exception as e:
        return {'egon_id': egon_id, 'region': region_name,
                'sub_nodes': [], 'error': str(e)}


# --- Bonds (Bindungszentrum) ---

async def _load_bonds_detail(egon_id: str) -> dict:
    from engine.neuroplastizitaet import BOND_FARBEN, _clamp

    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml') or {}
    bonds = bonds_data.get('bonds', [])
    sub_nodes = []

    for bond in bonds:
        if not isinstance(bond, dict):
            continue
        partner_id = bond.get('id', bond.get('partner_id', ''))
        score = bond.get('score', 0)
        staerke = score / 100.0 if score > 1 else score
        bond_typ = bond.get('bond_typ', 'bekannt')

        # Partner-Name
        # Owner-Bonds: Echten Namen, Person-Bonds: name-Feld, EGON-Bonds: naming.py
        bond_name_field = bond.get('name', '').strip().strip('<>')
        entity_type_raw = bond.get('type', 'egon')
        if entity_type_raw == 'owner':
            # Owner-Bond: Echten Owner-Namen zeigen, nicht "Owner"
            partner_name = _resolve_owner_name(egon_id)
        elif entity_type_raw == 'person' and bond_name_field:
            # Person-Bond: Name direkt aus dem Bond nehmen
            partner_name = bond_name_field
        elif partner_id.startswith('person_') and bond_name_field:
            partner_name = bond_name_field
        else:
            try:
                from engine.naming import get_display_name
                partner_name = get_display_name(partner_id, 'voll')
            except Exception:
                # Fallback: Letzten Teil der ID nehmen (eva_002 -> Eva)
                parts = partner_id.split('_')
                partner_name = parts[0].title() if parts else partner_id

        # Social Map laden
        social_map = {}
        try:
            sm = read_yaml_organ(egon_id, 'skills/memory/social_mapping',
                                 f'ueber_{partner_id}.yaml')
            if sm:
                social_map = {
                    'erster_eindruck': sm.get('mein_eindruck', {}).get('erster_eindruck', ''),
                    'aktueller_eindruck': sm.get('mein_eindruck', {}).get('aktueller_eindruck', ''),
                    'emotionale_bewertung': sm.get('emotionale_bewertung', {}),
                    'interaktionen_gesamt': sm.get('identitaet', {}).get('interaktionen_gesamt', 0),
                }
        except Exception:
            pass

        # Chat-Count
        chat_count = 0
        try:
            pair = sorted([egon_id, partner_id])
            chat_file = os.path.join(EGON_DATA_DIR, 'shared', 'egon_chats',
                                     f'{pair[0]}--{pair[1]}.json')
            if os.path.isfile(chat_file):
                with open(chat_file, 'r', encoding='utf-8') as f:
                    chat_count = len(json.load(f))
        except Exception:
            pass

        # Entity-Typ bestimmen: person / egon / owner
        entity_type = bond.get('type', 'egon')
        type_label_map = {'person': 'Person', 'egon': 'Egon', 'owner': 'Bezugsmensch'}
        type_label = type_label_map.get(entity_type, entity_type.title())
        # Label: "Ron (Person)" oder "Eva (Egon)" oder "Owner (Owner)"
        display_label = f'{partner_name} ({type_label})'

        # Farbe basiert auf Entity-Typ (nicht nur Bond-Typ)
        if entity_type == 'owner':
            hex_color = '#ffd700'     # Gold fuer Owner
        elif entity_type == 'person':
            hex_color = '#fb923c'     # Orange fuer Personen (immer)
        else:
            hex_color = '#7db4e0'     # Blau fuer andere EGONs

        sub_nodes.append({
            'id': f'bond_{partner_id}',
            'label': display_label,
            'type': 'bond',
            'hex': hex_color,
            'size': max(0.15, staerke),
            'importance': staerke,
            'summary': f'Score: {score}, Trust: {bond.get("trust", 0):.0%}, Typ: {bond_typ}',
            'detail': {
                'partner_id': partner_id,
                'partner_name': partner_name,
                'entity_type': entity_type,
                'score': score,
                'trust': bond.get('trust', 0.5),
                'bond_typ': bond_typ,
                'attachment_style': bond.get('attachment_style', 'undefined'),
                'familiarity': bond.get('familiarity', 0),
                'hat_narbe': bond.get('hat_narbe', False),
                'emotional_debt': bond.get('emotional_debt', 0),
                'last_interaction': bond.get('last_interaction', ''),
                'first_interaction': bond.get('first_interaction', ''),
                'history': bond.get('bond_history', []),
                'observations': bond.get('observations', []),
                'social_map': social_map,
                'chat_count': chat_count,
                'resonanz_score': bond.get('resonanz_score', None),
                'resonanz_status': bond.get('resonanz_status', None),
            },
        })

    # Owner-Diary als eigenen Node
    try:
        diary = read_yaml_organ(egon_id, 'social', 'owner_diary.yaml')
        if diary and diary.get('entries'):
            entries = diary['entries'][-10:]
            sub_nodes.append({
                'id': 'owner_diary',
                'label': 'Owner-Tagebuch',
                'type': 'diary',
                'hex': '#ffd54f',
                'size': 0.35,
                'importance': 0.7,
                'summary': f'{len(diary["entries"])} Eintraege',
                'detail': {'entries': entries, 'total': len(diary['entries'])},
            })
    except Exception:
        pass

    sub_nodes.sort(key=lambda x: x['importance'], reverse=True)
    return {
        'egon_id': egon_id, 'region': 'bonds',
        'sub_nodes': sub_nodes, 'connections': [],
        'metadata': {'total_items': len(sub_nodes)},
    }


# --- Praefrontal (Bewusstsein/Ego) ---

async def _load_praefrontal_detail(egon_id: str) -> dict:
    sub_nodes = []
    state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}

    # 1. Ego
    ego_text = read_organ(egon_id, 'core', 'ego.md') or ''
    if ego_text:
        sub_nodes.append({
            'id': 'ego',
            'label': 'Ego (Persoenlichkeit)',
            'type': 'text',
            'hex': '#5e7ce0',
            'size': 0.5,
            'importance': 0.9,
            'summary': f'{len(ego_text)} Zeichen',
            'detail': {'raw_text': ego_text[:3000], 'total_chars': len(ego_text)},
        })

    # 2. Self-Concept
    self_md = read_organ(egon_id, 'social', 'egon_self.md') or ''
    if self_md:
        sub_nodes.append({
            'id': 'self_concept',
            'label': 'Selbstbild',
            'type': 'text',
            'hex': '#818cf8',
            'size': 0.4,
            'importance': 0.8,
            'summary': f'{len(self_md)} Zeichen',
            'detail': {'raw_text': self_md[:3000], 'total_chars': len(self_md)},
        })

    # 3. Inner Voice (letzte Eintraege)
    iv_text = read_organ(egon_id, 'memory', 'inner_voice.md') or ''
    if not iv_text:
        iv_text = read_organ(egon_id, '', 'inner_voice.md') or ''
    if iv_text:
        sub_nodes.append({
            'id': 'inner_voice',
            'label': 'Innere Stimme',
            'type': 'text',
            'hex': '#a78bfa',
            'size': 0.45,
            'importance': 0.85,
            'summary': 'Letzte innere Gedanken',
            'detail': {'raw_text': iv_text[-2000:], 'total_chars': len(iv_text)},
        })

    # 4. Metacognition
    mc = state.get('metacognition', state.get('self_assessment', {}))
    if mc:
        sub_nodes.append({
            'id': 'metacognition',
            'label': 'Metakognition',
            'type': 'metacognition',
            'hex': '#c084fc',
            'size': 0.3,
            'importance': 0.6,
            'summary': 'Selbstbeobachtung',
            'detail': mc,
        })

    # 5. Processing State
    proc = state.get('processing', {})
    if proc:
        sub_nodes.append({
            'id': 'processing',
            'label': 'Verarbeitungszustand',
            'type': 'processing',
            'hex': '#60a5fa',
            'size': 0.25,
            'importance': 0.4,
            'summary': f'Speed: {proc.get("speed", "?")}',
            'detail': proc,
        })

    return {
        'egon_id': egon_id, 'region': 'praefrontal',
        'sub_nodes': sub_nodes, 'connections': [],
        'metadata': {'total_items': len(sub_nodes)},
    }


# --- Amygdala (Emotionaler Kern) ---

async def _load_amygdala_detail(egon_id: str) -> dict:
    state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}
    sub_nodes = []

    # Active Emotions
    for i, emo in enumerate(state.get('express', {}).get('active_emotions', [])):
        emo_type = emo.get('type', 'unknown')
        intensity = emo.get('intensity', 0)
        sub_nodes.append({
            'id': f'emotion_{emo_type}_{i}',
            'label': f'{emo_type.title()} ({intensity:.0%})',
            'type': 'emotion',
            'hex': _EMOTION_COLORS.get(emo_type, '#8890aa'),
            'size': max(0.12, intensity * 0.5),
            'importance': intensity,
            'summary': emo.get('verbal_anchor', emo.get('cause', '')),
            'detail': emo,
        })

    # Drives
    for drive, value in state.get('drives', {}).items():
        if not isinstance(value, (int, float)):
            continue
        sub_nodes.append({
            'id': f'drive_{drive}',
            'label': f'{drive} ({value:.0%})',
            'type': 'drive',
            'hex': _DRIVE_COLORS.get(drive, '#5e7ce0'),
            'size': max(0.1, value * 0.4),
            'importance': value,
            'summary': f'Panksepp-Drive',
            'detail': {'drive': drive, 'value': round(value, 3)},
        })

    # Survive
    for key, data in state.get('survive', {}).items():
        if not isinstance(data, dict):
            continue
        val = data.get('value', 0)
        sub_nodes.append({
            'id': f'survive_{key}',
            'label': f'{key.title()}: {val:.0%}',
            'type': 'survive',
            'hex': '#ef4444' if val < 0.3 else '#4ade80',
            'size': 0.2,
            'importance': max(0, 1.0 - val),
            'summary': data.get('verbal', ''),
            'detail': data,
        })

    # Thrive
    for key, data in state.get('thrive', {}).items():
        if not isinstance(data, dict):
            continue
        val = data.get('value', 0)
        sub_nodes.append({
            'id': f'thrive_{key}',
            'label': f'{key.title()}: {val:.0%}',
            'type': 'thrive',
            'hex': '#a78bfa',
            'size': 0.18,
            'importance': max(0, 1.0 - val),
            'summary': data.get('verbal', ''),
            'detail': data,
        })

    # Emotional Gravity
    eg = state.get('emotional_gravity', {})
    if eg:
        sub_nodes.append({
            'id': 'emotional_gravity',
            'label': f'Gravitation: {eg.get("interpretation_bias", "?")}',
            'type': 'gravity',
            'hex': '#fbbf24',
            'size': 0.2,
            'importance': 0.5,
            'summary': f'Baseline Mood: {eg.get("baseline_mood", "?")}',
            'detail': eg,
        })

    # Somatic Markers
    markers_md = read_organ(egon_id, '', 'markers.md') or ''
    if markers_md.strip():
        sub_nodes.append({
            'id': 'somatic_markers',
            'label': 'Somatische Marker',
            'type': 'text',
            'hex': '#f472b6',
            'size': 0.3,
            'importance': 0.5,
            'summary': 'Koerperliche Erinnerungsmarker',
            'detail': {'raw_text': markers_md[:3000]},
        })

    return {
        'egon_id': egon_id, 'region': 'amygdala',
        'sub_nodes': sub_nodes, 'connections': [],
        'metadata': {'total_items': len(sub_nodes)},
    }


# --- Hippocampus (Gedaechtnis) ---

async def _load_hippocampus_detail(egon_id: str) -> dict:
    sub_nodes = []

    # Recent Memory
    recent = read_organ(egon_id, 'skills', 'memory/recent_memory.md') or ''
    if recent.strip():
        sub_nodes.append({
            'id': 'recent_memory',
            'label': 'Kuerzliches Gedaechtnis (7 Tage)',
            'type': 'text',
            'hex': '#2dd4bf',
            'size': 0.45,
            'importance': 0.9,
            'summary': f'{len(recent)} Zeichen',
            'detail': {'raw_text': recent[:4000]},
        })

    # Episodes (letzte 30)
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml') or {}
    all_eps = episodes_data.get('episodes', []) or []
    for ep in all_eps[-30:]:
        if not isinstance(ep, dict):
            continue
        sig = ep.get('significance', 0.3)
        ep_id = ep.get('id', '?')
        sub_nodes.append({
            'id': f'episode_{ep_id}',
            'label': f'{ep_id} — {ep.get("date", "?")}',
            'type': 'episode',
            'hex': '#2dd4bf',
            'size': max(0.1, 0.12 + sig * 0.25),
            'importance': sig,
            'summary': (ep.get('summary', '') or '')[:120],
            'detail': ep,
        })

    # Experiences / Sparks
    exp_data = read_yaml_organ(egon_id, 'memory', 'experience.yaml') or {}
    for xp in (exp_data.get('experiences', []) or [])[-20:]:
        if not isinstance(xp, dict):
            continue
        sub_nodes.append({
            'id': f'xp_{xp.get("id", xp.get("date", "?"))}',
            'label': f'Erfahrung: {xp.get("skill", xp.get("category", "?"))}',
            'type': 'experience',
            'hex': '#60a5fa',
            'size': 0.15,
            'importance': xp.get('confidence', 0.5),
            'summary': (xp.get('learnings', xp.get('insight', '')) or '')[:100],
            'detail': xp,
        })

    # Cycle Memory
    cycle = read_organ(egon_id, 'skills', 'memory/memory_cycle_current.md') or ''
    if cycle.strip():
        sub_nodes.append({
            'id': 'cycle_memory',
            'label': 'Zyklusgedaechtnis',
            'type': 'text',
            'hex': '#0ea5e9',
            'size': 0.3,
            'importance': 0.6,
            'summary': 'Konsolidiertes Zyklusgedaechtnis',
            'detail': {'raw_text': cycle[:3000]},
        })

    # Archive
    archive = read_organ(egon_id, 'skills', 'memory/memory_archive.md') or ''
    if archive.strip():
        sub_nodes.append({
            'id': 'memory_archive',
            'label': 'Lebensarchiv',
            'type': 'text',
            'hex': '#6366f1',
            'size': 0.25,
            'importance': 0.4,
            'summary': 'Langzeit-Erinnerungsarchiv',
            'detail': {'raw_text': archive[:3000]},
        })

    # Cue Index
    cue = read_yaml_organ(egon_id, 'memory', 'cue_index.yaml') or {}
    if cue:
        sub_nodes.append({
            'id': 'cue_index',
            'label': 'Cue-Index',
            'type': 'cue_index',
            'hex': '#fbbf24',
            'size': 0.2,
            'importance': 0.5,
            'summary': f'{len(cue.get("wort_index", {}))} Woerter indexiert',
            'detail': {
                'wort_count': len(cue.get('wort_index', {})),
                'emotion_count': len(cue.get('emotions_index', {})),
                'partner_count': len(cue.get('partner_index', {})),
                'faden_count': len(cue.get('faden_index', {})),
                'stark_count': len(cue.get('stark_index', [])),
            },
        })

    return {
        'egon_id': egon_id, 'region': 'hippocampus',
        'sub_nodes': sub_nodes, 'connections': [],
        'metadata': {'total_items': len(sub_nodes),
                     'total_episodes': len(all_eps)},
    }


# --- Thalamus (Sensorische Schaltung) ---

async def _load_thalamus_detail(egon_id: str) -> dict:
    state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}
    sub_nodes = []

    # Routing
    proc = state.get('processing', {})
    routing = state.get('letztes_routing', state.get('thalamus_routing', {}))
    if routing or proc:
        sub_nodes.append({
            'id': 'routing',
            'label': 'Aktuelles Routing',
            'type': 'routing',
            'hex': '#f59e0b',
            'size': 0.4,
            'importance': 0.8,
            'summary': f'Pfad: {routing.get("pfad", proc.get("speed", "?"))}',
            'detail': {**proc, **routing},
        })

    # Decision History
    try:
        from engine.kalibrierung import get_decision_log
        decisions = get_decision_log(egon_id)
        for i, dec in enumerate(decisions[-10:]):
            sub_nodes.append({
                'id': f'decision_{i}',
                'label': f'{dec.get("lock_type", "?")} ({dec.get("trigger_value", 0):.2f})',
                'type': 'decision',
                'hex': '#ef4444' if dec.get('lock_type') == 'homoestase' else '#f59e0b',
                'size': 0.2,
                'importance': dec.get('trigger_value', 0.5),
                'summary': dec.get('description', ''),
                'detail': dec,
            })
    except Exception:
        pass

    return {
        'egon_id': egon_id, 'region': 'thalamus',
        'sub_nodes': sub_nodes, 'connections': [],
        'metadata': {'total_items': len(sub_nodes)},
    }


# --- Hypothalamus (Koerperregulation) ---

async def _load_hypothalamus_detail(egon_id: str) -> dict:
    state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}
    sub_nodes = []

    # Drives als Gauges
    for drive, value in state.get('drives', {}).items():
        if not isinstance(value, (int, float)):
            continue
        sub_nodes.append({
            'id': f'hypo_drive_{drive}',
            'label': f'{drive}: {value:.0%}',
            'type': 'drive_gauge',
            'hex': _DRIVE_COLORS.get(drive, '#5e7ce0'),
            'size': max(0.12, value * 0.35),
            'importance': value,
            'summary': 'Panksepp-Antrieb',
            'detail': {'drive': drive, 'value': round(value, 3)},
        })

    # Circadian
    circ = state.get('zirkadian', state.get('circadian', {}))
    if circ:
        sub_nodes.append({
            'id': 'circadian',
            'label': f'Zirkadian: {circ.get("phase", "?")}',
            'type': 'circadian',
            'hex': '#fbbf24',
            'size': 0.3,
            'importance': 0.6,
            'summary': f'Phase: {circ.get("phase", "unbekannt")}',
            'detail': circ,
        })

    # Energy/Safety (Survive)
    for key, data in state.get('survive', {}).items():
        if not isinstance(data, dict):
            continue
        sub_nodes.append({
            'id': f'hypo_survive_{key}',
            'label': f'{key.title()}: {data.get("value", 0):.0%}',
            'type': 'survive',
            'hex': '#10b981',
            'size': 0.2,
            'importance': 0.5,
            'summary': data.get('verbal', ''),
            'detail': data,
        })

    return {
        'egon_id': egon_id, 'region': 'hypothalamus',
        'sub_nodes': sub_nodes, 'connections': [],
        'metadata': {'total_items': len(sub_nodes)},
    }


# --- Hirnstamm (DNA/Identitaetskern) ---

async def _load_hirnstamm_detail(egon_id: str) -> dict:
    state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}
    sub_nodes = []

    # SOUL/DNA
    dna_text = read_organ(egon_id, 'core', 'soul.md') or ''
    if not dna_text:
        dna_text = read_organ(egon_id, 'core', 'dna.md') or ''
    if not dna_text:
        dna_text = read_organ(egon_id, '', 'soul.md') or ''
    if dna_text:
        sub_nodes.append({
            'id': 'dna',
            'label': 'DNA (Kern-Identitaet)',
            'type': 'text',
            'hex': '#f97316',
            'size': 0.5,
            'importance': 1.0,
            'summary': f'{len(dna_text)} Zeichen — Unveraenderbar',
            'detail': {'raw_text': dna_text[:5000], 'total_chars': len(dna_text)},
        })

    # DNA Profile
    dna_profile = state.get('dna_profile', 'DEFAULT')
    sub_nodes.append({
        'id': 'dna_profile',
        'label': f'Profil: {dna_profile}',
        'type': 'dna_profile',
        'hex': '#fb923c',
        'size': 0.3,
        'importance': 0.8,
        'summary': f'DNA-Profil bestimmt Morphologie',
        'detail': {
            'profile': dna_profile,
            'geschlecht': state.get('geschlecht', '?'),
            'generation': state.get('generation', 0),
            'zyklus': state.get('zyklus', 0),
        },
    })

    # Pairing
    pairing = state.get('pairing', {})
    if pairing:
        sub_nodes.append({
            'id': 'pairing',
            'label': f'Pairing: {pairing.get("status", "keine")}',
            'type': 'pairing',
            'hex': '#e91e63',
            'size': 0.25,
            'importance': 0.6,
            'summary': f'Partner: {pairing.get("partner", "keiner")}',
            'detail': pairing,
        })

    return {
        'egon_id': egon_id, 'region': 'hirnstamm',
        'sub_nodes': sub_nodes, 'connections': [],
        'metadata': {'total_items': len(sub_nodes)},
    }


# --- Neokortex (Wissen/Skills) ---

async def _load_neokortex_detail(egon_id: str) -> dict:
    sub_nodes = []

    # Skills
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml') or {}
    for sk in (skills_data.get('skills', []) or []):
        if not isinstance(sk, dict):
            continue
        level = sk.get('level', 1)
        freshness = sk.get('freshness', 0.5)
        sub_nodes.append({
            'id': f'skill_{sk.get("id", sk.get("name", "?"))}',
            'label': f'{sk.get("name", "?")} (L{level})',
            'type': 'skill',
            'hex': '#4ade80' if freshness > 0.5 else '#fbbf24',
            'size': max(0.1, level * 0.1),
            'importance': freshness,
            'summary': f'Freshness: {freshness:.0%}',
            'detail': sk,
        })

    # Skills.md (Freitext)
    skills_md = read_organ(egon_id, '', 'skills.md') or ''
    if skills_md.strip():
        sub_nodes.append({
            'id': 'skills_text',
            'label': 'Skill-Profil (Freitext)',
            'type': 'text',
            'hex': '#06b6d4',
            'size': 0.3,
            'importance': 0.5,
            'summary': f'{len(skills_md)} Zeichen',
            'detail': {'raw_text': skills_md[:3000]},
        })

    # Experiences
    exp_data = read_yaml_organ(egon_id, 'memory', 'experience.yaml') or {}
    for xp in (exp_data.get('experiences', []) or [])[-15:]:
        if not isinstance(xp, dict):
            continue
        sub_nodes.append({
            'id': f'neocortex_xp_{xp.get("id", xp.get("date", "?"))}',
            'label': f'Erfahrung: {xp.get("skill", xp.get("task", "?"))}',
            'type': 'experience',
            'hex': '#60a5fa',
            'size': 0.12,
            'importance': xp.get('confidence', 0.5),
            'summary': (xp.get('learnings', '') or '')[:100],
            'detail': xp,
        })

    return {
        'egon_id': egon_id, 'region': 'neokortex',
        'sub_nodes': sub_nodes, 'connections': [],
        'metadata': {'total_items': len(sub_nodes)},
    }


# --- Insula (Koerperbewusstsein) ---

async def _load_insula_detail(egon_id: str) -> dict:
    state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}
    sub_nodes = []

    # Body
    body_md = read_organ(egon_id, 'core', 'body.md') or ''
    if body_md.strip():
        sub_nodes.append({
            'id': 'body_map',
            'label': 'Koerper-Karte',
            'type': 'text',
            'hex': '#f472b6',
            'size': 0.4,
            'importance': 0.7,
            'summary': 'Motor-Vokabular + Knochen',
            'detail': {'raw_text': body_md[:3000]},
        })

    # Somatic Markers
    markers_md = read_organ(egon_id, '', 'markers.md') or ''
    if markers_md.strip():
        sub_nodes.append({
            'id': 'insula_markers',
            'label': 'Somatische Marker',
            'type': 'text',
            'hex': '#ec4899',
            'size': 0.35,
            'importance': 0.6,
            'summary': 'Koerperliche Erinnerungsmarker',
            'detail': {'raw_text': markers_md[:3000]},
        })

    # Somatic Gate
    sg = state.get('somatic_gate', {})
    if sg:
        sub_nodes.append({
            'id': 'somatic_gate',
            'label': 'Somatisches Tor',
            'type': 'somatic_gate',
            'hex': '#be185d',
            'size': 0.25,
            'importance': 0.5,
            'summary': 'Koerperliche Entscheidungsschwelle',
            'detail': sg,
        })

    return {
        'egon_id': egon_id, 'region': 'insula',
        'sub_nodes': sub_nodes, 'connections': [],
        'metadata': {'total_items': len(sub_nodes)},
    }


# --- Cerebellum (Mustererkennung) ---

async def _load_cerebellum_detail(egon_id: str) -> dict:
    sub_nodes = []

    # Lebensfaeden
    try:
        threads_data = read_yaml_organ(egon_id, 'skills/memory', 'thread_index.yaml')
        if threads_data:
            for t_id, t_info in threads_data.items():
                if not isinstance(t_info, dict):
                    continue
                sub_nodes.append({
                    'id': f'thread_{t_id}',
                    'label': t_info.get('title', t_id),
                    'type': 'lebensfaden',
                    'hex': '#a78bfa',
                    'size': 0.2,
                    'importance': 0.5,
                    'summary': f'Phase: {t_info.get("phase", "?")}',
                    'detail': t_info,
                })
    except Exception:
        pass

    # Lebensfaeden.yaml (falls vorhanden)
    faeden = read_yaml_organ(egon_id, 'core', 'lebensfaeden.yaml')
    if not faeden:
        faeden = read_yaml_organ(egon_id, 'skills/memory', 'lebensfaeden.yaml')
    if faeden and isinstance(faeden, dict):
        for key, val in faeden.items():
            if isinstance(val, dict) and key not in [sn['id'] for sn in sub_nodes]:
                sub_nodes.append({
                    'id': f'faden_{key}',
                    'label': val.get('titel', val.get('title', key)),
                    'type': 'lebensfaden',
                    'hex': '#7c3aed',
                    'size': 0.2,
                    'importance': 0.5,
                    'summary': f'{val.get("status", val.get("phase", "?"))}',
                    'detail': val,
                })

    # Memory.md (Zwiebel-Modell)
    mem_md = read_organ(egon_id, '', 'memory.md') or ''
    if mem_md.strip():
        sub_nodes.append({
            'id': 'memory_layers',
            'label': 'Gedaechtnis-Schichten',
            'type': 'text',
            'hex': '#8b5cf6',
            'size': 0.3,
            'importance': 0.4,
            'summary': 'L1-L5 Zwiebel-Modell',
            'detail': {'raw_text': mem_md[:3000]},
        })

    return {
        'egon_id': egon_id, 'region': 'cerebellum',
        'sub_nodes': sub_nodes, 'connections': [],
        'metadata': {'total_items': len(sub_nodes)},
    }


# ================================================================
# 11. Brain Search — Volltextsuche ueber ALLE Organe
# ================================================================

def _search_text(text: str, query: str, context_chars: int = 80) -> list:
    """Findet alle Vorkommen von query in text, gibt Match-Snippets zurueck."""
    if not text or not query:
        return []
    results = []
    lower_text = text.lower()
    lower_q = query.lower()
    start = 0
    while True:
        idx = lower_text.find(lower_q, start)
        if idx == -1:
            break
        # Snippet mit Kontext
        snip_start = max(0, idx - context_chars)
        snip_end = min(len(text), idx + len(query) + context_chars)
        snippet = ('...' if snip_start > 0 else '') + text[snip_start:snip_end].strip() + ('...' if snip_end < len(text) else '')
        results.append(snippet)
        start = idx + len(query)
        if len(results) >= 3:  # Max 3 Matches pro Quelle
            break
    return results


@router.get('/egon/{egon_id}/brain/search')
async def search_brain(egon_id: str, q: str = Query(..., min_length=1)):
    """Durchsucht ALLE Gehirn-Organe nach einem Suchbegriff."""
    query = q.strip()
    results = []

    # --- 1. Episodes ---
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml') or {}
    for ep in (episodes_data.get('episodes', []) or []):
        if not isinstance(ep, dict):
            continue
        searchable = ' '.join([
            ep.get('summary', ''),
            ' '.join(ep.get('tags', []) or []),
            ep.get('type', ''),
            str(ep.get('with', '')),
            str(ep.get('thread_title', '')),
        ])
        matches = _search_text(searchable, query)
        if matches:
            results.append({
                'id': f'episode_{ep.get("id", "?")}',
                'type': 'episode',
                'region': 'hippocampus',
                'label': f'Episode {ep.get("id", "?")} — {ep.get("date", "")}',
                'match': matches[0],
                'score': 0.9,
                'detail': ep,
            })

    # --- 2. Bonds (Observations + Partner) ---
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml') or {}
    for bond in (bonds_data.get('bonds', []) or []):
        if not isinstance(bond, dict):
            continue
        obs_text = ' '.join(bond.get('observations', []) or [])
        searchable = ' '.join([
            bond.get('id', ''), bond.get('bond_typ', ''), obs_text,
            str(bond.get('attachment_style', '')),
        ])
        matches = _search_text(searchable, query)
        if matches:
            results.append({
                'id': f'bond_{bond.get("id", "?")}',
                'type': 'bond',
                'region': 'bonds',
                'label': f'Bond: {bond.get("id", "?")} ({bond.get("bond_typ", "?")})',
                'match': matches[0],
                'score': 0.85,
                'detail': bond,
            })

    # --- 3. Experiences ---
    exp_data = read_yaml_organ(egon_id, 'memory', 'experience.yaml') or {}
    for xp in (exp_data.get('experiences', []) or []):
        if not isinstance(xp, dict):
            continue
        searchable = ' '.join([
            xp.get('skill', ''), xp.get('task', ''), xp.get('category', ''),
            xp.get('learnings', ''), xp.get('insight', ''),
        ])
        matches = _search_text(searchable, query)
        if matches:
            results.append({
                'id': f'xp_{xp.get("id", xp.get("date", "?"))}',
                'type': 'experience',
                'region': 'neokortex',
                'label': f'Erfahrung: {xp.get("skill", xp.get("task", "?"))}',
                'match': matches[0],
                'score': 0.8,
                'detail': xp,
            })

    # --- 4. Skills ---
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml') or {}
    for sk in (skills_data.get('skills', []) or []):
        if not isinstance(sk, dict):
            continue
        searchable = sk.get('name', '') + ' ' + sk.get('description', '')
        matches = _search_text(searchable, query)
        if matches:
            results.append({
                'id': f'skill_{sk.get("id", sk.get("name", "?"))}',
                'type': 'skill',
                'region': 'neokortex',
                'label': f'Skill: {sk.get("name", "?")}',
                'match': matches[0],
                'score': 0.75,
                'detail': sk,
            })

    # --- 5. Inner Voice ---
    inner = read_organ(egon_id, 'memory', 'inner_voice.md') or ''
    if not inner:
        inner = read_organ(egon_id, 'skills/memory', 'inner_voice.md') or ''
    matches = _search_text(inner, query)
    if matches:
        results.append({
            'id': 'inner_voice',
            'type': 'text',
            'region': 'praefrontal',
            'label': 'Innere Stimme',
            'match': matches[0],
            'score': 0.85,
            'detail': {'raw_text': inner[:3000]},
        })

    # --- 6. Ego ---
    ego = read_organ(egon_id, 'core', 'ego.md') or ''
    matches = _search_text(ego, query)
    if matches:
        results.append({
            'id': 'ego',
            'type': 'text',
            'region': 'praefrontal',
            'label': 'Ego (Persoenlichkeit)',
            'match': matches[0],
            'score': 0.7,
            'detail': {'raw_text': ego[:3000]},
        })

    # --- 7. Self-Concept ---
    self_md = read_organ(egon_id, 'social', 'egon_self.md') or ''
    matches = _search_text(self_md, query)
    if matches:
        results.append({
            'id': 'self_concept',
            'type': 'text',
            'region': 'praefrontal',
            'label': 'Selbstbild',
            'match': matches[0],
            'score': 0.7,
            'detail': {'raw_text': self_md[:3000]},
        })

    # --- 8. SOUL/DNA ---
    dna = read_organ(egon_id, 'core', 'soul.md') or ''
    if not dna:
        dna = read_organ(egon_id, 'core', 'dna.md') or ''
    if not dna:
        dna = read_organ(egon_id, '', 'soul.md') or ''
    matches = _search_text(dna, query)
    if matches:
        results.append({
            'id': 'dna',
            'type': 'text',
            'region': 'hirnstamm',
            'label': 'DNA (Kern-Identitaet)',
            'match': matches[0],
            'score': 0.6,
            'detail': {'raw_text': dna[:3000]},
        })

    # --- 9. Recent Memory ---
    recent = read_organ(egon_id, 'skills', 'memory/recent_memory.md') or ''
    matches = _search_text(recent, query)
    if matches:
        results.append({
            'id': 'recent_memory',
            'type': 'text',
            'region': 'hippocampus',
            'label': 'Kurzzeit-Gedaechtnis (7 Tage)',
            'match': matches[0],
            'score': 0.9,
            'detail': {'raw_text': recent[:4000]},
        })

    # --- 10. Owner Diary ---
    owner_diary = read_yaml_organ(egon_id, 'social', 'owner_diary.yaml') or {}
    for entry in (owner_diary.get('entries', []) or []):
        if not isinstance(entry, dict):
            continue
        searchable = ' '.join([
            entry.get('text', ''), entry.get('content', ''), entry.get('summary', ''),
        ])
        matches = _search_text(searchable, query)
        if matches:
            results.append({
                'id': f'diary_owner_{entry.get("date", "?")}',
                'type': 'diary',
                'region': 'bonds',
                'label': f'Owner-Tagebuch: {entry.get("date", "?")}',
                'match': matches[0],
                'score': 0.85,
                'detail': entry,
            })

    # --- 11. Self Diary ---
    self_diary = read_yaml_organ(egon_id, 'social', 'self_diary.yaml') or {}
    for entry in (self_diary.get('entries', []) or []):
        if not isinstance(entry, dict):
            continue
        searchable = ' '.join([
            entry.get('text', ''), entry.get('content', ''), entry.get('summary', ''),
        ])
        matches = _search_text(searchable, query)
        if matches:
            results.append({
                'id': f'diary_self_{entry.get("date", "?")}',
                'type': 'diary',
                'region': 'praefrontal',
                'label': f'Selbst-Tagebuch: {entry.get("date", "?")}',
                'match': matches[0],
                'score': 0.8,
                'detail': entry,
            })

    # --- 12. State (Emotions, Drives, Verbal Anchors) ---
    state = read_yaml_organ(egon_id, 'core', 'state.yaml') or {}
    for emo in (state.get('express', {}).get('active_emotions', []) or []):
        if not isinstance(emo, dict):
            continue
        searchable = ' '.join([
            emo.get('type', ''), emo.get('cause', ''), emo.get('verbal_anchor', ''),
        ])
        matches = _search_text(searchable, query)
        if matches:
            results.append({
                'id': f'emotion_{emo.get("type", "?")}',
                'type': 'emotion',
                'region': 'amygdala',
                'label': f'Emotion: {emo.get("type", "?")}',
                'match': matches[0],
                'score': 0.9,
                'detail': emo,
            })

    # --- 13. Social Mapping (ueber_*.yaml) ---
    social_dir = os.path.join(EGON_DATA_DIR, egon_id, 'social', 'social_mapping')
    if os.path.isdir(social_dir):
        for fname in os.listdir(social_dir):
            if fname.startswith('ueber_') and fname.endswith('.yaml'):
                fpath = os.path.join(social_dir, fname)
                try:
                    import yaml
                    with open(fpath, 'r', encoding='utf-8') as f:
                        smap = yaml.safe_load(f) or {}
                    searchable = ' '.join([
                        str(smap.get('erster_eindruck', '')),
                        str(smap.get('aktueller_eindruck', '')),
                        str(smap.get('emotionale_bewertung', '')),
                    ])
                    matches = _search_text(searchable, query)
                    if matches:
                        partner = fname.replace('ueber_', '').replace('.yaml', '')
                        results.append({
                            'id': f'social_map_{partner}',
                            'type': 'bond',
                            'region': 'bonds',
                            'label': f'Soziale Karte: {partner}',
                            'match': matches[0],
                            'score': 0.75,
                            'detail': smap,
                        })
                except Exception:
                    pass

    # --- 14. Body.md ---
    body = read_organ(egon_id, 'core', 'body.md') or ''
    matches = _search_text(body, query)
    if matches:
        results.append({
            'id': 'body_map',
            'type': 'text',
            'region': 'insula',
            'label': 'Koerper-Karte',
            'match': matches[0],
            'score': 0.6,
            'detail': {'raw_text': body[:3000]},
        })

    # Sortiere nach Score (absteigend)
    results.sort(key=lambda r: r.get('score', 0), reverse=True)

    return {
        'query': query,
        'egon_id': egon_id,
        'results': results[:30],  # Max 30 Ergebnisse
        'total': len(results),
    }


# ================================================================
# 11. Contact Management — Loeschen, Papierkorb, Wiederherstellen
# ================================================================

@router.delete('/egon/{egon_id}/brain/contact/{name}')
async def delete_contact_endpoint(egon_id: str, name: str):
    """Loescht einen Kontakt (verschiebt in Papierkorb).

    Kontaktkarte + Bond + Network-Eintrag werden entfernt.
    Der Kontakt bleibt 30 Tage im Papierkorb und kann wiederhergestellt werden.
    """
    try:
        from engine.contact_manager import delete_contact
        found = delete_contact(egon_id, name)
        if found:
            return {'status': 'trashed', 'name': name, 'egon_id': egon_id,
                    'message': f'{name} in Papierkorb verschoben (30 Tage aufbewahrt)'}
        else:
            return {'status': 'not_found', 'name': name, 'egon_id': egon_id,
                    'message': f'Kein Kontakt "{name}" gefunden'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@router.get('/egon/{egon_id}/brain/trash')
async def get_trash(egon_id: str):
    """Gibt den Papierkorb-Inhalt zurueck."""
    try:
        from engine.contact_manager import get_trash_summary
        items = get_trash_summary(egon_id)
        return {'egon_id': egon_id, 'items': items, 'count': len(items)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@router.post('/egon/{egon_id}/brain/trash/{name}/restore')
async def restore_contact_endpoint(egon_id: str, name: str):
    """Stellt einen Kontakt aus dem Papierkorb wieder her."""
    try:
        from engine.contact_manager import restore_from_trash
        restored = restore_from_trash(egon_id, name)
        if restored:
            return {'status': 'restored', 'name': name, 'egon_id': egon_id}
        else:
            return {'status': 'not_found', 'name': name, 'egon_id': egon_id,
                    'message': f'"{name}" nicht im Papierkorb gefunden'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


# ================================================================
# 12. Interaction Log — Wissenschaftliches Protokoll abrufen
# ================================================================

@router.get('/interaction-log')
async def get_interaction_log(
    date: Optional[str] = None,
    egon_id: Optional[str] = None,
    limit: int = Query(default=100, le=500),
):
    """Gibt das wissenschaftliche Interaktions-Protokoll zurueck.

    Query-Parameter:
        date: YYYY-MM-DD (default: heute)
        egon_id: Optional — nur Interaktionen dieses EGONs
        limit: Max Anzahl (default 100, max 500)

    Jeder Eintrag enthaelt: timestamp, user_message, display_text,
    inner_voice, thalamus, body_data, bone_update, pre/post_state,
    episode, experience, diary, self_diary, processing_time_ms.
    """
    from engine.interaction_log import read_interactions, get_log_files, count_interactions

    if date:
        records = read_interactions(date, egon_id=egon_id, limit=limit)
        return {
            'date': date,
            'egon_id': egon_id,
            'count': len(records),
            'interactions': records,
        }
    else:
        files = get_log_files()
        overview = []
        for f in files[-30:]:
            d = f.replace('.jsonl', '')
            counts = count_interactions(d)
            overview.append({
                'date': d,
                'total': sum(counts.values()),
                'per_egon': counts,
            })
        return {
            'log_files': files,
            'overview': overview,
        }


@router.get('/interaction-log/stats')
async def get_interaction_stats():
    """Statistiken ueber alle Interaktionen — fuer Paper-Analyse."""
    from engine.interaction_log import get_log_files, count_interactions

    total_per_egon: dict = {}
    total_all = 0

    for f in get_log_files():
        d = f.replace('.jsonl', '')
        counts = count_interactions(d)
        for eid, cnt in counts.items():
            total_per_egon[eid] = total_per_egon.get(eid, 0) + cnt
            total_all += cnt

    return {
        'total_interactions': total_all,
        'per_egon': total_per_egon,
        'log_days': len(get_log_files()),
    }
