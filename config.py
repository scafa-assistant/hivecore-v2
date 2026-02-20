import os
from dotenv import load_dotenv

load_dotenv()

# Tier 1: Moonshot
MOONSHOT_API_KEY = os.getenv('MOONSHOT_API_KEY')
MOONSHOT_BASE_URL = os.getenv('MOONSHOT_BASE_URL', 'https://api.moonshot.ai/v1')
MOONSHOT_MODEL = os.getenv('MOONSHOT_MODEL', 'moonshot-v1-8k')

# Tier 2: Kimi K2.5
KIMI_API_KEY = os.getenv('KIMI_API_KEY')
KIMI_BASE_URL = os.getenv('KIMI_BASE_URL', 'https://api.moonshot.ai/v1')
KIMI_MODEL = os.getenv('KIMI_MODEL', 'kimi-k2.5')

# Tier 3: Sonnet 4.6
SONNET_API_KEY = os.getenv('SONNET_API_KEY')
SONNET_BASE_URL = os.getenv('SONNET_BASE_URL', 'https://api.anthropic.com/v1')
SONNET_MODEL = os.getenv('SONNET_MODEL', 'claude-sonnet-4-5-20250929')

# EGON Data
EGON_DATA_DIR = os.getenv('EGON_DATA_DIR', './egons')

# Pulse Schedule
PULSE_HOUR = int(os.getenv('PULSE_HOUR', '8'))
PULSE_MINUTE = int(os.getenv('PULSE_MINUTE', '0'))
