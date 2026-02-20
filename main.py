"""HiveCore v2 — FastAPI Entry Point.

Start: uvicorn main:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.chat import router as chat_router
from api.pulse import router as pulse_router
from api.profile import router as profile_router
from api.files import router as files_router
from scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    print('HiveCore v2 running. Adam is alive.')
    yield
    scheduler.shutdown()


app = FastAPI(title='HiveCore', version='0.2.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # Expo App verbindet per WiFi
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(chat_router, prefix='/api')
app.include_router(pulse_router, prefix='/api')
app.include_router(profile_router, prefix='/api')
app.include_router(files_router, prefix='/api')


app.mount('/download', StaticFiles(directory='static'), name='static')


@app.get('/')
async def root():
    return {
        'name': 'HiveCore v2',
        'version': '0.2.0',
        'status': 'alive',
        'egon': 'adam',
        'apk': '/download/EgonsDash.apk',
    }
