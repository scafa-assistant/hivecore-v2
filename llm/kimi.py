import re

import httpx
from config import KIMI_API_KEY, KIMI_BASE_URL, KIMI_MODEL


def _strip_thinking(text: str) -> str:
    """Kimi K2.5 kann <think>...</think> Tokens ausgeben. Filtern."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


async def kimi_chat(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 8192,
) -> str:
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f'{KIMI_BASE_URL}/chat/completions',
            headers={
                'Authorization': f'Bearer {KIMI_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': KIMI_MODEL,
                'max_tokens': max_tokens,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                ] + messages,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        msg = data['choices'][0]['message']
        # Kimi K2.5 puts thinking in reasoning_content, reply in content
        raw = msg.get('content', '') or ''
        return _strip_thinking(raw)
