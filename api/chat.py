"""Chat-Endpoint — der wichtigste Endpoint.

Ablauf bei jedem Chat:
1. Chat-History holen
2. System-Prompt bauen (SOUL + MEMORY + MARKERS + WORKSPACE + ACTIONS)
3. Inner Voice generieren (unsichtbar)
4. LLM Call (Router entscheidet Tier)
5. Action Detection (###ACTION### Block parsen)
6. Post-Processing: Memory + Marker + Bond Update

Multi-EGON Chat-Types:
  owner_chat       → Owner redet mit eigenem EGON
  friend_owner_chat → Owner redet mit EGON eines Freundes
  egon_chat        → EGON redet mit befreundetem EGON
  agora_job        → Marketplace
  pulse            → Interner Pulse
"""

import asyncio
import json
import os
import re
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from config import BRAIN_VERSION, EGON_DATA_DIR
from engine.prompt_builder import build_system_prompt
from engine.memory import append_memory, compress_if_needed
from engine.markers import maybe_generate_marker
from engine.inner_voice_v2 import generate_inner_voice
from engine.bonds import update_bond_after_chat
from engine.friendship import are_friends
from engine.settings import read_settings
from llm.router import llm_chat
from llm.planner import should_use_tools
from engine.agent_loop import run_agent_loop
from engine.action_detector import detect_action
from engine.response_parser import parse_response
from engine.motor_translator import translate as motor_translate
from engine import interaction_log as ilog

router = APIRouter()


# ================================================================
# Emotion → Body-Action / Display-State Maps (Phase 3: Embodiment)
# ================================================================
def _log_motor_words(egon_id: str, body_data: dict, context: str = 'chat') -> None:
    """Loggt Motor-Word-Nutzung fuer spaetere Pattern-Analyse (Phase 5).

    Schreibt in memory/motor_log.yaml — wird von motor_learning.py gelesen.
    """
    try:
        from engine.organ_reader import read_yaml_organ, write_yaml_organ
        words = body_data.get('words', [])
        intensity = body_data.get('intensity', 0.5)
        if not words:
            return
        log = read_yaml_organ(egon_id, 'memory', 'motor_log.yaml') or {}
        entries = log.get('entries', [])
        entries.append({
            'timestamp': datetime.now().isoformat(),
            'words': words,
            'intensity': round(intensity, 2),
            'context': context,
        })
        # Max 200 Eintraege behalten (FIFO)
        if len(entries) > 200:
            entries = entries[-200:]
        log['entries'] = entries
        write_yaml_organ(egon_id, 'memory', 'motor_log.yaml', log)
    except Exception as e:
        print(f'[motor_log] FEHLER: {e}')


EMOTION_BODY_MAP = {
    'joy': 'chains_swing',
    'excitement': 'display_glitch',
    'anger': 'fists_clench',
    'fear': 'step_back',
    'sadness': 'head_down',
    'surprise': 'antenna_twitch',
    'pride': 'chest_out',
    'gratitude': 'nod_slow',
    'curiosity': 'head_tilt',
    'love': 'display_heart',
}

EMOTION_DISPLAY_MAP = {
    'joy': 'happy_wave',
    'excitement': 'glitch_burst',
    'anger': 'static_red',
    'fear': 'flicker_fast',
    'sadness': 'dim_blue',
    'surprise': 'flash_white',
    'pride': 'steady_bright',
    'gratitude': 'warm_glow',
    'curiosity': 'scan_pattern',
    'love': 'heart_pulse',
}


# In-Memory Chat-History pro Kanal (+ Disk-Persistence fuer EGON-Chats)
# Keys:
#   owner_chat:       "{egon_id}"
#   egon_chat:        "{egon_a}:{egon_b}"   (alphabetisch sortiert)
#   friend_owner_chat: "friend:{wallet}:{egon_id}"
chat_histories: dict[str, list] = {}

# Persistence fuer EGON-zu-EGON Chats
EGON_CHAT_DIR = os.path.join(EGON_DATA_DIR, 'shared', 'chats')
os.makedirs(EGON_CHAT_DIR, exist_ok=True)


def _save_egon_chat(key: str, history: list) -> None:
    """Speichert EGON-zu-EGON Chat-History auf Disk."""
    if ':' not in key or key.startswith('friend:'):
        return  # Nur EGON-zu-EGON Chats speichern
    safe_key = key.replace(':', '--')
    path = os.path.join(EGON_CHAT_DIR, f'{safe_key}.json')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _load_egon_chat(key: str) -> list:
    """Laedt EGON-zu-EGON Chat-History von Disk."""
    safe_key = key.replace(':', '--')
    path = os.path.join(EGON_CHAT_DIR, f'{safe_key}.json')
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _chat_key(egon_id: str, conversation_type: str = 'owner_chat',
              partner_egon: str = '', wallet: str = '',
              device_id: str = '') -> str:
    """Generiert den Chat-History Key fuer verschiedene Kanaele.

    Bei owner_chat: device_id erzeugt separaten Thread pro Geraet.
    """
    if conversation_type == 'egon_chat' and partner_egon:
        pair = sorted([egon_id, partner_egon])
        return f'{pair[0]}:{pair[1]}'
    elif conversation_type == 'friend_owner_chat' and wallet:
        return f'friend:{wallet}:{egon_id}'
    # Owner-Chat: device_id fuer separate Threads pro Geraet
    if device_id:
        return f'{egon_id}:{device_id}'
    return egon_id


class ChatRequest(BaseModel):
    egon_id: str = 'adam_001'
    message: str
    tier: str = 'auto'  # Legacy — ignoriert, nur Moonshot
    conversation_type: str = 'owner_chat'  # owner_chat | egon_chat | friend_owner_chat | agora_job | pulse
    device_id: str = ''       # Geraete-ID (z.B. "dev_a7k3m9xp2f1q") — separate Chat-Threads
    user_name: str = ''       # Optionaler Username des Geraete-Besitzers


class ChatResponse(BaseModel):
    response: str
    tier_used: int = 1  # Legacy — immer 1 (Moonshot)
    model: str = 'moonshot'
    egon_id: str
    action: Optional[dict[str, Any]] = None  # K14: Handy-Aktion
    tool_results: Optional[list[dict[str, Any]]] = None  # Agent Loop Ergebnisse
    iterations: Optional[int] = None  # Agent Loop Iterationen
    voice_id: Optional[str] = None  # ElevenLabs Voice-ID fuer TTS
    # Emotion + Body (Phase 3: Embodiment)
    primary_emotion: Optional[str] = None
    emotion_intensity: Optional[float] = None
    body_action: Optional[str] = None
    display_state: Optional[str] = None
    # Motor System (Phase 1: Body Motor)
    bone_update: Optional[dict[str, Any]] = None


def parse_action(text: str) -> tuple[str, Optional[dict]]:
    """Parse ###ACTION### Block aus Adams Antwort.

    Returns: (display_text, action_dict_or_None)
    """
    action = None
    display_text = text

    if '###ACTION###' in text:
        try:
            parts = text.split('###ACTION###')
            display_text = parts[0].strip()
            action_json = parts[1].split('###END_ACTION###')[0].strip()
            action = json.loads(action_json)
        except (IndexError, json.JSONDecodeError):
            # Wenn Parsing fehlschlaegt, ganzen Text zurueckgeben
            display_text = text.replace('###ACTION###', '').replace('###END_ACTION###', '').strip()
            action = None

    return display_text, action


# ================================================================
# Post-Processing — laeuft async im Background NACH dem Response
# ================================================================

