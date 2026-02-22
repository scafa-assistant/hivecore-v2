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


# Sektionen die IMMER geladen werden
ESSENTIAL_SECTIONS = [
    'Identität',
    'Was du bist',
    'Was dich antreibt',
    'Tu es. Denk nicht nur drüber nach.',
    'Wie du mit anderen umgehst',
    'Was Vertrauen für dich bedeutet',
    'Hintergrund',
    'Was dein Schöpfer dir mitgibt',
]

# Sektionen die nur bei Tier 2+ geladen werden
EXTENDED_SECTIONS = [
    'Wie du trauerst',
    'Was dich sozial macht',
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
