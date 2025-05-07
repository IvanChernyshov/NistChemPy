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


