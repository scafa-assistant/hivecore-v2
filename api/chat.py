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

router = APIRouter()

# In-Memory Chat-History pro Kanal
# Keys:
#   owner_chat:       "{egon_id}"
#   egon_chat:        "{egon_a}:{egon_b}"   (alphabetisch sortiert)
#   friend_owner_chat: "friend:{wallet}:{egon_id}"
chat_histories: dict[str, list] = {}


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
    system_prompt += f'\n# INNERER GEDANKE GERADE:\n{inner}'
    system_prompt += '\n# Lass diesen Gedanken deine Antwort beeinflussen, aber sage ihn NICHT laut. Er ist privat.'

    # 5. User-Message zur History
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

    # 6. Action Detection — parse ###ACTION### Block
    display_text, action = parse_action(result['content'])

    # 7. Antwort in History (ohne Action-Block)
    history.append({'role': 'assistant', 'content': display_text})
    chat_histories[history_key] = history

    # 8. Post-Processing (Memory + Marker + Bond)
    try:
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

            await update_emotion_after_chat(egon_id, message, display_text)
            update_drives_after_chat(egon_id, message, display_text)
            await update_bond_v2(egon_id, message, display_text)
            await maybe_create_episode(egon_id, message, display_text)

            # Phase 6: Owner lernen + Kontakte erkennen
            await maybe_update_owner_portrait(egon_id, message, display_text)
            await detect_and_process_mentions(egon_id, message, display_text)
        else:
            # v1: Altes System (Markers + Flat Memory + Bonds)
            await append_memory(egon_id, message, display_text)
            await compress_if_needed(egon_id, max_entries=50)
            await maybe_generate_marker(egon_id, message, display_text)
            update_bond_after_chat(egon_id, user_msg=message)

        # Formatierungs-Praeferenzen erkennen + speichern (v1 + v2)
        from engine.formatting_detector import maybe_update_formatting
        await maybe_update_formatting(egon_id, message)
    except Exception:
        pass  # Post-Processing darf den Chat nicht blockieren

    # 9. Voice-ID aus Settings holen (fuer ElevenLabs TTS in der App)
    voice_id = None
    try:
        settings = read_settings(egon_id)
        voice_id = settings.get('voice', {}).get('elevenlabs_voice_id')
    except Exception:
        pass

    return ChatResponse(
        response=display_text,
        tier_used=result['tier_used'],
        model=result['model'],
        egon_id=egon_id,
        action=action,
        tool_results=tool_results_data if tool_results_data else None,
        iterations=iterations if iterations else None,
        voice_id=voice_id,
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

    # 2. Chat-History fuer dieses Paar
    history_key = _chat_key(to_egon, 'egon_chat', partner_egon=from_egon)
    if history_key not in chat_histories:
        chat_histories[history_key] = []
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

    # 5. Inner Voice fuer to_egon
    try:
        inner = await generate_inner_voice(to_egon, f'{from_egon} sagt: {message}')
        system_prompt += f'\n# INNERER GEDANKE GERADE:\n{inner}'
        system_prompt += '\n# Lass diesen Gedanken deine Antwort beeinflussen, aber sage ihn NICHT laut.'
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
