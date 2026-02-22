import re
import json as json_module

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


async def kimi_chat_with_tools(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    max_tokens: int = 8192,
) -> dict:
    """Kimi K2.5 mit Function-Calling (OpenAI-kompatibles Format).

    Returns:
        {
            'content': str | None,
            'tool_calls': list | None,
            'raw_message': dict,
        }
    """
    payload = {
        'model': KIMI_MODEL,
        'max_tokens': max_tokens,
        'messages': [
            {'role': 'system', 'content': system_prompt},
        ] + messages,
        'tools': tools,
    }

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f'{KIMI_BASE_URL}/chat/completions',
            headers={
                'Authorization': f'Bearer {KIMI_API_KEY}',
                'Content-Type': 'application/json',
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    msg = data['choices'][0]['message']
    content = msg.get('content')
    if content:
        content = _strip_thinking(content)

    tool_calls_raw = msg.get('tool_calls')
    tool_calls = None
    if tool_calls_raw:
        tool_calls = []
        for tc in tool_calls_raw:
            fn = tc.get('function', {})
            args = fn.get('arguments', '{}')
            if isinstance(args, str):
                try:
                    args = json_module.loads(args)
                except json_module.JSONDecodeError:
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
