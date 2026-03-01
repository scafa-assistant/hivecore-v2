import os
from dotenv import load_dotenv

load_dotenv()

# LLM: Moonshot / Kimi K2.5 — einzige API
MOONSHOT_API_KEY = os.getenv('MOONSHOT_API_KEY')
MOONSHOT_BASE_URL = os.getenv('MOONSHOT_BASE_URL', 'https://api.moonshot.ai/v1')
MOONSHOT_MODEL = os.getenv('MOONSHOT_MODEL', 'moonshot-v1-32k')

KIMI_API_KEY = os.getenv('KIMI_API_KEY')
KIMI_BASE_URL = os.getenv('KIMI_BASE_URL', 'https://api.moonshot.ai/v1')
KIMI_MODEL = os.getenv('KIMI_MODEL', 'kimi-k2.5')

# EGON Data
EGON_DATA_DIR = os.getenv('EGON_DATA_DIR', './egons')

# Brain Version: 'v1' = old 8-file brain, 'v2' = new 12-organ-5-layer brain
BRAIN_VERSION = os.getenv('BRAIN_VERSION', 'v1')

# Pulse Schedule
PULSE_HOUR = int(os.getenv('PULSE_HOUR', '8'))
PULSE_MINUTE = int(os.getenv('PULSE_MINUTE', '0'))

# Web3Auth
WEB3AUTH_CLIENT_ID = os.getenv('WEB3AUTH_CLIENT_ID', '')
