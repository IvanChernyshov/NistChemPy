'''Artifact I/O helpers for user-local WebBook indexes.'''

from __future__ import annotations

import datetime as _datetime
import hashlib as _hashlib
import json as _json
import shutil as _shutil
from pathlib import Path as _Path


def file_sha256(path: _Path) -> str:
    '''Return the SHA256 digest of a local file.

    Args:
        path: File path.

    Returns:
        str: Hexadecimal SHA256 digest.
    '''
    hasher = _hashlib.sha256()
    with open(path, 'rb') as infile:
        for chunk in iter(lambda: infile.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_json_file(path: _Path) -> dict:
    '''Read a JSON object from a file if it exists.

    Args:
        path: JSON file path.

    Returns:
        dict: Parsed object, or an empty dictionary on missing/invalid files.
    '''
    if not path.exists():
        return {}
    try:
        return _json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def utc_timestamp() -> str:
    '''Return the current UTC timestamp in compact ISO format.'''
    return (
        _datetime.datetime.now(_datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace('+00:00', 'Z')
    )


def copy_file(src, dst) -> None:
    '''Copy a file while creating the destination parent directory.

    Args:
        src: Source file path.
        dst: Destination file path.
    '''
    destination = _Path(dst)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _shutil.copy2(src, destination)
