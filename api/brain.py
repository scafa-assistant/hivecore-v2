"""Brain API — Neuro-Map Endpoints fuer das Frontend.

Stellt die strukturellen Gehirn-Daten bereit die Patch 16
(Neuroplastizitaet) im Backend generiert:

- /brain/snapshot:     Kompletter Faden-Zustand (alle Kategorien)
- /brain/events:       Polling fuer neue Events seit Timestamp
- /brain/bonds:        Alle Bonds als Liste mit Typ, Staerke, Narben
- /brain/interactions: Chat-Histories + Bond-Daten aller Partner
- /brain/regions:      Regionen-Nutzung (Aktivitaets-Heatmap)

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
from engine.organ_reader import read_yaml_organ

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
            try:
                from engine.naming import get_display_name
                partner_name = get_display_name(partner_id, 'voll')
            except Exception:
                partner_name = partner_id.split('_')[0].title() if '_' in partner_id else partner_id

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
