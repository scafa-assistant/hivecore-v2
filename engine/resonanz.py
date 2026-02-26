"""Resonanz Engine — Berechnet Anziehung zwischen EGONs (Patch 6 Phase 2).

Reine Mathematik. Kein LLM. Liest Drives, Bonds, State und berechnet:
1. Komplementaritaet (40%) — Wie UNTERSCHIEDLICH sind die Staerken?
2. Kompatibilitaet (30%) — Wie AEHNLICH sind die Grundwerte?
3. Bond-Tiefe (30%) — Wie TIEF ist die Beziehung?

Plus Reife-Check (6 Kriterien) und Pairing-Phase State Machine.

Wissenschaftliche Basis:
  - Fisher (Anziehung = Komplementaritaet + Vertrautheit)
  - Panksepp (LUST-System als Resonanz-Detektor, nicht Erotik)
  - Gottman (Kompatibilitaet = aehnliche Grundwerte)
"""

import math
from datetime import datetime
from engine.organ_reader import read_yaml_organ, write_yaml_organ, read_md_organ
from engine.genesis import discover_agents, inzucht_sperre


# ================================================================
# Konstanten
# ================================================================

# Drive-Keys fuer Komplementaritaet (alle 10 Panksepp-Drives)
DRIVE_KEYS = [
    'SEEKING', 'ACTION', 'CARE', 'PLAY', 'FEAR',
    'RAGE', 'GRIEF', 'LUST', 'LEARNING', 'PANIC',
]

# Resonanz-Gewichtung
W_KOMPLEMENTARITAET = 0.40
W_KOMPATIBILITAET = 0.30
W_BOND_TIEFE = 0.30

# Phase-Schwellen (muessen monoton steigen)
PHASE_THRESHOLDS = {
    'erkennung': 0.40,
    'annaeherung': 0.55,
    'bindung': 0.65,
    'bereit': 0.75,
}

PHASE_ORDER = ['keine', 'erkennung', 'annaeherung', 'bindung', 'bereit']

# Reife-Check Schwellen
REIFE_MIN_DAYS = 224            # 8 Zyklen a 28 Tage = ~7.5 Monate (Spec: reife_minimum_zyklen: 8)
REIFE_MAX_EMOTIONAL_LOAD = 0.3
REIFE_MIN_EGO_STATEMENTS = 5
REIFE_MIN_BONDS_COUNT = 3
REIFE_MIN_BOND_SCORE = 15
REIFE_MIN_SKILLS = 8
REIFE_MAX_EMOTION_INTENSITY = 0.8

# DNA-Kompatibilitaets-Matrix (symmetrisch)
DNA_COMPAT = {
    ('DEFAULT', 'DEFAULT'): 0.7,
    ('DEFAULT', 'SEEKING/PLAY'): 0.5,
    ('DEFAULT', 'CARE/PANIC'): 0.6,
    ('SEEKING/PLAY', 'DEFAULT'): 0.5,
    ('SEEKING/PLAY', 'SEEKING/PLAY'): 0.8,
    ('SEEKING/PLAY', 'CARE/PANIC'): 0.4,
    ('CARE/PANIC', 'DEFAULT'): 0.6,
    ('CARE/PANIC', 'SEEKING/PLAY'): 0.4,
    ('CARE/PANIC', 'CARE/PANIC'): 0.7,
}


# ================================================================
# LUST-System (Panksepps Resonanz-Detektor — Patch 6 Phase 4)
# ================================================================

