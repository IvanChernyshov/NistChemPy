'''Compound discovery helpers for user-local WebBook indexes.'''

from __future__ import annotations

import collections as _collections
import dataclasses as _dataclasses
import gzip as _gzip
import re as _re
import typing as _tp
import urllib.parse as _urlparse
import xml.etree.ElementTree as _ElementTree

import bs4 as _bs4

import nistchempy.requests as _requests
import nistchempy.search as _search

FORMULA_BROWSER_ROOT = f'{_requests.BASE_URL}/cgi/formula/'
FORMULA_BROWSER_SOURCE = 'formula-browser'
FORMULA_SEARCH_SOURCE = 'formula-search'
ROBOTS_URL = f'{_requests.BASE_URL}/robots.txt'
SITEMAP_SOURCE = 'sitemap'
FORMULA_SEARCH_ELEMENTS = (
    'He', 'Li', 'Be', 'B', 'N', 'O', 'F', 'Ne', 'Na', 'Mg',
    'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti',
    'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge',
    'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo',
    'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te',
    'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm',
    'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf',
    'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb',
    'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U',
    'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No',
    'Lr', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn',
    'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og',
)


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


def discover_formula_search(
        carbon_start=1, carbon_end=None, hydrogen_max=149,
        heteroatom_max=50, elements=None, request_config=None, limit=None,
        max_queries=None, search_func=None, lost_queries=None,
        failed_queries=None):
    '''Discover compound seeds with bounded formula-search subdivision.

    This strategy promotes the bounded carbon-formula search strategy into a
    reusable discovery source. It searches ``C<n>`` formula spaces, refines
    searches that hit the WebBook result cutoff by hydrogen count, then by one
    heteroelement wildcard/count. The strategy discovers candidate WebBook IDs
    only; final metadata and section availability still require compound-page
    enrichment.

    Args:
        carbon_start: First carbon count to scan, inclusive.
        carbon_end: Last carbon count to scan, inclusive. This argument is
            required so bounded formula-search runs are explicit.
        hydrogen_max: Maximum hydrogen count used when refining lost searches.
        heteroatom_max: Maximum count for one heteroelement refinement.
        elements: Optional iterable or comma-separated string of element
            symbols used for heteroelement refinement. If omitted, use the
            same non-H/non-C element list as the historical updater strategy.
        request_config: Optional NistChemPy request configuration.
        limit: Optional maximum number of unique seed rows to collect.
        max_queries: Optional maximum number of formula-search queries to run.
        search_func: Optional search function for testing. It must accept
            ``formula``, ``params``, and ``config`` arguments and return an
            object with ``success``, ``compound_ids``, and ``lost`` attributes.
        lost_queries: Optional list populated with unresolved formula queries
            that still hit the WebBook result cutoff after available
            refinement.
        failed_queries: Optional list populated with unsuccessful WebBook
            formula-search responses.

    Returns:
        list[dict]: Discovery seed dictionaries.

    Raises:
        ValueError: If the formula-search bounds are invalid.
    '''
    _validate_formula_search_bounds(
        carbon_start=carbon_start,
        carbon_end=carbon_end,
        hydrogen_max=hydrogen_max,
        heteroatom_max=heteroatom_max,
        max_queries=max_queries,
    )
    elements = _normalise_elements(elements)
    search_func = search_func or _run_webbook_formula_search
    params = _search.NistSearchParameters(allow_other=True, no_ion=True)
    seeds_by_key = {}
    query_count = 0
    if lost_queries is None:
        lost_queries = []
    if failed_queries is None:
        failed_queries = []

    def record_lost_query(formula, stage):
        lost_queries.append({
            'query': formula,
            'stage': stage,
            'reason': (
                'Search still reached the WebBook result cutoff after '
                'available formula refinement.'
            ),
            'strategy': FORMULA_SEARCH_SOURCE,
        })

    def search_formula(formula):
        nonlocal query_count
        if max_queries is not None and query_count >= max_queries:
            return False, True
        query_count += 1
        result = search_func(formula, params=params, config=request_config)
        if not getattr(result, 'success', False):
            failed_queries.append({
                'query': formula,
                'reason': getattr(result, 'message', '') or (
                    'Formula-search request did not succeed.'
                ),
                'strategy': FORMULA_SEARCH_SOURCE,
            })
            return False, False
        for compound_id in getattr(result, 'compound_ids', []) or []:
            seed = seed_from_formula_search_id(compound_id, formula)
            key = seed['lookup_key']
            if key not in seeds_by_key:
                seeds_by_key[key] = seed
            if limit is not None and len(seeds_by_key) >= limit:
                return bool(getattr(result, 'lost', False)), True
        return bool(getattr(result, 'lost', False)), False

    def should_stop():
        if limit is not None and len(seeds_by_key) >= limit:
            return True
        if max_queries is not None and query_count >= max_queries:
            return True
        return False

    for carbon_count in range(carbon_start, carbon_end + 1):
        lost, stop = search_formula(f'C{carbon_count}')
        if stop or should_stop():
            break
        if not lost:
            continue

        for hydrogen_count in range(hydrogen_max + 1):
            formula = f'C{carbon_count}H{hydrogen_count}'
            lost, stop = search_formula(formula)
            if stop or should_stop():
                break
            if not lost:
                continue

            if not elements:
                record_lost_query(formula, 'hydrogen')
                continue

            for element in elements:
                formula = f'C{carbon_count}H{hydrogen_count}{element}?'
                lost, stop = search_formula(formula)
                if stop or should_stop():
                    break
                if not lost:
                    continue

                if heteroatom_max < 1:
                    record_lost_query(formula, 'heteroelement_wildcard')
                    continue

                for element_count in range(1, heteroatom_max + 1):
                    formula = (
                        f'C{carbon_count}H{hydrogen_count}'
                        f'{element}{element_count}'
                    )
                    lost, stop = search_formula(formula)
                    if stop or should_stop():
                        break
                    if lost:
                        record_lost_query(formula, 'heteroelement_count')
                if should_stop():
                    break
            if should_stop():
                break

    return list(seeds_by_key.values())


