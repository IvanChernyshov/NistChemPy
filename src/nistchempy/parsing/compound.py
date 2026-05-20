'''Functionality to parse NIST Chemistry WebBook compound pages.'''

#%% Imports

import re as _re
import typing as _tp
import urllib.parse as _uparse

import bs4 as _bs4

import nistchempy.requests as _ncpr


#%% Helpers

def get_compound_header(soup: _tp.Optional[_bs4.BeautifulSoup]):
    '''Return the main compound-page header, if present.

    Args:
        soup: Parsed HTML page.

    Returns:
        BeautifulSoup tag for the compound header, or None.
    '''
    if soup is None:
        return None
    return soup.find('h1', {'id': 'Top'})


def get_compound_info_list(soup: _tp.Optional[_bs4.BeautifulSoup]):
    '''Return the main compound metadata list, if present.

    Args:
        soup: Parsed HTML page.

    Returns:
        BeautifulSoup tag for the main metadata list, or None.
    '''
    header = get_compound_header(soup)
    if header is None:
        return None
    return header.find_next('ul')


def _find_info_item(soup: _tp.Optional[_bs4.BeautifulSoup], label: str):
    info = get_compound_info_list(soup)
    if info is None:
        return None
    hit = info.find(string=_re.compile(label, _re.IGNORECASE))
    if hit is None:
        return None
    return hit.find_parent('li')


def _extract_info_text(
        soup: _tp.Optional[_bs4.BeautifulSoup],
        label: str
    ) -> _tp.Optional[str]:
    item = _find_info_item(soup, label)
    if item is None:
        return None
    text = item.get_text('\n', strip=True)
    text = _re.sub(rf'^\s*{label}\s*:?\s*', '', text,
                   flags=_re.IGNORECASE)
    return text.strip() or None


def _query_value(ref: _tp.Union[str, _bs4.Tag], key: str) -> _tp.Optional[str]:
    if isinstance(ref, _bs4.Tag):
        ref = ref.attrs.get('href', '')
    query = _uparse.urlparse(str(ref)).query
    values = _uparse.parse_qs(query).get(key, [])
    return values[0] if values else None


def _absolute_webbook_url(ref: str) -> str:
    return _uparse.urljoin(_ncpr.BASE_URL, ref)


#%% Search

def get_found_compounds(soup: _tp.Optional[_bs4.BeautifulSoup]) -> dict:
    '''Extract IDs of found compounds for NIST Chemistry WebBook search.

    Args:
        soup: Parsed search-result page.

    Returns:
        Dictionary with ``IDs`` and ``lost`` entries.
    '''
    if soup is None:
        return {'IDs': [], 'lost': False}

    try:
        refs = soup.find('ol').find_all('a', href=_re.compile('/cgi/cbook.cgi'))
        ids = []
        for ref in refs:
            value = _query_value(ref, 'ID')
            if value is not None:
                ids.append(value)
        lost = 'due to the large number of matching species' in soup.text.lower()
    except AttributeError:
        ids = []
        lost = False

    return {'IDs': ids, 'lost': lost}


#%% Compound detection

def is_compound_page(soup: _tp.Optional[_bs4.BeautifulSoup]) -> bool:
    '''Check whether an HTML page is a single compound page.

    Args:
        soup: Parsed HTML page.

    Returns:
        True when the page looks like a single compound page.
    '''
    return get_compound_info_list(soup) is not None


#%% Compound ID

def get_compound_id_from_comment(
        soup: _tp.Optional[_bs4.BeautifulSoup]
    ) -> _tp.Optional[str]:
    '''Extract compound ID from commented fields in the Notes section.

    Args:
        soup: Parsed compound page.

    Returns:
        NIST compound ID, or None.
    '''
    if soup is None:
        return None
    for comment in soup.find_all(string=lambda text: isinstance(text, _bs4.Comment)):
        comment = str(comment).replace('\r\n', '').replace('\n', '')
        match = _re.search(r'/cgi/.*\?Form=(.*?)&', comment)
        if match:
            return match.group(1)

    return None


def get_compound_id_from_units_switch(
        soup: _tp.Optional[_bs4.BeautifulSoup]
    ) -> _tp.Optional[str]:
    '''Extract compound ID from the energy-units switch URL.

    Args:
        soup: Parsed compound page.

    Returns:
        NIST compound ID, or None.
    '''
    info = get_compound_info_list(soup)
    if info is None:
        return None
    refs = info.find_all(name='a', string=_re.compile('witch to'))
    for ref in refs:
        value = _query_value(ref, 'ID')
        if value is not None:
            return value

    return None