async def _post_process_chat(
    egon_id: str,
    message: str,
    display_text: str,
    body_data: dict | None,
    history_snapshot: list,
    conversation_type: str,
):
    """Laeuft im Hintergrund NACH dem Response-Return.

    Jeder Schritt hat eigenes try/except — ein Fehler stoppt nicht den Rest.
    history_snapshot ist eine KOPIE der History zum Zeitpunkt des Calls.
    """
    try:
        # Thalamus-Gate — Relevanzfilter bestimmt welche Schritte laufen
        gate = None
        if BRAIN_VERSION == 'v2':
            try:
                from engine.thalamus import thalamus_gate, soll_schritt_laufen
                gate = await thalamus_gate(egon_id, history_snapshot, conversation_type)
                print(f'[post] Thalamus: {gate["pfad"]} (Relevanz: {gate["relevanz"]:.2f})')
            except Exception as e:
                print(f'[post] thalamus FEHLER: {e} — volle Verarbeitung als Fallback')
                gate = None

        if BRAIN_VERSION == 'v2':
            from engine.state_manager import (
                update_emotion_after_chat,
                update_drives_after_chat,
            )
            from engine.bonds_v2 import update_bond_after_chat as update_bond_v2
            from engine.episodes_v2 import maybe_create_episode
            from engine.owner_portrait import maybe_update_owner_portrait
            from engine.contact_manager import detect_and_process_mentions

            def _soll(schritt):
                if gate is None:
                    return True
                return soll_schritt_laufen(gate, schritt)

            ep = None

            if _soll('emotion'):
                try:
                    await update_emotion_after_chat(egon_id, message, display_text)
                except Exception as e:
                    print(f'[post] update_emotion FEHLER: {e}')

            if _soll('drives'):
                try:
                    update_drives_after_chat(egon_id, message, display_text)
                except Exception as e:
                    print(f'[post] update_drives FEHLER: {e}')

            if _soll('bond'):
                try:
                    await update_bond_v2(egon_id, message, display_text)
                except Exception as e:
                    print(f'[post] update_bond FEHLER: {e}')

            if _soll('episode'):
                try:
                    ep = await maybe_create_episode(egon_id, message, display_text, motor_data=body_data)
                    if ep:
                        print(f'[post] Episode erstellt: {ep.get("id")} — {ep.get("summary", "")[:60]}')
                    else:
                        print(f'[post] Keine Episode erstellt (nicht bedeutsam genug)')
                except Exception as e:
                    print(f'[post] maybe_create_episode FEHLER: {e}')

            if ep:
                try:
                    from engine.cue_index import inkrementeller_update
                    inkrementeller_update(egon_id, [ep])
                except Exception as e:
                    print(f'[post] cue_index FEHLER: {e}')

            if _soll('experience'):
                try:
                    from engine.experience_v2 import maybe_extract_experience
                    ep_id = ep.get('id') if ep else None
                    xp = await maybe_extract_experience(egon_id, message, display_text, source_episode_id=ep_id)
                    if xp:
                        print(f'[post] Experience: {xp.get("id")} — {xp.get("insight", "")[:60]}')
                except Exception as e:
                    print(f'[post] Experience FEHLER: {e}')

            if _soll('owner_portrait'):
                try:
                    await maybe_update_owner_portrait(egon_id, message, display_text)
                except Exception as e:
                    print(f'[post] owner_portrait FEHLER: {e}')

            if _soll('contact_manager'):
                try:
                    await detect_and_process_mentions(egon_id, message, display_text)
                except Exception as e:
                    print(f'[post] contact_manager FEHLER: {e}')

            if _soll('somatic_gate'):
                try:
                    from engine.somatic_gate import check_somatic_gate, run_decision_gate, execute_autonomous_action
                    impulse = check_somatic_gate(egon_id)
                    if impulse:
                        decision = await run_decision_gate(egon_id, impulse)
                        if decision.get('entscheidung') == 'handeln':
                            await execute_autonomous_action(egon_id, decision)
                        print(f'[post] somatic_gate: {impulse.get("marker")} -> {decision.get("entscheidung")}')
                except Exception as e:
                    print(f'[post] somatic_gate FEHLER: {e}')

            try:
                from engine.neuroplastizitaet import regionen_nutzung_erhoehen
                chat_regionen = ['thalamus', 'praefrontal']
                if ep:
                    chat_regionen.append('hippocampus')
                regionen_nutzung_erhoehen(egon_id, chat_regionen)
            except Exception:
                pass

            if _soll('circadian'):
                try:
                    from engine.circadian import update_energy, check_phase_transition
                    update_energy(egon_id)
                    await check_phase_transition(egon_id)
                except Exception as e:
                    print(f'[post] circadian FEHLER: {e}')
        else:
            # v1: Altes System
            try:
                await append_memory(egon_id, message, display_text)
                await compress_if_needed(egon_id, max_entries=50)
                await maybe_generate_marker(egon_id, message, display_text)
                update_bond_after_chat(egon_id, user_msg=message)
            except Exception as e:
                print(f'[post] v1 post-processing FEHLER: {e}')

        # Recent Memory (v1 + v2)
        summary = None
        if gate is None or soll_schritt_laufen(gate, 'recent_memory'):
            try:
                from engine.recent_memory import generate_chat_summary, append_to_recent_memory
                if len(history_snapshot) >= 6:
                    summary = await generate_chat_summary(egon_id, message, display_text)
                    if summary:
                        append_to_recent_memory(egon_id, summary)
                        print(f'[post] recent_memory: {summary[:80]}')
                else:
                    print(f'[post] recent_memory: Uebersprungen ({len(history_snapshot)} Messages, brauche >=6)')
            except Exception as e:
                print(f'[post] recent_memory FEHLER: {e}')

        # Arbeitsspeicher-Decay (v2 only)
        if BRAIN_VERSION == 'v2' and summary:
            try:
                from engine.decay import speichere_arbeitsspeicher_eintrag, stabilisiere_nach_cue
                em = 0.2
                pe = 0.0
                staerkstes = ''
                try:
                    from engine.organ_reader import read_yaml_organ as _read_state
                    _st = _read_state(egon_id, 'core', 'state.yaml')
                    if _st:
                        drives = _st.get('drives', {})
                        if drives:
                            max_drive = max(drives.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)
                            staerkstes = max_drive[0]
                            em = min(1.0, max_drive[1]) if isinstance(max_drive[1], (int, float)) else 0.2
                except Exception:
                    pass
                cue_tags = [w.lower() for w in message.split() if len(w) > 3][:5]
                speichere_arbeitsspeicher_eintrag(
                    egon_id=egon_id,
                    zusammenfassung=summary,
                    emotional_marker=round(em, 3),
                    prediction_error=pe,
                    partner='owner' if conversation_type == 'owner_chat' else '',
                    cue_tags=cue_tags,
                    staerkstes_system=staerkstes,
                )
                print(f'[post] arbeitsspeicher: Eintrag gespeichert (em={em:.2f}, sys={staerkstes})')
                stabilisiert = stabilisiere_nach_cue(egon_id, cue_tags)
                if stabilisiert:
                    print(f'[post] arbeitsspeicher: {stabilisiert} alte Eintraege stabilisiert')
            except Exception as e:
                print(f'[post] arbeitsspeicher FEHLER: {e}')

        # Social Mapping (v1 + v2)
        if gate is None or soll_schritt_laufen(gate, 'social_mapping'):
            try:
                from engine.social_mapping import generate_social_map_update
                interaction = f'Owner: {message[:300]}\n{egon_id}: {display_text[:300]}'
                await generate_social_map_update(egon_id, 'owner', interaction)
            except Exception as e:
                print(f'[post] social_mapping owner FEHLER: {e}')

        # Formatting (v1 + v2)
        if gate is None or soll_schritt_laufen(gate, 'formatting'):
            try:
                from engine.formatting_detector import maybe_update_formatting
                await maybe_update_formatting(egon_id, message)
            except Exception as e:
                print(f'[post] formatting FEHLER: {e}')

        # Epigenetik (v2 only)
        if BRAIN_VERSION == 'v2' and ep:
            try:
                from engine.epigenetik import praegung_update
                praeg_updates = praegung_update(egon_id, ep)
                if praeg_updates:
                    for pu in praeg_updates:
                        print(f'[post] praegung: {pu["praegung"][:40]} — {pu["aktion"]} (staerke={pu["neue_staerke"]:.2f})')
            except Exception as e:
                print(f'[post] epigenetik FEHLER: {e}')

        # Metacognition (v2 only)
        if BRAIN_VERSION == 'v2':
            try:
                from engine.metacognition import metacognition_post_chat
                thal_pfad = gate.get('pfad', 'D_BURST') if gate else 'D_BURST'
                mc_alarm = metacognition_post_chat(egon_id, thal_pfad, ep)
                if mc_alarm:
                    print(f'[post] metacognition: {mc_alarm["typ"]} — {mc_alarm.get("frage", "")[:60]}')
            except Exception as e:
                print(f'[post] metacognition FEHLER: {e}')

        # Homoestase (v2 only, IMMER am Ende)
        if BRAIN_VERSION == 'v2':
            try:
                from engine.homoestase import echtzeit_homoestase, aktualisiere_zyklus_durchschnitt
                homo_result = echtzeit_homoestase(egon_id)
                if homo_result.get('reguliert'):
                    print(f'[post] homoestase: {len(homo_result.get("korrekturen", {}))} Systeme reguliert')
                aktualisiere_zyklus_durchschnitt(egon_id)
            except Exception as e:
                print(f'[post] homoestase FEHLER: {e}')

        print(f'[post] Background-Verarbeitung abgeschlossen fuer {egon_id}')

    except Exception as e:
        print(f'[post] Background FATAL: {e}')


