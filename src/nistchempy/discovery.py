'''Compound discovery helpers for user-local WebBook indexes.'''

from __future__ import annotations

import collections as _collections
import dataclasses as _dataclasses
import gzip as _gzip
import re as _re
import typing as _tp
import urllib.parse as _urlparse

import bs4 as _bs4

import nistchempy.requests as _requests

FORMULA_BROWSER_ROOT = f'{_requests.BASE_URL}/cgi/formula/'
FORMULA_BROWSER_SOURCE = 'formula-browser'
ROBOTS_URL = f'{_requests.BASE_URL}/robots.txt'
SITEMAP_SOURCE = 'sitemap'


@_dataclasses.dataclass
class FormulaBrowserPage:
    '''Parsed formula-browser page content.

    Args:
        prefix_urls: Formula-browser prefix URLs to visit later.
        seeds: Intermediate seed dictionaries extracted from species links.
    '''

    prefix_urls: _tp.List[str]
    seeds: _tp.List[dict]


@_dataclasses.dataclass
class SitemapPage:
    '''Parsed sitemap XML page content.

    Args:
        sitemap_urls: Nested sitemap URLs to visit later.
        seeds: Intermediate seed dictionaries extracted from compound URLs.
    '''

    sitemap_urls: _tp.List[str]
    seeds: _tp.List[dict]


def discover_formula_browser(
        start_url=None, request_config=None, limit=None, max_pages=None,
        request_func=None):
    '''Discover compound seeds by traversing the WebBook formula browser.

    This function discovers intermediate seeds only. It does not visit final
    compound pages to extract InChI, molecular weights, structure links, or
    section availability.

    Args:
        start_url: Optional formula-browser URL to start from. If omitted, the
            root formula-browser page is used.
        request_config: Optional NistChemPy request configuration.
        limit: Optional maximum number of unique seed rows to collect.
        max_pages: Optional maximum number of formula-browser pages to visit.
        request_func: Optional request function for testing. It must accept
            ``url`` and ``config`` arguments and return an object with ``ok``,
            ``soup``, and ``text`` attributes.

    Returns:
        list[dict]: Discovery seed dictionaries.

    Raises:
        ConnectionError: If a formula-browser request fails.
    '''
    request_func = request_func or _requests.make_nist_request
    start_url = _normalize_url(start_url or FORMULA_BROWSER_ROOT)
    pending = _collections.deque([start_url])
    visited = set()
    seeds_by_key = {}

    while pending:
        if max_pages is not None and len(visited) >= max_pages:
            break

        page_url = pending.popleft()
        if page_url in visited:
            continue
        visited.add(page_url)

        response = request_func(page_url, config=request_config)
        if not response.ok:
            raise ConnectionError(
                f'Bad server response while reading {page_url}: '
                f'{getattr(response, "text", "")}'
            )

        parsed = parse_formula_browser_page(response.soup, page_url=page_url)
        for prefix_url in parsed.prefix_urls:
            if prefix_url not in visited:
                pending.append(prefix_url)

        for seed in parsed.seeds:
            key = seed['lookup_key']
            if key not in seeds_by_key:
                seeds_by_key[key] = seed
            if limit is not None and len(seeds_by_key) >= limit:
                return list(seeds_by_key.values())

    return list(seeds_by_key.values())


