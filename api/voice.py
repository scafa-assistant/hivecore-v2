"""Voice-Endpoint — Sprachnachrichten empfangen und verarbeiten.

Ablauf:
1. Audio-Datei per Multipart-Upload empfangen
2. Permanent speichern in /opt/hivecore-v2/audio/
3. Mit faster-whisper transkribieren
4. Transkript an den normalen Chat-Flow weiterleiten
5. Antwort + Transkript + audio_url zurueckgeben
"""

import os
import shutil
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, Any
from pydantic import BaseModel
from engine.transcribe import transcribe

router = APIRouter()
logger = logging.getLogger(__name__)

# Permanentes Audio-Verzeichnis
AUDIO_DIR = Path('/opt/hivecore-v2/audio')
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


class VoiceResponse(BaseModel):
    response: str
    tier_used: int
    model: str
    egon_id: str
    transcript: str
    action: Optional[dict[str, Any]] = None
    voice_id: Optional[str] = None
    audio_url: Optional[str] = None  # URL zur gespeicherten Audio-Datei


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

    audio_url = None
    try:
        # 2. Permanent speichern
        ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f'{ts}_{egon_id}{suffix}'
        permanent_path = AUDIO_DIR / filename
        shutil.copy2(tmp_path, permanent_path)
        audio_url = f'/api/audio/{filename}'
        logger.info(f'Audio gespeichert: {permanent_path}')

        # 3. Transkribieren
        transcript = transcribe(tmp_path, language='de')

        if not transcript:
            # Audio gespeichert aber kein Text erkannt — trotzdem 200 mit audio_url
            logger.warning(f'Transkription leer fuer {filename} — sende Default-Antwort')
            return VoiceResponse(
                response='Ich konnte deine Sprachnachricht leider nicht verstehen. Versuch es nochmal — sprich deutlich und nah ans Mikrofon.',
                tier_used=0,
                model='whisper-fallback',
                egon_id=egon_id,
                transcript='',
                audio_url=audio_url,
            )

        logger.info(f'Transkript: "{transcript[:100]}"')

        # 4. An normalen Chat-Flow weiterleiten
        from api.chat import chat, ChatRequest

        chat_req = ChatRequest(
            egon_id=egon_id,
            message=transcript,
            tier='auto',
            device_id=device_id,
            user_name=user_name,
        )
        chat_result = await chat(chat_req)

        # 5. Response zusammenbauen
        return VoiceResponse(
            response=chat_result.response,
            tier_used=chat_result.tier_used,
            model=chat_result.model,
            egon_id=chat_result.egon_id,
            transcript=transcript,
            action=chat_result.action,
            voice_id=chat_result.voice_id,
            audio_url=audio_url,
        )

    finally:
        # Temp-Datei aufraeumen (Permanent-Kopie bleibt)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