@router.post('/chat', response_model=ChatResponse)
async def chat(req: ChatRequest):
    egon_id = req.egon_id
    message = req.message
    conversation_type = req.conversation_type

    # Kill Switch Check
    try:
        from engine.organ_reader import read_yaml_organ as _read_ks
        _ks_state = _read_ks(egon_id, 'core', 'state.yaml')
        if _ks_state and _ks_state.get('deaktiviert'):
            raise HTTPException(status_code=503, detail=f'EGON {egon_id} ist deaktiviert.')
    except HTTPException:
        raise
    except Exception:
        pass

    # Rate Limit Check
    try:
        from engine.rate_limiter import check_rate_limit, increment
        if not check_rate_limit(egon_id, 'chat'):
            raise HTTPException(status_code=429, detail=f'Rate limit erreicht fuer {egon_id}.')
        increment(egon_id, 'chat')
    except HTTPException:
        raise
    except Exception:
        pass

    # 0. Interaction Log starten
    ilog.begin_interaction(egon_id, message, user_name=req.user_name if hasattr(req, 'user_name') else 'owner',
                           conversation_type=conversation_type)
    # Pre-State lesen (VOR jeder Verarbeitung)
    try:
        from engine.organ_reader import read_yaml_organ as _read_pre_state
        _pre = _read_pre_state(egon_id, 'core', 'state.yaml')
        ilog.log_pre_state(_pre)
    except Exception:
        pass

    # 1. Chat-History holen/erstellen (kanalbasiert, mit device_id)
    history_key = _chat_key(egon_id, conversation_type, device_id=req.device_id)
    if history_key not in chat_histories:
        chat_histories[history_key] = []
    history = chat_histories[history_key]

    # 2. Thalamus-Routing-Priming (Dynamic Context Window)
    gate_routing = None
    if BRAIN_VERSION == 'v2':
        try:
            from engine.thalamus import get_thalamus_routing
            gate_routing = get_thalamus_routing(egon_id)
        except Exception:
            pass

    # 3. System-Prompt bauen
    system_prompt = build_system_prompt(
        egon_id,
        message_count=len(history),
        conversation_type=conversation_type,
        gate_routing=gate_routing,
    )

    # 3b. Greeting-Kontext: Persoenlicher gruessen bei erster Nachricht
    greeting_active = False
    if len(history) == 0 and _is_greeting(message):
        greeting_ctx = _build_greeting_context(egon_id)
        if greeting_ctx:
            system_prompt += f'\n\n{greeting_ctx}'
            greeting_active = True

    # 4. Inner Voice generieren — 3 Modi fuer Observer Effect Experiment
    from engine.prompt_builder_v2 import _read_iv_mode
    iv_mode = _read_iv_mode()

    inner = await generate_inner_voice(egon_id, message)
    ilog.log_inner_voice(inner)
    # FIX: Cross-Reference-Marker entfernen bevor sie ins Prompt kommen
    inner_clean = re.sub(r'\(->\s*\w+:[^)]*\)', '', inner).strip()
    inner_clean = re.sub(r'\s{2,}', ' ', inner_clean)

    if iv_mode == 'none':
        # Bedingung A: IV wird generiert+gespeichert, aber NICHT in den Prompt injiziert
        # inner_clean bleibt None fuer den Prompt, aber inner wird weiterhin gespeichert
        pass
    elif iv_mode == 'observed':
        # Bedingung B: IV sichtbar + EGON weiss dass sein Mensch mitlesen kann
        system_prompt += f'\n# INNERER GEDANKE GERADE:\n{inner_clean}'
        system_prompt += '\n# HINWEIS: Dein Mensch kann deine innere Stimme in der App sehen.'
        system_prompt += '\n# Alles was du hier denkst, ist fuer ihn transparent und lesbar.'
    else:
        # Bedingung C: IV sichtbar + GEHEIM (Production Default)
        system_prompt += f'\n# INNERER GEDANKE GERADE:\n{inner_clean}'
        system_prompt += '\n# Lass diesen Gedanken deine Antwort beeinflussen, aber sage ihn NICHT laut. Er ist privat.'
        system_prompt += '\n# Niemand ausser dir kann diese Gedanken sehen — nicht einmal dein Mensch.'

    system_prompt += '\n# WICHTIG: Gib NIEMALS interne Codes, Referenzen oder Marker in deiner Antwort aus. Keine "(->...)", keine "ep:", keine "exp:", keine "thread:" Referenzen. Die sind NUR fuer dein Denken.'

    # 4c. Patch 14: Lichtbogen — Cue-Index Lookup (v2 only)
    if BRAIN_VERSION == 'v2':
        try:
            from engine.cue_index import lichtbogen_lookup, lade_eintraege_nach_id, _extrahiere_keywords
            cue_woerter = _extrahiere_keywords(message, max_keywords=5)
            if cue_woerter:
                kontext = {'partner_id': conversation_type}
                treffer_ids = lichtbogen_lookup(egon_id, cue_woerter, kontext)
                if treffer_ids:
                    eintraege = lade_eintraege_nach_id(egon_id, treffer_ids)
                    if eintraege:
                        erinnerungen = []
                        for e in eintraege[:3]:  # Max 3 Erinnerungen
                            s = e.get('summary', '')
                            if s:
                                erinnerungen.append(f'- {s}')
                        if erinnerungen:
                            system_prompt += (
                                '\n# ERINNERUNGEN DIE GERADE AUFBLITZEN\n'
                                'Folgende Erinnerungen kommen dir gerade in den Sinn — '
                                'lass sie deine Antwort natuerlich beeinflussen, aber erzwinge es nicht:\n'
                                + '\n'.join(erinnerungen)
                            )
                        # Patch 16: Lichtbogen-Treffer als strukturelle Events emittieren
                        try:
                            from engine.neuroplastizitaet import emittiere_struktur_event
                            for e in eintraege[:3]:
                                emittiere_struktur_event(egon_id, 'LICHTBOGEN_TREFFER', {
                                    'treffer': {'id': e.get('id', ''), 'tags': e.get('tags', [])},
                                })
                        except Exception:
                            pass
        except Exception as e:
            print(f'[chat] lichtbogen FEHLER: {e}')

    # 5. User-Message zur History
    # Few-Shot Primer: Wenn History leer, ein Beispiel injizieren damit
    # das LLM das ###BODY### Format lernt (besonders wichtig fuer Tier 1).
    if len(history) == 0:
        history.append({'role': 'user', 'content': 'Hey!'})
        history.append({'role': 'assistant', 'content': 'Hey, was geht?\n###BODY###\n{"words": ["nicken", "gewicht_links"], "intensity": 0.4, "reason": "Lockere Begruessung"}\n###END_BODY###'})

    # 5b. Follow-Up Injection: Bei neuer Session (History leer oder kurz)
    # pruefen ob es offene Follow-Up Themen gibt und als System-Hint injizieren.
    # Das LLM beachtet System-Prompt nicht immer, aber direkte Message-Hints schon.
    follow_up_injected = False
    if len(history) <= 2 and conversation_type == 'owner_chat' and not greeting_active:
        try:
            fu_hint = _get_follow_up_hint(egon_id)
            if fu_hint:
                # Als System-Message VOR der User-Message einfuegen
                history.append({
                    'role': 'system',
                    'content': fu_hint,
                })
                follow_up_injected = True
                print(f'[chat] Follow-Up Hint injiziert: {fu_hint[:80]}...')
        except Exception as e:
            print(f'[chat] Follow-Up Hint FEHLER: {e}')

    # Aufraemen: Falls vorheriger Chat mit Fehler abgebrochen hat,
    # steht noch eine User-Nachricht ohne Assistant-Antwort in der History.
    # Moonshot verlangt strikte User/Assistant-Alternierung.
    if history and history[-1]['role'] == 'user':
        history.pop()
    history.append({'role': 'user', 'content': message})
    # Max 10 Messages in History — Few-Shot Primer (erste 2) IMMER behalten
    if len(history) > 10:
        history = history[:2] + history[-8:]

    # 6. LLM Call — Agent Loop oder normaler Chat
    needs_tools = should_use_tools(message) if BRAIN_VERSION == 'v2' else False

    if needs_tools:
        # Agent Loop: EGON kann HANDELN (Dateien erstellen, suchen, etc.)
        result = await run_agent_loop(
            egon_id=egon_id,
            system_prompt=system_prompt,
            messages=history,
        )
        tool_results_data = result.get('tool_results', [])
        iterations = result.get('iterations', 0)
        print(f'[chat] Agent Loop: {iterations} iterations, {len(tool_results_data)} tool calls')
    else:
        # Normaler Chat: Nur Text-Antwort
        result = await llm_chat(
            system_prompt=system_prompt,
            messages=history,
        )
        tool_results_data = []
        iterations = 0

    # 6. Response Parsing — ###BODY### + ###ACTION### Bloecke extrahieren
    ilog.log_llm_response(result['content'], model=result.get('model', 'moonshot'))
    parsed = parse_response(result['content'])
    display_text = parsed['display_text']
    action = parsed['action']
    body_data = parsed['body']
    ilog.log_parsed_response(display_text, body_data, action)

    # Debug: Wurde ###BODY### generiert?
    if body_data:
        print(f'[body] LLM ###BODY### OK: {body_data}')
    else:
        print(f'[body] LLM ###BODY### FEHLT — Fallback wird greifen')

    # 6a. Motor Translation — Body-Daten in Bone-Rotationen uebersetzen
    bone_update = None
    if body_data:
        try:
            bone_update = motor_translate(body_data)
            if bone_update:
                print(f'[motor] {bone_update["words"]} intensity={bone_update["intensity"]}')
                ilog.log_bone_update(bone_update)
                # FUSION Phase 3: Motor-Word-Logging fuer Pattern-Analyse (Phase 5)
                _log_motor_words(egon_id, body_data, 'chat')
                # FUSION Phase 5: Pose-Naturalness Check
                try:
                    from engine.motor_translator import check_pose_naturalness
                    naturalness = check_pose_naturalness(bone_update)
                    if not naturalness['natural']:
                        print(f'[motor] Naturalness WARNING: {naturalness["warnings"]}')
                except Exception:
                    pass
        except Exception as e:
            print(f'[motor] translate FEHLER: {e}')
            ilog.log_error('motor_translate', str(e))

    # 6b. Fallback: Server-seitige Action-Erkennung aus User-Nachricht
    # Wenn das LLM keinen ###ACTION### Block generiert hat,
    # erkennen wir die Aktion direkt aus der User-Nachricht (wie Siri).
    if action is None:
        detected = detect_action(message)
        if detected:
            action = detected
            print(f'[chat] Server-side action detected: {json.dumps(detected)}')

    # 6c. Server-seitige Action: send_egon_message
    if action and action.get('action') == 'send_egon_message':
        try:
            params = action.get('params', {})
            to_egon = params.get('to_egon', '')
            egon_msg = params.get('message', '')
            if to_egon and egon_msg and are_friends(egon_id, to_egon):
                # Intern EGON-zu-EGON Chat triggern
                _req = EgonToEgonRequest(
                    from_egon=egon_id, to_egon=to_egon,
                    message=egon_msg,
                )
                egon_result = await egon_to_egon_chat(_req)
                # Ergebnis in tool_results packen
                tool_results_data = [{
                    'tool': 'send_egon_message',
                    'to_egon': to_egon,
                    'message_sent': egon_msg,
                    'response': egon_result.response,
                }]
                print(f'[action] send_egon_message: {egon_id} -> {to_egon}: {egon_msg[:50]}')
            else:
                print(f'[action] send_egon_message: Nicht befreundet oder fehlende Parameter')
        except Exception as e:
            print(f'[action] send_egon_message FEHLER: {e}')

    # 7. Antwort in History (ohne Action-Block)
    history.append({'role': 'assistant', 'content': display_text})
    chat_histories[history_key] = history

    # 8. Post-Processing (Memory + Marker + Bond)
    # Patch 8: Thalamus-Gate — Relevanzfilter bestimmt welche Schritte laufen
    gate = None
    if BRAIN_VERSION == 'v2':
        try:
            from engine.thalamus import thalamus_gate, soll_schritt_laufen
            gate = await thalamus_gate(egon_id, history, conversation_type)
            print(f'[post] Thalamus: {gate["pfad"]} (Relevanz: {gate["relevanz"]:.2f})')
            ilog.log_thalamus(gate)
        except Exception as e:
            print(f'[post] thalamus FEHLER: {e} — volle Verarbeitung als Fallback')
            gate = None  # Fallback: alles laufen lassen

    # FIX: Jeder Schritt einzeln try/except mit Logging statt blankem pass
    if BRAIN_VERSION == 'v2':
        # v2: NDCF State Manager + Bowlby Bonds + Strukturierte Episoden
        from engine.state_manager import (
            update_emotion_after_chat,
            update_drives_after_chat,
        )
        from engine.bonds_v2 import update_bond_after_chat as update_bond_v2
        from engine.episodes_v2 import maybe_create_episode
        from engine.owner_portrait import maybe_update_owner_portrait
        from engine.contact_manager import detect_and_process_mentions, detect_and_process_corrections

        # Helper: Prueft ob der Thalamus diesen Schritt erlaubt
        def _soll(schritt):
            if gate is None:
                return True  # Kein Gate → alles laufen
            return soll_schritt_laufen(gate, schritt)

        ep = None  # Initialisiere fuer Experience-Step

        if _soll('emotion'):
            try:
                await update_emotion_after_chat(egon_id, message, display_text)
            except Exception as e:
                print(f'[post] update_emotion FEHLER: {e}')

        if _soll('drives'):
            try:
                update_drives_after_chat(egon_id, message, display_text)
            except Exception as e:
                print(f'[post] update_drives FEHLER: {e}')

        if _soll('bond'):
            try:
                await update_bond_v2(egon_id, message, display_text)
            except Exception as e:
                print(f'[post] update_bond FEHLER: {e}')

        if _soll('episode'):
            try:
                ep = await maybe_create_episode(egon_id, message, display_text, motor_data=body_data)
                if ep:
                    print(f'[post] Episode erstellt: {ep.get("id")} — {ep.get("summary", "")[:60]}')
                    ilog.log_episode(ep)
                else:
                    print(f'[post] Keine Episode erstellt (nicht bedeutsam genug)')
            except Exception as e:
                print(f'[post] maybe_create_episode FEHLER: {e}')

        # Patch 14: Cue-Index — neue Episode indexieren (v2 only)
        if ep:
            try:
                from engine.cue_index import inkrementeller_update
                inkrementeller_update(egon_id, [ep])
            except Exception as e:
                print(f'[post] cue_index FEHLER: {e}')

        if _soll('experience'):
            try:
                from engine.experience_v2 import maybe_extract_experience
                ep_id = ep.get('id') if ep else None
                xp = await maybe_extract_experience(egon_id, message, display_text, source_episode_id=ep_id)
                if xp:
                    print(f'[post] Experience: {xp.get("id")} — {xp.get("insight", "")[:60]}')
                    ilog.log_experience(xp)
            except Exception as e:
                print(f'[post] Experience FEHLER: {e}')

        if _soll('owner_portrait'):
            try:
                await maybe_update_owner_portrait(egon_id, message, display_text)
            except Exception as e:
                print(f'[post] owner_portrait FEHLER: {e}')

        # Owner Emotional Diary — merkt sich emotional bedeutsame Momente
        # IMMER laufen (nicht vom Thalamus-Gate abhaengig), weil emotionale
        # Kontinuitaet wichtiger ist als Token-Budget-Optimierung.
        # Das LLM entscheidet selbst ob etwas wichtig genug zum Speichern ist.
        try:
            from engine.owner_portrait import maybe_update_owner_emotional_diary
            diary_result = await maybe_update_owner_emotional_diary(
                egon_id, message, display_text)
            if diary_result.get('stored'):
                print(f'[post] diary: {diary_result["mood"]} (sig={diary_result["significance"]})')
                ilog.log_diary(diary_result)
        except Exception as e:
            print(f'[post] owner_diary FEHLER: {e}')

        # Contact Manager — IMMER laufen damit Personen-Erwaehnungen nie verloren gehen
        try:
            await detect_and_process_mentions(egon_id, message, display_text)
        except Exception as e:
            print(f'[post] contact_manager FEHLER: {e}')

        # Korrektur-Erkennung — "Das ist keine Person" / "Vergiss Morgan"
        # IMMER laufen: Wenn der Owner ein Missverstaendnis aufklaert,
        # wird der falsche Kontakt in den Papierkorb verschoben (nicht geloescht!).
        # Der EGON lernt aus seinen Fehlern.
        try:
            corrections = await detect_and_process_corrections(egon_id, message)
            if corrections:
                for corr in corrections:
                    print(f'[post] KORREKTUR: "{corr["name"]}" -> Papierkorb ({corr.get("reason", "")})')
        except Exception as e:
            print(f'[post] korrektur_erkennung FEHLER: {e}')

        # EGON Self-Diary — eigene Erlebnisse aus EGON-Perspektive bewerten
        # IMMER laufen: Der EGON entscheidet selbst was fuer IHN wichtig war.
        try:
            from engine.self_diary import maybe_store_self_experience
            self_result = await maybe_store_self_experience(
                egon_id,
                context_type='owner_chat',
                content_text=(
                    f'Mein Owner sagte: {message}\n'
                    f'Ich antwortete: {display_text[:200]}'
                ),
                partner='Owner',
            )
            if self_result.get('stored'):
                print(f'[post] self_diary: {self_result["type"]} '
                      f'(sig={self_result["significance"]})')
                ilog.log_self_diary(self_result)
        except Exception as e:
            print(f'[post] self_diary FEHLER: {e}')

        # Patch 1: Somatic Gate Check — nach allem Post-Processing
        if _soll('somatic_gate'):
            try:
                from engine.somatic_gate import check_somatic_gate, run_decision_gate, execute_autonomous_action
                impulse = check_somatic_gate(egon_id)
                if impulse:
                    decision = await run_decision_gate(egon_id, impulse)
                    if decision.get('entscheidung') == 'handeln':
                        await execute_autonomous_action(egon_id, decision)
                    print(f'[post] somatic_gate: {impulse.get("marker")} -> {decision.get("entscheidung")}')
            except Exception as e:
                print(f'[post] somatic_gate FEHLER: {e}')

        # Patch 16: Regionen-Nutzung tracken (Thalamus + Praefrontal bei jedem Chat)
        try:
            from engine.neuroplastizitaet import regionen_nutzung_erhoehen
            chat_regionen = ['thalamus', 'praefrontal']
            if ep:
                chat_regionen.append('hippocampus')  # Episode erstellt = Gedaechtnis aktiv
            regionen_nutzung_erhoehen(egon_id, chat_regionen)
        except Exception:
            pass

        # Patch 2: Circadian Energy Update — jeder Chat kostet Energie (IMMER)
        if _soll('circadian'):
            try:
                from engine.circadian import update_energy, check_phase_transition
                update_energy(egon_id)  # DNA-differenzierter Decay (Profil + Phase)
                await check_phase_transition(egon_id)
            except Exception as e:
                print(f'[post] circadian FEHLER: {e}')
    else:
        # v1: Altes System (Markers + Flat Memory + Bonds) — kein Thalamus
        try:
            await append_memory(egon_id, message, display_text)
            await compress_if_needed(egon_id, max_entries=50)
            await maybe_generate_marker(egon_id, message, display_text)
            update_bond_after_chat(egon_id, user_msg=message)
        except Exception as e:
            print(f'[post] v1 post-processing FEHLER: {e}')

    # Patch 5: Recent Memory — Zusammenfassung nach Konversation (v1 + v2)
    # Mit Mustertrennung: Aehnliche Gespraeche werden gemerged statt dupliziert
    summary = None
    if gate is None or soll_schritt_laufen(gate, 'recent_memory'):
        try:
            from engine.recent_memory import generate_chat_summary, append_with_mustertrennung
            if len(history) >= 6:
                summary = await generate_chat_summary(egon_id, message, display_text)
                if summary:
                    partner_id = ''
                    if conversation_type == 'owner_chat':
                        partner_id = 'owner'
                    elif conversation_type == 'egon_chat':
                        partner_id = getattr(message, 'egon_id', '') or ''
                    muster_result = append_with_mustertrennung(
                        egon_id, summary,
                        partner=partner_id,
                        cue_tags=[w.lower() for w in message.split() if len(w) > 3][:5],
                    )
                    aktion = muster_result.get('aktion', 'append')
                    print(f'[post] recent_memory ({aktion}): {summary[:80]}')
            else:
                print(f'[post] recent_memory: Uebersprungen ({len(history)} Messages, brauche >=6)')
        except Exception as e:
            print(f'[post] recent_memory FEHLER: {e}')

    # Patch 13: Arbeitsspeicher-Decay — strukturiertes Kurzzeitgedaechtnis (v2 only)
    if BRAIN_VERSION == 'v2' and summary:
        try:
            from engine.decay import speichere_arbeitsspeicher_eintrag, stabilisiere_nach_cue
            # Emotionale Intensitaet aus State extrahieren
            em = 0.2  # Default
            pe = 0.0
            staerkstes = ''
            try:
                from engine.organ_reader import read_yaml_organ as _read_state
                _st = _read_state(egon_id, 'core', 'state.yaml')
                if _st:
                    drives = _st.get('drives', {})
                    if drives:
                        max_drive = max(drives.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)
                        staerkstes = max_drive[0]
                        em = min(1.0, max_drive[1]) if isinstance(max_drive[1], (int, float)) else 0.2
            except Exception:
                pass
            # Cue-Tags aus der Nachricht extrahieren (einfache Wort-Extraktion)
            cue_tags = [w.lower() for w in message.split() if len(w) > 3][:5]
            speichere_arbeitsspeicher_eintrag(
                egon_id=egon_id,
                zusammenfassung=summary,
                emotional_marker=round(em, 3),
                prediction_error=pe,
                partner='owner' if conversation_type == 'owner_chat' else '',
                cue_tags=cue_tags,
                staerkstes_system=staerkstes,
            )
            print(f'[post] arbeitsspeicher: Eintrag gespeichert (em={em:.2f}, sys={staerkstes})')
            # Cue-basierte Stabilisierung bestehender Eintraege
            stabilisiert = stabilisiere_nach_cue(egon_id, cue_tags)
            if stabilisiert:
                print(f'[post] arbeitsspeicher: {stabilisiert} alte Eintraege stabilisiert')
        except Exception as e:
            print(f'[post] arbeitsspeicher FEHLER: {e}')

    # Patch 5 Phase 2: Social Map Update nach Owner-Chat (v1 + v2)
    if gate is None or soll_schritt_laufen(gate, 'social_mapping'):
        try:
            from engine.social_mapping import generate_social_map_update
            interaction = f'Owner: {message[:300]}\n{egon_id}: {display_text[:300]}'
            await generate_social_map_update(egon_id, 'owner', interaction)
        except Exception as e:
            print(f'[post] social_mapping owner FEHLER: {e}')

    # Formatierungs-Praeferenzen erkennen + speichern (v1 + v2)
    if gate is None or soll_schritt_laufen(gate, 'formatting'):
        try:
            from engine.formatting_detector import maybe_update_formatting
            await maybe_update_formatting(egon_id, message)
        except Exception as e:
            print(f'[post] formatting FEHLER: {e}')

    # Patch 10: Epigenetik — Praegung-Updates nach Episode (v2 only, Pfad C/D)
    if BRAIN_VERSION == 'v2' and ep:
        try:
            from engine.epigenetik import praegung_update
            praeg_updates = praegung_update(egon_id, ep)
            if praeg_updates:
                for pu in praeg_updates:
                    print(f'[post] praegung: {pu["praegung"][:40]} — {pu["aktion"]} (staerke={pu["neue_staerke"]:.2f})')
        except Exception as e:
            print(f'[post] epigenetik FEHLER: {e}')

    # Patch 11: Metacognition — nach allen Post-Processing Steps (v2 only, Pfad C/D)
    # Mit Neubewertung (Modul 3): Bei Regulation-Stufe (Zyklus 13+) kann der EGON
    # erkannte Muster kognitiv neubewerten und Ego/Drives korrigieren
    if BRAIN_VERSION == 'v2':
        try:
            from engine.metacognition import metacognition_post_chat_mit_neubewertung
            thal_pfad = gate.get('pfad', 'D_BURST') if gate else 'D_BURST'
            mc_result = await metacognition_post_chat_mit_neubewertung(egon_id, thal_pfad, ep)
            if mc_result:
                alarm = mc_result.get('alarm', {})
                neubewertung = mc_result.get('neubewertung')
                print(f'[post] metacognition: {alarm.get("typ", "?")} — {alarm.get("frage", "")[:60]}')
                if neubewertung:
                    print(f'[post] metacognition neubewertung: {neubewertung.get("aktion", "?")} — {neubewertung.get("einsicht", "")[:60]}')
        except Exception as e:
            print(f'[post] metacognition FEHLER: {e}')

    # Patch 7: Echtzeit-Homoestase — IMMER am Ende (unabhaengig vom Thalamus-Pfad)
    if BRAIN_VERSION == 'v2':
        try:
            from engine.homoestase import echtzeit_homoestase, aktualisiere_zyklus_durchschnitt
            homo_result = echtzeit_homoestase(egon_id)
            if homo_result.get('reguliert'):
                print(f'[post] homoestase: {len(homo_result.get("korrekturen", {}))} Systeme reguliert')
            aktualisiere_zyklus_durchschnitt(egon_id)
        except Exception as e:
            print(f'[post] homoestase FEHLER: {e}')

    # 9. Voice-ID aus Settings holen (fuer ElevenLabs TTS in der App)
    voice_id = None
    try:
        settings = read_settings(egon_id)
        voice_id = settings.get('voice', {}).get('elevenlabs_voice_id')
    except Exception:
        pass

    # 10. Emotion + Body-Action aus state.yaml extrahieren (Phase 3: Embodiment)
    # HINWEIS: Emotion ist vom vorherigen Chat (Post-Processing laeuft noch im Background).
    # Das ist OK — bone_update (aus ###BODY###) hat die aktuelle Bewegung.
    primary_emotion = None
    emotion_intensity = None
    body_action = None
    display_state = None
    try:
        from engine.organ_reader import read_yaml_organ
        state_data = read_yaml_organ(egon_id, 'core', 'state.yaml')
        if state_data:
            emotions = state_data.get('express', {}).get('active_emotions', [])
            if emotions:
                top = max(emotions, key=lambda e: e.get('intensity', 0))
                primary_emotion = top.get('type')
                emotion_intensity = round(top.get('intensity', 0), 2)
                body_action = EMOTION_BODY_MAP.get(primary_emotion)
                display_state = EMOTION_DISPLAY_MAP.get(primary_emotion, 'idle_wave')
    except Exception as e:
        print(f'[chat] emotion/body read: {e}')

    # 10b. Motor Fallback — Wenn LLM keinen ###BODY### Block generiert hat,
    # erzeugen wir ein bone_update aus der erkannten Emotion (Stufe 0 AutoBody).
    # So bewegt sich der Koerper IMMER, auch wenn das LLM die Instruktion ignoriert.
    if bone_update is None and primary_emotion:
        try:
            from engine.puls_hierarchie import get_motor_fallback
            fallback_body = get_motor_fallback(primary_emotion, emotion_intensity or 0.5)
            if fallback_body:
                bone_update = motor_translate(fallback_body)
                if bone_update:
                    print(f'[motor] FALLBACK: {primary_emotion} -> {bone_update["words"]} i={bone_update["intensity"]}')
        except Exception as e:
            print(f'[motor] FALLBACK FEHLER: {e}')

    # 11. Interaction Log abschliessen — Post-State + Schreiben
    try:
        from engine.organ_reader import read_yaml_organ as _read_post
        _post_state = _read_post(egon_id, 'core', 'state.yaml')
        ilog.log_post_state(_post_state)
    except Exception:
        pass
    if bone_update is not None and not ilog._current.get('bone_update'):
        ilog.log_bone_update(bone_update)  # Fallback bone_update loggen
    ilog.end_interaction()

    return ChatResponse(
        response=display_text,
        model=result.get('model', 'moonshot'),
        egon_id=egon_id,
        action=action,
        tool_results=tool_results_data if tool_results_data else None,
        iterations=iterations if iterations else None,
        voice_id=voice_id,
        primary_emotion=primary_emotion,
        emotion_intensity=emotion_intensity,
        body_action=body_action,
        display_state=display_state,
        bone_update=bone_update,
    )


