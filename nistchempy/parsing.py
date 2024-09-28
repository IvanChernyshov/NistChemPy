'''The module contains parsing-related functionality'''

#%% Imports

import re as _re

import urllib.parse as _uparse

import bs4 as _bs4

import nistchempy.requests as _ncpr

import typing as _tp


#%% Search

def get_found_compounds(soup: _bs4.BeautifulSoup) -> dict:
    '''Extracts IDs of found compounds for NIST Chemistry WebBook search
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        dict: extracted NIST search parameters
    
    '''
    try:
        refs = soup.find('ol').findChildren('a', href = _re.compile('/cgi/cbook.cgi'))
        IDs = [_uparse.parse_qs(_uparse.urlparse(a.attrs['href']).query)['ID'][0] \
                                                                 for a in refs]
        lost = 'due to the large number of matching species' in soup.text.lower()
    except AttributeError: # no ol with compound refs
        IDs = []
        lost = False
    
    return {'IDs': IDs, 'lost': lost}



#%% Compound detection

def is_compound_page(soup: _bs4.BeautifulSoup) -> bool:
    '''Checks if html is a single compound page
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        bool: True for a single compound page
    
    '''
    header = soup.findAll('h1', {'id': 'Top'})
    if not header:
        return False
    # get info
    header = header[0]
    info = header.findNext('ul')
    if not info:
        return False
    
    return True



#%% Compound ID

def get_compound_id_from_comment(soup: _bs4.BeautifulSoup) -> _tp.Optional[str]:
    '''Extracts compound ID from commented field in Notes section
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Optional[str]: NIST compound ID, None if not detected
    
    '''
    for comment in soup.findAll(string = lambda text: isinstance(text, _bs4.Comment)):
        comment = str(comment).replace('\r\n', '').replace('\n', '')
        match = _re.search(r'/cgi/.*\?Form=(.*?)&', comment)
        if not match:
            continue
        return match.group(1)
    
    return None


def get_compound_id_from_units_switch(soup: _bs4.BeautifulSoup) -> _tp.Optional[str]:
    '''Extracts compound ID from url to switch energy units
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Optional[str]: NIST compound ID, None if not detected
    
    '''
    # get info block
    header = soup.findAll('h1', {'id': 'Top'})[0]
    info = header.findNext('ul')
    # get switch link
    refs = info.findChildren(name = 'a', string = _re.compile('witch to'))
    if not refs:
        return None
    # extract ID
    for ref in refs:
        match = _re.search('/cgi/.*\?ID=(.*)&', str(ref))
        if match:
            return match.group(1)
    
    return None


def get_compound_id_from_data_refs(soup: _bs4.BeautifulSoup) -> _tp.Optional[str]:
    '''Extracts compound ID from urls to compound data
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Optional[str]: NIST compound ID, None if not detected
    
    '''
    # TODO: implement
    
    return None


def get_compound_id(soup: _bs4.BeautifulSoup) -> _tp.Optional[str]:
    '''Checks if html is a single compound page and returns NIST compound ID if so
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Optional[str]: NIST compound ID for single compound webpage and None otherwise
    
    '''
    ID = get_compound_id_from_comment(soup)
    if ID is None:
        ID = get_compound_id_from_units_switch(soup)
    if ID is None:
        ID = get_compound_id_from_data_refs(soup)
    
    return ID


#%% Other compound fields

def get_compound_name(soup: _bs4.BeautifulSoup) -> str:
    '''Extracts chemical name from compound page
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        str: chemical name of a NIST compound
    
    '''
    header = soup.findAll('h1', {'id': 'Top'})[0]
    name = header.text.strip()
    
    return name


def get_compound_synonyms(soup: _bs4.BeautifulSoup) -> _tp.List[str]:
    '''Extracts synonyms of chemical name from compound page
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.List[str]: list of alternative chemical names
    
    '''
    # prepare
    header = soup.findAll('h1', {'id': 'Top'})[0]
    info = header.findNext('ul')
    synonyms = []
    # find synonyms
    hits = info.findChildren(string = _re.compile('Other names'))
    if hits:
        text = hits[0].findParent('li').text.replace('Other names:', '').strip()
        synonyms = [_.strip(';').strip() for _ in text.split('\n')]
        synonyms = [_ for _ in synonyms if _]
    
    return synonyms


