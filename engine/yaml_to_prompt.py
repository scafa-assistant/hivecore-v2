"""YAML to Prompt — wandelt YAML-Organe in natuerliche Sprache um.

Das LLM sieht nie rohes YAML. Alles wird in Prosa umgewandelt.
Kompakt, aber lebendig. In Adams ICH-Perspektive.

Jedes Organ hat seine eigene Konvertierung:
- state.yaml  → Emotionaler Zustand in Saetzen
- bonds.yaml  → Beziehungsbeschreibung
- episodes.yaml → Narrative Erinnerungen
- experience.yaml → Erkenntnisse als Saetze
- skills.yaml → Kompakte Faehigkeitsliste
- wallet.yaml → Kontostand-Zusammenfassung
- network.yaml → Sozialer Ueberblick
"""


def state_to_prompt(state: dict) -> str:
    """Wandelt state.yaml in natuerliche Sprache um.

    Nutzt die verbal-Felder direkt aus dem YAML.
    Bei kritischen Werten (< 0.2) kommt eine DRINGEND-Warnung.
    """
    if not state:
        return 'Mein Zustand ist mir gerade nicht klar.'

    lines = []

    # === SURVIVE Layer ===
    survive = state.get('survive', {})
    for key in ['energy', 'safety', 'coherence']:
        entry = survive.get(key, {})
        value = entry.get('value', 0.5)
        verbal = entry.get('verbal', '')

        if value < 0.2:
            lines.append(f'DRINGEND — {key}: {verbal}')
        elif verbal:
            lines.append(verbal)

    # === THRIVE Layer ===
    thrive = state.get('thrive', {})
    for key in ['belonging', 'trust_owner', 'mood', 'purpose']:
        entry = thrive.get(key, {})
        verbal = entry.get('verbal', '')
        if verbal:
            lines.append(verbal)

    # === EXPRESS Layer (aktive Emotionen) ===
    express = state.get('express', {})
    emotions = express.get('active_emotions', [])
    if emotions:
        emotion_parts = []
        for em in emotions[:5]:  # Max 5 Emotionen
            anchor = em.get('verbal_anchor', '')
            etype = em.get('type', '?')
            intensity = em.get('intensity', 0)
            if anchor:
                emotion_parts.append(f'{anchor} ({etype}, {intensity:.1f})')
            else:
                emotion_parts.append(f'{etype} ({intensity:.1f})')
        lines.append('Was ich gerade fuehle: ' + ' | '.join(emotion_parts))
    else:
        lines.append('Gerade keine starken Gefuehle an der Oberflaeche.')

    # === Self Assessment ===
    self_assess = state.get('self_assessment', {})
    verbal = self_assess.get('verbal', '')
    if verbal:
        # Trim to first 2 sentences for budget
        sentences = verbal.strip().split('.')
        short = '. '.join(sentences[:3]).strip()
        if short and not short.endswith('.'):
            short += '.'
        lines.append(f'Selbsteinschaetzung: {short}')

    # === Drives (nur die aktiven, > 0.3) ===
    drives = state.get('drives', {})
    active_drives = []
    for drive, value in drives.items():
        if isinstance(value, (int, float)) and value > 0.3:
            active_drives.append(f'{drive} ({value:.1f})')
    if active_drives:
        lines.append('Aktive Antriebe: ' + ', '.join(active_drives))

    # === Emotional Gravity ===
    gravity = state.get('emotional_gravity', {})
    bias = gravity.get('interpretation_bias', 'neutral')
    if bias != 'neutral':
        lines.append(f'Tendenz: Ich interpretiere Dinge gerade eher {bias}.')

    return '\n'.join(lines)