def discover_sitemap(
        start_url=None, request_config=None, limit=None, max_pages=None,
        request_func=None):
    '''Discover compound seeds by traversing WebBook robots/sitemap files.

    Sitemap discovery is intended as an audit/supplemental source. It extracts
    candidate compound URLs from sitemap XML files and writes intermediate seed
    rows only. Final metadata and section availability still require
    compound-page enrichment.

    Args:
        start_url: Optional robots.txt or sitemap URL to start from. If
            omitted, the WebBook robots.txt URL is used.
        request_config: Optional NistChemPy request configuration.
        limit: Optional maximum number of unique seed rows to collect.
        max_pages: Optional maximum number of robots/sitemap documents to
            visit.
        request_func: Optional request function for testing. It must accept
            ``url`` and ``config`` arguments and return an object with ``ok``
            and ``text`` attributes.

    Returns:
        list[dict]: Discovery seed dictionaries.

    Raises:
        ConnectionError: If a robots/sitemap request fails.
    '''
    request_func = request_func or _requests.make_nist_request
    start_url = _normalize_url(start_url or ROBOTS_URL)
    pending = _collections.deque([start_url])
    visited = set()
    seeds_by_key = {}

    while pending:
        if max_pages is not None and len(visited) >= max_pages:
            break

        page_url = pending.popleft()
        if page_url in visited:
            continue
        visited.add(page_url)

        response = request_func(page_url, config=request_config)
        if not response.ok:
            raise ConnectionError(
                f'Bad server response while reading {page_url}: '
                f'{getattr(response, "text", "")}'
            )

        text = _response_text(response, page_url)
        if _is_robots_content(page_url, text):
            next_urls = parse_robots_sitemaps(text, page_url=page_url)
            parsed = SitemapPage(sitemap_urls=next_urls, seeds=[])
        else:
            parsed = parse_sitemap_xml(text, page_url=page_url)

        for sitemap_url in parsed.sitemap_urls:
            if sitemap_url not in visited:
                pending.append(sitemap_url)

        for seed in parsed.seeds:
            key = seed['lookup_key']
            if key not in seeds_by_key:
                seeds_by_key[key] = seed
            if limit is not None and len(seeds_by_key) >= limit:
                return list(seeds_by_key.values())

    return list(seeds_by_key.values())


def parse_formula_browser_page(soup, page_url=FORMULA_BROWSER_ROOT):
    '''Parse one WebBook formula-browser page.

    Args:
        soup: BeautifulSoup object or HTML text for one formula-browser page.
        page_url: Absolute URL of the parsed page.

    Returns:
        FormulaBrowserPage: Parsed prefix URLs and species seeds.
    '''
    if isinstance(soup, str):
        soup = _bs4.BeautifulSoup(soup, features='html.parser')

    prefix_urls = []
    seeds = []
    source_query = _source_query_from_formula_url(page_url)

    for anchor in soup.find_all('a', href=True):
        href = anchor.attrs.get('href', '')
        url = _normalize_url(_urlparse.urljoin(page_url, href))
        kind = _classify_formula_browser_url(url)
        if kind is None:
            continue

        if kind == 'prefix':
            if url != _normalize_url(page_url):
                prefix_urls.append(url)
            continue

        formula_hint = _normalise_text(anchor.get_text(' ', strip=True))
        name_hint = _extract_parenthetical_hint(anchor, formula_hint)
        webbook_id = _extract_webbook_id(url)
        lookup_key = webbook_id or url
        seeds.append({
            'lookup_key': lookup_key,
            'lookup_url': url,
            'webbook_id': webbook_id,
            'name_hint': name_hint,
            'formula_hint': formula_hint,
            'source': FORMULA_BROWSER_SOURCE,
            'source_query': source_query,
            'needs_page_enrichment': True,
        })

    return FormulaBrowserPage(
        prefix_urls=_deduplicate(prefix_urls),
        seeds=_deduplicate_seed_dicts(seeds),
    )


def parse_robots_sitemaps(text: str, page_url=ROBOTS_URL):
    '''Parse sitemap URLs from a robots.txt document.

    Args:
        text: robots.txt content.
        page_url: URL of the parsed robots.txt document.

    Returns:
        list[str]: Absolute sitemap URLs.
    '''
    urls = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.lower().startswith('sitemap:'):
            continue
        sitemap_url = stripped.split(':', 1)[1].strip()
        if sitemap_url:
            urls.append(_normalize_url(_urlparse.urljoin(page_url, sitemap_url)))
    return _deduplicate(urls)


def parse_sitemap_xml(text: str, page_url=ROBOTS_URL):
    '''Parse one sitemap XML document into nested sitemaps and seeds.

    Args:
        text: Sitemap XML content.
        page_url: URL of the parsed sitemap document.

    Returns:
        SitemapPage: Parsed nested sitemap URLs and compound seeds.
    '''
    soup = _bs4.BeautifulSoup(text, features='xml')
    sitemap_urls = []
    seeds = []

    for loc in soup.find_all('loc'):
        raw_url = _normalise_text(loc.get_text(' ', strip=True))
        if not raw_url:
            continue
        url = _normalize_url(_urlparse.urljoin(page_url, _urlparse.unquote(raw_url)))
        parent = loc.find_parent()
        parent_name = getattr(parent, 'name', '')
        if parent_name == 'sitemap':
            sitemap_urls.append(url)
            continue
        if parent_name == 'url':
            seed = seed_from_sitemap_url(url, source_query=page_url)
            if seed is not None:
                seeds.append(seed)

    return SitemapPage(
        sitemap_urls=_deduplicate(sitemap_urls),
        seeds=_deduplicate_seed_dicts(seeds),
    )


