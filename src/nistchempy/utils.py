'''Utility functions'''

#%% Imports

from urllib.robotparser import RobotFileParser as _RobotFileParser

from nistchempy.requests import BASE_URL as _BASE_URL


#%% Functions

def get_crawl_delay(useragent: str = '*') -> float:
    '''Returns NIST Chemistry Webbook's crawl delay for the given user agent
    
    Attributes:
        useragent (str): user agent
    
    Returns:
        float: crawl delay in seconds
    
    '''
    parser = _RobotFileParser(f'{_BASE_URL}/robots.txt')
    parser.read()
    
    return parser.crawl_delay(useragent)


