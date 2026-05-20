'''Shared helpers for structured NistChemPy records.'''

from __future__ import annotations

import dataclasses as _dcs
import typing as _tp
from datetime import datetime as _datetime
from datetime import timezone as _timezone


JsonDict = _tp.Dict[str, _tp.Any]


def utc_now_iso() -> str:
    '''Return the current UTC timestamp in ISO 8601 format.

    Returns:
        str: Current UTC timestamp with second precision.
    '''
    return _datetime.now(_timezone.utc).replace(microsecond=0).isoformat()


def clean_mapping(mapping: _tp.Optional[_tp.Mapping]) -> JsonDict:
    '''Return a JSON-friendly copy of a mapping.

    Args:
        mapping: Optional mapping to copy. ``None`` is treated as an empty
            mapping.

    Returns:
        dict: Dictionary with keys and values converted to strings where
        possible, excluding ``None`` values.
    '''
    result = {}
    for key, value in dict(mapping or {}).items():
        if value is None:
            continue
        result[str(key)] = str(value)
    return result


def list_copy(values: _tp.Optional[_tp.Iterable]) -> _tp.List:
    '''Return a shallow list copy, treating ``None`` as an empty list.

    Args:
        values: Iterable values or ``None``.

    Returns:
        list: Copied list.
    '''
    if values is None:
        return []
    return list(values)


@_dcs.dataclass
class RecordBase:
    '''Base class for structured records returned by NistChemPy.'''

    record_type: str
    compound_id: str = ''
    source_url: str = ''
    retrieved_at: str = ''

    def base_dict(self) -> JsonDict:
        '''Return common record metadata as a dictionary.

        Returns:
            dict: Common record metadata.
        '''
        return {
            'record_type': self.record_type,
            'compound_id': self.compound_id,
            'source_url': self.source_url,
            'retrieved_at': self.retrieved_at,
        }
