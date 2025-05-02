'''Request wrappers for NIST Chemistry WebBook APIs

Attributes:
    BASE_URL   (str): base URL of the NIST Chemistry WebBook database
    SEARCH_URL (str): relative URL for the search API

'''

#%% Imports

import requests as _requests

import bs4 as _bs4

import dataclasses as _dcs
import typing as _tp


#%% Attributes

BASE_URL = 'https://webbook.nist.gov'
SEARCH_URL = f'{BASE_URL}/cgi/cbook.cgi'
INCHI_URL = f'{BASE_URL}/cgi/inchi'


#%% Basic GET request

def fix_html(html: str) -> str:
    '''Fixes detected typos in html code of NIST Chem WebBook web pages
    
    Arguments:
        html (str): text of html-file
    
    Returns:
        str: fixed html-file
    
    '''
    fixed = html.replace('clss=', 'class=')
    
    return fixed


@_dcs.dataclass(eq = False)
class NistResponse():
    '''Describes response to the GET request to the NIST Chemistry WebBook
    
    Attributes:
        response (_requests.models.Response): request's response
        ok (bool): True if request's status code is less than 400
        content_type (_tp.Optional[str]): content type of the response
        text (_tp.Optional[str]): text of the response
        soup (_tp.Optional[_bs4.BeautifulSoup]): BeautifulSoup object of the html response
    
    '''
    
    response: _requests.models.Response = _dcs.field(repr = False)
    ok: bool = _dcs.field(init = False, repr = True)
    content_type: _tp.Optional[str] = _dcs.field(init = False, repr = True)
    text: _tp.Optional[str] = _dcs.field(init = False, repr = False)
    soup: _tp.Optional[_bs4.BeautifulSoup] = _dcs.field(default = None, init = False, repr = False)
    
    
    def __post_init__(self):
        self.ok = self.response.ok
        self.text = self.response.text
        self.content_type = self.response.headers.get('content-type', None)
        if 'html' in self.content_type.lower():
            self.text = fix_html(self.text)
            self.soup = _bs4.BeautifulSoup(self.text, features = 'html.parser')
    
    
    def _save_response(self, path: str) -> None:
        '''Saves response HTML page for testing purposes'''
        with open(path, 'w') as outf:
            outf.write(self.response.text)



def make_nist_request(url: str, params: dict = {}, **kwargs) -> NistResponse:
    '''Dummy request to the NIST Chemistry WebBook
    
    Arguments:
        url (str): URL of the NIST webpage
        params (str): GET request parameters
        kwargs: requests.get kwargs parameters
    
    Returns:
        NistResponse: wrapper for the request's response
    
    '''
    r = _requests.get(url, params, **kwargs)
    nr = NistResponse(r)
    
    return nr