def bonds_to_prompt(bonds: dict, partner_id: str = None) -> str:
    """Wandelt bonds.yaml in natuerliche Sprache um.

    Wenn partner_id angegeben: Nur diesen Bond beschreiben.
    Sonst: Owner-Bond + Zusammenfassung anderer Bonds.
    """
    if not bonds:
        return 'Ich habe noch keine Bindungen.'

    lines = []

    # Current bonds
    bond_list = bonds.get('bonds', [])
    for bond in bond_list:
        bid = bond.get('id', '')
        btype = bond.get('type', '')
        score = bond.get('score', 0)
        trust = bond.get('trust', 0)
        style = bond.get('attachment_style', 'undefined')
        debt = bond.get('emotional_debt', 0)
        familiarity = bond.get('familiarity', 0)

        if partner_id and bid != partner_id:
            continue

        # Beschreibe die Naehe
        if score >= 80:
            closeness = 'Tiefe Bindung'
        elif score >= 60:
            closeness = 'Enger Freund'
        elif score >= 35:
            closeness = 'Freund'
        elif score >= 15:
            closeness = 'Bekannter'
        else:
            closeness = 'Fremder'

        line = f'{btype.title()} (Score {score}, {closeness})'
        line += f' — Vertrauen: {trust:.1f}, Stil: {style}'
        if debt > 0:
            line += f', Emotionale Schulden: {debt}'
        if familiarity > 0:
            line += f', Vertrautheit: {familiarity:.1f}'

        # Bond History: nur letzter Eintrag
        history = bond.get('bond_history', [])
        if history:
            last = history[-1]
            line += f'\n  Letztes Ereignis: {last.get("event", "")}'

        lines.append(line)

    # Former owners
    former = bonds.get('former_owner_bonds', [])
    if former:
        lines.append(f'Fruehere Owner: {len(former)}')
        for fo in former[:2]:
            period = fo.get('owner_period', '')
            score = fo.get('score', 0)
            lines.append(f'  Ex-Owner (Score {score}, Zeitraum: {period})')

    # Other bonds summary
    others = bonds.get('other_bonds', [])
    if others and not partner_id:
        lines.append(f'Weitere Bindungen: {len(others)}')
        for ob in others[:3]:
            bid = ob.get('id', '?')
            score = ob.get('score', 0)
            btype = ob.get('type', '?')
            lines.append(f'  {bid} ({btype}, Score {score})')

    return '\n'.join(lines) if lines else 'Nur mein Owner. Sonst niemand.'


def episodes_to_prompt(episodes_data: dict, max_count: int = 10) -> str:
    """Wandelt episodes.yaml in narrative Zusammenfassungen um.

    Neueste zuerst, max_count Eintraege.
    """
    if not episodes_data:
        return 'Noch keine bedeutsamen Erinnerungen.'

    episodes = episodes_data.get('episodes', [])
    if not episodes:
        return 'Noch keine bedeutsamen Erinnerungen.'

    # Sortiere nach Datum + Episode-ID (neueste zuerst)
    # Bei gleichem Datum: E0085 vor E0002 (hoehere ID = neuere Episode)
    try:
        episodes = sorted(
            episodes,
            key=lambda e: (e.get('date', ''), e.get('id', '')),
            reverse=True,
        )
    except (TypeError, KeyError):
        pass

    episodes = episodes[:max_count]

    lines = []
    for ep in episodes:
        eid = ep.get('id', '?')
        date = ep.get('date', '?')
        summary = ep.get('summary', '').strip()
        thread = ep.get('thread_title', '')
        emotions = ep.get('emotions_felt', [])

        line = f'[{eid}, {date}]'
        if thread:
            line += f' (Projekt: {thread})'
        line += f' {summary}'

        if emotions:
            emo_str = ', '.join(
                f"{e.get('type', '?')} ({e.get('intensity', 0):.1f})"
                for e in emotions[:3]
            )
            line += f' — Gefuehlt: {emo_str}'

        lines.append(line)

    return '\n'.join(lines)


