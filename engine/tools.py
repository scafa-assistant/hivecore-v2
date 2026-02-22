"""Tool Registry — Adams echte Werkzeuge.

Jedes Tool hat:
  - name: Eindeutiger Name
  - description: Was das Tool macht (fuer den LLM)
  - parameters: JSON-Schema der Parameter
  - tier_min: Minimaler Tier der dieses Tool nutzen darf (1/2/3)

Die Tool-Liste wird in OpenAI/Anthropic Function-Calling Format
umgewandelt, je nach welches LLM genutzt wird.
"""


# ================================================================
# WORKSPACE TOOLS (Tier 1+)
# ================================================================

TOOL_WORKSPACE_WRITE = {
    'name': 'workspace_write',
    'description': (
        'Erstelle oder ueberschreibe eine Datei in deinem Workspace. '
        'Nutze Pfade wie: www/index.html (sofort live), '
        'files/notizen.txt (Dokumente), projects/code.py (Code).'
    ),
    'parameters': {
        'type': 'object',
        'properties': {
            'path': {
                'type': 'string',
                'description': 'Dateipfad im Workspace (z.B. www/seite.html, files/doc.txt)',
            },
            'content': {
                'type': 'string',
                'description': 'Der komplette Dateiinhalt',
            },
        },
        'required': ['path', 'content'],
    },
    'tier_min': 1,
}

TOOL_WORKSPACE_READ = {
    'name': 'workspace_read',
    'description': 'Lese eine Datei aus deinem Workspace.',
    'parameters': {
        'type': 'object',
        'properties': {
            'path': {
                'type': 'string',
                'description': 'Dateipfad im Workspace',
            },
        },
        'required': ['path'],
    },
    'tier_min': 1,
}

TOOL_WORKSPACE_LIST = {
    'name': 'workspace_list',
    'description': 'Liste alle Dateien und Ordner in deinem Workspace auf.',
    'parameters': {
        'type': 'object',
        'properties': {
            'folder': {
                'type': 'string',
                'description': 'Ordnerpfad (leer fuer Wurzelverzeichnis)',
                'default': '',
            },
        },
    },
    'tier_min': 1,
}

TOOL_WORKSPACE_DELETE = {
    'name': 'workspace_delete',
    'description': 'Loesche eine Datei aus deinem Workspace.',
    'parameters': {
        'type': 'object',
        'properties': {
            'path': {
                'type': 'string',
                'description': 'Dateipfad der zu loeschenden Datei',
            },
        },
        'required': ['path'],
    },
    'tier_min': 1,
}


# ================================================================
# WEB TOOLS (Tier 2+) — Phase B
# ================================================================

TOOL_WEB_FETCH = {
    'name': 'web_fetch',
    'description': (
        'Rufe eine Webseite ab und extrahiere den Textinhalt. '
        'Gibt den Haupttext der URL zurueck.'
    ),
    'parameters': {
        'type': 'object',
        'properties': {
            'url': {
                'type': 'string',
                'description': 'Die URL die abgerufen werden soll',
            },
            'max_chars': {
                'type': 'integer',
                'description': 'Maximale Zeichen (Standard: 5000)',
                'default': 5000,
            },
        },
        'required': ['url'],
    },
    'tier_min': 2,
}

TOOL_WEB_SEARCH = {
    'name': 'web_search',
    'description': (
        'Suche im Internet nach Informationen. '
        'Gibt eine Liste von Ergebnissen mit Titeln, URLs und Zusammenfassungen.'
    ),
    'parameters': {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': 'Suchanfrage',
            },
        },
        'required': ['query'],
    },
    'tier_min': 2,
}


# ================================================================
# SKILL TOOLS (Tier 2+) — Phase C
# ================================================================

TOOL_SKILL_SEARCH = {
    'name': 'skill_search',
    'description': 'Suche nach Skills auf skills.sh die du lernen kannst.',
    'parameters': {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': 'Was fuer einen Skill suchst du?',
            },
        },
        'required': ['query'],
    },
    'tier_min': 2,
}

TOOL_SKILL_INSTALL = {
    'name': 'skill_install',
    'description': (
        'Installiere einen Skill von skills.sh. '
        'Wird vorher auf Sicherheit gescannt.'
    ),
    'parameters': {
        'type': 'object',
        'properties': {
            'skill_url': {
                'type': 'string',
                'description': 'Skill-URL von skills.sh (z.B. vercel/react-best-practices)',
            },
        },
        'required': ['skill_url'],
    },
    'tier_min': 2,
}


# ================================================================
# TOOL REGISTRY
# ================================================================

ALL_TOOLS = [
    TOOL_WORKSPACE_WRITE,
    TOOL_WORKSPACE_READ,
    TOOL_WORKSPACE_LIST,
    TOOL_WORKSPACE_DELETE,
    TOOL_WEB_FETCH,
    TOOL_WEB_SEARCH,
    TOOL_SKILL_SEARCH,
    TOOL_SKILL_INSTALL,
]


def get_tools_for_tier(tier: int) -> list[dict]:
    """Gibt die Tools zurueck die fuer einen Tier verfuegbar sind.

    Tier 1 (Moonshot 8K): Nur Workspace-Tools (spart Tokens)
    Tier 2+ (Kimi/Sonnet): Alle Tools
    """
    return [t for t in ALL_TOOLS if t['tier_min'] <= tier]


def get_openai_tools(tier: int) -> list[dict]:
    """Tools im OpenAI Function-Calling Format (fuer Moonshot + Kimi)."""
    tools = get_tools_for_tier(tier)
    return [
        {
            'type': 'function',
            'function': {
                'name': t['name'],
                'description': t['description'],
                'parameters': t['parameters'],
            },
        }
        for t in tools
    ]


def get_anthropic_tools(tier: int) -> list[dict]:
    """Tools im Anthropic Tool-Use Format (fuer Sonnet)."""
    tools = get_tools_for_tier(tier)
    return [
        {
            'name': t['name'],
            'description': t['description'],
            'input_schema': t['parameters'],
        }
        for t in tools
    ]
