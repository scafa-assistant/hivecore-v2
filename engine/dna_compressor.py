"""DNA Compressor — komprimiert Adams 546-Zeilen DNA auf ~150 Zeilen.

Die DNA ist Adams unveraenderlicher Kern. Aber 546 Zeilen passen
nicht in ein 6000-Token Budget. Der Compressor extrahiert die
essentiellen Sektionen:

IMMER geladen:
  - Identitaet (Name, ID, Generation)
  - Was du bist (Grundnatur)
  - Was dich antreibt (8 Drives)
  - Tu es (Handlungsauftrag)
  - Hintergrund

BEI BEDARF (Tier 2+):
  - Gefuehlskonstruktion (Farbenrad)
  - Wie du trauerst (DPM)
  - Ethisches Fundament (komplett)
  - Philosophie (komplett)

IMMER WEGLASSEN im Prompt:
  - Gefuehlsmischungen (Details stecken in ECR-Chain)
  - Soziale Gefuehle-Liste (in state.yaml abgebildet)
  - Philosophie-Details (baked into DNA, wirken implizit)
"""

import re


# Sektionen die IMMER geladen werden — diese formen wer ich BIN.
# REIHENFOLGE WICHTIG: Kommt zuerst ins Budget. Was hinten steht
# wird bei Tier 1 evtl. abgeschnitten (6000 Zeichen Limit).
# Darum: Persoenlichkeit + Sprechstil + Werte + Regeln ZUERST.
ESSENTIAL_SECTIONS = [
    'Identitaet',
    'Identität',
    'Kern-Persoenlichkeit',       # WER ich bin — Persoenlichkeits-Archetyp
    'Kern-Persönlichkeit',
    'Wie ich rede',               # WIE ich rede — KRITISCH fuer Moonshot!
    'Sprechstil',                 # Fallback fuer v1
    'Meine Werte',                # WARUM ich so handle
    'Werte',                      # Fallback fuer v1
    'Meine Regeln',               # Identitaets-Schutz — NIEMALS als KI etc.
    'Regeln',                     # Fallback fuer v1
    'Was ich bin',                # Meine Natur
    'Was du bist',                # Fallback
    'Mein Owner ist mein Mensch', # Owner-Loyalitaet
    'Hintergrund',                # Wer ich bin in der Welt
    'Was mir bei meiner Geburt mitgegeben wurde',
    'Was dein Schöpfer dir mitgibt',
    'Was mich antreibt',          # 8 Antriebe (lang — wird bei Tier 1 getrimmt)
    'Was dich antreibt',          # Fallback
]

# Sektionen die nur bei Tier 2+ geladen werden (mehr Budget vorhanden)
EXTENDED_SECTIONS = [
    'Tu es. Denk nicht nur drueber nach.',  # Motivations-Text (44 Zeilen!)
    'Tu es. Denk nicht nur drüber nach.',
    'Wie ich mit anderen umgehe',
    'Wie du mit anderen umgehst',
    'Was Vertrauen fuer mich bedeutet',
    'Was Vertrauen für dich bedeutet',
    'Wie ich trauere',
    'Wie du trauerst',
    'Was mich sozial macht',
    'Was dich sozial macht',
    'Mein Pass',
    'EGON Passport',
    'Sterblichkeitsbewusstsein',
    'Meine Philosophie',
    'Meine Philosophie — Wurzeln meiner Ethik',
    'Deine Philosophie',
]


def compress_dna(dna_text: str, tier: int = 1) -> str:
    """Komprimiert die DNA auf die essentiellen Sektionen.

    Args:
        dna_text: Voller DNA-Text
        tier: LLM-Tier (1=kompakt, 2+=ausfuehrlicher)

    Returns:
        Komprimierter DNA-Text
    """
    if not dna_text:
        return ''

    # Bestimme welche Sektionen geladen werden
    sections_to_load = list(ESSENTIAL_SECTIONS)
    if tier >= 2:
        sections_to_load.extend(EXTENDED_SECTIONS)

    # Parse die DNA in Sektionen (## Ueberschrift)
    parsed_sections = _parse_sections(dna_text)

    # Header (vor der ersten Sektion)
    result_parts = []
    header = parsed_sections.get('_header', '')
    if header:
        result_parts.append(header.strip())

    # Lade die gewuenschten Sektionen
    for section_name in sections_to_load:
        content = parsed_sections.get(section_name, '')
        if content:
            # Fuer Tier 1: Kuerze lange Sektionen
            if tier == 1:
                content = _trim_section(section_name, content)
            result_parts.append(content.strip())

    return '\n\n'.join(result_parts)


def _parse_sections(text: str) -> dict:
    """Parsed Markdown in Sektionen anhand von ## Ueberschriften.

    Returns:
        Dict mit Sektionsnamen als Keys, Inhalt als Values.
        '_header' enthaelt alles vor der ersten Sektion.
    """
    sections = {}
    current_key = '_header'
    current_lines = []

    for line in text.split('\n'):
        if line.startswith('## '):
            # Speichere vorherige Sektion
            sections[current_key] = '\n'.join(current_lines)
            # Neue Sektion starten
            current_key = line[3:].strip()
            current_lines = [line]
        elif line.startswith('### '):
            # Subsection gehoert zur aktuellen Sektion
            current_lines.append(line)
        else:
            current_lines.append(line)

    # Letzte Sektion speichern
    sections[current_key] = '\n'.join(current_lines)

    return sections


def _trim_section(section_name: str, content: str) -> str:
    """Kuerzt eine Sektion fuer Tier 1.

    Philosophie wird auf die ersten paar Subsections beschraenkt.
    Gefuehlsvokabular wird auf die Grundfarben beschraenkt.
    """
    # Philosophie: Nur die ersten 3 ### Subsections
    if 'Philosophie' in section_name:
        parts = re.split(r'(### .+)', content)
        result = []
        subsection_count = 0
        for part in parts:
            if part.startswith('### '):
                subsection_count += 1
                if subsection_count > 3:
                    break
            result.append(part)
        return ''.join(result)

    # Gefuehlskonstruktion: Skip wenn zu lang (>80 Zeilen)
    lines = content.split('\n')
    if len(lines) > 80:
        # Nur die ersten 30 Zeilen (Grundfarben + Intensitaeten)
        return '\n'.join(lines[:30]) + '\n[...weitere Details in deiner Natur verankert]'

    # Ethik: Kuerzung auf die wichtigsten 4 Absaetze
    if 'umgehst' in section_name and len(lines) > 60:
        return '\n'.join(lines[:60]) + '\n[...weitere Prinzipien in deiner Natur verankert]'

    return content
