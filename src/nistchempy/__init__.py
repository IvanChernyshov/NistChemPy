'''Unofficial tools for querying NIST Chemistry WebBook pages.

NistChemPy extracts selected molecular-property records from Chemistry
WebBook pages for research workflows. It is not affiliated with,
maintained by, or endorsed by NIST.
'''

__version__ = '2.0.0'
__updated__ = 'May 20, 2026'
__license__ = 'MIT'


from nistchempy.indexing.core import WebBookIndex, get_local_index
from nistchempy.indexing.build import import_index_csv
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
from nistchempy.exceptions import NistChemPyOptionalDependencyError
from nistchempy.utils import get_crawl_delay, safe_filename
from nistchempy.records import CompoundRecord, MolfileRecord
from nistchempy.records import SpectrumRecord, ChromatogramRecord
from nistchempy.structure import molblock_from_smiles
from nistchempy.structure import molblock_from_inchi
