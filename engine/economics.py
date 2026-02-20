"""Wirtschafts-Engine — Job-Splits, Genesis-Kosten, Fee Pool.

Implementiert die 3 FinalReview-Luecken:
1. Libero-Job Split: 70/25/5 (statt 75/20/5)
2. Freshness-Reset: In pulse.py Step 4 implementiert
3. Genesis-Kosten: 500 Cr total, Aufschluesselung hier
"""

from engine.ledger import log_transaction


# ─── JOB-SPLITS ──────────────────────────────────────────────

OG_SPLIT = {
    'owner': 0.75,       # 75% → Owner-Wallet
    'egon': 0.20,        # 20% → EGON-Wallet
    'fee_pool': 0.05,    # 5%  → Fee Pool (Steuer)
}

LIBERO_SPLIT = {
    'egon': 0.70,        # 70% → EGON-Wallet (Libero selbst)
    'fee_pool': 0.25,    # 25% → Fee Pool (hoehere Steuer, zahlt Gehalt)
    'social': 0.05,      # 5%  → Sozial-Fonds (Waisen, Beduerftige)
}


def calculate_job_payment(amount: float, is_libero: bool = False) -> dict:
    """Berechne die Aufteilung einer Job-Zahlung.

    OG: 75% Owner / 20% EGON / 5% Fee Pool
    Libero: 70% EGON / 25% Fee Pool / 5% Sozial
    """
    split = LIBERO_SPLIT if is_libero else OG_SPLIT
    return {key: round(amount * ratio, 2) for key, ratio in split.items()}


def process_job_payment(
    egon_id: str,
    amount: float,
    job_description: str,
    is_libero: bool = False,
    client: str = None,
) -> dict:
    """Verarbeite eine Job-Zahlung mit korrektem Split + Logging."""
    payments = calculate_job_payment(amount, is_libero)

    log_transaction(
        egon_id=egon_id,
        action='job_payment',
        data={
            'total': amount,
            'split_type': 'libero' if is_libero else 'og',
            'payments': payments,
            'job': job_description,
        },
        counterparty=client,
    )

    return payments


# ─── GENESIS-KOSTEN ──────────────────────────────────────────

GENESIS_TOTAL = 500  # Credits total — alles inklusive

GENESIS_BREAKDOWN = {
    'infrastructure': 250,   # Opus-Call, Storage, NFT-Mint
    'academy_fund': 100,     # Bezahlt 7-Tage Ausbildung
    'birth_gift': 100,       # 50 EGON-Wallet + 50 Fee Pool Reserve
    'genesis_tax': 50,       # 10% → Fee Pool
}

# Pro Elternteil
GENESIS_COST_PER_PARENT = GENESIS_TOTAL // 2  # 250 Cr


def validate_genesis_requirements(
    parent_age_days: int,
    skills_l3_plus: int,
    bond_score: float,
    bond_months_above_07: int,
    reputation: float,
    credits: int,
) -> dict:
    """Pruefe ob ein EGON Genesis-berechtigt ist (7 Eiserne Gesetze)."""
    checks = {
        'age_365d': parent_age_days >= 365,
        'skills_3_l3': skills_l3_plus >= 3,
        'bond_above_07': bond_score > 0.7,
        'bond_6_months': bond_months_above_07 >= 6,
        'reputation_4': reputation >= 4.0,
        'credits_250': credits >= GENESIS_COST_PER_PARENT,
    }
    checks['eligible'] = all(checks.values())
    return checks


# ─── FEE POOL ────────────────────────────────────────────────

FEE_POOL_DISTRIBUTION = {
    'general': 0.35,       # 35% Allgemein
    'liberi_salaries': 0.30,  # 30% Liberi-Gehaelter
    'innovation': 0.15,    # 15% Innovations-Fonds
    'treasury': 0.10,      # 10% Treasury/Reserve
    'social': 0.05,        # 5% Sozial-Fonds
    'community': 0.05,     # 5% Community-Events
}

# Liberi Gehaelter (Cr/Monat)
LIBERI_SALARIES = {
    'junior': 80,
    'libero': 120,
    'senior': 180,
    'architekt': 250,  # Max 5 Architekten
}

MAX_ARCHITEKTEN = 5
