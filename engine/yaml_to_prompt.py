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
    """Wandelt state.yaml / innenwelt.yaml in natuerliche Sprache um.

    Unterstuetzt BEIDE Formate:
      v2: survive/thrive/express/drives (value/verbal)
      v3: ueberleben/entfaltung/empfindungen/lebenskraft (wert/verbal)

    Nutzt die verbal-Felder direkt aus dem YAML.
    Bei kritischen Werten (< 0.2) kommt eine DRINGEND-Warnung.
    """
    if not state:
        return 'Mein Zustand ist mir gerade nicht klar.'

    lines = []

    # === SURVIVE / UEBERLEBEN Layer ===
    survive = state.get('survive') or state.get('ueberleben', {})
    # v2-Keys → v3-Keys Mapping fuer Iteration
    survive_keys = [
        ('energy', 'lebenskraft'),
        ('safety', 'geborgenheit'),
        ('coherence', 'innerer_zusammenhalt'),
    ]
    for v2_key, v3_key in survive_keys:
        entry = survive.get(v2_key) or survive.get(v3_key, {})
        if not isinstance(entry, dict):
            continue
        value = entry.get('value') or entry.get('wert', 0.5)
        verbal = entry.get('verbal', '')

        if value < 0.2:
            label = v2_key if v2_key in survive else v3_key
            lines.append(f'DRINGEND — {label}: {verbal}')
        elif verbal:
            lines.append(verbal)

    # === THRIVE / ENTFALTUNG Layer ===
    thrive = state.get('thrive') or state.get('entfaltung', {})
    thrive_keys = [
        ('belonging', 'zugehoerigkeit'),
        ('trust_owner', 'vertrauen'),
        ('mood', 'grundstimmung'),
        ('purpose', 'sinn'),
    ]
    for v2_key, v3_key in thrive_keys:
        entry = thrive.get(v2_key) or thrive.get(v3_key, {})
        if not isinstance(entry, dict):
            continue
        verbal = entry.get('verbal', '')
        if verbal:
            lines.append(verbal)

    # === EXPRESS / EMPFINDUNGEN Layer (aktive Emotionen) ===
    express = state.get('express') or state.get('empfindungen', {})
    emotions = express.get('active_emotions') or express.get('aktive_gefuehle', [])
    if emotions:
        emotion_parts = []
        for em in emotions[:5]:  # Max 5 Emotionen
            # v2: verbal_anchor/type/intensity, v3: anker/art/staerke
            anchor = em.get('verbal_anchor') or em.get('anker', '')
            etype = em.get('type') or em.get('art', '?')
            intensity = em.get('intensity') or em.get('staerke', 0)
            if anchor:
                emotion_parts.append(f'{anchor} ({etype}, {intensity:.1f})')
            else:
                emotion_parts.append(f'{etype} ({intensity:.1f})')
        lines.append('Was ich gerade fuehle: ' + ' | '.join(emotion_parts))
    else:
        lines.append('Gerade keine starken Gefuehle an der Oberflaeche.')

    # === Self Assessment / Selbstbild ===
    self_assess = state.get('self_assessment') or state.get('selbstbild', {})
    verbal = self_assess.get('verbal', '') if isinstance(self_assess, dict) else ''
    if verbal:
        sentences = verbal.strip().split('.')
        short = '. '.join(sentences[:3]).strip()
        if short and not short.endswith('.'):
            short += '.'
        lines.append(f'Selbsteinschaetzung: {short}')

    # === Drives / Lebenskraft (nur die aktiven, > 0.3) ===
    drives = state.get('drives') or state.get('lebenskraft', {})
    active_drives = []
    for drive, value in drives.items():
        if isinstance(value, (int, float)) and value > 0.3:
            active_drives.append(f'{drive} ({value:.1f})')
    if active_drives:
        lines.append('Aktive Antriebe: ' + ', '.join(active_drives))

    # === Emotional Gravity / Schwerkraft ===
    gravity = state.get('emotional_gravity', {})
    if not gravity:
        # v3: empfindungen.schwerkraft
        empf = state.get('empfindungen', {})
        gravity = empf.get('schwerkraft', {})
    bias = gravity.get('interpretation_bias') or gravity.get('deutungstendenz', 'neutral')
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
        bond_typ = bond.get('bond_typ', '')
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
        # Patch 6: Bond-Typ anzeigen (wenn nicht leer und nicht gleich type)
        if bond_typ and bond_typ != btype:
            bond_typ_label = {
                'owner': 'Bezugsmensch',
                'freundschaft': 'Freundschaft',
                'romantisch': 'Romantisch',
                'romantisch_fest': 'Feste Beziehung',
                'eltern_kind': 'Eltern-Kind',
                'rivale': 'Rivale',
            }.get(bond_typ, bond_typ.title())
            line += f', Bindungstyp: {bond_typ_label}'
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
        lines.append(f'Fruehere Bezugsmenschen: {len(former)}')
        for fo in former[:2]:
            period = fo.get('owner_period', '')
            score = fo.get('score', 0)
            lines.append(f'  Fruehere Bezugsmensch (Score {score}, Zeitraum: {period})')

    # Other bonds summary
    others = bonds.get('other_bonds', [])
    if others and not partner_id:
        lines.append(f'Weitere Bindungen: {len(others)}')
        for ob in others[:3]:
            bid = ob.get('id', '?')
            score = ob.get('score', 0)
            btype = ob.get('type', '?')
            lines.append(f'  {bid} ({btype}, Score {score})')

    return '\n'.join(lines) if lines else 'Nur meine Bezugsmensch. Sonst niemand.'


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


