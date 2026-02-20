"""Chat-Endpoint — der wichtigste Endpoint.

Ablauf bei jedem Chat:
1. Chat-History holen
2. System-Prompt bauen (SOUL + MEMORY + MARKERS)
3. Inner Voice generieren (unsichtbar)
4. LLM Call (Router entscheidet Tier)
5. Post-Processing: Memory + Marker + Bond Update
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from engine.prompt_builder import build_system_prompt
from engine.memory import append_memory, compress_if_needed
from engine.markers import maybe_generate_marker
from engine.inner_voice import generate_inner_voice
from engine.bonds import update_bond_after_chat
from llm.router import llm_chat

router = APIRouter()

# In-Memory Chat-History pro EGON
chat_histories: dict[str, list] = {}


class ChatRequest(BaseModel):
    egon_id: str = 'adam'
    message: str
    tier: str = 'auto'


class ChatResponse(BaseModel):
    response: str
    tier_used: int
    model: str
    egon_id: str


@router.post('/chat', response_model=ChatResponse)
async def chat(req: ChatRequest):
    egon_id = req.egon_id
    message = req.message
    tier = req.tier

    # 1. Chat-History holen/erstellen
    if egon_id not in chat_histories:
        chat_histories[egon_id] = []
    history = chat_histories[egon_id]

    # 2. System-Prompt bauen
    system_prompt = build_system_prompt(egon_id, message_count=len(history))

    # 3. Inner Voice generieren (unsichtbar, Tier 1)
    inner = await generate_inner_voice(egon_id, message)
    system_prompt += f'\n# INNERER GEDANKE GERADE:\n{inner}'
    system_prompt += '\n# Lass diesen Gedanken deine Antwort beeinflussen, aber sage ihn NICHT laut. Er ist privat.'

    # 4. User-Message zur History
    history.append({'role': 'user', 'content': message})
    # Max 10 Messages in History
    if len(history) > 10:
        history = history[-10:]

    # 5. LLM Call
    result = await llm_chat(
        system_prompt=system_prompt,
        messages=history,
        tier=tier,
    )

    # 6. Antwort in History
    history.append({'role': 'assistant', 'content': result['content']})
    chat_histories[egon_id] = history

    # 7. Post-Processing (Memory + Marker + Bond)
    try:
        await append_memory(egon_id, message, result['content'])
        await compress_if_needed(egon_id, max_entries=50)
        await maybe_generate_marker(egon_id, message, result['content'])
        update_bond_after_chat(egon_id)
    except Exception:
        pass  # Post-Processing darf den Chat nicht blockieren

    return ChatResponse(
        response=result['content'],
        tier_used=result['tier_used'],
        model=result['model'],
        egon_id=egon_id,
    )
