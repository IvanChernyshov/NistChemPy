'''User-local WebBook index build/write helpers.'''

from __future__ import annotations

import datetime as _datetime
import json as _json
import shutil as _shutil
import typing as _tp
import uuid as _uuid
from dataclasses import asdict as _asdict
from dataclasses import dataclass as _dataclass
from pathlib import Path as _Path

import pandas as _pd

import nistchempy.discovery as _discovery
from nistchempy.cache import resolve_index_path as _resolve_index_path
from nistchempy.exceptions import NistChemPyDataTermsError
from nistchempy.exceptions import NistChemPyIndexBuildError
from nistchempy.index import INDEX_FILENAME
from nistchempy.index import MANIFEST_FILENAME
from nistchempy.index import WebBookIndex
from nistchempy.requests import RequestConfig as _RequestConfig

STATE_FILENAME = 'state.jsonl'
ERRORS_FILENAME = 'errors.jsonl'
SEEDS_FILENAME = 'seeds.csv'
TMP_DIR_NAME = 'tmp'
DEFAULT_SOURCE_NOTICE = 'NIST Chemistry WebBook / SRD 69'
DEFAULT_DISCOVERY_STRATEGY = 'formula-browser'
LOCAL_CSV_STRATEGY = 'local-csv'
VALID_DISCOVERY_STRATEGIES = (
    'formula-browser',
    'formula-search',
    'sitemap',
    'combined',
)
VALID_MANIFEST_STRATEGIES = VALID_DISCOVERY_STRATEGIES + (
    LOCAL_CSV_STRATEGY,
    'legacy-csv',
)
DEFAULT_INDEX_CAPABILITIES = (
    'compound_discovery',
    'section_availability',
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


class LocalIndexBuilder:
    '''Write user-local NIST Chemistry WebBook index artifacts.

    This class contains the local cache writing layer used by index builders.
    Discovery sources first write ``seeds.csv`` records, and page-enrichment
    code later writes the final ``index.csv`` table. It does not itself
    implement WebBook traversal yet.

    Args:
        path: Optional local index directory.
        strategy: Compound-discovery strategy stored in the manifest. Supported
            network strategies are ``formula-browser``, ``formula-search``,
            ``sitemap``, and ``combined``. Local CSV imports use
            ``local-csv``.
        capabilities: Optional capability names to store in the manifest. If
            omitted, the builder records the standard page-enriched index
            capabilities.
        include_cas: Whether the index intentionally includes CAS RN values.
        accept_data_terms: Explicit acknowledgement that generated local data
            are local user artifacts and are not redistributed by NistChemPy.
    '''

    def __init__(
            self, path=None, strategy=DEFAULT_DISCOVERY_STRATEGY,
            capabilities=None, include_cas=False, accept_data_terms=False):
        self.path = _resolve_index_path(path)
        self.strategy = strategy
        self.capabilities = list(capabilities or DEFAULT_INDEX_CAPABILITIES)
        self.include_cas = include_cas
        self.accept_data_terms = accept_data_terms

        if self.strategy not in VALID_MANIFEST_STRATEGIES:
            valid = ', '.join(VALID_MANIFEST_STRATEGIES)
            raise ValueError(
                f'Unsupported discovery strategy: {strategy}. {valid}'
            )

    @property
    def index_path(self) -> _Path:
        '''Return the local index CSV path.'''
        return self.path / INDEX_FILENAME

    @property
    def manifest_path(self) -> _Path:
        '''Return the local manifest path.'''
        return self.path / MANIFEST_FILENAME

    @property
    def seeds_path(self) -> _Path:
        '''Return the local discovery seeds CSV path.'''
        return self.path / SEEDS_FILENAME

    @property
    def state_path(self) -> _Path:
        '''Return the local build state log path.'''
        return self.path / STATE_FILENAME

    @property
    def errors_path(self) -> _Path:
        '''Return the local build error log path.'''
        return self.path / ERRORS_FILENAME

    def prepare(self) -> None:
        '''Create local index directories and check acknowledgement.

        Raises:
            NistChemPyDataTermsError: If data-terms acknowledgement is missing.
        '''
        self._require_data_terms()
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / TMP_DIR_NAME).mkdir(parents=True, exist_ok=True)

    def write_index(
            self, data, replace=True, source=None, source_path=None,
            status='complete'):
        '''Write a final local index CSV and manifest atomically.

        Args:
            data: Index rows as a pandas DataFrame or row dictionaries.
            replace: If False, raise an error when index.csv already exists.
            source: Optional source description stored in the manifest.
            source_path: Optional source file/path stored in the manifest.
            status: Build status stored in the manifest.

        Returns:
            WebBookIndex: Loaded local index object.

        Raises:
            NistChemPyIndexBuildError: If the destination exists and replace is
                False.
        '''
        self.prepare()
        if self.index_path.exists() and not replace:
            raise NistChemPyIndexBuildError(
                f'Local WebBook index already exists at {self.index_path}.'
            )

        dataframe = _as_dataframe(data)
        tmp_index = self._temporary_path(INDEX_FILENAME)
        dataframe.to_csv(tmp_index, index=False)
        tmp_index.replace(self.index_path)

        manifest = self._make_manifest(
            row_count=len(dataframe),
            source=source,
            source_path=source_path,
            status=status,
            artifact='index',
        )
        self._write_manifest(manifest)

        self.append_state(
            'index_written',
            {
                'row_count': len(dataframe),
                'strategy': self.strategy,
                'status': status,
            },
        )
        return WebBookIndex.from_cache(self.path)

    def write_seeds(
            self, seeds, replace=True, source=None, source_path=None,
            status='seeds_complete'):
        '''Write intermediate discovery seeds atomically.

        Discovery seeds are an internal/advanced artifact used before compound
        page enrichment. They are not a final local WebBook index.

        Args:
            seeds: DiscoverySeed objects, dictionaries, or a DataFrame.
            replace: If False, raise an error when seeds.csv already exists.
            source: Optional source description stored in the manifest.
            source_path: Optional source file/path stored in the manifest.
            status: Discovery status stored in the manifest.

        Returns:
            pandas.DataFrame: Written seed table.

        Raises:
            NistChemPyIndexBuildError: If the destination exists and replace is
                False.
        '''
        self.prepare()
        if self.seeds_path.exists() and not replace:
            raise NistChemPyIndexBuildError(
                f'Local discovery seeds already exist at {self.seeds_path}.'
            )

        dataframe = _as_seed_dataframe(seeds)
        tmp_seeds = self._temporary_path(SEEDS_FILENAME)
        dataframe.to_csv(tmp_seeds, index=False)
        tmp_seeds.replace(self.seeds_path)

        manifest = self._make_manifest(
            row_count=0,
            seed_count=len(dataframe),
            source=source,
            source_path=source_path,
            status=status,
            artifact='seeds',
        )
        self._write_manifest(manifest)

        self.append_state(
            'seeds_written',
            {
                'seed_count': len(dataframe),
                'strategy': self.strategy,
                'status': status,
            },
        )
        return dataframe

    def discover_formula_browser(
            self, request_delay=3.0, timeout=30.0, max_attempts=3,
            limit=None, max_pages=None, replace=True, start_url=None,
            request_func=None):
        '''Discover intermediate seeds from the WebBook formula browser.

        Args:
            request_delay: Delay between NIST WebBook requests in seconds.
            timeout: Request timeout in seconds.
            max_attempts: Maximum attempts for each request.
            limit: Optional maximum number of seeds to collect.
            max_pages: Optional maximum number of formula-browser pages to
                visit.
            replace: If False, raise an error when seeds.csv already exists.
            start_url: Optional formula-browser URL to start from.
            request_func: Optional request function for tests.

        Returns:
            pandas.DataFrame: Written discovery seed table.
        '''
        if self.strategy != DEFAULT_DISCOVERY_STRATEGY:
            raise NistChemPyIndexBuildError(
                'Formula-browser discovery requires strategy='
                f'{DEFAULT_DISCOVERY_STRATEGY!r}.'
            )

        request_config = _RequestConfig(
            delay=request_delay,
            max_attempts=max_attempts,
            kwargs={'timeout': timeout},
        )
        self.append_state(
            'formula_browser_discovery_started',
            {
                'limit': limit,
                'max_pages': max_pages,
                'request_delay': request_delay,
                'timeout': timeout,
                'max_attempts': max_attempts,
                'start_url': start_url,
            },
        )
        seeds = _discovery.discover_formula_browser(
            start_url=start_url,
            request_config=request_config,
            limit=limit,
            max_pages=max_pages,
            request_func=request_func,
        )
        return self.write_seeds(
            seeds,
            replace=replace,
            source='NIST Chemistry WebBook formula browser',
            source_path=start_url or _discovery.FORMULA_BROWSER_ROOT,
            status='seeds_complete',
        )

    def append_state(self, event: str, payload=None) -> None:
        '''Append one JSON record to the local build state log.

        Args:
            event: Event name.
            payload: Optional JSON-serializable event payload.
        '''
        self.path.mkdir(parents=True, exist_ok=True)
        record = self._make_log_record(event, payload)
        with open(self.state_path, 'a', encoding='utf-8') as outfile:
            outfile.write(_json.dumps(record, sort_keys=True) + '\n')

    def append_error(self, stage: str, message: str, payload=None) -> None:
        '''Append one JSON record to the local build error log.

        Args:
            stage: Build stage name.
            message: Human-readable error message.
            payload: Optional JSON-serializable error payload.
        '''
        self.path.mkdir(parents=True, exist_ok=True)
        record = self._make_log_record(
            'error',
            {'stage': stage, 'message': message, 'payload': payload or {}},
        )
        with open(self.errors_path, 'a', encoding='utf-8') as outfile:
            outfile.write(_json.dumps(record, sort_keys=True) + '\n')

    def copy_from_csv(self, csv_path, replace=True):
        '''Create a cache-layout local index from an existing local CSV file.

        This helper is intended for local migration/testing only. It does not
        redistribute any WebBook-derived data.

        Args:
            csv_path: Existing local CSV file.
            replace: If False, raise an error when the destination exists.

        Returns:
            WebBookIndex: Loaded local index object.
        '''
        source = _Path(csv_path).expanduser().resolve()
        try:
            dataframe = _pd.read_csv(source, dtype='str')
        except Exception as exc:
            raise NistChemPyIndexBuildError(
                f'Failed to read local CSV index from {source}.'
            ) from exc

        return self.write_index(
            dataframe,
            replace=replace,
            source='local CSV file',
            source_path=str(source),
        )

    def _require_data_terms(self) -> None:
        if self.accept_data_terms:
            return
        raise NistChemPyDataTermsError(
            'Building or importing a local WebBook index requires explicit '
            'acknowledgement. Pass accept_data_terms=True in Python or use '
            '--accept-data-terms in the CLI. Generated local data are local '
            'user artifacts and are not redistributed or licensed by '
            'NistChemPy.'
        )

    def _make_manifest(
            self, row_count: int, source=None, source_path=None,
            status='complete', artifact='index', seed_count=None) -> dict:
        now = _utc_timestamp()
        manifest = {
            'schema_version': 1,
            'artifact': artifact,
            'strategy': self.strategy,
            'capabilities': self.capabilities,
            'include_cas': bool(self.include_cas),
            'status': status,
            'row_count': int(row_count),
            'source': source or DEFAULT_SOURCE_NOTICE,
            'source_path': source_path,
            'created_at': now,
            'updated_at': now,
            'generator': 'nistchempy.local_index_builder',
            'data_notice': (
                'Generated locally by the user. Not distributed with or '
                'licensed by NistChemPy.'
            ),
        }
        if seed_count is not None:
            manifest['seed_count'] = int(seed_count)
        return manifest

    def _make_log_record(self, event: str, payload=None) -> dict:
        return {
            'timestamp': _utc_timestamp(),
            'event': event,
            'payload': payload or {},
        }

    def _temporary_path(self, name: str) -> _Path:
        tmp_dir = self.path / TMP_DIR_NAME
        tmp_dir.mkdir(parents=True, exist_ok=True)
        return tmp_dir / f'{name}.{_uuid.uuid4().hex}.tmp'

    def _write_manifest(self, manifest: dict) -> None:
        tmp_manifest = self._temporary_path(MANIFEST_FILENAME)
        tmp_manifest.write_text(
            _json.dumps(manifest, indent=2, sort_keys=True) + '\n',
            encoding='utf-8',
        )
        tmp_manifest.replace(self.manifest_path)


