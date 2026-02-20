import httpx
from config import MOONSHOT_API_KEY, MOONSHOT_BASE_URL, MOONSHOT_MODEL


async def moonshot_chat(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 2048,
) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f'{MOONSHOT_BASE_URL}/chat/completions',
            headers={
                'Authorization': f'Bearer {MOONSHOT_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': MOONSHOT_MODEL,
                'max_tokens': max_tokens,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                ] + messages,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content']
