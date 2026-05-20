'''Schema constants and seed helpers for user-local WebBook indexes.'''

from __future__ import annotations

import typing as _tp
from dataclasses import asdict as _asdict
from dataclasses import dataclass as _dataclass

import pandas as _pd

INDEX_FILENAME = 'index.csv'
MANIFEST_FILENAME = 'manifest.json'
STATE_FILENAME = 'state.jsonl'
ERRORS_FILENAME = 'errors.jsonl'
SEEDS_FILENAME = 'seeds.csv'
PARTIAL_INDEX_FILENAME = 'index.partial.jsonl'
TMP_DIR_NAME = 'tmp'
DEFAULT_SOURCE_NOTICE = 'NIST Chemistry WebBook / SRD 69'
DEFAULT_DISCOVERY_STRATEGY = 'formula-browser'
FORMULA_SEARCH_DISCOVERY_STRATEGY = 'formula-search'
SITEMAP_DISCOVERY_STRATEGY = 'sitemap'
LOCAL_CSV_STRATEGY = 'local-csv'
VALID_DISCOVERY_STRATEGIES = (
    DEFAULT_DISCOVERY_STRATEGY,
    FORMULA_SEARCH_DISCOVERY_STRATEGY,
    SITEMAP_DISCOVERY_STRATEGY,
)
VALID_MANIFEST_STRATEGIES = VALID_DISCOVERY_STRATEGIES + (
    LOCAL_CSV_STRATEGY,
    'legacy-csv',
)
DEFAULT_INDEX_CAPABILITIES = (
    'compound_discovery',
    'section_availability',
)
DEFAULT_SEARCH_FIELDS = (
    'ID',
    'name',
    'synonyms',
    'formula',
    'inchi',
    'inchi_key',
    'cas_rn',
)
SEED_COLUMNS = (
    'lookup_key',
    'lookup_url',
    'webbook_id',
    'name_hint',
    'formula_hint',
    'source',
    'source_query',
    'needs_page_enrichment',
)


@_dataclass
class DiscoverySeed:
    '''Intermediate compound seed found before page enrichment.

    A discovery seed is not a final local index row. It records a compound-like
    identifier or URL found by a discovery source, such as the formula browser,
    formula search, or sitemaps. Final section availability still requires
    compound-page enrichment.

    Args:
        lookup_key: Stable key used for deduplication when WebBook ID is not
            available yet.
        lookup_url: Optional URL to visit during enrichment.
        webbook_id: Optional NIST Chemistry WebBook compound ID.
        name_hint: Optional name extracted from the discovery source.
        formula_hint: Optional formula extracted from the discovery source.
        source: Discovery source name.
        source_query: Query, formula-prefix path, sitemap URL, or other source
            locator that produced the seed.
        needs_page_enrichment: Whether the seed still needs compound-page
            parsing before it can become a final local index row.
    '''

    lookup_key: str
    lookup_url: str = ''
    webbook_id: str = ''
    name_hint: str = ''
    formula_hint: str = ''
    source: str = ''
    source_query: str = ''
    needs_page_enrichment: bool = True

    def to_dict(self) -> dict:
        '''Return the seed as a dictionary with stable CSV columns.'''
        result = _asdict(self)
        result['needs_page_enrichment'] = str(
            bool(self.needs_page_enrichment)
        ).lower()
        return result


def as_dataframe(data) -> _pd.DataFrame:
    '''Return data as a copied DataFrame.

    Args:
        data: DataFrame or iterable of row dictionaries.

    Returns:
        pandas.DataFrame: Normalized DataFrame copy.
    '''
    if isinstance(data, _pd.DataFrame):
        return data.copy()
    return _pd.DataFrame(list(data))


def as_seed_dataframe(seeds: _tp.Iterable) -> _pd.DataFrame:
    '''Return discovery seeds as a stable-column DataFrame.

    Args:
        seeds: DiscoverySeed objects, dictionaries, or a DataFrame.

    Returns:
        pandas.DataFrame: Normalized discovery seed table.
    '''
    if isinstance(seeds, _pd.DataFrame):
        dataframe = seeds.copy()
    else:
        rows = []
        for seed in seeds:
            if isinstance(seed, DiscoverySeed):
                rows.append(seed.to_dict())
            else:
                rows.append(dict(seed))
        dataframe = _pd.DataFrame(rows)

    for column in SEED_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = ''
    dataframe = dataframe.loc[:, list(SEED_COLUMNS)]
    dataframe['needs_page_enrichment'] = dataframe[
        'needs_page_enrichment'
    ].fillna(True).map(_bool_to_text)
    return dataframe


def _bool_to_text(value) -> str:
    if isinstance(value, str):
        return str(value).lower()
    return str(bool(value)).lower()