def discover_formula_browser(
        path=None, accept_data_terms=False, request_delay=3.0, timeout=30.0,
        max_attempts=3, limit=None, max_pages=None, replace=True,
        start_url=None):
    '''Discover formula-browser seeds into a local cache directory.

    Args:
        path: Optional local index directory.
        accept_data_terms: Explicit acknowledgement that generated local data
            are local user artifacts.
        request_delay: Delay between NIST WebBook requests in seconds.
        timeout: Request timeout in seconds.
        max_attempts: Maximum attempts for each request.
        limit: Optional maximum number of seeds to collect.
        max_pages: Optional maximum number of formula-browser pages to visit.
        replace: If False, raise an error when seeds.csv exists.
        start_url: Optional formula-browser URL to start from.

    Returns:
        pandas.DataFrame: Written discovery seed table.
    '''
    builder = LocalIndexBuilder(
        path=path,
        strategy=DEFAULT_DISCOVERY_STRATEGY,
        capabilities=('compound_discovery_seeds',),
        accept_data_terms=accept_data_terms,
    )
    return builder.discover_formula_browser(
        request_delay=request_delay,
        timeout=timeout,
        max_attempts=max_attempts,
        limit=limit,
        max_pages=max_pages,
        replace=replace,
        start_url=start_url,
    )