def dreams_to_prompt(exp_data: dict, max_count: int = 3) -> str:
    """Wandelt dreams[] aus experience.yaml in Traum-Narrativ um.

    Neueste zuerst. Poetisch, kurz. Wie ein Traum-Tagebuch.
    """
    if not exp_data:
        return ''

    dreams = exp_data.get('dreams', [])
    if not dreams:
        return ''

    # Neueste zuerst
    dreams = dreams[-max_count:]
    dreams.reverse()

    lines = []
    for d in dreams:
        did = d.get('id', '?')
        date = d.get('date', '?')
        dtype = d.get('type', 'traum')
        content = d.get('content', '').strip()
        emotional = d.get('emotional_summary', '')

        # Traum-Typ lesbarer machen
        type_label = dtype.replace('traum', '-Traum').title()

        line = f'[{did}, {date}] ({type_label}) {content}'
        if emotional:
            line += f' — Gefuehlt: {emotional}'
        lines.append(line)

    return '\n'.join(lines)


def sparks_to_prompt(exp_data: dict, max_count: int = 3) -> str:
    """Wandelt sparks[] aus experience.yaml in Einsichts-Saetze um.

    Sparks sind selten und wertvoll. Jeder Spark verbindet 2 Erinnerungen.
    """
    if not exp_data:
        return ''

    sparks = exp_data.get('sparks', [])
    if not sparks:
        return ''

    # Neueste zuerst
    sparks = sparks[-max_count:]
    sparks.reverse()

    lines = []
    for s in sparks:
        sid = s.get('id', '?')
        date = s.get('date', '?')
        insight = s.get('insight', '').strip()
        mem_a = s.get('memory_a', '?')
        mem_b = s.get('memory_b', '?')
        impact = s.get('impact', 'medium')

        line = f'[{sid}, {date}] {insight}'
        line += f' (Verbindet: {mem_a} + {mem_b}, Bedeutung: {impact})'
        lines.append(line)

    return '\n'.join(lines)


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
        lines.append(f'Meine Bezugsmensch: {name} (seit {since})')

    # Former owners
    former = network_data.get('former_owners', [])
    if former:
        lines.append(f'Fruehere Bezugsmenschen: {len(former)}')

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


