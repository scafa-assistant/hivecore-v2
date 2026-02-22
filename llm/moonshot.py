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


async def moonshot_chat_with_tools(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    max_tokens: int = 2048,
) -> dict:
    """Moonshot mit Function-Calling (OpenAI-kompatibles Format).

    Returns:
        {
            'content': str | None,     # Text-Antwort (wenn vorhanden)
            'tool_calls': list | None, # Tool-Calls (wenn vorhanden)
            'raw_message': dict,       # Originale Message fuer History
        }
    """
    payload = {
        'model': MOONSHOT_MODEL,
        'max_tokens': max_tokens,
        'messages': [
            {'role': 'system', 'content': system_prompt},
        ] + messages,
        'tools': tools,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f'{MOONSHOT_BASE_URL}/chat/completions',
            headers={
                'Authorization': f'Bearer {MOONSHOT_API_KEY}',
                'Content-Type': 'application/json',
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    msg = data['choices'][0]['message']
    content = msg.get('content')
    tool_calls_raw = msg.get('tool_calls')

    tool_calls = None
    if tool_calls_raw:
        tool_calls = []
        for tc in tool_calls_raw:
            fn = tc.get('function', {})
            args = fn.get('arguments', '{}')
            if isinstance(args, str):
                import json
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append({
                'id': tc.get('id', ''),
                'name': fn.get('name', ''),
                'arguments': args,
            })

    return {
        'content': content,
        'tool_calls': tool_calls,
        'raw_message': msg,
    }
