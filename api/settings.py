"""Settings API — Pro-EGON Konfiguration lesen und aendern.

Endpoints:
  GET  /api/settings          → Alle Settings eines EGONs lesen
  PUT  /api/settings          → Settings partiell updaten
  GET  /api/settings/defaults → Default-Settings (fuer neue EGONs)

Auth: In Phase 2 ueber Bearer Token.
      In Phase 1: Offen fuer Tests.
"""

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from engine.settings import (
    read_settings,
    update_settings,
    SETTINGS_DEFAULTS,
)

router = APIRouter()


# ================================================================
# Request / Response Models
# ================================================================

class SettingsResponse(BaseModel):
    egon_id: str
    settings: dict[str, Any]


class SettingsUpdateRequest(BaseModel):
    egon_id: str = 'adam_001'
    updates: dict[str, Any]
    # Partielle Updates: z.B. {"wallet": {"enabled": true}}


class SettingsUpdateResponse(BaseModel):
    egon_id: str
    settings: dict[str, Any]
    message: str


class SettingsDefaultsResponse(BaseModel):
    defaults: dict[str, Any]


# ================================================================
# Endpoints
# ================================================================

@router.get('/settings', response_model=SettingsResponse)
async def get_settings(egon_id: str = Query(default='adam_001')):
    """Alle Settings eines EGONs lesen (mit Defaults gemergt)."""
    settings = read_settings(egon_id)
    return SettingsResponse(
        egon_id=egon_id,
        settings=settings,
    )


@router.put('/settings', response_model=SettingsUpdateResponse)
async def put_settings(req: SettingsUpdateRequest):
    """Settings partiell updaten.

    Nur die uebergebenen Keys werden geaendert.
    Fehlende Keys bleiben wie sie sind.

    Beispiel Body:
    {
      "egon_id": "adam_001",
      "updates": {
        "wallet": {"enabled": true},
        "display": {"homescreen_widget": true}
      }
    }
    """
    merged = update_settings(req.egon_id, req.updates)
    return SettingsUpdateResponse(
        egon_id=req.egon_id,
        settings=merged,
        message=f'Settings fuer {req.egon_id} aktualisiert.',
    )


@router.get('/settings/defaults', response_model=SettingsDefaultsResponse)
async def get_defaults():
    """Default-Settings zurueckgeben (fuer neue EGONs / Reset)."""
    return SettingsDefaultsResponse(defaults=SETTINGS_DEFAULTS)
