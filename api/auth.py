"""Auth API — Web3Auth Login + Session Management + EGON Binding.

Ablauf:
1. Frontend: Web3Auth Modal → MetaMask/Social Login → Wallet-Adresse
2. POST /api/auth/login  → Session-Token (oder needs_bind: true)
3. POST /api/auth/bind   → Wallet an EGON binden (First-Bind)
4. GET  /api/auth/me     → User-Info + EGON-Profil
5. POST /api/auth/logout → Session invalidieren

Design:
  - In-Memory Sessions (Server-Restart = Logout)
  - Registry-basiertes Wallet → EGON Mapping (egons/registry.yaml)
  - First-Bind: Wallet wird permanent an EGON gebunden
"""

import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

import yaml
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from engine.wallet_bridge import check_balance
from engine.organ_reader import read_yaml_organ
from config import EGON_DATA_DIR

router = APIRouter()


# ================================================================
# In-Memory Session Store
# ================================================================

sessions: dict[str, dict] = {}
# Format: { token: { wallet_address, egon_id, created, last_seen } }


# ================================================================
# Registry Helfer
# ================================================================

def _registry_path() -> Path:
    return Path(EGON_DATA_DIR) / 'registry.yaml'


def _read_registry() -> dict:
    """Liest die EGON-Registry."""
    path = _registry_path()
    if not path.exists():
        return {'egons': {}, 'wallet_bindings': {}}
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data if data else {'egons': {}, 'wallet_bindings': {}}


def _write_registry(data: dict) -> None:
    """Schreibt die EGON-Registry."""
    path = _registry_path()
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


# ================================================================
# Request / Response Models
# ================================================================

class LoginRequest(BaseModel):
    wallet_address: str
    chain_id: Optional[str] = None
    provider: Optional[str] = None


class LoginResponse(BaseModel):
    token: Optional[str] = None
    egon_id: Optional[str] = None
    wallet_address: str
    needs_bind: bool = False
    available_egons: Optional[list[dict]] = None
    message: str


class BindRequest(BaseModel):
    wallet_address: str
    egon_id: str


class BindResponse(BaseModel):
    success: bool
    egon_id: str
    message: str


class UserInfo(BaseModel):
    wallet_address: str
    egon_id: str
    balance: float
    daily_cost: float
    days_left: float
    created: str
    provider: Optional[str] = None


class AvailableEgonsResponse(BaseModel):
    egons: list[dict]
    count: int


class LogoutResponse(BaseModel):
    success: bool
    message: str


# ================================================================
# Helfer
# ================================================================

def _resolve_egon_id(wallet_address: str) -> str | None:
    """Wallet-Adresse → EGON-ID aus registry.yaml. None wenn nicht gebunden."""
    registry = _read_registry()
    bindings = registry.get('wallet_bindings', {})
    return bindings.get(wallet_address)


def _get_available_egons() -> list[dict]:
    """Gibt alle ungebundenen EGONs zurueck."""
    registry = _read_registry()
    egons = registry.get('egons', {})
    available = []
    for eid, info in egons.items():
        if info.get('bound_wallet') is None and info.get('status') == 'alive':
            available.append({
                'egon_id': eid,
                'name': info.get('name', eid),
                'generation': info.get('generation', 0),
                'created': info.get('created', ''),
            })
    return available


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """FastAPI Dependency — Token aus Authorization Header lesen.

    Nutzung in Endpoints:
        @router.get('/protected')
        async def protected(user = Depends(get_current_user)):
            print(user['egon_id'])
    """
    if not authorization:
        raise HTTPException(status_code=401, detail='No authorization header')

    parts = authorization.split(' ')
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        raise HTTPException(status_code=401, detail='Invalid authorization format')

    token = parts[1]
    if token not in sessions:
        raise HTTPException(status_code=401, detail='Invalid or expired token')

    session = sessions[token]
    session['last_seen'] = datetime.now().isoformat()
    return session


# ================================================================
# Endpoints
# ================================================================

