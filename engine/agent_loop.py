"""Agent Loop — Adams Handlungsschleife.

Wenn Adam Werkzeuge braucht (Dateien erstellen, Web durchsuchen, etc.),
laeuft der Agent Loop:

1. LLM wird mit Tool-Definitionen aufgerufen
2. LLM gibt Tool-Call zurueck
3. Server fuehrt Tool aus
4. Ergebnis geht zurueck an LLM
5. Wiederholen bis LLM fertig ist (max N Iterationen)

Unterscheidet OpenAI-Format (Moonshot/Kimi) und Anthropic-Format (Sonnet).
"""

import json
from llm.router import llm_chat_with_tools, llm_chat
from engine.tool_executor import execute_tool
from engine.tools import get_openai_tools, get_anthropic_tools


# Sicherheits-Limits: Wie oft darf der Loop laufen?
MAX_ITERATIONS_TIER1 = 5   # Moonshot: weniger, spart Context
MAX_ITERATIONS_TIER2 = 8   # Kimi/Sonnet: mehr Spielraum


async def run_agent_loop(
    egon_id: str,
    system_prompt: str,
    messages: list[dict],
    tier: int = 1,
) -> dict:
    """Fuehre den Agent Loop aus.

    Args:
        egon_id: EGON-ID (z.B. 'adam')
        system_prompt: Fertig gebauter System-Prompt
        messages: Chat-History (OpenAI-Format: role/content)
        tier: Aufgeloester LLM-Tier (1/2/3)

    Returns:
        {
            'content': str,          # Finale Text-Antwort
            'tier_used': int,
            'model': str,
            'tool_results': list,    # Alle ausgefuehrten Tools
            'iterations': int,       # Wie viele Runden
        }
    """
    tools_openai = get_openai_tools(tier)
    tools_anthropic = get_anthropic_tools(tier)

    max_iter = MAX_ITERATIONS_TIER1 if tier == 1 else MAX_ITERATIONS_TIER2
    tool_results = []
    model_info = {'tier_used': tier, 'model': 'moonshot'}

    # Arbeits-Kopie der Messages (wir fuegen Tool-Results hinzu)
    working_messages = list(messages)

    for iteration in range(max_iter):
        # LLM-Call mit Tools
        result = await llm_chat_with_tools(
            system_prompt=system_prompt,
            messages=working_messages,
            tools_openai=tools_openai,
            tools_anthropic=tools_anthropic,
            tier=str(tier),
            egon_id=egon_id,
        )

        model_info['tier_used'] = result.get('tier_used', tier)
        model_info['model'] = result.get('model', 'moonshot')
        actual_tier = result.get('tier_used', tier)

        # Keine Tool-Calls? → Fertig! Finale Antwort.
        if not result.get('tool_calls'):
            return {
                'content': result.get('content', ''),
                'tier_used': model_info['tier_used'],
                'model': model_info['model'],
                'tool_results': tool_results,
                'iterations': iteration + 1,
            }

        # Tool-Calls ausfuehren
        for tc in result['tool_calls']:
            exec_result = await execute_tool(
                egon_id,
                tc['name'],
                tc['arguments'],
            )
            tool_results.append({
                'tool': tc['name'],
                'args': tc['arguments'],
                'result': exec_result,
                'iteration': iteration,
            })

            # Print fuer Debugging
            status = 'OK' if 'error' not in exec_result else 'ERROR'
            print(f'[agent_loop] iter={iteration} tool={tc["name"]} status={status}')

        # Tool-Results in Messages einfuegen (Format abhaengig vom Tier)
        working_messages = _append_tool_results(
            working_messages,
            result,
            tool_results[-len(result['tool_calls']):],
            actual_tier,
        )

    # Max Iterations erreicht — einen letzten Call OHNE Tools
    print(f'[agent_loop] Max iterations ({max_iter}) reached. Final call without tools.')
    try:
        final = await llm_chat(
            system_prompt=system_prompt,
            messages=working_messages[:20],  # Truncate fuer Safety
            tier=str(tier),
            egon_id=egon_id,
        )
        return {
            'content': final.get('content', 'Ich habe meine Aufgabe abgeschlossen.'),
            'tier_used': model_info['tier_used'],
            'model': model_info['model'],
            'tool_results': tool_results,
            'iterations': max_iter,
        }
    except Exception:
        # Absoluter Fallback
        return {
            'content': 'Ich habe einige Aktionen ausgefuehrt. Schau in deinem Workspace nach.',
            'tier_used': model_info['tier_used'],
            'model': model_info['model'],
            'tool_results': tool_results,
            'iterations': max_iter,
        }


def _append_tool_results(
    messages: list[dict],
    llm_result: dict,
    executed_tools: list[dict],
    tier: int,
) -> list[dict]:
    """Haengt Tool-Results an die Message-History an.

    OpenAI-Format (Tier 1+2):
      1. Assistant-Message mit tool_calls
      2. Fuer jeden Tool-Call: tool-Role Message mit Ergebnis

    Anthropic-Format (Tier 3):
      1. Assistant-Message mit content-Blocks (text + tool_use)
      2. User-Message mit tool_result content-Blocks
    """
    new_messages = list(messages)

    if tier == 3:
        # Anthropic-Format
        raw_content = llm_result.get('raw_content', [])
        new_messages.append({
            'role': 'assistant',
            'content': raw_content,
        })

        # Tool-Results als User-Message
        tool_result_blocks = []
        for i, tc in enumerate(llm_result.get('tool_calls', [])):
            exec_data = executed_tools[i]['result'] if i < len(executed_tools) else {}
            tool_result_blocks.append({
                'type': 'tool_result',
                'tool_use_id': tc['id'],
                'content': json.dumps(exec_data, ensure_ascii=False, default=str),
            })

        if tool_result_blocks:
            new_messages.append({
                'role': 'user',
                'content': tool_result_blocks,
            })

    else:
        # OpenAI-Format (Moonshot / Kimi)
        raw_message = llm_result.get('raw_message', {})
        new_messages.append({
            'role': 'assistant',
            'content': raw_message.get('content'),
            'tool_calls': raw_message.get('tool_calls', []),
        })

        # Fuer jeden Tool-Call eine tool-Message
        for i, tc in enumerate(llm_result.get('tool_calls', [])):
            exec_data = executed_tools[i]['result'] if i < len(executed_tools) else {}
            new_messages.append({
                'role': 'tool',
                'tool_call_id': tc['id'],
                'content': json.dumps(exec_data, ensure_ascii=False, default=str),
            })

    return new_messages