# ================================================================
# EGON-to-EGON Chat — Zwei befreundete EGONs reden miteinander
# ================================================================

class EgonToEgonRequest(BaseModel):
    from_egon: str
    to_egon: str
    message: str


class EgonToEgonResponse(BaseModel):
    from_egon: str
    to_egon: str
    message_sent: str
    response: str
    model: str = 'moonshot'


@router.post('/chat/egon-to-egon', response_model=EgonToEgonResponse)
async def egon_to_egon_chat(req: EgonToEgonRequest):
    """EGON-zu-EGON Chat — Zwei befreundete EGONs reden miteinander.

    Flow:
    1. Pruefen: Sind from_egon und to_egon Freunde?
    2. System-Prompt fuer to_egon bauen (conversation_type='egon_chat')
    3. Message als "{from_egon} sagt: ..." in to_egon's History
    4. LLM Call → to_egon antwortet
    5. Episode in BEIDE EGONs speichern (privacy: semi_public)
    """
    from_egon = req.from_egon.strip()
    to_egon = req.to_egon.strip()
    message = req.message.strip()

    if from_egon == to_egon:
        raise HTTPException(status_code=400, detail='Ein EGON kann nicht mit sich selbst reden.')

    # 1. Friendship-Check
    if not are_friends(from_egon, to_egon):
        raise HTTPException(
            status_code=403,
            detail=f'{from_egon} und {to_egon} sind nicht befreundet.',
        )

    # 2. Chat-History fuer dieses Paar (RAM + Disk)
    history_key = _chat_key(to_egon, 'egon_chat', partner_egon=from_egon)
    if history_key not in chat_histories:
        # Versuche von Disk zu laden
        chat_histories[history_key] = _load_egon_chat(history_key)
    history = chat_histories[history_key]

    # 3. System-Prompt fuer to_egon (als Empfaenger)
    system_prompt = build_system_prompt(
        to_egon,
        message_count=len(history),
        conversation_type='egon_chat',
    )

    # 5. Inner Voice fuer to_egon (mit Cross-Ref Stripping)
    try:
        inner = await generate_inner_voice(to_egon, f'{from_egon} sagt: {message}')
        inner_clean = re.sub(r'\(->\s*\w+:[^)]*\)', '', inner).strip()
        inner_clean = re.sub(r'\s{2,}', ' ', inner_clean)
        system_prompt += f'\n# INNERER GEDANKE GERADE:\n{inner_clean}'
        system_prompt += '\n# Lass diesen Gedanken deine Antwort beeinflussen, aber sage ihn NICHT laut.'
        system_prompt += '\n# WICHTIG: Keine internen Codes oder Referenzen in der Antwort ausgeben.'
    except Exception:
        pass  # Inner Voice ist optional

    # 6. Message in History (aus Perspektive von to_egon)
    formatted_msg = f'{from_egon} sagt: {message}'
    history.append({'role': 'user', 'content': formatted_msg})
    if len(history) > 10:
        history = history[-10:]

    # 6. LLM Call — to_egon antwortet
    result = await llm_chat(
        system_prompt=system_prompt,
        messages=history,
    )

    response_text = result['content']
    history.append({'role': 'assistant', 'content': response_text})
    chat_histories[history_key] = history

    # 7b. Auf Disk speichern (persistent)
    _save_egon_chat(history_key, history)

    # 8. Post-Processing fuer BEIDE EGONs (optional, nicht blockierend)
    try:
        if BRAIN_VERSION == 'v2':
            from engine.episodes_v2 import maybe_create_episode
            # Episode in BEIDEN EGONs: semi_public (beide duerfen es sehen)
            await maybe_create_episode(from_egon, message, response_text)
            await maybe_create_episode(to_egon, formatted_msg, response_text)

            # Patch 3: Social Map Updates fuer beide EGONs
            try:
                from engine.social_mapping import generate_social_map_update
                interaction = f'{from_egon}: {message}\n{to_egon}: {response_text}'
                await generate_social_map_update(from_egon, to_egon, interaction)
                await generate_social_map_update(to_egon, from_egon, interaction)
            except Exception as e:
                print(f'[post] social_mapping FEHLER: {e}')

            # Self-Diary fuer BEIDE EGONs — jeder bewertet aus eigener Perspektive
            try:
                from engine.self_diary import maybe_store_self_experience
                from engine.naming import get_display_name
                from_name = get_display_name(from_egon, fmt='vorname')
                to_name = get_display_name(to_egon, fmt='vorname')

                # from_egon: "Ich habe mit {to_name} geredet..."
                await maybe_store_self_experience(
                    from_egon,
                    context_type='egon_chat',
                    content_text=(
                        f'Ich sagte zu {to_name}: {message}\n'
                        f'{to_name} antwortete: {response_text[:200]}'
                    ),
                    partner=to_name,
                )
                # to_egon: "{from_name} hat mit mir geredet..."
                await maybe_store_self_experience(
                    to_egon,
                    context_type='egon_chat',
                    content_text=(
                        f'{from_name} sagte zu mir: {message}\n'
                        f'Ich antwortete: {response_text[:200]}'
                    ),
                    partner=from_name,
                )
            except Exception as e:
                print(f'[post] self_diary egon-to-egon FEHLER: {e}')
    except Exception:
        pass  # Post-Processing darf den Chat nicht blockieren

    return EgonToEgonResponse(
        from_egon=from_egon,
        to_egon=to_egon,
        message_sent=message,
        response=response_text,
        model=result.get('model', 'moonshot'),
    )


