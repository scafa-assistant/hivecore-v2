"""Web-Browsing fuer Adam — Phase B.

Zwei Funktionen:
  fetch_url(url, max_chars) — Webseite abrufen, HTML→Text extrahieren
  web_search(query)         — Internet durchsuchen via DuckDuckGo

Beide async, beide geben dicts zurueck (nie Exceptions).
Werden von tool_executor.py aufgerufen.
"""

import asyncio
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

# ================================================================
# HTML → Text Extraction
# ================================================================

# Primaer: trafilatura (beste Qualitaet)
try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

# Fallback: Eigener Minimal-Stripper
class _HTMLTextExtractor(HTMLParser):
    """Minimaler HTML→Text Fallback wenn trafilatura nicht installiert."""

    SKIP_TAGS = {'script', 'style', 'noscript', 'svg', 'head'}

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip_depth += 1
        elif tag.lower() in ('br', 'p', 'div', 'h1', 'h2', 'h3', 'h4', 'li', 'tr'):
            self._parts.append('\n')

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        text = ''.join(self._parts)
        # Mehrere Leerzeilen → max 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Mehrere Spaces → 1
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()


def _extract_text(html: str, url: str = '') -> str:
    """HTML → sauberer Text. Trafilatura first, Fallback auf eigenen Stripper."""
    if HAS_TRAFILATURA:
        text = trafilatura.extract(
            html,
            url=url,
            include_links=False,
            include_images=False,
            include_tables=True,
            favor_recall=True,
        )
        if text:
            return text

    # Fallback
    extractor = _HTMLTextExtractor()
    try:
        extractor.feed(html)
        return extractor.get_text()
    except Exception:
        # Absoluter Notfall: regex strip
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


def _extract_title(html: str) -> str:
    """Extrahiert <title> aus HTML."""
    match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        # HTML-Entities dekodieren
        title = title.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        title = title.replace('&#39;', "'").replace('&quot;', '"')
        return title[:200]  # Max 200 Zeichen
    return ''


# ================================================================
# URL Validation
# ================================================================

ALLOWED_SCHEMES = {'http', 'https'}
MAX_RESPONSE_BYTES = 1_000_000  # 1 MB max download


def _validate_url(url: str) -> str | None:
    """Validiert URL. Gibt Fehler-String zurueck oder None wenn OK."""
    if not url:
        return 'Keine URL angegeben.'

    # Schema pruefen
    parsed = urlparse(url)
    if not parsed.scheme:
        # Kein Schema → https:// annehmen
        url = f'https://{url}'
        parsed = urlparse(url)

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return f'URL-Schema "{parsed.scheme}" nicht erlaubt. Nur http/https.'

    if not parsed.netloc:
        return 'Ungueltige URL — kein Host gefunden.'

    # Keine lokalen Adressen
    host = parsed.hostname or ''
    if host in ('localhost', '127.0.0.1', '0.0.0.0', '::1'):
        return 'Lokale Adressen sind nicht erlaubt.'
    if host.startswith('192.168.') or host.startswith('10.') or host.startswith('172.'):
        return 'Private Netzwerk-Adressen sind nicht erlaubt.'

    return None


# ================================================================
# fetch_url — Webseite abrufen
# ================================================================

async def fetch_url(url: str, max_chars: int = 5000) -> dict:
    """Ruft eine URL ab und extrahiert Text aus dem HTML.

    Args:
        url: Die URL die abgerufen werden soll.
        max_chars: Maximale Zeichen die zurueckgegeben werden (Default: 5000).

    Returns:
        dict mit: url, title, content, status, truncated, char_count
        Bei Fehler: url, error, status
    """
    # URL-Schema ggf. ergaenzen
    if url and not url.startswith(('http://', 'https://')):
        url = f'https://{url}'

    # Validierung
    error = _validate_url(url)
    if error:
        return {'url': url, 'error': error, 'status': 0}

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            max_redirects=5,
            headers={
                'User-Agent': 'EGON/1.0 (Digital Being; +https://github.com/egon-ai)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
            },
        ) as client:
            response = await client.get(url)

            # Status pruefen
            if response.status_code >= 400:
                return {
                    'url': str(response.url),
                    'error': f'HTTP {response.status_code}',
                    'status': response.status_code,
                }

            # Content-Type pruefen
            content_type = response.headers.get('content-type', '')
            if 'text' not in content_type and 'html' not in content_type and 'xml' not in content_type:
                return {
                    'url': str(response.url),
                    'error': f'Nicht-Text Content-Type: {content_type}',
                    'status': response.status_code,
                }

            # Body lesen (max 1 MB)
            html = response.text[:MAX_RESPONSE_BYTES]

            # Text extrahieren
            title = _extract_title(html)
            text = _extract_text(html, url=str(response.url))

            if not text:
                return {
                    'url': str(response.url),
                    'error': 'Konnte keinen Text aus der Seite extrahieren.',
                    'status': response.status_code,
                    'title': title,
                }

            # Truncation
            truncated = len(text) > max_chars
            if truncated:
                text = text[:max_chars] + '\n\n[... gekuerzt]'

            return {
                'url': str(response.url),
                'title': title,
                'content': text,
                'status': response.status_code,
                'truncated': truncated,
                'char_count': len(text),
            }

    except httpx.TimeoutException:
        return {'url': url, 'error': 'Timeout — Seite hat nicht innerhalb von 30s geantwortet.', 'status': 0}
    except httpx.ConnectError:
        return {'url': url, 'error': 'Verbindungsfehler — Seite nicht erreichbar.', 'status': 0}
    except httpx.TooManyRedirects:
        return {'url': url, 'error': 'Zu viele Weiterleitungen.', 'status': 0}
    except Exception as e:
        return {'url': url, 'error': f'Fehler beim Abrufen: {type(e).__name__}: {e}', 'status': 0}


# ================================================================
# web_search — Internet durchsuchen
# ================================================================

# DuckDuckGo Search (kein API-Key noetig)
try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        HAS_DDGS = True
    except ImportError:
        HAS_DDGS = False


def _ddg_search_sync(query: str, max_results: int = 5) -> list[dict]:
    """Synchrone DuckDuckGo-Suche (wird in Thread gewrapped)."""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                'title': r.get('title', ''),
                'url': r.get('href', r.get('link', '')),
                'snippet': r.get('body', r.get('snippet', '')),
            })
    return results


async def web_search(query: str, max_results: int = 5) -> dict:
    """Durchsucht das Internet via DuckDuckGo.

    Args:
        query: Suchbegriff(e).
        max_results: Maximale Anzahl Ergebnisse (Default: 5).

    Returns:
        dict mit: query, results (list of {title, url, snippet}), total
        Bei Fehler: query, error, results (leere Liste)
    """
    if not query or not query.strip():
        return {'query': query, 'error': 'Kein Suchbegriff angegeben.', 'results': []}

    if not HAS_DDGS:
        return {
            'query': query,
            'error': 'duckduckgo-search ist nicht installiert. pip install duckduckgo-search',
            'results': [],
        }

    try:
        # DuckDuckGo ist synchron — in Thread ausfuehren
        results = await asyncio.to_thread(_ddg_search_sync, query.strip(), max_results)

        return {
            'query': query,
            'results': results,
            'total': len(results),
        }

    except Exception as e:
        return {
            'query': query,
            'error': f'Suche fehlgeschlagen: {type(e).__name__}: {e}',
            'results': [],
        }
