from llm.moonshot import moonshot_chat
from llm.kimi import kimi_chat
from llm.sonnet import sonnet_chat
from llm.planner import decide_tier

TIER_MODELS = {1: 'moonshot', 2: 'kimi', 3: 'sonnet'}


async def llm_chat(
    system_prompt: str,
    messages: list[dict],
    tier: str = 'auto',
) -> dict:
    # 1. Tier bestimmen
    if tier == 'auto':
        resolved_tier = await decide_tier(messages[-1]['content'])
    else:
        resolved_tier = int(tier)

    # 2. An richtiges Modell routen
    if resolved_tier == 1:
        response = await moonshot_chat(system_prompt, messages)
    elif resolved_tier == 2:
        response = await kimi_chat(system_prompt, messages)
    elif resolved_tier == 3:
        response = await sonnet_chat(system_prompt, messages)
    else:
        response = await moonshot_chat(system_prompt, messages)
        resolved_tier = 1

    return {
        'content': response,
        'tier_used': resolved_tier,
        'model': TIER_MODELS.get(resolved_tier, 'moonshot'),
    }
