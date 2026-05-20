'''Input/output helpers for structured NistChemPy records.'''

from __future__ import annotations

import json as _json
import os as _os
import typing as _tp

from nistchempy.records.base import JsonDict
from nistchempy.records.chromatography import ChromatogramRecord
from nistchempy.records.spectra import SpectrumRecord


RecordLike = _tp.Any


def record_to_dict(
        record: RecordLike,
        *,
        include_raw: bool = True,
        orient: str = 'records',
    ) -> JsonDict:
    '''Convert one structured record-like object to a dictionary.

    Args:
        record: Record object, object exposing ``to_dict()``, or mapping.
        include_raw: If True, include raw payloads such as JCAMP-DX text for
            spectrum records.
        orient: DataFrame orientation used for chromatography records.

    Returns:
        dict: JSON-friendly record dictionary.

    Raises:
        TypeError: If the object cannot be converted to a dictionary.
    '''
    if isinstance(record, SpectrumRecord):
        return record.to_dict(include_raw=include_raw)
    if isinstance(record, ChromatogramRecord):
        return record.to_dict(orient=orient)
    if isinstance(record, _tp.Mapping):
        return dict(record)
    if hasattr(record, 'to_dict'):
        result = record.to_dict()
        if isinstance(result, _tp.Mapping):
            return dict(result)
        raise TypeError(
            'record.to_dict() must return a mapping: '
            f'{type(result).__name__}'
        )
    raise TypeError(f'Unsupported record object: {type(record).__name__}')


def records_to_dicts(
        records: _tp.Iterable[RecordLike],
        *,
        include_raw: bool = True,
        orient: str = 'records',
    ) -> _tp.List[JsonDict]:
    '''Convert structured records to dictionaries.

    Args:
        records: Iterable of record objects, mappings, or objects exposing
            ``to_dict()``.
        include_raw: If True, include raw payloads such as JCAMP-DX text for
            spectrum records.
        orient: DataFrame orientation used for chromatography records.

    Returns:
        list[dict]: JSON-friendly record dictionaries.
    '''
    return [
        record_to_dict(record, include_raw=include_raw, orient=orient)
        for record in records
    ]


def write_records_json(
        records: _tp.Iterable[RecordLike],
        path: _tp.Union[str, _os.PathLike],
        *,
        include_raw: bool = True,
        orient: str = 'records',
        indent: int = 2,
        ensure_ascii: bool = False,
    ) -> None:
    '''Write structured records to a JSON array file.

    Args:
        records: Iterable of record objects, mappings, or objects exposing
            ``to_dict()``.
        path: Output JSON file path.
        include_raw: If True, include raw payloads such as JCAMP-DX text for
            spectrum records.
        orient: DataFrame orientation used for chromatography records.
        indent: JSON indentation level.
        ensure_ascii: Passed to ``json.dump``.
    '''
    data = records_to_dicts(
        records, include_raw=include_raw, orient=orient,
    )
    with open(path, 'w', encoding='utf-8') as outf:
        _json.dump(data, outf, indent=indent, ensure_ascii=ensure_ascii)
        outf.write('\n')


def write_records_jsonl(
        records: _tp.Iterable[RecordLike],
        path: _tp.Union[str, _os.PathLike],
        *,
        include_raw: bool = True,
        orient: str = 'records',
        ensure_ascii: bool = False,
    ) -> None:
    '''Write structured records to a JSON Lines file.

    Args:
        records: Iterable of record objects, mappings, or objects exposing
            ``to_dict()``.
        path: Output JSON Lines file path.
        include_raw: If True, include raw payloads such as JCAMP-DX text for
            spectrum records.
        orient: DataFrame orientation used for chromatography records.
        ensure_ascii: Passed to ``json.dumps``.
    '''
    with open(path, 'w', encoding='utf-8') as outf:
        for record in records:
            data = record_to_dict(
                record, include_raw=include_raw, orient=orient,
            )
            text = _json.dumps(data, ensure_ascii=ensure_ascii)
            outf.write(f'{text}\n')
