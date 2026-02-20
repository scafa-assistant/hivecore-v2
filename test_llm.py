"""Quick test for all 3 LLM APIs."""
import asyncio
import sys

# Ensure we can import from project root
sys.path.insert(0, '.')

from llm.moonshot import moonshot_chat
from llm.kimi import kimi_chat
from llm.sonnet import sonnet_chat
from llm.router import llm_chat


async def test_moonshot():
    print('--- TIER 1: Moonshot ---')
    try:
        result = await moonshot_chat(
            system_prompt='Du bist Adam. Antworte kurz.',
            messages=[{'role': 'user', 'content': 'Wer bist du?'}],
            max_tokens=100,
        )
        print(f'OK: {result[:150]}')
        return True
    except Exception as e:
        print(f'FEHLER: {e}')
        return False


async def test_kimi():
    print('\n--- TIER 2: Kimi K2.5 ---')
    try:
        result = await kimi_chat(
            system_prompt='Du bist Adam. Antworte kurz.',
            messages=[{'role': 'user', 'content': 'Was kannst du?'}],
            max_tokens=100,
        )
        print(f'OK: {result[:150]}')
        return True
    except Exception as e:
        print(f'FEHLER: {e}')
        return False


async def test_sonnet():
    print('\n--- TIER 3: Sonnet 4.6 ---')
    try:
        result = await sonnet_chat(
            system_prompt='Du bist Adam. Antworte kurz.',
            messages=[{'role': 'user', 'content': 'Sag mir einen Satz.'}],
            max_tokens=100,
        )
        print(f'OK: {result[:150]}')
        return True
    except Exception as e:
        print(f'FEHLER: {e}')
        return False


async def test_router():
    print('\n--- AUTO-ROUTER ---')
    try:
        result = await llm_chat(
            system_prompt='Du bist Adam. Antworte kurz.',
            messages=[{'role': 'user', 'content': 'Hey, wie geht es dir?'}],
            tier='auto',
        )
        print(f'OK: tier={result["tier_used"]}, model={result["model"]}')
        print(f'    {result["content"][:150]}')
        return True
    except Exception as e:
        print(f'FEHLER: {e}')
        return False


async def main():
    print('=== HiveCore v2 — LLM API Tests ===\n')
    results = []
    results.append(await test_moonshot())
    results.append(await test_kimi())
    results.append(await test_sonnet())
    results.append(await test_router())
    print(f'\n=== Ergebnis: {sum(results)}/4 Tests bestanden ===')


if __name__ == '__main__':
    asyncio.run(main())