def get_compound_id_from_data_refs(
        soup: _tp.Optional[_bs4.BeautifulSoup]
    ) -> _tp.Optional[str]:
    '''Extract compound ID from URLs to compound data sections.

    Args:
        soup: Parsed compound page.

    Returns:
        NIST compound ID, or None.
    '''
    info = get_compound_info_list(soup)
    if info is None:
        return None
    others = info.find_next(string=_re.compile('Other data available'))
    if not others:
        return None
    others = others.find_next('ul')
    if not others:
        return None

    refs = others.find_all(name='a', attrs={'href': _re.compile(r'/cgi/.*\?ID=')})
    for ref in refs:
        value = _query_value(ref, 'ID')
        if value is not None:
            return value

    return None


def get_compound_id(soup: _tp.Optional[_bs4.BeautifulSoup]) -> _tp.Optional[str]:
    '''Return the NIST compound ID for a single compound page.

    Args:
        soup: Parsed compound page.

    Returns:
        NIST compound ID, or None.
    '''
    compound_id = get_compound_id_from_comment(soup)
    if compound_id is None:
        compound_id = get_compound_id_from_units_switch(soup)
    if compound_id is None:
        compound_id = get_compound_id_from_data_refs(soup)

    return compound_id


#%% Other compound fields

def get_compound_name(soup: _tp.Optional[_bs4.BeautifulSoup]) -> _tp.Optional[str]:
    '''Extract chemical name from a compound page.

    Args:
        soup: Parsed compound page.

    Returns:
        Chemical name, or None.
    '''
    header = get_compound_header(soup)
    return header.text.strip() if header is not None else None


def get_compound_synonyms(soup: _tp.Optional[_bs4.BeautifulSoup]) -> _tp.List[str]:
    '''Extract compound synonyms from a compound page.

    Args:
        soup: Parsed compound page.

    Returns:
        Alternative chemical names.
    '''
    text = _extract_info_text(soup, 'Other names')
    if text is None:
        return []
    synonyms = [_.strip(';').strip() for _ in text.split('\n')]
    return [_ for _ in synonyms if _]


def get_compound_formula(soup: _tp.Optional[_bs4.BeautifulSoup]) -> _tp.Optional[str]:
    '''Extract chemical formula from a compound page.

    Args:
        soup: Parsed compound page.

    Returns:
        Chemical formula, or None.
    '''
    formula = _extract_info_text(soup, 'Formula')
    if formula is None:
        return None
    formula = _re.sub('Monomer', '', formula).strip()
    formula = _re.sub(r'\s+', ' ', formula)
    return formula or None


def get_compound_mol_weight(
        soup: _tp.Optional[_bs4.BeautifulSoup]
    ) -> _tp.Optional[float]:
    '''Extract molecular weight from a compound page.

    Args:
        soup: Parsed compound page.

    Returns:
        Molecular weight, or None.
    '''
    text = _extract_info_text(soup, 'Molecular weight')
    if text is None:
        return None
    match = _re.search(r'\d+(?:\.\d+)?', text)
    if match is None:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def get_compound_inchi(soup: _tp.Optional[_bs4.BeautifulSoup]) -> _tp.Optional[str]:
    '''Extract InChI from a compound page.

    Args:
        soup: Parsed compound page.

    Returns:
        InChI string, or None.
    '''
    info = get_compound_info_list(soup)
    if info is None:
        return None
    hits = info.find_all(attrs={'class': 'inchi-text'})
    for hit in hits:
        previous = hit.find_previous()
        if previous is not None and 'InChI:' in previous.text:
            return hit.text
    return None


def get_compound_inchi_key(
        soup: _tp.Optional[_bs4.BeautifulSoup]
    ) -> _tp.Optional[str]:
    '''Extract InChIKey from a compound page.

    Args:
        soup: Parsed compound page.

    Returns:
        InChIKey string, or None.
    '''
    info = get_compound_info_list(soup)
    if info is None:
        return None
    hits = info.find_all(attrs={'class': 'inchi-text'})
    for hit in hits:
        previous = hit.find_previous()
        if previous is not None and 'InChIKey:' in previous.text:
            return hit.text
    return None


def get_compound_casrn(soup: _tp.Optional[_bs4.BeautifulSoup]) -> _tp.Optional[str]:
    '''Extract CAS Registry Number from a compound page.

    Args:
        soup: Parsed compound page.

    Returns:
        CAS RN, or None.
    '''
    return _extract_info_text(soup, 'CAS Registry Number')


