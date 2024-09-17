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
    '''Describes response to the GET request to the NIST Chemistry WebBook'''
    
    response: _requests.models.Response = _dcs.field(repr = False)
    '''Request's response'''
    
    ok: _tp.Optional[str] = _dcs.field(init = False, repr = True)
    '''True for request's status codes less than 400'''
    
    content_type: _tp.Optional[str] = _dcs.field(init = False, repr = True)
    '''Content type of the response'''
    
    text: _tp.Optional[str] = _dcs.field(init = False, repr = False)
    '''Text of the response'''
    
    soup: _tp.Optional[_bs4.BeautifulSoup] = _dcs.field(default = None, init = False, repr = False)
    '''BeautifulSoup object of the html response'''
    
    def __post_init__(self):
        self.ok = self.response.ok
        self.text = self.response.text
        self.content_type = self.response.headers.get('content-type', None)
        if 'html' in self.content_type.lower():
            self.text = fix_html(self.text)
            self.soup = _bs4.BeautifulSoup(self.text, features = 'html.parser')


def make_nist_request(url: str, params: dict, **kwargs) -> NistResponse:
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


