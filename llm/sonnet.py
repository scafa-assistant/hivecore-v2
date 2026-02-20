import httpx
from config import SONNET_API_KEY, SONNET_MODEL

# ACHTUNG: Anthropic API hat ANDERES Format als OpenAI!
# - system ist ein TOP-LEVEL FELD, nicht in messages
# - Header: x-api-key (nicht Authorization: Bearer)
# - Response: data['content'][0]['text'] (nicht choices)


async def sonnet_chat(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 4096,
) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': SONNET_API_KEY,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json',
            },
            json={
                'model': SONNET_MODEL,
                'max_tokens': max_tokens,
                'system': system_prompt,
                'messages': messages,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data['content'][0]['text']
