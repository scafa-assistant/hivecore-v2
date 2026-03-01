"""Tool-Erkennung — Braucht diese Nachricht den Agent Loop?

Schnelle Heuristik (kein LLM-Call): Regex auf Aktions-Keywords.
"""

import re


# ================================================================
# Tool-Erkennung: Braucht diese Nachricht den Agent Loop?
# ================================================================

# Keywords die auf Aktions-Bedarf hindeuten
_ACTION_KEYWORDS_DE = [
    r'\berstell',
    r'\bbau\b', r'\bbaue\b', r'\bbaut\b',
    r'\bschreib\b', r'\bschreibe\b',
    r'\berzeug', r'\bgenerier', r'\bmach\b', r'\bmache\b',
    r'\bsuch\b', r'\bsuche\b', r'\brecherchier',
    r'\boeffne\b', r'\b[öo]ffne\b',
    r'\binstallier', r'\blerne\b',
    r'\bloesch', r'\bl[öo]sch',
    r'\blies\b', r'\blese\b', r'\bzeig\b', r'\bzeige\b',
    r'\bspeicher', r'\bdownload',
    r'\bwebseite\b', r'\bwebsite\b', r'\bhtml\b',
    r'\bdatei\b', r'\bfile\b', r'\bskill\b',
    r'\bworkspace\b',
]

_ACTION_KEYWORDS_EN = [
    r'\bcreate\b', r'\bbuild\b', r'\bwrite\b', r'\bgenerate\b',
    r'\bmake\b', r'\bsearch\b', r'\bfind\b', r'\bfetch\b',
    r'\binstall\b', r'\bdelete\b', r'\bremove\b',
    r'\bopen\b', r'\bread\b', r'\bshow\b', r'\blist\b',
    r'\bwebsite\b', r'\bhtml\b', r'\bfile\b', r'\bskill\b',
]

_ACTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in _ACTION_KEYWORDS_DE + _ACTION_KEYWORDS_EN
]


def should_use_tools(user_message: str) -> bool:
    """Erkennt ob eine Nachricht den Agent Loop braucht.

    Schnelle Heuristik (kein LLM-Call!):
    - Regex-Match auf Aktions-Keywords
    - Bei Match: Agent Loop
    - Kein Match: Normaler Chat

    Returns:
        True wenn Tools gebraucht werden, False sonst.
    """
    msg = user_message.strip().lower()

    # Sehr kurze Nachrichten: kein Agent Loop
    if len(msg) < 5:
        return False

    # Fragen ohne Aktions-Kontext: kein Agent Loop
    if msg.startswith(('wie geht', 'was denkst', 'wer bist', 'erzaehl',
                       'erzähl', 'wie fuehls', 'wie fühl')):
        return False

    # Keyword-Match
    for pattern in _ACTION_PATTERNS:
        if pattern.search(msg):
            return True

    return False