def get_compound_formula(soup: _bs4.BeautifulSoup) -> _tp.Optional[str]:
    '''Extracts chemical formula from compound page
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Optional[str]: chemical formula, and None if not found
    
    '''
    # prepare
    header = soup.findAll('h1', {'id': 'Top'})[0]
    info = header.findNext('ul')
    formula = None
    # find chemical formula
    hits = info.findChildren(string = _re.compile('Formula'))
    if hits:
        formula = hits[0].findParent('li').text.replace('Formula:', '').strip()
        #formula = _re.sub(r'(\d)([a-zA-Z])', r'\1 \2', formula)
        #formula = _re.sub(r'([a-zA-Z])([A-Z])', r'\1 \2', formula)
    
    return formula


def get_compound_mol_weight(soup: _bs4.BeautifulSoup) -> _tp.Optional[float]:
    '''Extracts molecular weight from compound page
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Optional[float]: molecular weight, and None if not found
    
    '''
    # prepare
    header = soup.findAll('h1', {'id': 'Top'})[0]
    info = header.findNext('ul')
    mw = None
    # find chemical formula
    hits = info.findChildren(string = _re.compile('Molecular weight'))
    if hits:
        text = hits[0].findParent('li').text.replace('Molecular weight:', '')
        text = _re.sub('[^0-9\.]', ' ', text).strip().split()[0]
        try:
            mw = float(text)
        except ValueError:
            try:
                text = _re.search('\d+\.\d+', text).group(0)
                mw = float(text)
            except ValueError:
                pass
    
    return mw


def get_compound_inchi(soup: _bs4.BeautifulSoup) -> _tp.Optional[str]:
    '''Extracts InChI from compound page
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Optional[str]: InChI string, and None if not found
    
    '''
    # prepare
    header = soup.findAll('h1', {'id': 'Top'})[0]
    info = header.findNext('ul')
    inchi = None
    # find chemical formula
    hits = info.findChildren(attrs = {'class': 'inchi-text'})
    if hits:
        for hit in hits:
            if 'InChI:' in hit.find_previous().text:
                inchi = hit.text
    
    return inchi


def get_compound_inchi_key(soup: _bs4.BeautifulSoup) -> _tp.Optional[str]:
    '''Extracts InChI key from compound page
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Optional[str]: InChI key string, and None if not found
    
    '''
    # prepare
    header = soup.findAll('h1', {'id': 'Top'})[0]
    info = header.findNext('ul')
    inchi_key = None
    # find chemical formula
    hits = info.findChildren(attrs = {'class': 'inchi-text'})
    if hits:
        for hit in hits:
            if 'InChIKey:' in hit.find_previous().text:
                inchi_key = hit.text
    
    return inchi_key


def get_compound_casrn(soup: _bs4.BeautifulSoup) -> _tp.Optional[str]:
    '''Extracts CAS registry number from compound page
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Optional[str]: CAS RN, and None if not found
    
    '''
    # prepare
    header = soup.findAll('h1', {'id': 'Top'})[0]
    info = header.findNext('ul')
    cas = None
    # find chemical formula
    hits = info.findChildren(string = _re.compile('CAS Registry Number'))
    if hits:
        text = hits[0].findParent('li').text.replace('CAS Registry Number:', '')
        cas = text.strip()
    
    return cas



def get_compound_mol_refs(soup: _bs4.BeautifulSoup) -> _tp.Dict[str, str]:
    '''Extracts dictionary of URLs for compound MOL-files from compound page
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Dict[str, str]: mol2D / mol3D are keys, URLs are values
    
    '''
    # preparations
    header = soup.findAll('h1', {'id': 'Top'})[0]
    info = header.findNext('ul')
    mol_refs = {}
    # 2D mol
    hits = info.findChildren(attrs = {'href': _re.compile('Str2File')})
    if hits:
        mol_refs['mol2D'] = _ncpr.BASE_URL + hits[0].attrs['href']
    # 3D mol
    hits = info.findChildren(attrs = {'href': _re.compile('Str3File')})
    if hits:
        mol_refs['mol3D'] = _ncpr.BASE_URL + hits[0].attrs['href']
    
    return mol_refs



