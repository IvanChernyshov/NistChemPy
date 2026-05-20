'''Compound-page enrichment helpers for user-local WebBook indexes.'''

from __future__ import annotations

import json as _json
import typing as _tp
import urllib.parse as _urlparse
from pathlib import Path as _Path

import pandas as _pd

import nistchempy.requests as _requests
import nistchempy.search as _search


def resolve_seed_url(seed) -> str:
    '''Resolve one discovery seed to a compound-page URL.

    Args:
        seed: Seed dictionary or pandas Series.

    Returns:
        str: Absolute URL to request during enrichment.

    Raises:
        ValueError: If the seed has no usable URL or WebBook ID.
    '''
    seed = dict(seed)
    lookup_url = _clean_scalar(seed.get('lookup_url', ''))
    webbook_id = _clean_scalar(seed.get('webbook_id', ''))

    if webbook_id and _is_formula_browser_lookup(lookup_url):
        return f'{_requests.SEARCH_URL}?ID={webbook_id}'
    if lookup_url:
        return _normalize_webbook_url(lookup_url)
    if webbook_id:
        return f'{_requests.SEARCH_URL}?ID={webbook_id}'

    raise ValueError('Discovery seed has neither lookup_url nor webbook_id.')


def flatten_compound_info(info: dict, include_cas=True) -> dict:
    '''Flatten parsed compound-page information into one index row.

    Args:
        info: Dictionary returned by ``parse_compound_page``.
        include_cas: If False, omit the ``cas_rn`` column.

    Returns:
        dict: Flat local-index row with old-index-compatible columns.
    '''
    info = info or {}
    row = {
        'ID': _clean_scalar(info.get('ID', '')),
        'name': _clean_scalar(info.get('name', '')),
        'synonyms': _format_synonyms(info.get('synonyms', [])),
        'formula': _clean_scalar(info.get('formula', '')),
        'mol_weight': _clean_scalar(info.get('mol_weight', '')),
        'inchi': _clean_scalar(info.get('inchi', '')),
        'inchi_key': _clean_scalar(info.get('inchi_key', '')),
    }
    if include_cas:
        row['cas_rn'] = _clean_scalar(info.get('cas_rn', ''))

    for key, value in (info.get('mol_refs') or {}).items():
        row[_clean_scalar(key)] = _clean_scalar(value)

    search_names = _search.get_search_parameters()
    for key, value in (info.get('data_refs') or {}).items():
        column = search_names.get(key, key)
        row[_clean_scalar(column)] = _clean_scalar(value)

    for refs_key in ('nist_public_refs', 'nist_subscription_refs'):
        for key, value in (info.get(refs_key) or {}).items():
            row[_clean_scalar(key)] = _clean_scalar(value)

    return row


def _drop_cas_if_needed(dataframe: _pd.DataFrame, include_cas: bool):
    if include_cas or 'cas_rn' not in dataframe.columns:
        return dataframe
    return dataframe.drop(columns=['cas_rn'])


def _read_partial_index_rows(path: _Path) -> _tp.List[dict]:
    if not path.exists():
        return []

    rows = []
    with open(path, 'r', encoding='utf-8') as infile:
        for line in infile:
            line = line.strip()
            if not line:
                continue
            rows.append(_json.loads(line))
    return rows


def _append_jsonl(path: _Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as outfile:
        outfile.write(_json.dumps(row, sort_keys=True) + '\n')


def _final_index_dataframe(
        rows: _tp.List[dict], include_cas=True) -> _pd.DataFrame:
    base_columns = [
        'ID', 'name', 'synonyms', 'formula', 'mol_weight', 'inchi',
        'inchi_key',
    ]
    if include_cas:
        base_columns.append('cas_rn')
    dataframe = _pd.DataFrame(rows)
    if dataframe.empty:
        return _pd.DataFrame(columns=base_columns)

    for column in reversed(base_columns):
        if column in dataframe.columns:
            value = dataframe.pop(column)
            dataframe.insert(0, column, value)

    if 'ID' in dataframe.columns:
        ids = dataframe['ID'].fillna('').astype(str)
        with_id = dataframe[ids.ne('')].drop_duplicates(
            subset=['ID'], keep='first'
        )
        without_id = dataframe[ids.eq('')]
        dataframe = _pd.concat([with_id, without_id], ignore_index=True)

    internal_columns = [
        column for column in dataframe.columns if column.startswith('_seed_')
    ]
    if internal_columns:
        dataframe = dataframe.drop(columns=internal_columns)
    return dataframe


def _seed_lookup_key(seed: dict) -> str:
    for key in ('lookup_key', 'webbook_id', 'lookup_url'):
        value = _clean_scalar(seed.get(key, ''))
        if value:
            return value
    return ''


def _is_formula_browser_lookup(url: str) -> bool:
    if not url:
        return False
    parsed = _urlparse.urlparse(_normalize_webbook_url(url))
    return parsed.path == '/cgi/formula'


def _normalize_webbook_url(url: str) -> str:
    parsed = _urlparse.urlparse(url)
    if not parsed.netloc:
        return _urlparse.urljoin(_requests.BASE_URL, url)
    return url


def _format_synonyms(value) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    return '\n'.join(_clean_scalar(item) for item in value if item)


def _clean_scalar(value) -> str:
    if value is None:
        return ''
    return str(value).strip()
