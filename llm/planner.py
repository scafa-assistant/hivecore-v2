from llm.moonshot import moonshot_chat

PLANNER_SYSTEM = '''Du bist ein Task-Router.
Antworte NUR mit einer Zahl: 1, 2 oder 3.

1 = Einfach: Chat, Gefuehle, Smalltalk, Erinnerungen,
    Pulse-Schritte, Memory-Updates, kurze Antworten.
2 = Komplex: Code schreiben, Analyse, Research,
    Multi-Step Reasoning, Brainstorm, lange Antworten.
3 = Kritisch: Genesis (SOUL-Verschmelzung),
    Jury-Endurteil, Season-Passport, Todeszene.

Antworte NUR mit: 1 oder 2 oder 3'''


async def decide_tier(user_message: str) -> int:
    result = await moonshot_chat(
        system_prompt=PLANNER_SYSTEM,
        messages=[{
            'role': 'user',
            'content': f'Task: {user_message[:300]}',
        }],
        max_tokens=5,
    )
    try:
        return int(result.strip()[0])
    except (ValueError, IndexError):
        return 1  # Fallback: Tier 1
