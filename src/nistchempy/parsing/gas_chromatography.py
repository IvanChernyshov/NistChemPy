'''The module contains functionality to parse gas chromatography info'''

#%% Imports

import re as _re
from copy import deepcopy as _deepcopy

import bs4 as _bs4

import nistchempy.requests as _ncpr

import pandas as _pd

import typing as _tp


#%% Functions

def get_chromatography_table_refs(
        soup: _tp.Optional[_bs4.BeautifulSoup]
    ) -> _tp.List[str]:
    '''Extracts references to large format tables containing info on
    chromatographic experiments
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.List[str]: list of URLs
    
    '''
    if soup is None:
        return []
    refs = soup.find_all('a', string=_re.compile('View large format table', _re.IGNORECASE))
    refs = [_ncpr.BASE_URL + ref['href'] for ref in refs]
    
    return refs


def get_literature_references(
        soup: _tp.Optional[_bs4.BeautifulSoup]
    ) -> _tp.Dict[str, str]:
    '''Extracts literature references from the corresponding section
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Dict: ref's span id => full reference text
    
    '''
    refs = {}
    if soup is None:
        return refs
    for entry in soup.find_all('span', attrs={'id': _re.compile(r'ref-\d+')}):
        idx = entry['id']
        p = _deepcopy(entry.find_parent())
        for child in p.select('span'):
            child.extract()
        for child in p.find_all(string = _re.compile('all data')):
            child.extract()
        text = p.text.replace('\n', ' ').strip(' .[]')
        text = _re.sub(' +', ' ', text)
        refs[idx] = text
    
    return refs


def parse_chromatography_table(soup: _bs4.BeautifulSoup) -> dict:
    '''Extracts references to large format tables containing info on
    chromatographic experiments
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        dict: contains info to initialize nistchempy.compound.Chromatogram
    
    '''
    if soup is None:
        raise ValueError('Cannot parse chromatography table from empty page.')

    # get title info
    headers = [h2 for h2 in soup.find_all('h2') if h2.get('id', None)]
    if not headers:
        raise ValueError('Cannot find chromatography table title.')
    h2 = headers[0]
    ps = [p.strip() for p in h2.text.split(',')]
    if len(ps) < 3:
        raise ValueError(f'Cannot parse chromatography table title: {h2.text!r}')
    info = {
        'ri_type': ps[0],
        'column_type': ps[1],
        'temp_regime': ps[2]
    }
    # get tables
    data = {}
    refs = get_literature_references(soup)
    tables = h2.find_all_next('table', attrs = {'class': 'data'})
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            header = row.find('th')
            if header is None:
                continue
            colname = header.text
            if colname == 'Reference':
                values = []
                for elem in row.find_all('td'):
                    if not elem.find('a'):
                        val = elem.text.strip()
                    else:
                        href = elem.find('a')['href']
                        val = refs.get(href.replace('#', ''), href)
                    values.append(val)
            else:
                values = [elem.text.strip() for elem in row.find_all('td')]
            if colname not in data:
                data[colname] = values
            else:
                data[colname] += values            
    # add to info
    info['data'] = _pd.DataFrame(data)
    
    return info