def seed_from_formula_search_id(compound_id: str, source_query=''):
    '''Create a discovery seed from a formula-search WebBook ID.

    Args:
        compound_id: NIST Chemistry WebBook compound ID.
        source_query: Formula query that found the compound ID.

    Returns:
        dict: Discovery seed dictionary.
    '''
    compound_id = _normalise_text(compound_id)
    return {
        'lookup_key': compound_id,
        'lookup_url': f'{_requests.SEARCH_URL}?ID={compound_id}',
        'webbook_id': compound_id,
        'name_hint': '',
        'formula_hint': source_query,
        'source': FORMULA_SEARCH_SOURCE,
        'source_query': source_query,
        'needs_page_enrichment': True,
    }


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
            urls.append(
                _normalize_url(_urlparse.urljoin(page_url, sitemap_url))
            )
    return _deduplicate(urls)


def parse_sitemap_xml(text: str, page_url=ROBOTS_URL):
    '''Parse one sitemap XML document into nested sitemaps and seeds.

    Args:
        text: Sitemap XML content.
        page_url: URL of the parsed sitemap document.

    Returns:
        SitemapPage: Parsed nested sitemap URLs and compound seeds.

    Raises:
        ValueError: If the XML document cannot be parsed.
    '''
    try:
        root = _ElementTree.fromstring(text)
    except _ElementTree.ParseError as exc:
        message = f'Failed to parse sitemap XML from {page_url}.'
        raise ValueError(message) from exc

    sitemap_urls = []
    seeds = []
    for child in list(root):
        child_name = _xml_local_name(child.tag)
        if child_name not in {'sitemap', 'url'}:
            continue

        raw_url = ''
        for item in list(child):
            if _xml_local_name(item.tag) == 'loc':
                raw_url = _normalise_text(item.text or '')
                break
        if not raw_url:
            continue

        url = _normalize_url(
            _urlparse.urljoin(page_url, _urlparse.unquote(raw_url))
        )
        if child_name == 'sitemap':
            sitemap_urls.append(url)
        else:
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


def _xml_local_name(name: str) -> str:
    if '}' in name:
        return name.rsplit('}', 1)[1]
    return name


def _run_webbook_formula_search(formula, params, config):
    return _search.run_search(
        formula,
        'formula',
        search_parameters=params,
        request_config=config,
    )


def _normalise_elements(elements):
    if elements is None:
        return list(FORMULA_SEARCH_ELEMENTS)
    if isinstance(elements, str):
        elements = [item.strip() for item in elements.split(',')]
    result = []
    for element in elements:
        element = _normalise_text(element)
        if element:
            result.append(element)
    return result


def _validate_formula_search_bounds(
        carbon_start, carbon_end, hydrogen_max, heteroatom_max, max_queries):
    if carbon_end is None:
        raise ValueError(
            'Formula-search discovery requires an explicit carbon_end value.'
        )
    checks = {
        'carbon_start': carbon_start,
        'carbon_end': carbon_end,
        'hydrogen_max': hydrogen_max,
        'heteroatom_max': heteroatom_max,
    }
    for name, value in checks.items():
        if value is None or int(value) != value or int(value) < 0:
            raise ValueError(f'{name} must be a non-negative integer.')
    if int(carbon_start) < 1:
        raise ValueError('carbon_start must be at least 1.')
    if int(carbon_end) < int(carbon_start):
        raise ValueError(
            'carbon_end must be greater than or equal to carbon_start.'
        )
    if max_queries is not None:
        if int(max_queries) != max_queries or int(max_queries) < 1:
            raise ValueError('max_queries must be a positive integer.')


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