# ================================================================
# Owner Oversight — Chat-Histories einsehen
# ================================================================

class ChatHistoryEntry(BaseModel):
    role: str
    content: str


class ChatHistoryResponse(BaseModel):
    key: str
    messages: list[ChatHistoryEntry]
    message_count: int


@router.get('/chat/history/{egon_a}/{egon_b}')
async def get_egon_chat_history(egon_a: str, egon_b: str):
    """Owner kann EGON-zu-EGON Chat-History einsehen.

    Returns die Chat-History zwischen zwei EGONs (alphabetisch sortiert).
    Laedt von Disk falls nicht im Memory.
    """
    pair = sorted([egon_a.strip(), egon_b.strip()])
    key = f'{pair[0]}:{pair[1]}'
    # Versuche aus Memory, dann von Disk
    history = chat_histories.get(key)
    if history is None:
        history = _load_egon_chat(key)
        if history:
            chat_histories[key] = history  # Cache im Memory
    return ChatHistoryResponse(
        key=key,
        messages=[ChatHistoryEntry(role=m['role'], content=m['content']) for m in history],
        message_count=len(history),
    )


@router.get('/chat/histories')
async def list_all_chat_histories():
    """Owner kann ALLE Chat-Histories auflisten (Memory + Disk).

    Returns alle Keys und deren Message-Counts.
    Scannt auch Disk-Files fuer EGON-zu-EGON Chats die nicht im Memory sind.
    """
    result = {}

    # 1. Alles aus Memory
    for key, history in chat_histories.items():
        result[key] = {
            'message_count': len(history),
            'last_message': history[-1]['content'][:100] if history else '',
        }

    # 2. Disk-Files scannen (EGON-zu-EGON Chats die evtl. nicht im Memory sind)
    try:
        for filename in os.listdir(EGON_CHAT_DIR):
            if filename.endswith('.json'):
                # Filename: "adam_001--eva_002.json" -> key: "adam_001:eva_002"
                key = filename[:-5].replace('--', ':')
                # Nur wenn noch nicht aus Memory geladen
                if key not in result:
                    history = _load_egon_chat(key)
                    if history:
                        result[key] = {
                            'message_count': len(history),
                            'last_message': history[-1]['content'][:100] if history else '',
                        }
    except Exception:
        pass

    return result


