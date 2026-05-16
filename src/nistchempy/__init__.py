'''Unofficial tools for querying NIST Chemistry WebBook pages.

NistChemPy extracts selected molecular-property records from Chemistry
WebBook pages for research workflows. It is not affiliated with,
maintained by, or endorsed by NIST.
'''

__version__ = '1.0.6'
__updated__ = 'May 16, 2026'
__license__ = 'MIT'


from nistchempy.compound_list import get_all_data
from nistchempy.compound import get_compound
from nistchempy.search import run_search, run_structural_search
from nistchempy.search import NistSearchParameters
from nistchempy.search import get_search_parameters, print_search_parameters
from nistchempy.requests import RequestConfig
from nistchempy.utils import get_crawl_delay


