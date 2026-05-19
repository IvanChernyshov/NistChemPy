'''Unofficial tools for querying NIST Chemistry WebBook pages.

NistChemPy extracts selected molecular-property records from Chemistry
WebBook pages for research workflows. It is not affiliated with,
maintained by, or endorsed by NIST.
'''

__version__ = '1.1.0.dev0'
__updated__ = 'May 19, 2026'
__license__ = 'MIT'


from nistchempy.compound_list import get_all_data
from nistchempy.index import WebBookIndex, get_local_index
from nistchempy.index_builder import import_index_csv
from nistchempy.compound import get_compound
from nistchempy.search import run_search, run_structural_search
from nistchempy.search import NistSearchParameters
from nistchempy.search import get_search_parameters, print_search_parameters
from nistchempy.requests import RequestConfig
from nistchempy.exceptions import NistChemPyError
from nistchempy.exceptions import NistChemPyIndexError
from nistchempy.exceptions import NistChemPyIndexNotFoundError
from nistchempy.exceptions import NistChemPyIndexBuildError
from nistchempy.exceptions import NistChemPyDataTermsError
from nistchempy.utils import get_crawl_delay