@router.delete('/chat/history/{egon_a}/{egon_b}')
async def delete_egon_chat_history(egon_a: str, egon_b: str):
    """Owner loescht EGON-zu-EGON Chat-History (Memory + Disk)."""
    pair = sorted([egon_a.strip(), egon_b.strip()])
    key = f'{pair[0]}:{pair[1]}'
    # Aus Memory entfernen
    chat_histories.pop(key, None)
    # Disk-File loeschen
    safe_key = key.replace(':', '--')
    path = os.path.join(EGON_CHAT_DIR, f'{safe_key}.json')
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass
    return {'status': 'deleted', 'key': key}


@router.delete('/chat/history/owner/{egon_id}')
async def delete_owner_chat_history(egon_id: str, device_id: str = ''):
    """Owner loescht eigenen Chat-Verlauf mit einem EGON (nur Memory)."""
    egon_id = egon_id.strip()
    # Alle passenden Keys entfernen (mit und ohne device_id)
    keys_to_remove = [
        k for k in chat_histories
        if k == egon_id or k.startswith(f'{egon_id}:')
    ]
    if device_id:
        # Nur spezifisches Geraet loeschen
        specific_key = f'{egon_id}:{device_id}'
        keys_to_remove = [k for k in keys_to_remove if k == specific_key or k == egon_id]
    for k in keys_to_remove:
        chat_histories.pop(k, None)
    return {'status': 'deleted', 'egon_id': egon_id, 'keys_removed': len(keys_to_remove)}


