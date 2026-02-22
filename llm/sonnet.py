import httpx
from config import SONNET_API_KEY, SONNET_MODEL

# ACHTUNG: Anthropic API hat ANDERES Format als OpenAI!
# - system ist ein TOP-LEVEL FELD, nicht in messages
# - Header: x-api-key (nicht Authorization: Bearer)
# - Response: data['content'][0]['text'] (nicht choices)
# - Tool-Use: tools als Top-Level, tool_result im User-Message


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


async def sonnet_chat_with_tools(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    max_tokens: int = 4096,
) -> dict:
    """Sonnet mit Tool-Use (Anthropic-natives Format).

    ACHTUNG: Anthropic-Format ist ANDERS als OpenAI:
    - tools ist Top-Level im Request
    - Tool-Calls kommen als content-Blocks mit type: "tool_use"
    - Tool-Results gehen als User-Message mit type: "tool_result"

    Returns:
        {
            'content': str | None,
            'tool_calls': list | None,
            'raw_content': list,  # Originale Content-Blocks fuer History
            'stop_reason': str,
        }
    """
    payload = {
        'model': SONNET_MODEL,
        'max_tokens': max_tokens,
        'system': system_prompt,
        'messages': messages,
        'tools': tools,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': SONNET_API_KEY,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json',
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    content_blocks = data.get('content', [])
    stop_reason = data.get('stop_reason', '')

    # Extrahiere Text und Tool-Calls aus Content-Blocks
    text_parts = []
    tool_calls = []

    for block in content_blocks:
        if block.get('type') == 'text':
            text_parts.append(block['text'])
        elif block.get('type') == 'tool_use':
            tool_calls.append({
                'id': block['id'],
                'name': block['name'],
                'arguments': block.get('input', {}),
            })

    content = '\n'.join(text_parts) if text_parts else None

    return {
        'content': content,
        'tool_calls': tool_calls if tool_calls else None,
        'raw_content': content_blocks,
        'stop_reason': stop_reason,
    }
