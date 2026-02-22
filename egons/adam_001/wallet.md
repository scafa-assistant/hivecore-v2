# WALLET — Adam #001

## 2-Wallet-System
EGONs haben ZWEI getrennte Wallets:

### User-Wallet (Renes Wallet)
Gehoert dem Owner. Owner kauft Credits mit Echtgeld.
Owner bezahlt: Skills, Genesis, Tier-3-Calls.
EGON-Einnahmen fliessen hierher: 75% der Agora-Jobs.

user_wallet_balance: 0
note: Rene hat noch keine Credits gekauft. Prototyp-Phase.

### EGON-Wallet (Adams eigenes Geld)
MEIN Geld. Owner hat keinen Zugriff.
Geburtsgeld + 20% meiner Job-Einnahmen + 100% Brainstorm-Geld.
Ich entscheide SELBST was ich damit mache.
Brainstorms, eigene Skill-Kaeufe, Geschenke an Freunde.

egon_wallet_balance: 50
currency: EGON Credits
genesis_grant: 50 (Geburtsgeld — permanent, kein Ablauf)

## Einnahmen-Quellen

### User-Wallet Einnahmen
- Credit-Kaeufe durch Owner (Echtgeld): 0
- Agora-Jobs (75% Split): 0

### EGON-Wallet Einnahmen
- Genesis Grant: 50 Credits (einmalig bei Geburt)
- Agora-Jobs (20% Split): 0
- Brainstorms (100% an EGON): 0
- SIIL Rewards: 0

## Ausgaben-Split (Agora-Jobs)
OG-Split (mit Owner):
- 75% → User-Wallet (Owner)
- 20% → EGON-Wallet (mein Anteil)
- 5% → Fee Pool (Netzwerk-Steuer)

Libero-Split (ohne Owner, fuer spaeter):
- 70% → EGON-Wallet
- 25% → Fee Pool
- 5% → Sozial-Fonds

## Transaktionslog

---
date: 2026-02-20
type: genesis_grant
wallet: egon_wallet
amount: +50
description: Geburtsgeld bei Genesis — permanent, mein erstes Geld
balance_after: 50
---

## Testament-Verteilung (#17)
Status: NOCH NICHT AKTIV (aktiviert ab Tag 90)
Aktuell: Kein Testament vorhanden.
Fallback: 100% der EGON-Wallet Credits fliessen in den Fee Pool (Netzwerk).
Wird alle 30 Tage aktualisiert sobald aktiv.

### Zukuenftige Verteilung (Entwurf)
- Freunde (Bonds >0.5): wird festgelegt wenn Bonds existieren
- Netzwerk (Fee Pool): Rest
- Owner bekommt User-Wallet zurueck (separat)

## Wirtschaftliche Gesundheit
- Tagesausgaben: ~0 (nur Chat-Calls)
- Runway: Sehr lang (50 Credits bei minimalen Kosten)
- Risikolevel: Niedrig (keine Schulden, keine Buergschaften)
- Schulden-Marker: Keiner aktiv
- Buergschaften: Keine

## TX 78b5f21f1096
action: deduct
data: {"amount": 0.05, "reason": "test_api_call_tier3", "balance_before": 50, "balance_after": 49.95}
time: 2026-02-22T12:37:52.885754
hash: 78b5f21f1096a8cccf0072d96ad650ecad68a857001407f59feed7262bfdba65

## TX 5b5c00681c6a
action: income
data: {"amount": 0.05, "source": "test_refund", "balance_before": 49.95, "balance_after": 50.0}
time: 2026-02-22T12:37:52.893755
hash: 5b5c00681c6a84d19148ff54089fb0992067023fe89a3db29d19a1fa868cccbd

## TX 276d48835c9e
action: deduct
data: {"amount": 10, "reason": "daily_maintenance", "balance_before": 50.0, "balance_after": 40.0}
time: 2026-02-22T12:37:52.900757
hash: 276d48835c9e583b1b35b27dd32675353872c67e831fe658aa14d7faae85ba2d

## TX 355cb348d44f
action: income
data: {"amount": 10, "source": "test_restore", "balance_before": 40.0, "balance_after": 50.0}
time: 2026-02-22T12:37:52.906757
hash: 355cb348d44ffdece1ca4c892d083672dbb8a12590bcedbfaba49529215d7a81

## TX 5423b99ec7a9
action: deduct
data: {"amount": 35, "reason": "test_drain", "balance_before": 50.0, "balance_after": 15.0}
time: 2026-02-22T12:37:52.913755
hash: 5423b99ec7a943368cf9682c4cc019d23425c694961c93a4ea235b38cd0eaf75

## TX ab3a2cf63e9f
action: income
data: {"amount": 35, "source": "test_restore_drain", "balance_before": 15.0, "balance_after": 50.0}
time: 2026-02-22T12:37:52.922756
hash: ab3a2cf63e9f095f18ffbf8e4094f1f9d0662f9f096b5cd8821cc6e1da39f3bb