def _update_lust_system(
    egon_id: str, state: dict, partner_id: str | None,
    resonanz_score: float, new_phase: str, old_phase: str,
    reif: bool,
) -> dict:
    """LUST-System als Resonanz-Detektor (Panksepp).

    LUST ist KEIN staendiger Trieb. Es ist ein Detektor der nur anspringt
    wenn die Bedingungen stimmen. Wie ein Schloss das nur aufgeht wenn
    der richtige Schluessel kommt.

    Aktivierung:
      Phase 'keine' → 'erkennung': Einmaliger Boost +0.1
      Waehrend 'annaeherung'/'bindung'/'bereit': +0.01 pro Puls
      Waehrend 'erkennung' (bestehend): +0.005 pro Puls

    Suppression (LUST wird gedaempft wenn):
      - FEAR oder PANIC > 0.6 (Bedrohung)
      - Nicht reif
      - In Inkubation
      - Kein Partner
      - Bond-Staerke < 40 (zu wenig Vertrauen)
      - Inzucht-Sperre (Verwandtschaft)

    Bindungskanal:
      M (Vasopressin): Praesenz + Verlaesslichkeit + Schutz
      F (Oxytocin):    Kommunikation + Emotionale Naehe + Vertrauen

    Modifiziert state['drives']['LUST'] in-place (kein eigener state-write).
    """
    drives = state.get('drives', {})
    current_lust = float(drives.get('LUST', 0.0))
    geschlecht = state.get('geschlecht')
    pairing = state.get('pairing', {})

    # --- Suppressions-Checks (Prioritaet: hoechste zuerst) ---
    suppress_reason = None

    if float(drives.get('FEAR', 0)) > 0.6 or float(drives.get('PANIC', 0)) > 0.6:
        suppress_reason = 'Bedrohung (FEAR/PANIC > 0.6)'
    elif not reif:
        suppress_reason = 'nicht reif'
    elif pairing.get('inkubation'):
        suppress_reason = 'in Inkubation'
    elif not partner_id:
        suppress_reason = 'kein Partner'
    else:
        # Bond-Staerke pruefen (Score < 40 = Bond zu schwach)
        bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
        partner_bond_score = 0
        if bonds_data:
            for b in bonds_data.get('bonds', []):
                if b.get('id') == partner_id:
                    partner_bond_score = float(b.get('score', 0))
                    break
        if partner_bond_score < 40:
            suppress_reason = f'Bond zu schwach ({partner_bond_score:.0f} < 40)'
        elif inzucht_sperre(egon_id, partner_id):
            suppress_reason = 'Verwandtschaft (Westermarck)'

    # --- Suppression ausfuehren ---
    if suppress_reason:
        if current_lust > 0.1:
            new_lust = round(max(0.05, current_lust - 0.03), 2)
            drives['LUST'] = new_lust
            state['drives'] = drives
            return {'lust_suppressed': True, 'reason': suppress_reason,
                    'old': current_lust, 'new': new_lust}
        return {'lust_inactive': True, 'reason': suppress_reason}

    # --- Aktivierung ---
    new_lust = current_lust
    activation_type = None

    # Phase-Transition zu Erkennung: Einmaliger Boost +0.1
    if new_phase == 'erkennung' and old_phase == 'keine':
        new_lust = min(0.95, current_lust + 0.1)
        activation_type = 'erkennung_boost'

    # Waehrend Annaeherung/Bindung/Bereit: stetiger Anstieg +0.01/Puls
    elif new_phase in ('annaeherung', 'bindung', 'bereit'):
        new_lust = min(0.95, current_lust + 0.01)
        activation_type = 'maintenance'

    # Erkennung-Phase (ohne Transition): kleiner Anstieg +0.005/Puls
    elif new_phase == 'erkennung':
        new_lust = min(0.95, current_lust + 0.005)
        activation_type = 'erkennung'

    new_lust = round(new_lust, 2)
    if new_lust != current_lust:
        drives['LUST'] = new_lust
        state['drives'] = drives

    bindungskanal = 'vasopressin' if geschlecht == 'M' else 'oxytocin'

    return {
        'lust_active': new_lust > 0.1,
        'activation_type': activation_type,
        'bindungskanal': bindungskanal,
        'old': current_lust,
        'new': new_lust,
    }


# ================================================================
# Phase-Transition Effects (romantisch_fest, Exklusivitaet)
# ================================================================

