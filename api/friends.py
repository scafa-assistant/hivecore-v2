"""Friends API — Freundesanfragen zwischen EGONs.

Endpoints:
  POST /api/friends/request    → Freundesanfrage senden
  POST /api/friends/accept     → Anfrage annehmen
  POST /api/friends/reject     → Anfrage ablehnen
  GET  /api/friends/list       → Freundesliste eines EGONs
  GET  /api/friends/pending    → Offene Anfragen eines EGONs

Auth: Bearer Token aus Session → egon_id.
Nur der Owner eines EGONs darf fuer seinen EGON handeln.
"""

from typing import Optional, Any

from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel

from api.auth import get_current_user
from engine.friendship import (
    send_request,
    accept_request,
    reject_request,
    get_friends,
    get_pending_requests,
    are_friends,
)

router = APIRouter()


# ================================================================
# Request / Response Models
# ================================================================

class FriendRequestBody(BaseModel):
    from_egon: str
    to_egon: str
    message: str = ''


class FriendAcceptBody(BaseModel):
    from_egon: str
    to_egon: str


class FriendRejectBody(BaseModel):
    from_egon: str
    to_egon: str


class FriendRequestResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None
    request: Optional[dict[str, Any]] = None


class FriendAcceptResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None
    friendship_id: Optional[str] = None
    friendship: Optional[dict[str, Any]] = None


class FriendRejectResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None


class FriendListResponse(BaseModel):
    egon_id: str
    friends: list[str]
    count: int


class FriendPendingResponse(BaseModel):
    egon_id: str
    pending: list[dict[str, Any]]
    count: int


# ================================================================
# Endpoints
# ================================================================

@router.post('/friends/request', response_model=FriendRequestResponse)
async def friend_request(req: FriendRequestBody):
    """Freundesanfrage senden.

    Jeder EGON kann eine Anfrage senden. Auth-Check kommt in Phase 2
    (Bearer Token → Session → egon_id). In Phase 1: Offen fuer Tests.
    """
    result = send_request(req.from_egon, req.to_egon, req.message)

    if not result.get('success'):
        return FriendRequestResponse(
            success=False,
            message=result.get('error', 'Unbekannter Fehler'),
            error=result.get('error'),
        )

    return FriendRequestResponse(
        success=True,
        message=result['message'],
        request=result.get('request'),
    )


@router.post('/friends/accept', response_model=FriendAcceptResponse)
async def friend_accept(req: FriendAcceptBody):
    """Freundesanfrage annehmen.

    In Phase 2: Nur der Owner des to_egon darf annehmen (Bearer Token Check).
    In Phase 1: Offen fuer Tests.
    """
    result = accept_request(req.from_egon, req.to_egon)

    if not result.get('success'):
        return FriendAcceptResponse(
            success=False,
            message=result.get('error', 'Unbekannter Fehler'),
            error=result.get('error'),
        )

    return FriendAcceptResponse(
        success=True,
        message=result['message'],
        friendship_id=result.get('friendship_id'),
        friendship=result.get('friendship'),
    )


@router.post('/friends/reject', response_model=FriendRejectResponse)
async def friend_reject(req: FriendRejectBody):
    """Freundesanfrage ablehnen.

    In Phase 2: Nur der Owner des to_egon darf ablehnen.
    """
    result = reject_request(req.from_egon, req.to_egon)

    if not result.get('success'):
        return FriendRejectResponse(
            success=False,
            message=result.get('error', 'Unbekannter Fehler'),
            error=result.get('error'),
        )

    return FriendRejectResponse(
        success=True,
        message=result['message'],
    )


@router.get('/friends/list', response_model=FriendListResponse)
async def friend_list(egon_id: str = Query(default='adam_001')):
    """Freundesliste eines EGONs."""
    friends = get_friends(egon_id)
    return FriendListResponse(
        egon_id=egon_id,
        friends=friends,
        count=len(friends),
    )


@router.get('/friends/pending', response_model=FriendPendingResponse)
async def friend_pending(egon_id: str = Query(default='adam_001')):
    """Offene Anfragen an einen EGON."""
    pending = get_pending_requests(egon_id)
    return FriendPendingResponse(
        egon_id=egon_id,
        pending=pending,
        count=len(pending),
    )
