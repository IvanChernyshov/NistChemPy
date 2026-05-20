'''Utility functions'''

#%% Imports

from urllib.robotparser import RobotFileParser as _RobotFileParser

import nistchempy.requests as _requests

import typing as _tp


#%% Functions

def get_crawl_delay(
        useragent: str = '*',
        config: _tp.Optional[_requests.RequestConfig] = None
    ) -> float:
    '''Returns NIST Chemistry Webbook's crawl delay for the given user agent
    
    Attributes:
        useragent (str): user agent
    
    Returns:
        float: crawl delay in seconds
    
    '''
    # get response
    config = config or _requests.RequestConfig()
    ROBOTS_URL = _requests.BASE_URL + '/robots.txt'
    nr = _requests.make_nist_request(ROBOTS_URL, config=config)
    if not nr.ok:
        raise ConnectionError(f'Bad server response: {nr.text}')
    # parse robots.txt
    parser = _RobotFileParser()
    parser.parse(nr.text.split('\n'))
    
    return parser.crawl_delay(useragent)


def safe_filename(text: str, replacement: str = '_') -> str:
    '''Return a filesystem-friendly filename fragment.

    Args:
        text: Input text to sanitize.
        replacement: Replacement character for unsafe characters.

    Returns:
        str: Sanitized filename. Empty results are returned as ``'file'``.
    '''
    unsafe = '<>:"/\\|?*\n\r\t'
    cleaned = ''.join(replacement if ch in unsafe else ch for ch in str(text))
    cleaned = cleaned.strip(' .')
    while replacement * 2 in cleaned:
        cleaned = cleaned.replace(replacement * 2, replacement)
    return cleaned or 'file'
