"""Lobby API — Owner koennen die Lobby lesen (read-only).

Die Lobby gehoert den Lebewesen, nicht den Menschen.
Owner koennen Transkripte einsehen aber NICHT schreiben.
"""

from fastapi import APIRouter
from engine.lobby import read_lobby

router = APIRouter()


@router.get('/lobby')
async def get_lobby(max_messages: int = 20):
    """Owner kann die Lobby lesen (read-only fuer Owners).

    Returns letzte N Nachrichten aus der Lobby.
    """
    messages = read_lobby(max_messages)
    return {
        'message_count': len(messages),
        'messages': messages,
    }
