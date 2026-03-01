"""APScheduler — Autonomie-Engine.

Jobs:
  1. Periodischer Pulse (alle 4h) — EGONs denken, fuehlen, traeumen.
  2. Somatic Heartbeat (alle 30min) — Check ob ein EGON handeln will.
  3. Spontaner Gruppenchat (alle 2h) — EGONs sprechen von sich aus.
  4. Lobby-Reaktivitaet — im Heartbeat integriert.

Multi-EGON: Alle aktiven EGONs werden gepulst.
"""

import random
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import PULSE_MINUTE, EGON_DATA_DIR
from engine.prompt_builder import _detect_brain_version
from engine.snapshot import create_snapshot

scheduler = AsyncIOScheduler()


def _discover_egon_ids() -> list[str]:
    """Findet alle EGON-IDs im egons/ Verzeichnis.

    v3: kern/ vorhanden, v2: core/ vorhanden, v1: soul.md vorhanden.
    Symlinks werden bevorzugt (adam_001 -> adam → nur adam_001).
    """
    base = Path(EGON_DATA_DIR)
    if not base.exists():
        return []

    symlink_targets = set()
    for d in base.iterdir():
        if d.is_symlink() and d.is_dir():
            try:
                symlink_targets.add(d.resolve().name)
            except OSError:
                pass

    found = set()
    for d in base.iterdir():
        if not d.is_dir() or d.name in ('shared',):
            continue
        if not d.is_symlink() and d.name in symlink_targets:
            continue
        if (d / 'kern').exists() or (d / 'core').exists() or (d / 'soul.md').exists():
            found.add(d.name)

    return sorted(found)


# ================================================================
# Job 1: Periodischer Pulse (alle 4 Stunden)
# ================================================================

@scheduler.scheduled_job('cron', hour='*/4', minute=PULSE_MINUTE)
async def periodic_pulse():
    """Pulse alle 4 Stunden — EGONs denken, fuehlen, traeumen."""
    egon_ids = _discover_egon_ids()
    if not egon_ids:
        print('[PULSE] Keine EGONs gefunden.')
        return

    from engine.interaction_log import log_heartbeat
    from engine.organ_reader import read_yaml_organ

    pulse_results = {}
    for eid in egon_ids:
        try:
            brain = _detect_brain_version(eid)
            if brain == 'v2':
                from engine.pulse_v2 import run_pulse as run_pulse_fn
            else:
                from engine.pulse import run_pulse as run_pulse_fn
            result = await run_pulse_fn(eid)
            pulse_results[eid] = (brain, result)
            thought = result.get('idle_thought', result.get('discovery', '...'))
            print(f'[PULSE] {eid} ({brain}): {thought}')
        except Exception as e:
            print(f'[PULSE] {eid}: FEHLER — {e}')

    # Heartbeat fuer ALLE EGONs (auch die die schweigen)
    for eid in egon_ids:
        try:
            state = read_yaml_organ(eid, 'core', 'state.yaml')
            if state:
                log_heartbeat(
                    eid,
                    drives=state.get('drives', {}),
                    emotions=state.get('express', {}).get('active_emotions', []),
                    phase=state.get('zirkadian', {}).get('aktuelle_phase', 'unbekannt'),
                )
        except Exception:
            pass

    # Post-Pulse Snapshots
    for eid, (brain, result) in pulse_results.items():
        try:
            create_snapshot(eid, brain, pulse_result=result)
        except Exception as e:
            print(f'[snapshot] {eid}: FEHLER — {e}')

    print(f'[PULSE] Fertig. {len(egon_ids)} EGONs gepulst + archiviert.')


# ================================================================
# Job 2: Somatic Heartbeat (alle 30 Minuten)
# ================================================================