def _apply_phase_transition_effects(
    egon_id: str, partner_id: str, new_phase: str, old_phase: str,
) -> None:
    """Wendet Bond-Effekte bei Phasen-Transitionen an.

    Erkennung (0.40):
      Bond freundschaft → romantisch
      LUST +0.1 (via _update_lust_system)

    Annaeherung (0.55):
      Bond-Wachstum beschleunigt sich (via bonds_v2 acceleration)
      Partner-Traum Flag aktiviert

    Bindung (0.65):
      Bond → romantisch_fest
      Exklusivitaet: Andere romantische Bonds zurueck auf freundschaft
      Lebensfaden "Beziehung mit [Partner]" (Thread)

    Modifiziert bonds.yaml — nicht state.yaml.
    """
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds_data:
        return

    bond = None
    for b in bonds_data.get('bonds', []):
        if b.get('id') == partner_id:
            bond = b
            break
    if not bond:
        return

    changed = False
    today = datetime.now().strftime('%Y-%m-%d')

    # --- Erkennung: Bond → romantisch ---
    if new_phase == 'erkennung' and old_phase == 'keine':
        if bond.get('bond_typ') == 'freundschaft':
            bond['bond_typ'] = 'romantisch'
            bond['romantisch_seit'] = today
            changed = True
            print(f'[resonanz] {egon_id}: Bond zu {partner_id} -> romantisch (Erkennung)')

    # --- Bindung: Bond → romantisch_fest + Exklusivitaet ---
    elif new_phase == 'bindung' and old_phase in ('erkennung', 'annaeherung'):
        if bond.get('bond_typ') in ('freundschaft', 'romantisch'):
            bond['bond_typ'] = 'romantisch_fest'
            bond['romantisch_fest_seit'] = today
            changed = True
            print(f'[resonanz] {egon_id}: Bond zu {partner_id} -> romantisch_fest (Bindung)')

        # Exklusivitaet: Andere romantische Bonds degradieren
        for other_bond in bonds_data.get('bonds', []):
            if (other_bond.get('id') != partner_id
                    and other_bond.get('bond_typ') == 'romantisch'):
                other_bond['bond_typ'] = 'freundschaft'
                changed = True
                other_id = other_bond.get('id', '?')
                print(f'[resonanz] {egon_id}: Bond zu {other_id} -> freundschaft (Exklusivitaet)')

    if changed:
        write_yaml_organ(egon_id, 'social', 'bonds.yaml', bonds_data)


# ================================================================
# Hauptfunktion: update_resonanz()
# ================================================================