def get_compound_data_refs(soup: _bs4.BeautifulSoup) -> _tp.Dict[str, str]:
    '''Extracts dictionary of URLs for compound properties from compound page
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Dict[str, str]: property names are keys, URLs are values
    
    '''
    MASKS = {'1': 'cTG', '2': 'cTC', '4': 'cTP', '8': 'cTR',
             '10': 'cSO', '20': 'cIE', '40': 'cIC', '80': 'cIR',
             '100': 'cTZ', '200': 'cMS', '400': 'cUV', '800': 'cES',
             '1000': 'cDI', '2000': 'cGC'}
    # preparations
    header = soup.findAll('h1', {'id': 'Top'})[0]
    info = header.findNext('ul')
    data_refs = {}
    # localize other data
    hits = info.findChildren(string = _re.compile('Other data available'))
    if not hits:
        return {}
    hit = hits[0].find_parent('li')
    if not hit:
        return {}
    # extract refs
    for item in hit.findChildren('li'):
        refs = [(a.text.strip(), a.attrs['href']) for a in item.findChildren('a')]
        if not refs:
            continue
        text, ref = refs[0]
        mask = _re.search('Mask=(\d+)', ref)
        key = MASKS.get(mask.group(1), text) if mask else text
        data_refs[key] = _ncpr.BASE_URL + ref
    
    return data_refs



def get_compound_nist_public_refs(soup: _bs4.BeautifulSoup) -> _tp.Dict[str, str]:
    '''Extracts dictionary of URLs for compound properties stored at other
    public NIST sites from compound page
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Dict[str, str]: property names are keys, URLs are values
    
    '''
    # preparations
    header = soup.findAll('h1', {'id': 'Top'})[0]
    info = header.findNext('ul')
    data_refs = {}
    # localize other data
    hits = info.findChildren(string = _re.compile('other public NIST sites'))
    if not hits:
        return {}
    hit = hits[0].find_parent('li')
    if not hit:
        return {}
    # extract refs
    for item in hit.findChildren('li'):
        refs = [(a.text.strip(), a.attrs['href']) for a in item.findChildren('a')]
        if not refs:
            continue
        text, ref = refs[0]
        data_refs[text] = ref
    
    return data_refs



def get_compound_nist_subscription_refs(soup: _bs4.BeautifulSoup) -> _tp.Dict[str, str]:
    '''Extracts dictionary of URLs for compound properties stored at other
    subscription NIST sites from compound page
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Dict[str, str]: property names are keys, URLs are values
    
    '''
    data_refs = {}
    # prepare
    headers = soup.findAll('h2', string = _re.compile('NIST subscription'))
    if not headers:
        return {}
    header = headers[0]
    # get list elements
    hit = header.find_next('ul')
    if not hit:
        return {}
    # iterate
    for item in hit.findChildren('li'):
        refs = [(a.text.strip(), a.attrs['href']) for a in item.findChildren('a')]
        if not refs:
            continue
        text, ref = refs[0]
        data_refs[text] = ref
    
    return data_refs



#%% Compound

def parse_compound_page(soup: _bs4.BeautifulSoup) -> _tp.Optional[dict]:
    '''Parses Nist compound webpage and returns dictionary with extracted info
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Optional[dict]: dictionary with extracted info and None if webpage
        does not correspond to single compound
    
    '''
    # extract
    ID = get_compound_id(soup)
    name = get_compound_name(soup)
    synonyms = get_compound_synonyms(soup)
    formula = get_compound_formula(soup)
    mol_weight = get_compound_mol_weight(soup)
    inchi = get_compound_inchi(soup)
    inchi_key = get_compound_inchi_key(soup)
    cas_rn = get_compound_casrn(soup)
    mol_refs = get_compound_mol_refs(soup)
    data_refs = get_compound_data_refs(soup)
    nist_public_refs = get_compound_nist_public_refs(soup)
    nist_subscription_refs = get_compound_nist_subscription_refs(soup)
    # output
    info = {'ID': ID, 'name': name, 'synonyms': synonyms, 'formula': formula,
            'mol_weight': mol_weight, 'inchi': inchi, 'inchi_key': inchi_key,
            'cas_rn': cas_rn, 'mol_refs': mol_refs, 'data_refs': data_refs,
            'nist_public_refs': nist_public_refs,
            'nist_subscription_refs': nist_subscription_refs}
    
    return info


