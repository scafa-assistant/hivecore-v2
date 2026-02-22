from llm.moonshot import moonshot_chat, moonshot_chat_with_tools
from llm.kimi import kimi_chat, kimi_chat_with_tools
from llm.sonnet import sonnet_chat, sonnet_chat_with_tools
from llm.planner import decide_tier
from config import BRAIN_VERSION

TIER_MODELS = {1: 'moonshot', 2: 'kimi', 3: 'sonnet'}


async def llm_chat(
    system_prompt: str,
    messages: list[dict],
    tier: str = 'auto',
    egon_id: str = 'adam_001',
) -> dict:
    # 1. Tier bestimmen
    if tier == 'auto':
        resolved_tier = await decide_tier(messages[-1]['content'])
    else:
        resolved_tier = int(tier)

    # 2. v2: API-Limits pruefen + Auto-Downgrade
    warning = None
    downgraded = False
    if BRAIN_VERSION == 'v2':
        try:
            from engine.api_manager import check_and_track_call, track_cost

            check = check_and_track_call(egon_id, resolved_tier)

            if check.get('blocked'):
                # Alle Limits erreicht — Fallback auf Tier 1 (unbegrenzt)
                resolved_tier = 1
                warning = check.get('message', '')
            elif check.get('downgraded'):
                resolved_tier = check['tier']
                warning = check.get('warning', '')
                downgraded = True
            else:
                resolved_tier = check['tier']
                warning = check.get('warning')

            # Kosten tracken
            track_cost(egon_id, check.get('tier_key', 'tier1_local'))
        except Exception as e:
            # API-Manager darf den Chat nicht blockieren
            print(f'[router] API-Manager error: {e}')

    # 3. An richtiges Modell routen
    if resolved_tier == 1:
        response = await moonshot_chat(system_prompt, messages)
    elif resolved_tier == 2:
        response = await kimi_chat(system_prompt, messages)
    elif resolved_tier == 3:
        response = await sonnet_chat(system_prompt, messages)
    else:
        response = await moonshot_chat(system_prompt, messages)
        resolved_tier = 1

    result = {
        'content': response,
        'tier_used': resolved_tier,
        'model': TIER_MODELS.get(resolved_tier, 'moonshot'),
    }

    # v2: Downgrade/Warning Info mitgeben
    if downgraded:
        result['downgraded'] = True
    if warning:
        result['warning'] = warning

    return result


async def llm_chat_with_tools(
    system_prompt: str,
    messages: list[dict],
    tools_openai: list[dict],
    tools_anthropic: list[dict],
    tier: str = 'auto',
    egon_id: str = 'adam_001',
) -> dict:
    """LLM-Call MIT Function-Calling.

    Nutzt OpenAI-Format fuer Moonshot/Kimi, Anthropic-Format fuer Sonnet.
    API-Limits werden genauso gehandhabt wie bei llm_chat().

    Args:
        tools_openai: Tool-Definitionen im OpenAI-Format
        tools_anthropic: Tool-Definitionen im Anthropic-Format

    Returns:
        {
            'content': str | None,
            'tool_calls': list | None,
            'tier_used': int,
            'model': str,
            'raw_message': dict | list,  # Fuer History-Aufbau
        }
    """
    # 1. Tier bestimmen
    if tier == 'auto':
        last_msg = messages[-1] if messages else {}
        # Bei Tool-Messages: Content kann dict/list sein
        user_text = ''
        if isinstance(last_msg.get('content'), str):
            user_text = last_msg['content']
        resolved_tier = await decide_tier(user_text) if user_text else 1
    else:
        resolved_tier = int(tier)

    # 2. v2: API-Limits pruefen
    if BRAIN_VERSION == 'v2':
        try:
            from engine.api_manager import check_and_track_call, track_cost

            check = check_and_track_call(egon_id, resolved_tier)
            if check.get('blocked'):
                resolved_tier = 1
            elif check.get('downgraded'):
                resolved_tier = check['tier']
            else:
                resolved_tier = check['tier']

            track_cost(egon_id, check.get('tier_key', 'tier1_local'))
        except Exception as e:
            print(f'[router] API-Manager error in tool call: {e}')

    # 3. An richtiges Modell routen (mit Tools)
    if resolved_tier == 3:
        # Sonnet: Anthropic-Format
        result = await sonnet_chat_with_tools(
            system_prompt, messages, tools_anthropic,
        )
    elif resolved_tier == 2:
        # Kimi: OpenAI-Format
        result = await kimi_chat_with_tools(
            system_prompt, messages, tools_openai,
        )
    else:
        # Moonshot: OpenAI-Format
        result = await moonshot_chat_with_tools(
            system_prompt, messages, tools_openai,
        )

    result['tier_used'] = resolved_tier
    result['model'] = TIER_MODELS.get(resolved_tier, 'moonshot')

    return result
