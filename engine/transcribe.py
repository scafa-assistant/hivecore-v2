"""Whisper-basierte Transkription fuer Voice-Messages.

Nutzt faster-whisper fuer effiziente Spracherkennung.
Fallback auf einfache Transkription wenn faster-whisper nicht installiert ist.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Versuche faster-whisper zu laden
_model = None
_model_loaded = False


def _load_model():
    """Lade Whisper-Modell (lazy, beim ersten Aufruf)."""
    global _model, _model_loaded
    if _model_loaded:
        return _model

    try:
        from faster_whisper import WhisperModel
        # "base" Modell ist ein guter Kompromiss aus Geschwindigkeit und Qualitaet
        model_size = os.getenv('WHISPER_MODEL', 'base')
        device = os.getenv('WHISPER_DEVICE', 'cpu')
        compute_type = 'int8' if device == 'cpu' else 'float16'

        logger.info(f'Lade Whisper-Modell: {model_size} auf {device} ({compute_type})')
        _model = WhisperModel(model_size, device=device, compute_type=compute_type)
        _model_loaded = True
        logger.info('Whisper-Modell erfolgreich geladen')
    except ImportError:
        logger.warning('faster-whisper nicht installiert — Transkription nicht verfuegbar')
        _model = None
        _model_loaded = True
    except Exception as e:
        logger.error(f'Fehler beim Laden des Whisper-Modells: {e}')
        _model = None
        _model_loaded = True

    return _model


def transcribe(audio_path: str, language: str = 'de') -> str:
    """Transkribiere eine Audio-Datei zu Text.

    Args:
        audio_path: Pfad zur Audio-Datei (m4a, wav, mp3, etc.)
        language: Sprache fuer die Erkennung (default: Deutsch)

    Returns:
        Transkribierter Text oder leerer String bei Fehler
    """
    import shutil

    # Audio-Datei Info loggen
    try:
        file_size = os.path.getsize(audio_path)
        logger.info(f'Transkription starten: {audio_path} ({file_size} bytes)')
        if file_size < 100:
            logger.warning(f'Audio-Datei sehr klein ({file_size} bytes) — vermutlich leer')
    except OSError as e:
        logger.error(f'Audio-Datei nicht lesbar: {e}')
        return ''

    # ffmpeg pruefen (benoetigt von faster-whisper)
    if not shutil.which('ffmpeg'):
        logger.error('ffmpeg nicht installiert — benoetigt fuer Audio-Konvertierung!')
        return ''

    model = _load_model()
    if model is None:
        logger.error('Kein Whisper-Modell verfuegbar — faster-whisper installiert?')
        return ''

    try:
        segments, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,  # Voice Activity Detection — filtert Stille
        )

        # Segmente zu Text zusammenfuegen
        seg_list = list(segments)
        transcript = ' '.join(seg.text.strip() for seg in seg_list)
        logger.info(
            f'Transkription: "{transcript[:100]}" '
            f'(Segmente: {len(seg_list)}, Sprache: {info.language}, '
            f'Dauer: {info.duration:.1f}s, Wahrsch.: {info.language_probability:.2f})'
        )

        if not transcript.strip():
            logger.warning(f'Transkription leer trotz {len(seg_list)} Segmenten — Audio evtl. nur Stille/Rauschen')

        return transcript.strip()

    except Exception as e:
        logger.error(f'Transkription fehlgeschlagen: {type(e).__name__}: {e}')
        return ''
