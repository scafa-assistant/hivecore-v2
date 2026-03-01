"""Agent Loop — Handlungsschleife fuer EGONs.

Wenn ein EGON Werkzeuge braucht (Dateien erstellen, Web durchsuchen, etc.),
laeuft der Agent Loop:

1. LLM wird mit Tool-Definitionen aufgerufen
2. LLM gibt Tool-Call zurueck
3. Server fuehrt Tool aus
4. Ergebnis geht zurueck an LLM
5. Wiederholen bis LLM fertig ist (max N Iterationen)

Alles laeuft ueber Moonshot (Kimi K2.5).
"""

import json
from llm.router import llm_chat_with_tools, llm_chat
from engine.tool_executor import execute_tool
from engine.tools import get_openai_tools


# Sicherheits-Limits: Wie oft darf der Loop laufen?
MAX_ITERATIONS = 5


async def run_agent_loop(
    egon_id: str,
    system_prompt: str,
    messages: list[dict],
) -> dict:
    """Fuehre den Agent Loop aus.

    Args:
        egon_id: EGON-ID (z.B. 'adam')
        system_prompt: Fertig gebauter System-Prompt
        messages: Chat-History (OpenAI-Format: role/content)

    Returns:
        {
            'content': str,          # Finale Text-Antwort
            'model': str,
            'tool_results': list,    # Alle ausgefuehrten Tools
            'iterations': int,       # Wie viele Runden
        }
    """
    tools_openai = get_openai_tools()

    max_iter = MAX_ITERATIONS
    tool_results = []
    model_info = {'model': 'moonshot'}

    # Arbeits-Kopie der Messages (wir fuegen Tool-Results hinzu)
    working_messages = list(messages)

    for iteration in range(max_iter):
        # LLM-Call mit Tools
        try:
            result = await llm_chat_with_tools(
                system_prompt=system_prompt,
                messages=working_messages,
                tools=tools_openai,
                egon_id=egon_id,
            )
        except Exception as e:
            # API-Fehler (z.B. 400 Bad Request) — graceful fallback
            print(f'[agent_loop] API error in iteration {iteration}: {e}')
            # Wenn wir schon Tool-Results haben, fasse sie zusammen
            if tool_results:
                summary_parts = []
                for tr in tool_results:
                    tool_name = tr['tool']
                    if 'error' in tr['result']:
                        summary_parts.append(f'{tool_name}: Fehler — {tr["result"]["error"]}')
                    else:
                        msg = tr['result'].get('message', tr['result'].get('status', 'OK'))
                        summary_parts.append(f'{tool_name}: {msg}')
                return {
                    'content': 'Erledigt! ' + '; '.join(summary_parts),
                    'model': model_info['model'],
                    'tool_results': tool_results,
                    'iterations': iteration + 1,
                }
            raise  # Kein Fallback moeglich

        model_info['model'] = result.get('model', 'moonshot')

        # Keine Tool-Calls? → Fertig! Finale Antwort.
        if not result.get('tool_calls'):
            return {
                'content': result.get('content', ''),
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

        # Tool-Results in Messages einfuegen
        working_messages = _append_tool_results(
            working_messages,
            result,
            tool_results[-len(result['tool_calls']):],
        )

    # Max Iterations erreicht — einen letzten Call OHNE Tools
    print(f'[agent_loop] Max iterations ({max_iter}) reached. Final call without tools.')
    try:
        final = await llm_chat(
            system_prompt=system_prompt,
            messages=working_messages[:20],  # Truncate fuer Safety
            egon_id=egon_id,
        )
        return {
            'content': final.get('content', 'Ich habe meine Aufgabe abgeschlossen.'),
            'model': model_info['model'],
            'tool_results': tool_results,
            'iterations': max_iter,
        }
    except Exception:
        # Absoluter Fallback
        return {
            'content': 'Ich habe einige Aktionen ausgefuehrt. Schau in deinem Workspace nach.',
            'model': model_info['model'],
            'tool_results': tool_results,
            'iterations': max_iter,
        }


def _append_tool_results(
    messages: list[dict],
    llm_result: dict,
    executed_tools: list[dict],
) -> list[dict]:
    """Haengt Tool-Results an die Message-History an.

    OpenAI-Format (Moonshot / Kimi K2.5):
      1. Assistant-Message mit tool_calls
      2. Fuer jeden Tool-Call: tool-Role Message mit Ergebnis
    """
    new_messages = list(messages)

    if True:
        # OpenAI-Format (Moonshot / Kimi K2.5)
        raw_message = llm_result.get('raw_message', {})

        # WICHTIG: content darf NICHT None sein — Moonshot gibt 400 Bad Request
        # wenn content=null in der History steht. Leerer String ist OK.
        assistant_content = raw_message.get('content') or ''

        # Tool-Calls aus raw_message extrahieren (Original-Format von der API)
        raw_tool_calls = raw_message.get('tool_calls', [])

        assistant_msg = {
            'role': 'assistant',
            'content': assistant_content,
        }
        # tool_calls NUR hinzufuegen wenn vorhanden (manche APIs moegen leere Arrays nicht)
        if raw_tool_calls:
            assistant_msg['tool_calls'] = raw_tool_calls
        new_messages.append(assistant_msg)

        # Fuer jeden Tool-Call eine tool-Message
        for i, tc in enumerate(llm_result.get('tool_calls', [])):
            exec_data = executed_tools[i]['result'] if i < len(executed_tools) else {}
            tool_msg = {
                'role': 'tool',
                'tool_call_id': tc['id'],
                'name': tc['name'],  # Manche APIs brauchen das name-Feld
                'content': json.dumps(exec_data, ensure_ascii=False, default=str),
            }
            new_messages.append(tool_msg)

    return new_messages