def import_index_csv(
        csv_path, path=None, include_cas=False, accept_data_terms=False,
        replace=True):
    '''Create a local index cache layout from an existing local CSV file.

    Args:
        csv_path: Existing local CSV file.
        path: Optional destination local index directory.
        include_cas: Whether the local CSV intentionally includes CAS RN data.
        accept_data_terms: Explicit acknowledgement that generated/imported
            local data are local user artifacts.
        replace: If False, raise an error when destination index.csv exists.

    Returns:
        WebBookIndex: Loaded local index object.
    '''
    builder = LocalIndexBuilder(
        path=path,
        strategy=LOCAL_CSV_STRATEGY,
        include_cas=include_cas,
        accept_data_terms=accept_data_terms,
    )
    return builder.copy_from_csv(csv_path, replace=replace)


def unavailable_network_build_message() -> str:
    '''Return the current message for unavailable network index builders.'''
    return (
        'Network-based local index discovery and enrichment are not '
        'implemented in this development step yet. Use --from-csv to import '
        'an existing local CSV index, or wait for the WebBook discovery and '
        'page-enrichment builder patches.'
    )


def unavailable_discovery_message() -> str:
    '''Return the current message for unavailable discovery-only builders.'''
    return (
        'Formula-browser discovery is available through the discover command. '
        'Formula-search and sitemap discovery strategies are not implemented '
        'in this development step yet.'
    )


def _as_dataframe(data) -> _pd.DataFrame:
    if isinstance(data, _pd.DataFrame):
        return data.copy()
    return _pd.DataFrame(list(data))


def _as_seed_dataframe(seeds) -> _pd.DataFrame:
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


def _utc_timestamp() -> str:
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
