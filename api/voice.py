"""Voice-Endpoint — Sprachnachrichten empfangen und verarbeiten.

Ablauf:
1. Audio-Datei per Multipart-Upload empfangen
2. Mit faster-whisper transkribieren
3. Transkript an den normalen Chat-Flow weiterleiten
4. Antwort + Transkript zurueckgeben
"""

import os
import tempfile
import logging
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, Any
from pydantic import BaseModel
from engine.transcribe import transcribe

router = APIRouter()
logger = logging.getLogger(__name__)


class VoiceResponse(BaseModel):
    response: str
    tier_used: int
    model: str
    egon_id: str
    transcript: str
    action: Optional[dict[str, Any]] = None
    voice_id: Optional[str] = None


@router.post('/chat/voice', response_model=VoiceResponse)
async def chat_voice(
    audio: UploadFile = File(...),
    egon_id: str = Form(default='adam_001'),
    device_id: str = Form(default=''),
    user_name: str = Form(default=''),
):
    """Voice-Message empfangen, transkribieren und als Chat verarbeiten."""

    # 1. Audio-Datei temporaer speichern
    suffix = os.path.splitext(audio.filename or 'voice.m4a')[1] or '.m4a'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    logger.info(f'Voice-Upload: {audio.filename} ({len(content)} bytes) von {device_id or "unknown"}')

    try:
        # 2. Transkribieren
        transcript = transcribe(tmp_path, language='de')
        if not transcript:
            raise HTTPException(
                status_code=422,
                detail='Transkription fehlgeschlagen — kein Text erkannt'
            )

        logger.info(f'Transkript: "{transcript[:100]}"')

        # 3. An normalen Chat-Flow weiterleiten
        # Import hier um zirkulaere Imports zu vermeiden
        from api.chat import chat, ChatRequest

        chat_req = ChatRequest(
            egon_id=egon_id,
            message=transcript,
            tier='auto',
            device_id=device_id,
            user_name=user_name,
        )
        chat_result = await chat(chat_req)

        # 4. Response zusammenbauen
        return VoiceResponse(
            response=chat_result.response,
            tier_used=chat_result.tier_used,
            model=chat_result.model,
            egon_id=chat_result.egon_id,
            transcript=transcript,
            action=chat_result.action,
            voice_id=chat_result.voice_id,
        )

    finally:
        # Temp-Datei aufraeumen
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
