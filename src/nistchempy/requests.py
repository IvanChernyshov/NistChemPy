'''Request wrappers for NIST Chemistry WebBook APIs

Attributes:
    BASE_URL   (str): base URL of the NIST Chemistry WebBook database
    SEARCH_URL (str): relative URL for the search API
    INCHI_URL  (str): relative URL for obtaining NIST compounds via InChI

'''

#%% Imports

import numbers as _numbers
import time as _time

import requests as _requests

import bs4 as _bs4

import dataclasses as _dcs
import typing as _tp


#%% Attributes

BASE_URL = 'https://webbook.nist.gov'
SEARCH_URL = f'{BASE_URL}/cgi/cbook.cgi'
INCHI_URL = f'{BASE_URL}/cgi/inchi'


#%% Request kwargs

@_dcs.dataclass
class RequestConfig():
    '''Configuration for NIST Chemistry WebBook HTTP requests.

    Attributes:
        delay: Time delay in seconds after receiving a response from NIST.
        max_attempts: Number of request attempts. Values greater than one
            enable retrying after request errors or non-OK responses.
        kwargs: Extra keyword arguments passed to the underlying requests
            function. The mapping is copied during initialization.

    '''
    delay: float = 0.0
    max_attempts: _tp.Optional[int] = 1
    kwargs: dict = _dcs.field(default_factory = dict)
    
    
    def __post_init__(self):
        try:
            self.delay = float(self.delay)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f'Time delay must be a non-negative number: {self.delay}'
            ) from exc

        if self.delay < 0:
            raise ValueError(f'Time delay must be non-negative: {self.delay}')

        if isinstance(self.max_attempts, bool):
            raise ValueError(
                f'max_attempts must be a positive integer: {self.max_attempts}'
            )
        if not isinstance(self.max_attempts, _numbers.Integral):
            raise ValueError(
                f'max_attempts must be a positive integer: {self.max_attempts}'
            )
        if self.max_attempts < 1:
            raise ValueError(
                f'max_attempts must be a positive integer: {self.max_attempts}'
            )
        self.max_attempts = int(self.max_attempts)

        if self.kwargs is None:
            self.kwargs = {}
        if not isinstance(self.kwargs, dict):
            raise TypeError(f'kwargs must be a dictionary: {self.kwargs!r}')
        self.kwargs = dict(self.kwargs)

        self.kwargs.pop('params', None)
        if 'timeout' not in self.kwargs:
            self.kwargs['timeout'] = 30.0



#%% Basic GET request

def fix_html(html: str) -> str:
    '''Fixes detected typos in html code of NIST Chem WebBook web pages
    
    Arguments:
        html (str): text of html-file
    
    Returns:
        str: fixed html-file
    
    '''
    fixed = html.replace('clss=', 'class=').replace('\xa0', ' ')
    
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
        self.content_type = self.response.headers.get('content-type', '')
        if 'html' in self.content_type.lower():
            self.text = fix_html(self.text)
            self.soup = _bs4.BeautifulSoup(self.text, features = 'html.parser')
    
    
    def _save_response(self, path: str) -> None:
        '''Saves response HTML page for testing purposes'''
        with open(path, 'w') as outf:
            outf.write(self.response.text)



def make_nist_request(url: str, params: _tp.Optional[dict] = None,
                      config: _tp.Optional[RequestConfig] = None) -> NistResponse:
    '''Dummy GET request to the NIST Chemistry WebBook
    
    Arguments:
        url (str): URL of the NIST webpage
        params (dict): GET request parameters
        config (_tp.Optional[RequestConfig]): additional requests.get parameters
    
    Returns:
        NistResponse: wrapper for the request's response
    
    '''
    # get config
    config = config or RequestConfig()
    params = dict(params or {})
    # get response
    n_err = 0
    while True:
        # catch error
        try:
            r = _requests.get(url, params=params, **config.kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            n_err += 1
            if n_err == config.max_attempts:
                raise e
            _time.sleep(config.delay)
            continue
        # check response
        nr = NistResponse(r)
        n_err += not nr.ok
        _time.sleep(config.delay)
        if nr.ok or n_err == config.max_attempts:
            return nr



def make_nist_post_request(url: str, data: _tp.Optional[dict] = None,
                           json: _tp.Optional[dict] = None,
                           files: _tp.Optional[dict] = None,
                           config: _tp.Optional[RequestConfig] = None) -> NistResponse:
    '''POST request to the NIST Chemistry WebBook
    
    Arguments:
        url (str): URL of the NIST webpage
        data (dict): POST data object to send in the body of the request
        json (dict): JSON serializable object to send in the body of the request
        files (dict): POST qwarg to send files in the body of the request
        config (_tp.Optional[RequestConfig]): additional requests.post parameters
    
    Returns:
        NistResponse: wrapper for the request's response
    
    '''
    # get config
    config = config or RequestConfig()
    data = dict(data or {})
    json = dict(json or {})
    files = dict(files or {})
    # get response
    n_err = 0
    while True:
        # catch error
        try:
            params = {
                'data': data if data else None,
                'json': json if json else None
            }
            if files:
                params['files'] = files
            r = _requests.post(url, **params, **config.kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            n_err += 1
            if n_err == config.max_attempts:
                raise e
            _time.sleep(config.delay)
            continue
        # check response
        nr = NistResponse(r)
        n_err += not nr.ok
        _time.sleep(config.delay)
        if nr.ok or n_err == config.max_attempts:
            return nr