def seed_from_sitemap_url(url: str, source_query=''):
    '''Create a discovery seed from a sitemap URL when it is compound-like.

    Args:
        url: URL found in a sitemap ``<loc>`` element.
        source_query: Sitemap URL that produced the compound URL.

    Returns:
        dict | None: Discovery seed dictionary, or None for non-compound URLs.
    '''
    url = _normalize_url(_urlparse.unquote(url))
    parsed = _urlparse.urlparse(url)
    base_netloc = _urlparse.urlparse(_requests.BASE_URL).netloc
    if parsed.netloc and parsed.netloc != base_netloc:
        return None

    webbook_id = ''
    if parsed.path == '/cgi/cbook.cgi':
        webbook_id = _extract_webbook_id(url)
        if not webbook_id:
            return None
    elif not parsed.path.startswith('/cgi/inchi/'):
        return None

    lookup_key = webbook_id or url
    return {
        'lookup_key': lookup_key,
        'lookup_url': url,
        'webbook_id': webbook_id,
        'name_hint': '',
        'formula_hint': '',
        'source': SITEMAP_SOURCE,
        'source_query': source_query,
        'needs_page_enrichment': True,
    }


def _classify_formula_browser_url(url):
    parsed = _urlparse.urlparse(url)
    query = _urlparse.parse_qs(parsed.query)

    if parsed.netloc and parsed.netloc != _urlparse.urlparse(
            _requests.BASE_URL).netloc:
        return None

    if parsed.path.startswith('/cgi/formula/') and not parsed.query:
        if parsed.path.rstrip('/') == '/cgi/formula':
            return None
        return 'prefix'

    if parsed.path in ('/cgi/formula', '/cgi/cbook.cgi') and 'ID' in query:
        return 'seed'

    if parsed.path.startswith('/cgi/inchi/'):
        return 'seed'

    return None


def _extract_webbook_id(url) -> str:
    query = _urlparse.parse_qs(_urlparse.urlparse(url).query)
    values = query.get('ID')
    if not values:
        return ''
    return values[0]


def _extract_parenthetical_hint(anchor, formula_hint: str) -> str:
    item = anchor.find_parent('li')
    if item is None:
        return ''

    text = _normalise_text(item.get_text(' ', strip=True))
    if not text.startswith(formula_hint):
        return ''

    suffix = text[len(formula_hint):].strip()
    match = _re.fullmatch(r'\((.*)\)', suffix)
    if not match:
        return ''

    hint = match.group(1).strip()
    if _re.fullmatch(r'\d+\s+species', hint, flags=_re.IGNORECASE):
        return ''
    return hint


def _source_query_from_formula_url(url) -> str:
    parsed = _urlparse.urlparse(url)
    if parsed.path.startswith('/cgi/formula/'):
        return _urlparse.unquote(parsed.path.split('/cgi/formula/', 1)[1])
    return ''


def _response_text(response, url: str) -> str:
    if url.lower().endswith('.gz'):
        raw_response = getattr(response, 'response', None)
        content = getattr(raw_response, 'content', None)
        if content:
            try:
                return _gzip.decompress(content).decode('utf-8')
            except OSError:
                pass
    return getattr(response, 'text', '') or ''


def _is_robots_content(url: str, text: str) -> bool:
    parsed = _urlparse.urlparse(url)
    if parsed.path.endswith('/robots.txt'):
        return True
    return any(
        line.strip().lower().startswith('sitemap:')
        for line in text.splitlines()
    )


def _normalize_url(url) -> str:
    parsed = _urlparse.urlparse(url)
    if not parsed.netloc:
        url = _urlparse.urljoin(_requests.BASE_URL, url)
    return url


def _normalise_text(text: str) -> str:
    return _re.sub(r'\s+', ' ', text or '').strip()


def _deduplicate(values):
    result = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _deduplicate_seed_dicts(seeds):
    result = []
    seen = set()
    for seed in seeds:
        key = seed['lookup_key']
        if key in seen:
            continue
        seen.add(key)
        result.append(seed)
    return result