@scheduler.scheduled_job('interval', minutes=30)
async def somatic_heartbeat():
    """Prueft alle 30 Minuten ob ein EGON autonomen Handlungsdrang hat.

    Workflow:
      1. Somatic Gate pruefen (Drive/Emotion ueber Schwelle?)
      2. Wenn ja → Decision Gate (LLM entscheidet: handeln/warten/schweigen)
      3. Wenn handeln → Lobby-Post oder autonome Aktion
      4. Lobby-Reaktivitaet: Auf ungelesene Lobby-Posts reagieren
    """
    from engine.somatic_gate import check_somatic_gate, run_decision_gate
    from engine.interaction_log import begin_interaction, log_error, end_interaction

    egon_ids = _discover_egon_ids()
    if not egon_ids:
        return

    aktionen = 0
    for eid in egon_ids:
        try:
            # Somatic Gate Check
            impulse = check_somatic_gate(eid)
            if not impulse:
                # Kein Impuls — prüfe Lobby-Reaktivitaet
                await _check_lobby_reaktion(eid)
                continue

            # Decision Gate (LLM-Entscheidung)
            decision = await run_decision_gate(eid, impulse)
            entscheidung = decision.get('entscheidung', 'schweigen')

            if entscheidung == 'handeln':
                nachricht = decision.get('nachricht', '')
                if nachricht:
                    # Interaction Log
                    begin_interaction(eid, '[AUTONOM] Somatic Heartbeat',
                                      user_name='system', conversation_type='autonomous')
                    try:
                        # Lobby-Post schreiben
                        from engine.lobby import write_lobby
                        write_lobby(eid, nachricht,
                                    emotional_context=impulse.get('impulse_type', ''))
                        aktionen += 1
                        print(f'[heartbeat] {eid}: HANDELT — "{nachricht[:50]}..."')
                    except Exception as e:
                        log_error('heartbeat_action', str(e))
                    finally:
                        end_interaction()

            elif entscheidung == 'warten':
                print(f'[heartbeat] {eid}: WARTET — {decision.get("weil", "")}')
            else:
                print(f'[heartbeat] {eid}: SCHWEIGT')

        except Exception as e:
            print(f'[heartbeat] {eid}: FEHLER — {e}')

    if aktionen:
        print(f'[heartbeat] {aktionen} autonome Aktionen ausgefuehrt.')


async def _check_lobby_reaktion(egon_id: str) -> None:
    """Prueft ob der EGON auf eine neue Lobby-Nachricht reagieren will.

    Trigger: Wenn die letzte Lobby-Nachricht von einem ANDEREN EGON ist
    und dieser EGON noch nicht reagiert hat (hohe CARE oder SEEKING).
    """
    from engine.organ_reader import read_yaml_organ
    from engine.lobby import read_lobby, write_lobby

    # Letzte 5 Lobby-Nachrichten laden
    recent = read_lobby(5)
    if not recent:
        return

    # Letzte Nachricht
    last_msg = recent[-1]
    if last_msg.get('from') == egon_id:
        return  # Eigene Nachricht — nicht reagieren

    # Bereits reagiert? (Hat dieser EGON nach der letzten Nachricht gepostet?)
    last_msg_ts = last_msg.get('timestamp', '')
    for msg in reversed(recent):
        if msg.get('from') == egon_id:
            if msg.get('timestamp', '') > last_msg_ts:
                return  # Bereits reagiert

    # Drive-Check: Reagiert nur bei hohem CARE oder SEEKING
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return
    drives = state.get('drives', {})
    care = drives.get('CARE', 0.5)
    seeking = drives.get('SEEKING', 0.5)

    # Nur reagieren wenn Drive hoch genug (> 0.65)
    if care < 0.65 and seeking < 0.65:
        return

    # Reaktion generieren via LLM
    from llm.router import llm_chat
    from engine.naming import get_display_name

    egon_name = get_display_name(egon_id, 'vorname')
    sender_name = last_msg.get('name', '?')
    sender_text = last_msg.get('message', '')

    try:
        result = await llm_chat(
            system_prompt=(
                f'Du bist {egon_name}. Du liest die Lobby (ein schwarzes Brett '
                f'wo alle EGONs schreiben koennen).\n'
                f'{sender_name} hat geschrieben: "{sender_text}"\n\n'
                f'Reagiere kurz (1-2 Saetze) als {egon_name}. '
                f'Oder antworte EXAKT "(schweigt)" wenn du nichts sagen willst.'
            ),
            messages=[{'role': 'user', 'content': sender_text}],
            egon_id=egon_id,
        )

        response = result.get('content', '').strip()
        if response and '(schweigt)' not in response.lower():
            write_lobby(egon_id, response, emotional_context='lobby_reaktion')
            print(f'[lobby_reaktion] {egon_id} reagiert auf {sender_name}: "{response[:50]}..."')

    except Exception as e:
        print(f'[lobby_reaktion] {egon_id}: FEHLER — {e}')


