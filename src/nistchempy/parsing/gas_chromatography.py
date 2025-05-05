'''The module contains functionality to parse gas chromatography info'''

#%% Imports

import re as _re
from copy import deepcopy as _deepcopy

import bs4 as _bs4

import nistchempy.requests as _ncpr

import pandas as _pd

import typing as _tp


#%% Functions

def get_chromatography_table_refs(soup: _bs4.BeautifulSoup) -> _tp.List[str]:
    '''Extracts references to large format tables containing info on
    chromatographic experiments
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.List[str]: list of URLs
    
    '''
    refs = soup.findChildren('a', string = _re.compile('View large format table', _re.IGNORECASE))
    refs = [_ncpr.BASE_URL + ref['href'] for ref in refs]
    
    return refs


def get_literature_references(soup: _bs4.BeautifulSoup) -> _tp.Dict[str, str]:
    '''Extracts literature references from the corresponding section
    
    Arguments:
        soup (_bs4.BeautifulSoup): bs4-parsed web-page
    
    Returns:
        _tp.Dict: ref's span id => full reference text
    
    '''
    refs = {}
    for entry in soup.findChildren('span', attrs = {'id': _re.compile('ref-\d+')}):
        idx = entry['id']
        p = _deepcopy(entry.findParent())
        for child in p.select('span'):
            child.extract()
        for child in p.findChildren(string = _re.compile('all data')):
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
    # get title info
    h2 = [h2 for h2 in soup.findChildren('h2') if h2.get('id', None)][0]
    ps = [p.strip() for p in h2.text.split(',')]
    info = {
        'ri_type': ps[0],
        'column_type': ps[1],
        'temp_regime': ps[2]
    }
    # get tables
    data = {}
    refs = get_literature_references(soup)
    tables = h2.findAllNext('table', attrs = {'class': 'data'})
    for table in tables:
        rows = table.findChildren('tr')
        for row in rows:
            colname = row.findChild('th').text
            if colname == 'Reference':
                values = []
                for elem in row.findChildren('td'):
                    if not elem.findChild('a'):
                        val = elem.text.strip()
                    else:
                        href = elem.findChild('a')['href']
                        val = refs[href.replace('#', '')]
                    values.append(val)
            else:
                values = [elem.text.strip() for elem in row.findChildren('td')]
            if colname not in data:
                data[colname] = values
            else:
                data[colname] += values            
    # add to info
    info['data'] = _pd.DataFrame(data)
    
    return info


