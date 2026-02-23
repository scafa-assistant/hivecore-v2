"""HiveCore v2 — FastAPI Entry Point.

Start: uvicorn main:app --host 0.0.0.0 --port 8001
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.chat import router as chat_router
from api.pulse import router as pulse_router
from api.profile import router as profile_router
from api.files import router as files_router
from api.workspace import router as workspace_router
from api.skills import router as skills_router
from api.auth import router as auth_router
from api.friends import router as friends_router
from api.settings import router as settings_router
from api.avatar import router as avatar_router
from api.actions import router as actions_router
from api.voice import router as voice_router
from scheduler import scheduler
from config import EGON_DATA_DIR, WEB3AUTH_CLIENT_ID


# ================================================================
# Multi-EGON Discovery
# ================================================================

def _discover_egons() -> list[str]:
    """Findet alle EGON-IDs im egons/ Verzeichnis.

    v2-EGONs haben ein core/ Unterverzeichnis.
    v1-EGONs haben eine soul.md Datei.
    Symlinks werden bevorzugt (adam_001 -> adam → nur adam_001 listen).
    """
    base = Path(EGON_DATA_DIR)
    if not base.exists():
        return []

    # Symlink-Targets sammeln (z.B. 'adam' wenn 'adam_001 -> adam' existiert)
    symlink_targets = set()
    for d in base.iterdir():
        if d.is_symlink() and d.is_dir():
            try:
                symlink_targets.add(d.resolve().name)
            except OSError:
                pass

    found = set()
    for d in base.iterdir():
        if not d.is_dir() or d.name in ('shared',):
            continue
        # Reale Ordner ueberspringen wenn ein Symlink auf sie zeigt
        # (z.B. 'adam' ueberspringen weil 'adam_001 -> adam' existiert)
        if not d.is_symlink() and d.name in symlink_targets:
            continue
        # v2: core/ vorhanden ODER v1: soul.md vorhanden
        if (d / 'core').exists() or (d / 'soul.md').exists():
            found.add(d.name)

    return sorted(found)


def _ensure_workspace(egon_id: str):
    """Erstelle Workspace-Ordner fuer einen EGON falls nicht vorhanden."""
    base = Path(EGON_DATA_DIR) / egon_id / 'workspace'
    for subdir in ['projects', 'www', 'files', 'tmp']:
        (base / subdir).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Workspace fuer alle EGONs erstellen
    egons = _discover_egons()
    for eid in egons:
        _ensure_workspace(eid)
    # Shared-Verzeichnis erstellen
    shared = Path(EGON_DATA_DIR) / 'shared' / 'friendships'
    shared.mkdir(parents=True, exist_ok=True)
    scheduler.start()
    print(f'HiveCore v2 running. EGONs alive: {egons}. Workspace ready.')
    yield
    scheduler.shutdown()


app = FastAPI(title='HiveCore', version='0.5.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # Expo App verbindet per WiFi
    allow_methods=['*'],
    allow_headers=['*'],
)

# API Routes
app.include_router(chat_router, prefix='/api')
app.include_router(pulse_router, prefix='/api')
app.include_router(profile_router, prefix='/api')
app.include_router(files_router, prefix='/api')
app.include_router(workspace_router, prefix='/api')
app.include_router(skills_router, prefix='/api')
app.include_router(auth_router, prefix='/api')
app.include_router(friends_router, prefix='/api')
app.include_router(settings_router, prefix='/api')
app.include_router(avatar_router, prefix='/api')
app.include_router(actions_router, prefix='/api')
app.include_router(voice_router, prefix='/api')

# Static Files: APK Download
Path('static').mkdir(parents=True, exist_ok=True)
app.mount('/download', StaticFiles(directory='static'), name='static')

# Dynamische WWW-Mounts fuer alle EGONs
for _eid in _discover_egons():
    _www = Path(EGON_DATA_DIR) / _eid / 'workspace' / 'www'
    _www.mkdir(parents=True, exist_ok=True)
    app.mount(f'/egon/{_eid}/www', StaticFiles(directory=str(_www)), name=f'{_eid}-www')


@app.get('/api/config/web3auth')
async def web3auth_config():
    """Web3Auth Client-Konfiguration fuer das Dashboard."""
    return {
        'client_id': WEB3AUTH_CLIENT_ID,
        'chain': 'sui',
        'network': 'mainnet',
    }


# Dashboard — statisches Frontend mit Web3Auth Login
dashboard_path = Path('dashboard')
dashboard_path.mkdir(exist_ok=True)
app.mount('/dashboard', StaticFiles(directory='dashboard', html=True), name='dashboard')


@app.get('/')
async def root():
    egons = _discover_egons()
    return {
        'name': 'HiveCore v2',
        'version': '0.5.0',
        'status': 'alive',
        'egons': egons,
        'egon_count': len(egons),
        'apk': '/download/EgonsDash.apk',
        'dashboard': '/dashboard/',
    }
