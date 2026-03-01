"""Gruppenchat API — Owner + alle EGONs in einer Gruppe.

Endpoints:
  GET  /api/groupchat              — Messages abrufen (Polling)
  POST /api/groupchat              — Nachricht senden (Owner schreibt)
  GET  /api/groupchat/participants — Teilnehmer-Liste mit Namen/Farben
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from engine.groupchat import (
    add_message,
    get_messages,
    get_recent_context,
    select_responders,
    generate_egon_groupchat_response,
    GRUPPENCHAT_EGONS,
)
from engine.naming import get_display_name
from engine.organ_reader import read_yaml_organ

router = APIRouter()

# Farben pro EGON (fuer Frontend-Avatare)
EGON_COLORS = {
    'adam_001': '#4A90D9',
    'eva_002': '#D94A7A',
    'lilith_003': '#9B59B6',
    'marx_004': '#E67E22',
    'ada_005': '#1ABC9C',
    'parzival_006': '#F1C40F',
    'sokrates_007': '#3498DB',
    'leibniz_008': '#2ECC71',
    'goethe_009': '#E74C3C',
    'eckhart_010': '#95A5A6',
}


class GroupChatSendRequest(BaseModel):
    message: str
    user_name: str = 'Rene'


@router.get('/groupchat')
async def get_groupchat(since_id: str = '', limit: int = 50):
    """Polling-Endpoint. Gibt Messages seit einer ID zurueck."""
    messages = get_messages(since_id=since_id or None, limit=limit)
    return {
        'messages': messages,
        'count': len(messages),
    }


@router.post('/groupchat')
async def send_groupchat(req: GroupChatSendRequest):
    """Owner sendet eine Nachricht. Loest EGON-Antworten aus.

    Flow:
    1. Owner-Message speichern
    2. 2-3 EGONs auswaehlen
    3. Jeder EGON generiert Antwort (oder schweigt)
    4. Alle neuen Messages zurueck
    """
    # 1. Owner-Message speichern
    owner_msg = add_message(
        from_type='owner',
        from_id='owner',
        from_name=req.user_name,
        message=req.message,
    )

    new_messages = [owner_msg]

    # 2. Responder auswaehlen
    selected = select_responders(
        message=req.message,
        sender_id='owner',
        all_egon_ids=GRUPPENCHAT_EGONS,
        max_responders=3,
    )

    # 3. Antworten generieren (sequentiell, damit Kontext aufbaut)
    recent_context = get_recent_context(max_messages=15)

    for egon_id in selected:
        try:
            response = await generate_egon_groupchat_response(
                egon_id=egon_id,
                recent_context=recent_context,
                trigger_message=req.message,
                sender_name=req.user_name,
            )
            if response:
                egon_name = get_display_name(egon_id, 'vorname')
                egon_msg = add_message(
                    from_type='egon',
                    from_id=egon_id,
                    from_name=egon_name,
                    message=response,
                )
                new_messages.append(egon_msg)
                # Kontext updaten fuer naechsten EGON
                recent_context += f'\n{egon_name}: {response}'
        except Exception as e:
            print(f'[groupchat] Error generating response for {egon_id}: {e}')

    return {
        'messages': new_messages,
        'count': len(new_messages),
        'responders': selected,
    }


@router.get('/groupchat/participants')
async def get_participants():
    """Teilnehmer-Liste mit Display-Infos fuer das Frontend."""
    participants = [
        {
            'id': 'owner',
            'name': 'Rene',
            'type': 'owner',
            'color': '#00d4aa',
        }
    ]

    for egon_id in GRUPPENCHAT_EGONS:
        name = get_display_name(egon_id, 'vorname')
        participants.append({
            'id': egon_id,
            'name': name,
            'type': 'egon',
            'color': EGON_COLORS.get(egon_id, '#888888'),
        })

    return {'participants': participants}