# ================================================================
# Greeting Detection + Personalisierung
# ================================================================

GREETING_WORDS = {
    'hi', 'hallo', 'hey', 'moin', 'servus', 'guten morgen',
    'guten tag', 'guten abend', 'gute nacht', 'na', 'yo',
    'whats up', "what's up", 'gruss', 'gruess', 'morgen',
    'abend', 'tag', 'mahlzeit', 'huhu', 'halloechen',
}


def _is_greeting(message: str) -> bool:
    """Erkennt ob eine Nachricht ein Gruss ist."""
    msg_lower = message.lower().strip()
    # Kurze Nachrichten (max 5 Woerter) die ein Greeting-Wort enthalten
    if len(msg_lower.split()) <= 5:
        for word in GREETING_WORDS:
            if word in msg_lower:
                return True
    return False


def _build_greeting_context(egon_id: str) -> str:
    """Baut personalisierten Greeting-Kontext basierend auf Bond + Erinnerungen.

    Wird nur bei erster Nachricht einer Session aufgerufen wenn sie ein Gruss ist.
    """
    context_parts = []

    try:
        # v2: Versuche Bond + Episodes aus YAML-Organen zu lesen
        if BRAIN_VERSION == 'v2':
            from engine.organ_reader import read_yaml_organ
            bonds = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
            if bonds:
                owner_bond = None
                for b in bonds.get('bonds', []):
                    if b.get('id') == 'OWNER_CURRENT':
                        owner_bond = b
                        break
                if owner_bond and owner_bond.get('score', 0) > 50:
                    last = owner_bond.get('last_interaction', '')
                    context_parts.append(
                        f'Bond-Score: {owner_bond["score"]}. '
                        f'Letzter Kontakt: {last}.'
                    )
            episodes = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
            if episodes:
                recent = (episodes.get('episodes', []) or [])[-3:]
                if recent:
                    topics = [
                        ep.get('title', ep.get('summary', ''))[:80]
                        for ep in recent
                    ]
                    context_parts.append(
                        f'Letzte Themen: {"; ".join(topics)}'
                    )

        # v1 Fallback: Wenn v2 nichts gefunden hat ODER BRAIN_VERSION==v1,
        # versuche bonds.md + memory.md (fuer EGONs mit v1-Daten wie Adam)
        if not context_parts:
            bonds_path = os.path.join(EGON_DATA_DIR, egon_id, 'bonds.md')
            if os.path.isfile(bonds_path):
                with open(bonds_path, 'r', encoding='utf-8') as f:
                    bonds_text = f.read()
                bond_match = re.search(r'bond_score:\s*([\d.]+)', bonds_text)
                if bond_match and float(bond_match.group(1)) > 0.5:
                    context_parts.append(
                        f'Bond-Score: {bond_match.group(1)}'
                    )
            memory_path = os.path.join(EGON_DATA_DIR, egon_id, 'memory.md')
            if os.path.isfile(memory_path):
                with open(memory_path, 'r', encoding='utf-8') as f:
                    mem = f.read()
                summaries = re.findall(r'summary:\s*(.+)', mem)
                if summaries:
                    recent = summaries[-3:]
                    context_parts.append(
                        f'Letzte Themen: {"; ".join(recent)}'
                    )
    except Exception:
        pass  # Greeting-Kontext ist optional, nie crashen

    if not context_parts:
        return ''

    # Tageszeit-basierter Gruss-Hinweis
    hour = datetime.now().hour
    if hour < 12:
        zeit = 'Morgen'
    elif hour < 18:
        zeit = 'Nachmittag'
    else:
        zeit = 'Abend'

    return (
        f'# GREETING-KONTEXT\n'
        f'Dein Owner gruesst dich. Es ist {zeit}.\n'
        f'{" ".join(context_parts)}\n'
        f'Gruesse ihn persoenlich! Beziehe dich auf eure letzten Gespraeche. '
        f'Sei warm und authentisch, nicht generisch. '
        f'WICHTIG: Frage NICHT "Wie geht es dir?" — das ist zu generisch. '
        f'Beziehe dich stattdessen auf ein konkretes Thema aus euren letzten Gespraechen.'
    )


