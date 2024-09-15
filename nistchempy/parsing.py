'''Functionality for parsing of Chemistry WebBook's web pages'''

#%% Imports

import re as _re
import bs4 as _bs4


#%% Functions

def is_compound(soup):
    '''
    Checks if html is a single compound page and returns NIST ID if yes
    '''
    header = soup.findAll('h1', {'id': 'Top'})
    if not header:
        return None
    # get info
    header = header[0]
    info = header.findNext('ul')
    if not info:
        return None
    # extract NIST ID
    for comment in soup.findAll(text = lambda text: isinstance(text, _bs4.Comment)):
        comment = str(comment).replace('\r\n', '').replace('\n', '')
        if not '/cgi/cbook.cgi' in comment:
            continue
        return _re.search(r'/cgi/cbook.cgi\?Form=(.*?)&', comment).group(1)
    
    return None


