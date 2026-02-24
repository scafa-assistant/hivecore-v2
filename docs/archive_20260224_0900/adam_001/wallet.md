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

## TX 2c81c79ab702
action: daily_pulse
data: {"step": "state_update", "date": "2026-02-20 23:09"}
time: 2026-02-20T23:09:38.433741
hash: 2c81c79ab7029ee208aa3f218bca9cac9b912f356b2d573461ff68dee8fbd3b7

## TX fcee43e05402
action: daily_pulse
data: {"step": "state_update", "date": "2026-02-20 23:09"}
time: 2026-02-20T23:09:53.829754
hash: fcee43e054028c7a60482c17ed4aa53d1f38346f540177863a947578dd494e00

## TX 438a08904312
action: daily_pulse
data: {"step": "state_update", "date": "2026-02-21 08:00"}
time: 2026-02-21T08:00:05.105941
hash: 438a08904312a343f632d95ccae6b14e64e3163c9fcf9777e324463f6a79b9ad

## TX 89f50e82f128
action: daily_pulse
data: {"step": "state_update", "date": "2026-02-22 08:00"}
time: 2026-02-22T08:00:05.020431
hash: 89f50e82f128fe08d70325d4690f13d28e50023576722ad5177fcd19fe70475a

## TX a3a76504bacc
action: daily_pulse
data: {"step": "state_update", "date": "2026-02-23 08:00"}
time: 2026-02-23T08:00:06.197842
hash: a3a76504bacc8d9e270926c6d455c5f42992810296e7608929f78f41125e57d5

## TX 5d5fdc258fb5
action: daily_pulse_v2
data: {"step": "state_update", "date": "2026-02-24 08:00", "hours_since_owner": 23976.0, "daily_maintenance": {"success": true, "skipped": true, "reason": "finances_disabled"}}
time: 2026-02-24T08:00:08.313388
hash: 5d5fdc258fb5bd375f76355263b1bef13ea29d7cc162d78e9a2e69bef673c90b

## TX 5f378753397a
action: daily_pulse_v2
data: {"step": "state_update", "date": "2026-02-24 08:35", "hours_since_owner": 23976.0, "daily_maintenance": {"success": true, "skipped": true, "reason": "finances_disabled"}}
time: 2026-02-24T08:35:09.230660
hash: 5f378753397aef7ab52fb50b2fe2c050144e27be8aaa36c85b46b92983cac7e8

## TX 7931493de93f
action: daily_pulse
data: {"step": "state_update", "date": "2026-02-24 08:37"}
time: 2026-02-24T08:37:05.728208
hash: 7931493de93f0fabd22d3f12b29a57b385ac98f2bce8f962d470f7da202ade37

## TX 4a67544816a9
action: daily_pulse
data: {"step": "state_update", "date": "2026-02-24 08:53"}
time: 2026-02-24T08:53:03.535064
hash: 4a67544816a957fb5ab441bddd531de37d8207032a8aaa03ad4f580b684449dc
