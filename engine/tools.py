"""Tool Registry — EGON Werkzeuge.

Jedes Tool hat:
  - name: Eindeutiger Name
  - description: Was das Tool macht (fuer den LLM)
  - parameters: JSON-Schema der Parameter

Alle Tools stehen allen EGONs zur Verfuegung.
Alles laeuft ueber Moonshot (Kimi K2.5).
"""


# ================================================================
# WORKSPACE TOOLS
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
}


# ================================================================
# WEB TOOLS
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
}


# ================================================================
# SKILL TOOLS
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


def get_openai_tools() -> list[dict]:
    """Alle Tools im OpenAI Function-Calling Format (fuer Moonshot / Kimi K2.5)."""
    return [
        {
            'type': 'function',
            'function': {
                'name': t['name'],
                'description': t['description'],
                'parameters': t['parameters'],
            },
        }
        for t in ALL_TOOLS
    ]
