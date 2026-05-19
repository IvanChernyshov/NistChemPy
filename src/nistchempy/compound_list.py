'''Deprecated helpers for local WebBook index loading.'''

import warnings as _warnings

from nistchempy.index import get_local_index as _get_local_index


def get_all_data(path=None):
    '''Return the user-local WebBook index as a pandas DataFrame.

    Deprecated:
        NistChemPy no longer ships a prebuilt WebBook-derived index. Use
        ``nistchempy.get_local_index(path).to_dataframe()`` or
        ``nistchempy.WebBookIndex.from_cache(path).to_dataframe()`` instead.

    Args:
        path: Optional local index directory.

    Returns:
        pandas.DataFrame: User-local WebBook index table.
    '''
    _warnings.warn(
        'nistchempy.get_all_data() is deprecated. NistChemPy no longer ships '
        'a prebuilt WebBook index. Use nistchempy.get_local_index() or '
        'nistchempy.WebBookIndex.from_cache() instead.',
        DeprecationWarning,
        stacklevel=2,
    )
    return _get_local_index(path=path).to_dataframe()
