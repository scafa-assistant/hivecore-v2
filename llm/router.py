"""LLM Router — Eine API: Moonshot (Kimi K2.5).

Alles laeuft ueber Moonshot. Kein Tier-System, kein Routing.
"""

from llm.moonshot import moonshot_chat, moonshot_chat_with_tools


async def llm_chat(
    system_prompt: str,
    messages: list[dict],
    egon_id: str = 'adam_001',
    **_,  # Ignoriert verbleibende Legacy-Parameter
) -> dict:
    response = await moonshot_chat(system_prompt, messages)
    return {
        'content': response,
        'model': 'moonshot',
    }


async def llm_chat_with_tools(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    egon_id: str = 'adam_001',
    **_,  # Ignoriert verbleibende Legacy-Parameter
) -> dict:
    result = await moonshot_chat_with_tools(
        system_prompt, messages, tools,
    )
    result['model'] = 'moonshot'
    return result
