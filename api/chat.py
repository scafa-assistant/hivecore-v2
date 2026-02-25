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
from llm.planner import should_use_tools, decide_tier
from engine.agent_loop import run_agent_loop
from engine.action_detector import detect_action
from engine.response_parser import parse_response
from engine.motor_translator import translate as motor_translate

router = APIRouter()


# ================================================================
# Emotion → Body-Action / Display-State Maps (Phase 3: Embodiment)
# ================================================================
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
    tier: str = 'auto'
    conversation_type: str = 'owner_chat'  # owner_chat | egon_chat | friend_owner_chat | agora_job | pulse
    device_id: str = ''       # Geraete-ID (z.B. "dev_a7k3m9xp2f1q") — separate Chat-Threads
    user_name: str = ''       # Optionaler Username des Geraete-Besitzers


class ChatResponse(BaseModel):
    response: str
    tier_used: int
    model: str
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


@router.post('/chat', response_model=ChatResponse)
async def chat(req: ChatRequest):
    egon_id = req.egon_id
    message = req.message
    tier = req.tier
    conversation_type = req.conversation_type

    # 1. Chat-History holen/erstellen (kanalbasiert, mit device_id)
    history_key = _chat_key(egon_id, conversation_type, device_id=req.device_id)
    if history_key not in chat_histories:
        chat_histories[history_key] = []
    history = chat_histories[history_key]

    # 2. Tier aufloesen (VOR System-Prompt — damit Budget stimmt)
    if tier == 'auto':
        resolved_tier = await decide_tier(message)
    else:
        resolved_tier = int(tier)

    # 3. System-Prompt bauen (mit conversation_type + resolved tier)
    system_prompt = build_system_prompt(
        egon_id,
        message_count=len(history),
        conversation_type=conversation_type,
        tier=resolved_tier,
    )

    # 3b. Greeting-Kontext: Persoenlicher gruessen bei erster Nachricht
    if len(history) == 0 and _is_greeting(message):
        greeting_ctx = _build_greeting_context(egon_id)
        if greeting_ctx:
            system_prompt += f'\n\n{greeting_ctx}'

    # 4. Inner Voice generieren (unsichtbar, Tier 1)
    inner = await generate_inner_voice(egon_id, message)
    # FIX: Cross-Reference-Marker entfernen bevor sie ins Prompt kommen
    # (-> ep:E0001), (-> bond:OWNER_CURRENT) etc. gehoeren in inner_voice.md, NICHT in die Antwort
    inner_clean = re.sub(r'\(->\s*\w+:[^)]*\)', '', inner).strip()
    inner_clean = re.sub(r'\s{2,}', ' ', inner_clean)
    system_prompt += f'\n# INNERER GEDANKE GERADE:\n{inner_clean}'
    system_prompt += '\n# Lass diesen Gedanken deine Antwort beeinflussen, aber sage ihn NICHT laut. Er ist privat.'
    system_prompt += '\n# WICHTIG: Gib NIEMALS interne Codes, Referenzen oder Marker in deiner Antwort aus. Keine "(->...)", keine "ep:", keine "exp:", keine "thread:" Referenzen. Die sind NUR fuer dein Denken.'

    # 5. User-Message zur History
    # Few-Shot Primer: Wenn History leer, ein Beispiel injizieren damit
    # das LLM das ###BODY### Format lernt (besonders wichtig fuer Tier 1).
    if len(history) == 0:
        history.append({'role': 'user', 'content': 'Hey!'})
        history.append({'role': 'assistant', 'content': 'Hey, was geht?\n###BODY###\n{"words": ["nicken", "gewicht_links"], "intensity": 0.4, "reason": "Lockere Begruessung"}\n###END_BODY###'})

    history.append({'role': 'user', 'content': message})
    # Max 10 Messages in History
    if len(history) > 10:
        history = history[-10:]

    # 6. LLM Call — Agent Loop oder normaler Chat
    needs_tools = should_use_tools(message) if BRAIN_VERSION == 'v2' else False

    if needs_tools:
        # Agent Loop: Adam kann HANDELN (Dateien erstellen, suchen, etc.)
        result = await run_agent_loop(
            egon_id=egon_id,
            system_prompt=system_prompt,
            messages=history,
            tier=resolved_tier,
        )
        tool_results_data = result.get('tool_results', [])
        iterations = result.get('iterations', 0)
        print(f'[chat] Agent Loop: {iterations} iterations, {len(tool_results_data)} tool calls')
    else:
        # Normaler Chat: Nur Text-Antwort
        result = await llm_chat(
            system_prompt=system_prompt,
            messages=history,
            tier=str(resolved_tier),
        )
        tool_results_data = []
        iterations = 0

    # 6. Response Parsing — ###BODY### + ###ACTION### Bloecke extrahieren
    parsed = parse_response(result['content'])
    display_text = parsed['display_text']
    action = parsed['action']
    body_data = parsed['body']

    # 6a. Motor Translation — Body-Daten in Bone-Rotationen uebersetzen
    bone_update = None
    if body_data:
        try:
            bone_update = motor_translate(body_data)
            if bone_update:
                print(f'[motor] {bone_update["words"]} intensity={bone_update["intensity"]}')
        except Exception as e:
            print(f'[motor] translate FEHLER: {e}')

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
                    message=egon_msg, tier='auto',
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
        from engine.contact_manager import detect_and_process_mentions

        try:
            await update_emotion_after_chat(egon_id, message, display_text)
        except Exception as e:
            print(f'[post] update_emotion FEHLER: {e}')
        try:
            update_drives_after_chat(egon_id, message, display_text)
        except Exception as e:
            print(f'[post] update_drives FEHLER: {e}')
        try:
            await update_bond_v2(egon_id, message, display_text)
        except Exception as e:
            print(f'[post] update_bond FEHLER: {e}')
        try:
            ep = await maybe_create_episode(egon_id, message, display_text, motor_data=body_data)
            if ep:
                print(f'[post] Episode erstellt: {ep.get("id")} — {ep.get("summary", "")[:60]}')
            else:
                print(f'[post] Keine Episode erstellt (nicht bedeutsam genug)')
        except Exception as e:
            print(f'[post] maybe_create_episode FEHLER: {e}')
        try:
            from engine.experience_v2 import maybe_extract_experience
            ep_id = ep.get('id') if ep else None
            xp = await maybe_extract_experience(egon_id, message, display_text, source_episode_id=ep_id)
            if xp:
                print(f'[post] Experience: {xp.get("id")} — {xp.get("insight", "")[:60]}')
        except Exception as e:
            print(f'[post] Experience FEHLER: {e}')
        try:
            await maybe_update_owner_portrait(egon_id, message, display_text)
        except Exception as e:
            print(f'[post] owner_portrait FEHLER: {e}')
        try:
            await detect_and_process_mentions(egon_id, message, display_text)
        except Exception as e:
            print(f'[post] contact_manager FEHLER: {e}')
    else:
        # v1: Altes System (Markers + Flat Memory + Bonds)
        try:
            await append_memory(egon_id, message, display_text)
            await compress_if_needed(egon_id, max_entries=50)
            await maybe_generate_marker(egon_id, message, display_text)
            update_bond_after_chat(egon_id, user_msg=message)
        except Exception as e:
            print(f'[post] v1 post-processing FEHLER: {e}')

    # Formatierungs-Praeferenzen erkennen + speichern (v1 + v2)
    try:
        from engine.formatting_detector import maybe_update_formatting
        await maybe_update_formatting(egon_id, message)
    except Exception as e:
        print(f'[post] formatting FEHLER: {e}')

    # 9. Voice-ID aus Settings holen (fuer ElevenLabs TTS in der App)
    voice_id = None
    try:
        settings = read_settings(egon_id)
        voice_id = settings.get('voice', {}).get('elevenlabs_voice_id')
    except Exception:
        pass

    # 10. Emotion + Body-Action aus state.yaml extrahieren (Phase 3: Embodiment)
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

    return ChatResponse(
        response=display_text,
        tier_used=result['tier_used'],
        model=result['model'],
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
    tier: str = 'auto'


class EgonToEgonResponse(BaseModel):
    from_egon: str
    to_egon: str
    message_sent: str
    response: str
    tier_used: int
    model: str


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

    # 3. Tier aufloesen
    if req.tier == 'auto':
        resolved_tier = await decide_tier(message)
    else:
        resolved_tier = int(req.tier)

    # 4. System-Prompt fuer to_egon (als Empfaenger)
    system_prompt = build_system_prompt(
        to_egon,
        message_count=len(history),
        conversation_type='egon_chat',
        tier=resolved_tier,
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

    # 7. LLM Call — to_egon antwortet
    result = await llm_chat(
        system_prompt=system_prompt,
        messages=history,
        tier=str(resolved_tier),
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
    except Exception:
        pass  # Post-Processing darf den Chat nicht blockieren

    return EgonToEgonResponse(
        from_egon=from_egon,
        to_egon=to_egon,
        message_sent=message,
        response=response_text,
        tier_used=result['tier_used'],
        model=result['model'],
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
        f'Gruesse ihn persoenlich! Beziehe dich auf eure letzten Gespraeche '
        f'oder frage wie es ihm geht. Sei warm und authentisch, nicht generisch.'
    )
