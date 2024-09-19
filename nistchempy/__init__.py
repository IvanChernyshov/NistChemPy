'''This package is a Python interface for the NIST Chemistry WebBook database
that provides additional data for the efficient compound search and 
automatic retrievement of the stored physico-chemical data

'''

__version__ = '0.3.0'
__updated__ = 'October 02, 2024'
__license__ = 'MIT'


from nistchempy.compound_list import get_all_data
from nistchempy.compound import get_compound
from nistchempy.search import search, NistSearchParameters
from nistchempy.search import print_search_parameters