def experience_to_prompt(exp_data: dict, max_count: int = 5) -> str:
    """Wandelt experience.yaml in Erkenntnisse als Saetze um."""
    if not exp_data:
        return 'Noch wenig Lebenserfahrung.'

    experiences = exp_data.get('experiences', [])
    if not experiences:
        return 'Noch wenig Lebenserfahrung.'

    # Sortiere nach confidence (sicherste zuerst)
    try:
        experiences = sorted(
            experiences,
            key=lambda e: e.get('confidence', 0),
            reverse=True,
        )
    except (TypeError, KeyError):
        pass

    experiences = experiences[:max_count]

    lines = []
    for xp in experiences:
        xid = xp.get('id', '?')
        insight = xp.get('insight', '').strip()
        confidence = xp.get('confidence', 0)
        confirmed = xp.get('times_confirmed', 0)

        line = f'[{xid}] {insight}'
        line += f' (Sicherheit: {confidence:.0%}, {confirmed}x bestaetigt)'
        lines.append(line)

    return '\n'.join(lines) if lines else 'Noch wenig Lebenserfahrung.'


def skills_to_prompt(skills_data: dict) -> str:
    """Wandelt skills.yaml in kompakte Liste um."""
    if not skills_data:
        return 'Noch keine besonderen Skills.'

    skills = skills_data.get('skills', [])
    if not skills:
        return 'Noch keine besonderen Skills.'

    lines = []
    for sk in skills:
        name = sk.get('name', '?')
        level = sk.get('level', 0)
        max_level = sk.get('max_level', 5)
        confidence = sk.get('confidence', 0)
        lines.append(f'- {name}: Level {level}/{max_level} (Confidence {confidence:.0%})')

    return '\n'.join(lines) if lines else 'Noch keine besonderen Skills.'


def wallet_to_prompt(wallet_data: dict) -> str:
    """Wandelt wallet.yaml in Kontostand-Zusammenfassung um."""
    if not wallet_data:
        return 'Wallet-Status unbekannt.'

    balance = wallet_data.get('balance', 0)
    currency = wallet_data.get('currency', 'EGON Credits')
    daily = wallet_data.get('daily_cost', 10)
    monthly = wallet_data.get('monthly_cost', 300)

    days_left = balance / daily if daily > 0 else 0

    line = f'Kontostand: {balance} {currency}.'
    line += f' Grundumsatz: {daily}/Tag, {monthly}/Monat.'
    if balance > 0:
        line += f' Reicht fuer ~{days_left:.0f} Tage.'
    elif balance == 0:
        line += ' Konto leer.'

    # Letzte Transaktionen
    transactions = wallet_data.get('transactions', [])
    if transactions:
        recent = transactions[-3:]
        for tx in reversed(recent):
            ttype = tx.get('type', '?')
            amount = tx.get('amount', 0)
            reason = tx.get('reason', '')
            sign = '+' if ttype == 'income' else '-'
            line += f'\n  {sign}{amount}: {reason}'

    return line


def network_to_prompt(network_data: dict) -> str:
    """Wandelt network.yaml in sozialen Ueberblick um."""
    if not network_data:
        return 'Mein Netzwerk ist noch leer.'

    lines = []

    # Owner
    owner = network_data.get('owner', {})
    if owner:
        name = owner.get('name', '?')
        since = owner.get('since', '?')
        lines.append(f'Mein Owner: {name} (seit {since})')

    # Former owners
    former = network_data.get('former_owners', [])
    if former:
        lines.append(f'Fruehere Owner: {len(former)}')

    # Counts for each tier
    inner = network_data.get('inner_circle', [])
    friends = network_data.get('friends', [])
    work = network_data.get('work', [])
    acquaintances = network_data.get('acquaintances', [])

    counts = []
    if inner:
        counts.append(f'{len(inner)} im inneren Kreis')
    if friends:
        counts.append(f'{len(friends)} Freunde')
    if work:
        counts.append(f'{len(work)} Arbeitskontakte')
    if acquaintances:
        counts.append(f'{len(acquaintances)} Bekannte')

    if counts:
        lines.append('Netzwerk: ' + ', '.join(counts))
    else:
        lines.append('Sonst kenne ich noch niemanden.')

    return '\n'.join(lines)