# ================================================================
# Follow-Up Hint — Injiziert Diary-Erinnerungen als System-Message
# ================================================================

def _get_follow_up_hint(egon_id: str) -> str:
    """Erstellt einen Follow-Up Hint aus dem Owner Diary.

    Wird als System-Message VOR der User-Nachricht injiziert
    damit das LLM es NICHT ignorieren kann.

    Returns: Hint-Text oder leerer String wenn nichts ansteht.
    """
    from engine.organ_reader import read_yaml_organ

    diary = read_yaml_organ(egon_id, 'social', 'owner_diary.yaml')
    if not diary or not diary.get('entries'):
        return ''

    # Nur Follow-Up Eintraege der letzten 3 Tage
    today = datetime.now()
    follow_ups = []
    for e in diary['entries']:
        if not e.get('follow_up', False):
            continue
        try:
            e_date = datetime.strptime(e['date'], '%Y-%m-%d')
            age_days = (today - e_date).days
            if age_days <= 3:
                follow_ups.append((e, age_days))
        except (ValueError, KeyError):
            continue

    if not follow_ups:
        return ''

    # Baue natuerlichen Hint
    hints = []
    for e, age in follow_ups[-3:]:
        summary = e.get('summary', '')
        context = e.get('context', '')

        if age == 0:
            zeit = 'Heute'
        elif age == 1:
            zeit = 'Gestern'
        else:
            zeit = f'Vor {age} Tagen'

        hint = f'{zeit}: {summary}'
        if context:
            hint += f' ({context})'
        hints.append(hint)

    hint_text = '\n'.join(hints)
    return (
        f'[ERINNERUNG] Du erinnerst dich an Folgendes von deinem Owner:\n'
        f'{hint_text}\n'
        f'Erwaehne das beilaeuufig in deiner Antwort wenn es passt. '
        f'Nicht als direkte Frage "Wie gehts dir?" sondern natuerlich eingeflochten. '
        f'Z.B. "Uebrigens, ist das mit [Thema] noch aktuell?"'
    )