@router.post('/auth/login', response_model=LoginResponse)
async def login(req: LoginRequest):
    """Web3Auth Login — Wallet-Adresse → Session-Token.

    Wenn die Wallet noch an keinen EGON gebunden ist:
    → needs_bind: true + Liste verfuegbarer EGONs.
    """
    wallet = req.wallet_address.strip()
    if not wallet or len(wallet) < 10:
        raise HTTPException(status_code=400, detail='Invalid wallet address')

    egon_id = _resolve_egon_id(wallet)

    # Wallet noch nicht gebunden?
    if egon_id is None:
        available = _get_available_egons()
        return LoginResponse(
            wallet_address=wallet,
            needs_bind=True,
            available_egons=available,
            message='Wallet noch nicht gebunden. Waehle deinen EGON.',
        )

    # Bestehende Session fuer diese Wallet finden oder neue erstellen
    existing_token = None
    for tok, sess in sessions.items():
        if sess.get('wallet_address') == wallet:
            existing_token = tok
            break

    if existing_token:
        token = existing_token
        sessions[token]['last_seen'] = datetime.now().isoformat()
    else:
        token = secrets.token_urlsafe(32)
        sessions[token] = {
            'wallet_address': wallet,
            'egon_id': egon_id,
            'created': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'provider': req.provider,
            'chain_id': req.chain_id,
        }

    return LoginResponse(
        token=token,
        egon_id=egon_id,
        wallet_address=wallet,
        message=f'Willkommen! Du bist mit {egon_id} verbunden.',
    )


@router.post('/auth/bind', response_model=BindResponse)
async def bind(req: BindRequest):
    """First-Bind: Wallet permanent an EGON binden.

    Achtung: Diese Verbindung ist permanent (ausser Owner-Transfer).
    """
    wallet = req.wallet_address.strip()
    egon_id = req.egon_id.strip()

    if not wallet or len(wallet) < 10:
        raise HTTPException(status_code=400, detail='Invalid wallet address')

    registry = _read_registry()

    # Pruefen: EGON existiert?
    if egon_id not in registry.get('egons', {}):
        raise HTTPException(status_code=404, detail=f'EGON {egon_id} nicht gefunden.')

    # Pruefen: EGON schon gebunden?
    egon_info = registry['egons'][egon_id]
    if egon_info.get('bound_wallet') is not None:
        raise HTTPException(
            status_code=409,
            detail=f'EGON {egon_id} ist bereits an eine andere Wallet gebunden.',
        )

    # Pruefen: Wallet schon an anderen EGON gebunden?
    bindings = registry.get('wallet_bindings', {})
    if wallet in bindings:
        raise HTTPException(
            status_code=409,
            detail=f'Wallet ist bereits an {bindings[wallet]} gebunden.',
        )

    # Bind!
    registry['egons'][egon_id]['bound_wallet'] = wallet
    if 'wallet_bindings' not in registry:
        registry['wallet_bindings'] = {}
    registry['wallet_bindings'][wallet] = egon_id
    _write_registry(registry)

    # SUI-Stub: SPAETER: EgonNFT Transfer auf SUI
    # await sui.transfer_nft(egon_nft_id, wallet)

    return BindResponse(
        success=True,
        egon_id=egon_id,
        message=f'{egon_id} ist jetzt permanent an deine Wallet gebunden.',
    )


@router.get('/auth/available-egons', response_model=AvailableEgonsResponse)
async def available_egons():
    """Liste aller ungebundenen EGONs (fuer First-Bind Auswahl)."""
    available = _get_available_egons()
    return AvailableEgonsResponse(egons=available, count=len(available))


@router.get('/auth/me', response_model=UserInfo)
async def me(authorization: Optional[str] = Header(None)):
    """Aktuelle User-Info + Wallet-Balance."""
    user = get_current_user(authorization)
    egon_id = user['egon_id']

    balance_info = check_balance(egon_id)

    return UserInfo(
        wallet_address=user['wallet_address'],
        egon_id=egon_id,
        balance=balance_info.get('balance', 0),
        daily_cost=balance_info.get('daily_cost', 0),
        days_left=balance_info.get('days_left', 0),
        created=user.get('created', ''),
        provider=user.get('provider'),
    )


@router.post('/auth/logout', response_model=LogoutResponse)
async def logout(authorization: Optional[str] = Header(None)):
    """Session invalidieren."""
    if not authorization:
        return LogoutResponse(success=True, message='Kein Token — nichts zu tun.')

    parts = authorization.split(' ')
    if len(parts) == 2:
        token = parts[1]
        if token in sessions:
            del sessions[token]

    return LogoutResponse(success=True, message='Abgemeldet.')
