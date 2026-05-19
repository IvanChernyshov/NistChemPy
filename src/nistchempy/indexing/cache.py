'''Local cache path helpers for NistChemPy.'''

from __future__ import annotations

import os as _os
import sys as _sys
from pathlib import Path as _Path


INDEX_ENV_VAR = 'NISTCHEMPY_INDEX_PATH'
INDEX_DIR_NAME = 'webbook-index'


def _fallback_cache_base() -> _Path:
    '''Return a platform-appropriate cache base without external packages.'''
    if _sys.platform == 'darwin':
        return _Path.home() / 'Library' / 'Caches' / 'nistchempy'
    if _os.name == 'nt':
        base = _os.environ.get('LOCALAPPDATA')
        if base:
            return _Path(base) / 'nistchempy' / 'Cache'
        return _Path.home() / 'AppData' / 'Local' / 'nistchempy' / 'Cache'
    base = _os.environ.get('XDG_CACHE_HOME')
    if base:
        return _Path(base) / 'nistchempy'
    return _Path.home() / '.cache' / 'nistchempy'


def get_default_cache_dir() -> _Path:
    '''Return the default user-local NistChemPy cache directory.

    Returns:
        pathlib.Path: Default directory for user-local NistChemPy artifacts.
    '''
    try:
        from platformdirs import user_cache_dir as _user_cache_dir
    except ImportError:
        return _fallback_cache_base()
    return _Path(_user_cache_dir('nistchempy'))


def get_default_index_path() -> _Path:
    '''Return the default path of the user-local WebBook index directory.

    Returns:
        pathlib.Path: Default local WebBook index directory.
    '''
    return get_default_cache_dir() / INDEX_DIR_NAME


def resolve_index_path(path=None) -> _Path:
    '''Resolve a local WebBook index directory path.

    Args:
        path: Optional explicit index directory. If omitted, the
            NISTCHEMPY_INDEX_PATH environment variable is used when set.
            Otherwise, the platform-specific user cache directory is used.

    Returns:
        pathlib.Path: Resolved index directory path.
    '''
    if path is not None:
        return _Path(path).expanduser().resolve()

    env_path = _os.environ.get(INDEX_ENV_VAR)
    if env_path:
        return _Path(env_path).expanduser().resolve()

    return get_default_index_path().expanduser().resolve()