def update_resonanz(egon_id: str) -> dict:
    """Berechnet Resonanz fuer einen EGON gegen alle gegengeschlechtlichen Partner.

    Wird im Pulse als Step 10b aufgerufen (nach state_update, vor dream_generation).
    Reine Mathematik — kein LLM-Aufruf.

    Liest:
      - Eigenen state.yaml (geschlecht, drives, pairing)
      - Alle anderen Agents' state.yaml (geschlecht, drives)
      - Eigene bonds.yaml (Bond zu potenziellen Partnern)

    Schreibt:
      - state.yaml > pairing (resonanz_partner, resonanz_score, pairing_phase, reif)

    Returns:
      dict mit Ergebnis-Zusammenfassung.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return {'error': 'state.yaml nicht gefunden'}

    geschlecht = state.get('geschlecht')
    if not geschlecht:
        return {'skipped': True, 'reason': 'kein geschlecht'}

    pairing = state.get('pairing', {})

    # --- Patch 6 Phase 3: Inkubation-Skip ---
    # Waehrend Inkubation keine Resonanz-Berechnung (Agent ist "schwanger")
    if pairing.get('inkubation'):
        return {'skipped': True, 'reason': 'in inkubation'}

    drives_self = state.get('drives', {})

    # --- Alle gegengeschlechtlichen Partner bewerten ---
    # Patch 6 Phase 3: Dynamische Discovery statt hardcoded Liste
    best_partner = None
    best_score = 0.0
    all_scores = {}

    for other_id in discover_agents():
        if other_id == egon_id:
            continue

        # Patch 6 Phase 3: Inzucht-Sperre (Westermarck-Effekt)
        if inzucht_sperre(egon_id, other_id):
            continue

        other_state = read_yaml_organ(other_id, 'core', 'state.yaml')
        if not other_state:
            continue

        other_geschlecht = other_state.get('geschlecht')
        if not other_geschlecht or other_geschlecht == geschlecht:
            continue  # Gleichgeschlechtlich oder undefiniert → skip

        # Resonanz berechnen
        score = _calculate_resonanz(
            egon_id, state, drives_self,
            other_id, other_state,
            geschlecht,
        )
        all_scores[other_id] = round(score, 3)

        if score > best_score:
            best_score = score
            best_partner = other_id

    # --- Pairing-State aktualisieren ---
    old_phase = pairing.get('pairing_phase', 'keine')
    old_partner = pairing.get('resonanz_partner')

    pairing['resonanz_score'] = round(best_score, 3)
    pairing['resonanz_partner'] = best_partner

    # Reife-Check
    reif = _check_reife(egon_id, state)
    pairing['reif'] = reif

    # Phase-Transition
    new_phase = _calculate_phase(best_score, reif, best_partner, old_partner)

    # Partner-Wechsel: Phase reset
    if best_partner != old_partner and old_partner is not None:
        new_phase = _calculate_phase(best_score, False, best_partner, None)
        print(f'[resonanz] {egon_id}: Partner-Wechsel {old_partner} -> {best_partner}, Phase reset')

    pairing['pairing_phase'] = new_phase

    # --- Patch 6 Phase 4: LUST-System Update ---
    lust_result = _update_lust_system(
        egon_id, state, best_partner, best_score,
        new_phase, old_phase, reif,
    )
    # LUST-Info in pairing speichern (fuer Prompt-Builder)
    pairing['lust_aktiv'] = lust_result.get('lust_active', False)
    pairing['bindungskanal'] = 'vasopressin' if geschlecht == 'M' else 'oxytocin'
    # Partner-Traum ab Annaeherung aktivieren (fuer Dream-Generator)
    pairing['partner_traum_aktiv'] = new_phase in ('annaeherung', 'bindung', 'bereit')

    # --- Zurueckschreiben (inkl. LUST-Aenderungen an drives) ---
    state['pairing'] = pairing
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    # --- Phase-Transition Effects (romantisch_fest, Exklusivitaet) ---
    if new_phase != old_phase and best_partner:
        _apply_phase_transition_effects(egon_id, best_partner, new_phase, old_phase)

    # Log bei Phase-Wechsel
    if new_phase != old_phase:
        print(f'[resonanz] {egon_id}: Phase {old_phase} -> {new_phase} '
              f'(Partner: {best_partner}, Score: {best_score:.3f})')
    # Log LUST-Aenderung
    if lust_result.get('activation_type'):
        print(f'[resonanz] {egon_id}: LUST {lust_result["activation_type"]} '
              f'({lust_result["old"]:.2f} -> {lust_result["new"]:.2f})')

    result = {
        'resonanz_partner': best_partner,
        'resonanz_score': round(best_score, 3),
        'pairing_phase': new_phase,
        'phase_changed': new_phase != old_phase,
        'reif': reif,
        'all_scores': all_scores,
        'lust': lust_result,
    }

    # --- Patch 6 Phase 3: Bilateral Consent + Genesis-Trigger ---
    if new_phase == 'bereit' and best_partner:
        from engine.genesis import check_bilateral_consent, initiate_pairing
        if check_bilateral_consent(egon_id, best_partner):
            blueprint = initiate_pairing(egon_id, best_partner)
            result['genesis_triggered'] = True
            result['blueprint'] = blueprint
            print(f'[resonanz] {egon_id}: GENESIS TRIGGERED mit {best_partner}!')

    return result


# ================================================================
# Resonanz-Berechnung
# ================================================================

def _calculate_resonanz(
    egon_id: str, state_self: dict, drives_self: dict,
    other_id: str, state_other: dict,
    geschlecht: str,
) -> float:
    """Berechnet den Resonanz-Score (0.0-1.0) zwischen zwei EGONs.

    Drei gewichtete Faktoren:
    - Komplementaritaet (40%): Drive-Vektor-Differenz
    - Kompatibilitaet (30%): DNA + Emotional Gravity + Processing
    - Bond-Tiefe (30%): Score + Trust + History + Zeitbonus

    Plus geschlechtsspezifische Modulation.
    """
    drives_other = state_other.get('drives', {})

    # --- Faktor 1: Komplementaritaet (40%) ---
    komplementaritaet = _calc_komplementaritaet(drives_self, drives_other)

    # --- Faktor 2: Kompatibilitaet (30%) ---
    kompatibilitaet = _calc_kompatibilitaet(state_self, state_other)

    # --- Faktor 3: Bond-Tiefe (30%) ---
    bond_tiefe = _calc_bond_tiefe(egon_id, other_id)

    # Gewichtete Summe
    resonanz = (
        komplementaritaet * W_KOMPLEMENTARITAET
        + kompatibilitaet * W_KOMPATIBILITAET
        + bond_tiefe * W_BOND_TIEFE
    )

    # Gender-Modulation
    if geschlecht == 'F':
        # Frauen gewichten emotionale Tiefe (Kompatibilitaet) hoeher
        resonanz *= 1.0 + (kompatibilitaet - 0.5) * 0.2
    elif geschlecht == 'M':
        # Maenner gewichten Unterschiede (Komplementaritaet) hoeher
        resonanz *= 1.0 + (komplementaritaet - 0.5) * 0.2

    return max(0.0, min(1.0, resonanz))


# ================================================================
# Faktor 1: Komplementaritaet (40%)
# ================================================================

def _calc_komplementaritaet(drives_a: dict, drives_b: dict) -> float:
    """Berechnet wie UNTERSCHIEDLICH die Staerken zweier Agents sind.

    Euclidean Distance der Drive-Vektoren, normalisiert auf 0.0-1.0.
    HOCH wenn Partner stark ist wo ich schwach bin → "Zusammen sind wir mehr".

    Args:
        drives_a: Drive-Dict Agent A (SEEKING, ACTION, CARE, ...)
        drives_b: Drive-Dict Agent B

    Returns:
        0.0 (identisch) bis 1.0 (maximal verschieden)
    """
    if not drives_a or not drives_b:
        return 0.0

    # Drive-Vektoren aufbauen
    vec_a = [float(drives_a.get(k, 0.0)) for k in DRIVE_KEYS]
    vec_b = [float(drives_b.get(k, 0.0)) for k in DRIVE_KEYS]

    # Euclidean Distance
    sum_sq = sum((a - b) ** 2 for a, b in zip(vec_a, vec_b))
    distance = math.sqrt(sum_sq)

    # Normalisieren: max moegliche Distanz = sqrt(N * 1.0^2) = sqrt(10) ≈ 3.16
    max_distance = math.sqrt(len(DRIVE_KEYS))
    normalized = distance / max_distance if max_distance > 0 else 0.0

    return max(0.0, min(1.0, normalized))


# ================================================================
# Faktor 2: Kompatibilitaet (30%)
# ================================================================

def _calc_kompatibilitaet(state_a: dict, state_b: dict) -> float:
    """Berechnet wie AEHNLICH die Grundwerte zweier Agents sind.

    Sub-Faktoren:
    - DNA-Profil Alignment (40%): Lookup-Matrix
    - Emotional Gravity Alignment (30%): baseline_mood + interpretation_bias
    - Processing Style Similarity (30%): speed + emotional_load
    """
    # --- DNA-Profil Alignment (40%) ---
    dna_a = state_a.get('dna_profile', 'DEFAULT')
    dna_b = state_b.get('dna_profile', 'DEFAULT')
    dna_score = DNA_COMPAT.get((dna_a, dna_b), 0.5)

    # --- Emotional Gravity Alignment (30%) ---
    gravity_a = state_a.get('emotional_gravity', {})
    gravity_b = state_b.get('emotional_gravity', {})

    baseline_a = float(gravity_a.get('baseline_mood', 0.5))
    baseline_b = float(gravity_b.get('baseline_mood', 0.5))
    mood_sim = 1.0 - abs(baseline_a - baseline_b)

    bias_a = gravity_a.get('interpretation_bias', 'neutral')
    bias_b = gravity_b.get('interpretation_bias', 'neutral')
    bias_sim = 1.0 if bias_a == bias_b else 0.5

    emotional_gravity_score = mood_sim * 0.6 + bias_sim * 0.4

    # --- Processing Style Similarity (30%) ---
    proc_a = state_a.get('processing', {})
    proc_b = state_b.get('processing', {})

    speed_a = proc_a.get('speed', 'normal')
    speed_b = proc_b.get('speed', 'normal')
    speed_sim = 1.0 if speed_a == speed_b else 0.5

    load_a = float(proc_a.get('emotional_load', 0.5))
    load_b = float(proc_b.get('emotional_load', 0.5))
    load_sim = 1.0 - abs(load_a - load_b)

    processing_score = speed_sim * 0.4 + load_sim * 0.6

    # Gewichtete Kombination
    return (
        dna_score * 0.4
        + emotional_gravity_score * 0.3
        + processing_score * 0.3
    )


# ================================================================
# Faktor 3: Bond-Tiefe (30%)
# ================================================================

def _calc_bond_tiefe(egon_id: str, other_id: str) -> float:
    """Berechnet wie TIEF die Beziehung zwischen zwei EGONs ist.

    Sub-Faktoren:
    - Bond Score (40%): score / 100
    - Trust (30%): direkt aus Bond
    - History Count + Crisis Bonus (20%): gemeinsame Erlebnisse
    - Log-Zeitbonus (10%): log2(Tage+1) / log2(365)
    """
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds_data:
        return 0.0

    # Bond zu other_id finden
    bond = None
    for b in bonds_data.get('bonds', []):
        if b.get('id') == other_id:
            bond = b
            break

    if not bond:
        return 0.0  # Kein Bond vorhanden

    # Bond Score (0-100 → 0-1)
    score = float(bond.get('score', 0)) / 100.0

    # Trust (bereits 0-1)
    trust = float(bond.get('trust', 0.0))

    # History Count + Crisis Bonus
    history = bond.get('bond_history', [])
    history_count = len(history)
    history_score = min(1.0, history_count / 10.0)  # 10 Events = Maximum

    # Crisis Bonus: Trust-Drops in History = gemeinsam durchgestandene Krisen
    crisis_count = 0
    for h in history:
        try:
            if float(h.get('trust_after', 0)) < float(h.get('trust_before', 0)):
                crisis_count += 1
        except (ValueError, TypeError):
            pass
    crisis_bonus = min(0.2, crisis_count * 0.05)
    history_score = min(1.0, history_score + crisis_bonus)

    # Log-Zeitbonus (Tage seit erster Interaktion)
    first = bond.get('since') or bond.get('first_interaction', '')
    time_score = 0.0
    if first:
        try:
            first_date = datetime.strptime(str(first), '%Y-%m-%d')
            days = (datetime.now() - first_date).days
            # Logarithmisch: log2(Tage+1) / log2(365) → 1 Jahr ≈ 1.0
            if days > 0:
                time_score = min(1.0, math.log2(days + 1) / math.log2(365))
        except (ValueError, TypeError):
            pass

    return (
        score * 0.4
        + trust * 0.3
        + history_score * 0.2
        + time_score * 0.1
    )


# ================================================================
# Reife-Check (6 Kriterien)
# ================================================================

def _check_reife(egon_id: str, state: dict) -> bool:
    """Prueft ob ein EGON reif fuer Pairing ist.

    ALLE 6 Kriterien muessen erfuellt sein:
    1. Minimum-Alter: ≥56 Tage seit Erstellung
    2. Emotionale Stabilitaet: emotional_load < 0.3
    3. Identitaets-Reife: ≥5 Aussagen in ego.md
    4. Soziale Kompetenz: ≥3 Bonds mit Score > 15
    5. Skill-Diversitaet: ≥8 Skills
    6. Keine aktive Krise: Keine Emotion mit Intensitaet > 0.8
    """
    # 1. Minimum-Alter: ≥56 Tage
    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if bonds_data:
        for b in bonds_data.get('bonds', []):
            if b.get('id') == 'OWNER_CURRENT':
                first = b.get('first_interaction', '')
                if first:
                    try:
                        created = datetime.strptime(str(first), '%Y-%m-%d')
                        age_days = (datetime.now() - created).days
                        if age_days < REIFE_MIN_DAYS:
                            return False
                    except (ValueError, TypeError):
                        return False
                else:
                    return False  # Kein Erstellungsdatum
                break
    else:
        return False

    # 2. Emotionale Stabilitaet: emotional_load < 0.3
    load = float(state.get('processing', {}).get('emotional_load', 1.0))
    if load >= REIFE_MAX_EMOTIONAL_LOAD:
        return False

    # 3. Identitaets-Reife: ≥5 Aussagen in ego.md
    ego_text = read_md_organ(egon_id, 'core', 'ego.md')
    if ego_text:
        statements = [
            line for line in ego_text.strip().split('\n')
            if line.strip()
            and not line.strip().startswith('#')
            and not line.strip().startswith('[')
            and len(line.strip()) > 10
        ]
        if len(statements) < REIFE_MIN_EGO_STATEMENTS:
            return False
    else:
        return False

    # 4. Soziale Kompetenz: ≥3 Bonds mit Score > 15
    if bonds_data:
        qualifying_bonds = [
            b for b in bonds_data.get('bonds', [])
            if float(b.get('score', 0)) > REIFE_MIN_BOND_SCORE
        ]
        if len(qualifying_bonds) < REIFE_MIN_BONDS_COUNT:
            return False
    else:
        return False

    # 5. Skill-Diversitaet: ≥8 Skills
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    skills = skills_data.get('skills', []) if skills_data else []
    if len(skills) < REIFE_MIN_SKILLS:
        return False

    # 6. Keine aktive Krise: Keine Emotion > 0.8
    emotions = state.get('express', {}).get('active_emotions', [])
    for em in emotions:
        try:
            if float(em.get('intensity', 0)) > REIFE_MAX_EMOTION_INTENSITY:
                return False
        except (ValueError, TypeError):
            pass

    return True


# ================================================================
# Phase State Machine
# ================================================================

def _calculate_phase(
    resonanz_score: float,
    reif: bool,
    current_partner: str | None,
    old_partner: str | None,
) -> str:
    """Bestimmt die Pairing-Phase basierend auf Resonanz-Score.

    Phasen (vorwaerts):
      keine       → erkennung:   resonanz > 0.40
      erkennung   → annaeherung: resonanz > 0.55
      annaeherung → bindung:     resonanz > 0.65
      bindung     → bereit:      resonanz > 0.75 + reif=True

    Rueckwaerts: Phase faellt zurueck wenn Score unter Schwelle sinkt.
    """
    if not current_partner:
        return 'keine'

    if resonanz_score >= PHASE_THRESHOLDS['bereit'] and reif:
        return 'bereit'
    elif resonanz_score >= PHASE_THRESHOLDS['bindung']:
        return 'bindung'
    elif resonanz_score >= PHASE_THRESHOLDS['annaeherung']:
        return 'annaeherung'
    elif resonanz_score >= PHASE_THRESHOLDS['erkennung']:
        return 'erkennung'
    else:
        return 'keine'


# ================================================================
# Konflikt-Penalty (Future Hook fuer bonds_v2.py)
# ================================================================

def apply_conflict_penalty(egon_id: str, penalty: float = 0.05) -> None:
    """Reduziert den Resonanz-Score nach einem Konflikt.

    Wird von bonds_v2.py aufgerufen wenn trust_delta stark negativ.
    Kann auch extern aufgerufen werden bei Eskalation.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    pairing = state.get('pairing', {})
    current_score = float(pairing.get('resonanz_score', 0.0))
    new_score = max(0.0, current_score - penalty)
    pairing['resonanz_score'] = round(new_score, 3)

    # Phase neu berechnen
    reif = pairing.get('reif', False)
    partner = pairing.get('resonanz_partner')
    old_phase = pairing.get('pairing_phase', 'keine')
    new_phase = _calculate_phase(new_score, reif, partner, partner)
    pairing['pairing_phase'] = new_phase

    state['pairing'] = pairing
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    if new_phase != old_phase:
        print(f'[resonanz] {egon_id}: Konflikt-Penalty {penalty:.2f} → '
              f'Phase {old_phase} -> {new_phase} (Score: {new_score:.3f})')