def get_compound_mol_refs(
        soup: _tp.Optional[_bs4.BeautifulSoup]
    ) -> _tp.Dict[str, str]:
    '''Extract URLs for available MOL files from a compound page.

    Args:
        soup: Parsed compound page.

    Returns:
        Mapping from ``mol2D`` / ``mol3D`` keys to URLs.
    '''
    info = get_compound_info_list(soup)
    if info is None:
        return {}
    mol_refs = {}

    hits = info.find_all(attrs={'href': _re.compile('Str2File')})
    if hits:
        mol_refs['mol2D'] = _absolute_webbook_url(hits[0].attrs['href'])

    hits = info.find_all(attrs={'href': _re.compile('Str3File')})
    if hits:
        mol_refs['mol3D'] = _absolute_webbook_url(hits[0].attrs['href'])

    return mol_refs


def get_compound_data_refs(
        soup: _tp.Optional[_bs4.BeautifulSoup]
    ) -> _tp.Dict[str, str]:
    '''Extract URLs for available compound data sections.

    Args:
        soup: Parsed compound page.

    Returns:
        Mapping from WebBook section keys/names to URLs.
    '''
    masks = {
        '1': 'cTG', '2': 'cTC', '4': 'cTP', '8': 'cTR',
        '10': 'cSO', '20': 'cIE', '40': 'cIC', '80': 'cIR',
        '100': 'cTZ', '200': 'cMS', '400': 'cUV', '800': 'cES',
        '1000': 'cDI', '2000': 'cGC',
    }
    info = get_compound_info_list(soup)
    if info is None:
        return {}

    hits = info.find_all(string=_re.compile('Other data available'))
    if not hits:
        return {}
    hit = hits[0].find_parent('li')
    if not hit:
        return {}

    data_refs = {}
    for item in hit.find_all('li'):
        refs = [(a.text.strip(), a.attrs['href']) for a in item.find_all('a')]
        if not refs:
            continue
        text, ref = refs[0]
        mask = _re.search(r'Mask=(\d+)', ref)
        key = masks.get(mask.group(1), text) if mask else text
        data_refs[key] = _absolute_webbook_url(ref)

    return data_refs


def get_compound_nist_public_refs(
        soup: _tp.Optional[_bs4.BeautifulSoup]
    ) -> _tp.Dict[str, str]:
    '''Extract URLs for compound data at other public NIST sites.

    Args:
        soup: Parsed compound page.

    Returns:
        Mapping from source names to URLs.
    '''
    info = get_compound_info_list(soup)
    if info is None:
        return {}

    hits = info.find_all(string=_re.compile('other public NIST sites'))
    if not hits:
        return {}
    hit = hits[0].find_parent('li')
    if not hit:
        return {}

    data_refs = {}
    for item in hit.find_all('li'):
        refs = [(a.text.strip(), a.attrs['href']) for a in item.find_all('a')]
        if not refs:
            continue
        text, ref = refs[0]
        data_refs[text] = ref

    return data_refs


def get_compound_nist_subscription_refs(
        soup: _tp.Optional[_bs4.BeautifulSoup]
    ) -> _tp.Dict[str, str]:
    '''Extract URLs for compound data at subscription NIST sites.

    Args:
        soup: Parsed compound page.

    Returns:
        Mapping from source names to URLs.
    '''
    if soup is None:
        return {}
    data_refs = {}
    headers = soup.find_all('h2', string=_re.compile('NIST subscription'))
    if not headers:
        return {}
    hit = headers[0].find_next('ul')
    if not hit:
        return {}

    for item in hit.find_all('li'):
        refs = [(a.text.strip(), a.attrs['href']) for a in item.find_all('a')]
        if not refs:
            continue
        text, ref = refs[0]
        data_refs[text] = ref

    return data_refs


#%% Compound

def parse_compound_page(soup: _tp.Optional[_bs4.BeautifulSoup]) -> _tp.Optional[dict]:
    '''Parse a single compound page.

    Args:
        soup: Parsed compound page.

    Returns:
        Extracted compound information, or None if the page is not a single
        compound page.
    '''
    if not is_compound_page(soup):
        return None

    info = {
        'ID': get_compound_id(soup),
        'name': get_compound_name(soup),
        'synonyms': get_compound_synonyms(soup),
        'formula': get_compound_formula(soup),
        'mol_weight': get_compound_mol_weight(soup),
        'inchi': get_compound_inchi(soup),
        'inchi_key': get_compound_inchi_key(soup),
        'cas_rn': get_compound_casrn(soup),
        'mol_refs': get_compound_mol_refs(soup),
        'data_refs': get_compound_data_refs(soup),
        'nist_public_refs': get_compound_nist_public_refs(soup),
        'nist_subscription_refs': get_compound_nist_subscription_refs(soup),
    }

    return info
