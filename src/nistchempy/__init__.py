'''This package is a Python interface for the NIST Chemistry WebBook database
that provides additional data for the efficient compound search and 
automatic retrievement of the stored physico-chemical data

'''

__version__ = '1.0.4'
__updated__ = 'May 06, 2025'
__license__ = 'MIT'


from nistchempy.compound_list import get_all_data
from nistchempy.compound import get_compound
from nistchempy.search import run_search, NistSearchParameters
from nistchempy.search import get_search_parameters, print_search_parameters
from nistchempy.requests import RequestConfig
from nistchempy.utils import get_crawl_delay