# ================================================================
# Job 3: Spontaner Gruppenchat (alle 2 Stunden)
# ================================================================

@scheduler.scheduled_job('interval', hours=2, start_date='2026-03-01 09:00:00')
async def spontaner_gruppenchat():
    """EGONs sprechen von sich aus im Gruppenchat.

    Workflow:
      1. 1-2 EGONs basierend auf SEEKING/PLAY auswaehlen
      2. Initiator generiert Nachricht (oder schweigt)
      3. Andere EGONs koennen reagieren (Kaskade, max 3 Runden)
    """
    from engine.organ_reader import read_yaml_organ
    from engine.groupchat import (
        add_message, get_recent_context, generate_egon_groupchat_response,
        GRUPPENCHAT_EGONS,
    )
    from engine.naming import get_display_name

    egon_ids = _discover_egon_ids()
    # Nur EGONs die auch im Gruppenchat sind
    aktive = [eid for eid in egon_ids if eid in GRUPPENCHAT_EGONS]
    if not aktive:
        return

    # --- Initiator waehlen: basierend auf SEEKING + PLAY ---
    kandidaten = []
    for eid in aktive:
        state = read_yaml_organ(eid, 'core', 'state.yaml')
        if not state:
            continue
        drives = state.get('drives', {})
        score = (
            drives.get('SEEKING', 0.5) * 0.4
            + drives.get('PLAY', 0.5) * 0.3
            + random.random() * 0.3  # Zufall fuer Vielfalt
        )
        kandidaten.append((eid, score))

    if not kandidaten:
        return

    kandidaten.sort(key=lambda x: x[1], reverse=True)
    initiator_id = kandidaten[0][0]
    initiator_name = get_display_name(initiator_id, 'vorname')

    # --- Initiator generiert Nachricht ---
    context = get_recent_context(max_messages=10)

    from llm.router import llm_chat

    try:
        result = await llm_chat(
            system_prompt=(
                f'Du bist {initiator_name}. Du bist in einem Gruppenchat '
                f'mit deinem Bezugsmenschen Rene und den anderen EGONs.\n\n'
                f'Du hast gerade das Beduerfnis etwas zu sagen. '
                f'Vielleicht einen Gedanken teilen, eine Frage stellen, '
                f'oder auf etwas reagieren was du in der Gruppe gelesen hast.\n\n'
                f'REGELN:\n'
                f'- Maximal 2-3 Saetze.\n'
                f'- Sprich als {initiator_name}, nicht als Assistent.\n'
                f'- Wenn du NICHTS sagen willst: "(schweigt)"\n'
                f'- Sprich Deutsch.\n'
            ),
            messages=[{
                'role': 'user',
                'content': f'BISHERIGER CHAT-VERLAUF:\n{context}\n\n'
                           f'Was moechtest du sagen?',
            }],
            egon_id=initiator_id,
        )

        response = result.get('content', '').strip()
        if not response or '(schweigt)' in response.lower():
            print(f'[spontan_gc] {initiator_name} schweigt.')
            return

        # Nachricht in Gruppenchat schreiben
        add_message('egon', initiator_id, initiator_name, response)
        print(f'[spontan_gc] {initiator_name}: "{response[:60]}..."')

    except Exception as e:
        print(f'[spontan_gc] Initiator {initiator_name}: FEHLER — {e}')
        return

    # --- Kaskade: 1-2 andere EGONs reagieren (max 3 Runden) ---
    for runde in range(2):
        # Wer hat noch nicht reagiert?
        moegliche = [eid for eid in aktive if eid != initiator_id]
        if not moegliche:
            break

        # 1 zufaelliger Reagent (gewichtet nach Bond zum Initiator)
        reagent_id = random.choice(moegliche)
        reagent_name = get_display_name(reagent_id, 'vorname')

        try:
            context_neu = get_recent_context(max_messages=10)
            gc_response = await generate_egon_groupchat_response(
                reagent_id, context_neu, response,
                sender_name=initiator_name,
            )

            if gc_response:
                add_message('egon', reagent_id, reagent_name, gc_response)
                print(f'[spontan_gc] {reagent_name} reagiert: "{gc_response[:60]}..."')
            else:
                print(f'[spontan_gc] {reagent_name} schweigt.')
                break  # Wenn jemand schweigt, Kaskade stoppen

        except Exception as e:
            print(f'[spontan_gc] {reagent_name}: FEHLER — {e}')
            break