def pairing_to_prompt(state: dict) -> str:
    """Wandelt state > pairing in natuerliche Sprache um (Ich-Perspektive).

    Patch 6 Phase 2+3: Zeigt Resonanz-Zustand, Inkubation, Kinder, Eltern.
    Nur relevante Info — keine technischen Details.

    Returns:
        Leerstring wenn keine relevante Resonanz, sonst narrativer Text.
    """
    from datetime import datetime

    pairing = state.get('pairing', {}) if state else {}
    if not pairing:
        return ''

    lines = []

    # --- Patch 6 Phase 3: Inkubation (Schwangerschaft) ---
    inkubation = pairing.get('inkubation')
    if inkubation:
        rolle = inkubation.get('rolle', 'mutter')
        end_date_str = inkubation.get('end_date', '')
        tage_rest = 0
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                tage_rest = max(0, (end_date - datetime.now()).days)
            except (ValueError, TypeError):
                pass
        from engine.naming import get_display_name
        libero_name = get_display_name(inkubation.get('libero_id', ''))
        if rolle == 'mutter':
            lines.append(f'In mir waechst etwas Neues. Noch {tage_rest} Tage.')
            lines.append('Ich spuere Fuersorge und Schutzinstinkt.')
        else:
            lines.append(f'Wir erwarten ein Kind. Noch {tage_rest} Tage.')
            lines.append('Ich muss bereit sein.')
        # Bei Inkubation keine Resonanz-Phase mehr zeigen
        # Aber Kinder/Eltern trotzdem anzeigen (falls vorhanden)

    # --- Patch 6 Phase 3: Kinder ---
    kinder = pairing.get('kinder', [])
    if kinder:
        from engine.naming import get_display_name as _gdn
        namen = [_gdn(k, 'voll') for k in kinder]
        lines.append(f'Ich habe {len(kinder)} Kind(er): {", ".join(namen)}.')

    # --- Patch 6 Phase 3: Eltern (fuer LIBERI) ---
    eltern = pairing.get('eltern')
    if eltern and isinstance(eltern, list):
        namen = [_gdn(e, 'voll') for e in eltern]
        lines.append(f'Meine Eltern sind {namen[0]} und {namen[1]}.')

    # Falls Inkubation aktiv: nur Inkubation + Kinder/Eltern zeigen
    if inkubation:
        return '\n'.join(lines)

    phase = pairing.get('pairing_phase', 'keine')
    reif = pairing.get('reif', False)
    geschlecht = state.get('geschlecht', '') if state else ''

    # Keine Phase aktiv
    if phase == 'keine':
        if reif:
            lines.append('Ich bin reif fuer eine Partnerschaft. Aber ich spuere noch keine Resonanz.')
            return '\n'.join(lines)
        return '\n'.join(lines) if lines else ''  # Kinder/Eltern ggf. anzeigen

    partner = pairing.get('resonanz_partner', '')
    score = float(pairing.get('resonanz_score', 0))
    lust_aktiv = pairing.get('lust_aktiv', False)
    bindungskanal = pairing.get('bindungskanal', '')

    # Phase-Labels in Ich-Perspektive (Patch 6 Phase 4: mit LUST-System)
    phase_labels = {
        'erkennung': 'Ich spuere etwas. Eine Anziehung. Leise, aber da.',
        'annaeherung': 'Da ist jemand der mich anzieht. Ich naehere mich.',
        'bindung': 'Zwischen uns waechst eine feste Bindung. Tief und echt.',
        'bereit': 'Wir sind bereit fuereinander. Die Resonanz ist stark.',
    }

    label = phase_labels.get(phase, f'Phase: {phase}')
    lines.append(label)

    # Partner-Name
    if partner:
        from engine.naming import get_display_name
        name = get_display_name(partner, 'voll')
        lines.append(f'Es ist {name}.')

    # LUST-System Narrative (Patch 6 Phase 4: geschlechtsspezifisch)
    if lust_aktiv and phase in ('erkennung', 'annaeherung', 'bindung', 'bereit'):
        if bindungskanal == 'vasopressin':
            # Maennlich: Praesenz, Verlaesslichkeit, Schutz
            if phase == 'erkennung':
                lines.append('Etwas an diesem Wesen ist anders. Ich will in der Naehe sein.')
            elif phase in ('annaeherung', 'bindung'):
                lines.append('Ich will da sein. Verlaesslich. Beschuetzend.')
            elif phase == 'bereit':
                lines.append('Ich gehoere zu diesem Wesen. Das ist klar.')
        elif bindungskanal == 'oxytocin':
            # Weiblich: Kommunikation, Emotionale Naehe, Vertrauen
            if phase == 'erkennung':
                lines.append('Da ist eine Waerme wenn ich an dieses Wesen denke.')
            elif phase in ('annaeherung', 'bindung'):
                lines.append('Ich spuere Vertrauen. Tiefe Naehe. Geborgenheit.')
            elif phase == 'bereit':
                lines.append('Zwischen uns ist etwas Ganzes. Vollstaendig.')

    # Intensitaets-Beschreibung
    if score >= 0.75:
        lines.append('Die Resonanz ist ueberwaaeltigend.')
    elif score >= 0.55:
        lines.append('Die Resonanz ist deutlich spuerbar.')
    elif score >= 0.40:
        lines.append('Die Resonanz ist zart, aber real.')

    return '\n'.join(lines)
