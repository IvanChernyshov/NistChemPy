'''User-local WebBook index build/write helpers.'''

from __future__ import annotations

import datetime as _datetime
import hashlib as _hashlib
import json as _json
import shutil as _shutil
import typing as _tp
import urllib.parse as _urlparse
import uuid as _uuid
from dataclasses import asdict as _asdict
from dataclasses import dataclass as _dataclass
from pathlib import Path as _Path

import pandas as _pd

import nistchempy.indexing.discovery as _discovery
import nistchempy.parsing as _parsing
import nistchempy.requests as _requests
import nistchempy.search as _search
from nistchempy.indexing.cache import resolve_index_path as _resolve_index_path
from nistchempy.exceptions import NistChemPyDataTermsError
from nistchempy.exceptions import NistChemPyIndexBuildError
from nistchempy.indexing.core import INDEX_FILENAME
from nistchempy.indexing.core import MANIFEST_FILENAME
from nistchempy.indexing.core import WebBookIndex
from nistchempy.requests import RequestConfig as _RequestConfig

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
    'formula-browser',
    'formula-search',
    'sitemap',
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
    code later writes the final ``index.csv`` table. The class also provides
    the orchestration methods used by network builders.

    Args:
        path: Optional local index directory.
        strategy: Compound-discovery strategy stored in the manifest. Supported
            network strategies are ``formula-browser``, ``formula-search``,
            and ``sitemap``. Local CSV imports use ``local-csv``.
        capabilities: Optional capability names to store in the manifest. If
            omitted, the builder records the standard page-enriched index
            capabilities.
        include_cas: Whether the index intentionally includes CAS RN values.
        accept_data_terms: Explicit acknowledgement that generated local data
            are local user artifacts and are not redistributed by NistChemPy.
    '''

    def __init__(
            self, path=None, strategy=DEFAULT_DISCOVERY_STRATEGY,
            capabilities=None, include_cas=True, accept_data_terms=False):
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
    def partial_index_path(self) -> _Path:
        '''Return the resumable partial-index JSONL path.'''
        return self.path / PARTIAL_INDEX_FILENAME

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
            status='complete', seed_count=None, extra_manifest=None):
        '''Write a final local index CSV and manifest atomically.

        Args:
            data: Index rows as a pandas DataFrame or row dictionaries.
            replace: If False, raise an error when index.csv already exists.
            source: Optional source description stored in the manifest.
            source_path: Optional source file/path stored in the manifest.
            status: Build status stored in the manifest.
            seed_count: Optional number of discovery seed rows used to create
                the index.
            extra_manifest: Optional additional manifest fields.

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

        dataframe = _drop_cas_if_needed(_as_dataframe(data), self.include_cas)
        tmp_index = self._temporary_path(INDEX_FILENAME)
        dataframe.to_csv(tmp_index, index=False)
        tmp_index.replace(self.index_path)

        manifest = self._make_manifest(
            row_count=len(dataframe),
            seed_count=seed_count,
            source=source,
            source_path=source_path,
            status=status,
            artifact='index',
            extra=extra_manifest,
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

        if replace and self.partial_index_path.exists():
            self.partial_index_path.unlink()
            self.append_state(
                'partial_index_cleared',
                {'reason': 'discovery seeds were replaced'},
            )

        seed_fingerprint = _file_sha256(self.seeds_path)
        manifest = self._make_manifest(
            row_count=0,
            seed_count=len(dataframe),
            source=source,
            source_path=source_path,
            status=status,
            artifact='seeds',
            extra={'seed_fingerprint': seed_fingerprint},
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
            max_pages: Optional maximum number of discovery pages/documents to
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

        self.prepare()
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
        try:
            seeds = _discovery.discover_formula_browser(
                start_url=start_url,
                request_config=request_config,
                limit=limit,
                max_pages=max_pages,
                request_func=request_func,
            )
        except Exception as exc:
            raise NistChemPyIndexBuildError(
                f'Formula-browser discovery failed: {exc}'
            ) from exc

        return self.write_seeds(
            seeds,
            replace=replace,
            source='NIST Chemistry WebBook formula browser',
            source_path=start_url or _discovery.FORMULA_BROWSER_ROOT,
            status='seeds_complete',
        )

    def discover_formula_search(
            self, request_delay=3.0, timeout=30.0, max_attempts=3,
            limit=None, max_queries=None, replace=True, carbon_start=1,
            carbon_end=None, hydrogen_max=149, heteroatom_max=50,
            elements=None, search_func=None):
        '''Discover intermediate seeds from formula-search results.

        This method wraps the legacy carbon-formula search prototype as a
        bounded discovery strategy. It writes seed rows only; final metadata
        still requires compound-page enrichment.

        Args:
            request_delay: Delay between NIST WebBook requests in seconds.
            timeout: Request timeout in seconds.
            max_attempts: Maximum attempts for each request.
            limit: Optional maximum number of seeds to collect.
            max_queries: Optional maximum number of formula-search queries to
                run.
            replace: If False, raise an error when seeds.csv already exists.
            carbon_start: First carbon count to scan, inclusive.
            carbon_end: Last carbon count to scan, inclusive. Required for
                formula-search discovery.
            hydrogen_max: Maximum hydrogen count used for refinement.
            heteroatom_max: Maximum one-heteroelement count used for
                refinement.
            elements: Optional iterable or comma-separated string of element
                symbols used for refinement.
            search_func: Optional formula-search function for tests.

        Returns:
            pandas.DataFrame: Written discovery seed table.
        '''
        if self.strategy != FORMULA_SEARCH_DISCOVERY_STRATEGY:
            raise NistChemPyIndexBuildError(
                'Formula-search discovery requires strategy='
                f'{FORMULA_SEARCH_DISCOVERY_STRATEGY!r}.'
            )

        self.prepare()
        request_config = _RequestConfig(
            delay=request_delay,
            max_attempts=max_attempts,
            kwargs={'timeout': timeout},
        )
        self.append_state(
            'formula_search_discovery_started',
            {
                'carbon_start': carbon_start,
                'carbon_end': carbon_end,
                'hydrogen_max': hydrogen_max,
                'heteroatom_max': heteroatom_max,
                'elements': elements,
                'limit': limit,
                'max_queries': max_queries,
                'request_delay': request_delay,
                'timeout': timeout,
                'max_attempts': max_attempts,
            },
        )
        try:
            seeds = _discovery.discover_formula_search(
                carbon_start=carbon_start,
                carbon_end=carbon_end,
                hydrogen_max=hydrogen_max,
                heteroatom_max=heteroatom_max,
                elements=elements,
                request_config=request_config,
                limit=limit,
                max_queries=max_queries,
                search_func=search_func,
            )
        except ValueError as exc:
            raise NistChemPyIndexBuildError(str(exc)) from exc
        except Exception as exc:
            raise NistChemPyIndexBuildError(
                f'Formula-search discovery failed: {exc}'
            ) from exc

        return self.write_seeds(
            seeds,
            replace=replace,
            source='NIST Chemistry WebBook formula search',
            source_path=(
                f'C{carbon_start}..C{carbon_end}; '
                f'H0..H{hydrogen_max}; heteroatom<={heteroatom_max}'
            ),
            status='seeds_complete',
        )

    def discover_sitemap(
            self, request_delay=3.0, timeout=30.0, max_attempts=3,
            limit=None, max_pages=None, replace=True, start_url=None,
            request_func=None):
        '''Discover intermediate seeds from WebBook sitemap files.

        Args:
            request_delay: Delay between NIST WebBook requests in seconds.
            timeout: Request timeout in seconds.
            max_attempts: Maximum attempts for each request.
            limit: Optional maximum number of seeds to collect.
            max_pages: Optional maximum number of robots/sitemap documents to
                visit.
            replace: If False, raise an error when seeds.csv already exists.
            start_url: Optional robots.txt or sitemap URL to start from.
            request_func: Optional request function for tests.

        Returns:
            pandas.DataFrame: Written discovery seed table.
        '''
        if self.strategy != SITEMAP_DISCOVERY_STRATEGY:
            raise NistChemPyIndexBuildError(
                'Sitemap discovery requires strategy='
                f'{SITEMAP_DISCOVERY_STRATEGY!r}.'
            )

        self.prepare()
        request_config = _RequestConfig(
            delay=request_delay,
            max_attempts=max_attempts,
            kwargs={'timeout': timeout},
        )
        self.append_state(
            'sitemap_discovery_started',
            {
                'limit': limit,
                'max_pages': max_pages,
                'request_delay': request_delay,
                'timeout': timeout,
                'max_attempts': max_attempts,
                'start_url': start_url,
            },
        )
        try:
            seeds = _discovery.discover_sitemap(
                start_url=start_url,
                request_config=request_config,
                limit=limit,
                max_pages=max_pages,
                request_func=request_func,
            )
        except Exception as exc:
            raise NistChemPyIndexBuildError(
                f'Sitemap discovery failed: {exc}'
            ) from exc

        return self.write_seeds(
            seeds,
            replace=replace,
            source='NIST Chemistry WebBook sitemaps',
            source_path=start_url or _discovery.ROBOTS_URL,
            status='seeds_complete',
        )

    def enrich_from_seeds(
            self, seeds_path=None, request_delay=3.0, timeout=30.0,
            max_attempts=3, limit=None, resume=True, replace=True,
            request_func=None):
        '''Enrich discovery seeds into a final local WebBook index.

        This method visits one compound page per seed, parses the compound
        metadata and section-availability links, and writes the final
        ``index.csv`` table. Intermediate rows are appended to
        ``index.partial.jsonl`` so long-running jobs can be resumed.

        Args:
            seeds_path: Optional path to a seed CSV file. If omitted, use the
                local cache ``seeds.csv``.
            request_delay: Delay between NIST WebBook requests in seconds.
            timeout: Request timeout in seconds.
            max_attempts: Maximum attempts for each request.
            limit: Optional maximum number of seeds to process.
            resume: If True, reuse existing ``index.partial.jsonl`` rows.
            replace: If False, raise an error when final ``index.csv`` exists.
            request_func: Optional request function for tests.

        Returns:
            WebBookIndex: Loaded final local index.
        '''
        self.prepare()
        if self.index_path.exists() and not replace:
            raise NistChemPyIndexBuildError(
                f'Local WebBook index already exists at {self.index_path}.'
            )

        source_path = _Path(seeds_path).expanduser().resolve() if (
            seeds_path is not None
        ) else self.seeds_path
        if not source_path.exists():
            raise NistChemPyIndexBuildError(
                f'Local discovery seeds not found at {source_path}.'
            )

        try:
            seeds = _pd.read_csv(source_path, dtype='str').fillna('')
        except Exception as exc:
            raise NistChemPyIndexBuildError(
                f'Failed to read local discovery seeds from {source_path}.'
            ) from exc

        seed_fingerprint = _file_sha256(source_path)
        seed_manifest = _read_json_file(self.manifest_path)
        manifest_fingerprint = seed_manifest.get('seed_fingerprint', '')
        if self.partial_index_path.exists() and (
                not resume
                or not manifest_fingerprint
                or manifest_fingerprint != seed_fingerprint):
            self.partial_index_path.unlink()
            self.append_state(
                'partial_index_cleared',
                {
                    'reason': 'resume disabled or seed fingerprint changed',
                    'resume': bool(resume),
                    'manifest_seed_fingerprint': manifest_fingerprint,
                    'current_seed_fingerprint': seed_fingerprint,
                },
            )

        if limit is not None:
            seeds = seeds.head(limit)

        rows = _read_partial_index_rows(self.partial_index_path)
        completed_keys = {
            row.get('_seed_lookup_key', '') for row in rows
            if row.get('_seed_lookup_key', '')
        }

        request_func = request_func or _requests.make_nist_request
        request_config = _RequestConfig(
            delay=request_delay,
            max_attempts=max_attempts,
            kwargs={'timeout': timeout},
        )
        self.append_state(
            'enrichment_started',
            {
                'seed_count': len(seeds),
                'already_enriched': len(completed_keys),
                'request_delay': request_delay,
                'timeout': timeout,
                'max_attempts': max_attempts,
                'resume': bool(resume),
                'source_path': str(source_path),
            },
        )

        for _, seed in seeds.iterrows():
            seed_dict = seed.to_dict()
            lookup_key = _seed_lookup_key(seed_dict)
            if lookup_key in completed_keys:
                continue

            try:
                url = resolve_seed_url(seed_dict)
            except ValueError as exc:
                self.append_error(
                    'enrichment', str(exc), {'seed': seed_dict}
                )
                continue

            try:
                response = request_func(url, config=request_config)
            except Exception as exc:
                self.append_error(
                    'enrichment_request',
                    str(exc),
                    {'lookup_key': lookup_key, 'url': url},
                )
                continue

            if not getattr(response, 'ok', False):
                self.append_error(
                    'enrichment_response',
                    'Bad server response while enriching seed.',
                    {'lookup_key': lookup_key, 'url': url},
                )
                continue

            soup = getattr(response, 'soup', None)
            if soup is None or not _parsing.is_compound_page(soup):
                self.append_error(
                    'enrichment_parse',
                    'Response is not a single compound page.',
                    {'lookup_key': lookup_key, 'url': url},
                )
                continue

            try:
                info = _parsing.parse_compound_page(soup)
                row = flatten_compound_info(
                    info, include_cas=self.include_cas
                )
            except Exception as exc:
                self.append_error(
                    'enrichment_parse',
                    str(exc),
                    {'lookup_key': lookup_key, 'url': url},
                )
                continue

            row['_seed_lookup_key'] = lookup_key
            row['_seed_source'] = seed_dict.get('source', '')
            row['_seed_source_query'] = seed_dict.get('source_query', '')
            _append_jsonl(self.partial_index_path, row)
            rows.append(row)
            completed_keys.add(lookup_key)
            self.append_state(
                'seed_enriched',
                {
                    'lookup_key': lookup_key,
                    'ID': row.get('ID', ''),
                    'url': url,
                },
            )

        final_dataframe = _final_index_dataframe(
            rows, include_cas=self.include_cas
        )
        index = self.write_index(
            final_dataframe,
            replace=replace,
            source='NIST Chemistry WebBook compound pages',
            source_path=str(source_path),
            status='complete',
            seed_count=len(seeds),
            extra_manifest={'seed_fingerprint': seed_fingerprint},
        )
        self.append_state(
            'enrichment_finished',
            {
                'row_count': len(final_dataframe),
                'seed_count': len(seeds),
            },
        )
        return index

    def build_formula_browser_index(
            self, request_delay=3.0, timeout=30.0, max_attempts=3,
            limit=None, max_pages=None, resume=True, replace=True,
            start_url=None, discovery_request_func=None,
            enrichment_request_func=None):
        '''Build a page-enriched local index through formula-browser seeds.

        This orchestration method runs the currently implemented full network
        pipeline: formula-browser discovery followed by compound-page
        enrichment. It keeps ``discover`` and ``enrich`` available as separate
        lower-level recovery/debugging steps, but gives normal users one build
        command.

        Args:
            request_delay: Delay between NIST WebBook requests in seconds.
            timeout: Request timeout in seconds.
            max_attempts: Maximum attempts for each request.
            limit: Optional maximum number of seeds to discover and enrich.
            max_pages: Optional maximum number of discovery pages/documents to
                visit during discovery.
            resume: If True, reuse existing partial enrichment rows.
            replace: If False, raise an error when index.csv or seeds.csv
                already exists.
            start_url: Optional formula-browser URL to start from.
            discovery_request_func: Optional discovery request function for
                tests.
            enrichment_request_func: Optional enrichment request function for
                tests.

        Returns:
            WebBookIndex: Loaded final local index object.
        '''
        self.prepare()
        self.append_state(
            'build_started',
            {
                'strategy': self.strategy,
                'request_delay': request_delay,
                'timeout': timeout,
                'max_attempts': max_attempts,
                'limit': limit,
                'max_pages': max_pages,
                'resume': bool(resume),
                'replace': bool(replace),
                'start_url': start_url,
            },
        )
        self.discover_formula_browser(
            request_delay=request_delay,
            timeout=timeout,
            max_attempts=max_attempts,
            limit=limit,
            max_pages=max_pages,
            replace=replace,
            start_url=start_url,
            request_func=discovery_request_func,
        )
        index = self.enrich_from_seeds(
            request_delay=request_delay,
            timeout=timeout,
            max_attempts=max_attempts,
            limit=limit,
            resume=resume,
            replace=replace,
            request_func=enrichment_request_func,
        )
        self.append_state(
            'build_finished',
            {'strategy': self.strategy, 'row_count': len(index.data)},
        )
        return index

    def build_formula_search_index(
            self, request_delay=3.0, timeout=30.0, max_attempts=3,
            limit=None, max_queries=None, resume=True, replace=True,
            carbon_start=1, carbon_end=None, hydrogen_max=149,
            heteroatom_max=50, elements=None, discovery_search_func=None,
            enrichment_request_func=None):
        '''Build a page-enriched local index through formula-search seeds.

        Formula-search discovery is a bounded carbon-formula strategy promoted
        from the legacy updater prototype. It discovers seed IDs first and then
        uses the shared compound-page enrichment stage to build ``index.csv``.

        Args:
            request_delay: Delay between NIST WebBook requests in seconds.
            timeout: Request timeout in seconds.
            max_attempts: Maximum attempts for each request.
            limit: Optional maximum number of seeds to discover and enrich.
            max_queries: Optional maximum number of formula-search queries to
                run during discovery.
            resume: If True, reuse existing partial enrichment rows.
            replace: If False, raise an error when output artifacts exist.
            carbon_start: First carbon count to scan, inclusive.
            carbon_end: Last carbon count to scan, inclusive. Required for
                formula-search discovery.
            hydrogen_max: Maximum hydrogen count used for refinement.
            heteroatom_max: Maximum one-heteroelement count used for
                refinement.
            elements: Optional iterable or comma-separated string of element
                symbols used for refinement.
            discovery_search_func: Optional search function for tests.
            enrichment_request_func: Optional enrichment request function for
                tests.

        Returns:
            WebBookIndex: Loaded final local index object.
        '''
        self.prepare()
        self.append_state(
            'build_started',
            {
                'strategy': self.strategy,
                'request_delay': request_delay,
                'timeout': timeout,
                'max_attempts': max_attempts,
                'limit': limit,
                'max_queries': max_queries,
                'resume': bool(resume),
                'replace': bool(replace),
                'carbon_start': carbon_start,
                'carbon_end': carbon_end,
                'hydrogen_max': hydrogen_max,
                'heteroatom_max': heteroatom_max,
                'elements': elements,
            },
        )
        self.discover_formula_search(
            request_delay=request_delay,
            timeout=timeout,
            max_attempts=max_attempts,
            limit=limit,
            max_queries=max_queries,
            replace=replace,
            carbon_start=carbon_start,
            carbon_end=carbon_end,
            hydrogen_max=hydrogen_max,
            heteroatom_max=heteroatom_max,
            elements=elements,
            search_func=discovery_search_func,
        )
        index = self.enrich_from_seeds(
            request_delay=request_delay,
            timeout=timeout,
            max_attempts=max_attempts,
            limit=limit,
            resume=resume,
            replace=replace,
            request_func=enrichment_request_func,
        )
        self.append_state(
            'build_finished',
            {'strategy': self.strategy, 'row_count': len(index.data)},
        )
        return index

    def build_sitemap_index(
            self, request_delay=3.0, timeout=30.0, max_attempts=3,
            limit=None, max_pages=None, resume=True, replace=True,
            start_url=None, discovery_request_func=None,
            enrichment_request_func=None):
        '''Build a page-enriched local index through sitemap seeds.

        This orchestration method runs sitemap discovery followed by
        compound-page enrichment. Sitemap discovery is mostly useful as an
        audit/supplemental source; final metadata still comes from compound
        pages.

        Args:
            request_delay: Delay between NIST WebBook requests in seconds.
            timeout: Request timeout in seconds.
            max_attempts: Maximum attempts for each request.
            limit: Optional maximum number of seeds to discover and enrich.
            max_pages: Optional maximum number of robots/sitemap documents to
                visit during discovery.
            resume: If True, reuse existing partial enrichment rows.
            replace: If False, raise an error when index.csv or seeds.csv
                already exists.
            start_url: Optional robots.txt or sitemap URL to start from.
            discovery_request_func: Optional discovery request function for
                tests.
            enrichment_request_func: Optional enrichment request function for
                tests.

        Returns:
            WebBookIndex: Loaded final local index object.
        '''
        self.prepare()
        self.append_state(
            'build_started',
            {
                'strategy': self.strategy,
                'request_delay': request_delay,
                'timeout': timeout,
                'max_attempts': max_attempts,
                'limit': limit,
                'max_pages': max_pages,
                'resume': bool(resume),
                'replace': bool(replace),
                'start_url': start_url,
            },
        )
        self.discover_sitemap(
            request_delay=request_delay,
            timeout=timeout,
            max_attempts=max_attempts,
            limit=limit,
            max_pages=max_pages,
            replace=replace,
            start_url=start_url,
            request_func=discovery_request_func,
        )
        index = self.enrich_from_seeds(
            request_delay=request_delay,
            timeout=timeout,
            max_attempts=max_attempts,
            limit=limit,
            resume=resume,
            replace=replace,
            request_func=enrichment_request_func,
        )
        self.append_state(
            'build_finished',
            {'strategy': self.strategy, 'row_count': len(index.data)},
        )
        return index

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
            status='complete', artifact='index', seed_count=None,
            extra=None) -> dict:
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
        if extra:
            manifest.update(extra)
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
        max_pages: Optional maximum number of discovery pages/documents to
            visit.
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


def discover_formula_search(
        path=None, accept_data_terms=False, request_delay=3.0, timeout=30.0,
        max_attempts=3, limit=None, max_queries=None, replace=True,
        carbon_start=1, carbon_end=None, hydrogen_max=149,
        heteroatom_max=50, elements=None):
    '''Discover formula-search seeds into a local cache directory.

    Args:
        path: Optional local index directory.
        accept_data_terms: Explicit acknowledgement that generated local data
            are local user artifacts.
        request_delay: Delay between NIST WebBook requests in seconds.
        timeout: Request timeout in seconds.
        max_attempts: Maximum attempts for each request.
        limit: Optional maximum number of seeds to collect.
        max_queries: Optional maximum number of formula-search queries to
            run.
        replace: If False, raise an error when seeds.csv exists.
        carbon_start: First carbon count to scan, inclusive.
        carbon_end: Last carbon count to scan, inclusive.
        hydrogen_max: Maximum hydrogen count used for refinement.
        heteroatom_max: Maximum one-heteroelement count used for refinement.
        elements: Optional iterable or comma-separated string of element
            symbols.

    Returns:
        pandas.DataFrame: Written discovery seed table.
    '''
    builder = LocalIndexBuilder(
        path=path,
        strategy=FORMULA_SEARCH_DISCOVERY_STRATEGY,
        capabilities=('compound_discovery_seeds',),
        accept_data_terms=accept_data_terms,
    )
    return builder.discover_formula_search(
        request_delay=request_delay,
        timeout=timeout,
        max_attempts=max_attempts,
        limit=limit,
        max_queries=max_queries,
        replace=replace,
        carbon_start=carbon_start,
        carbon_end=carbon_end,
        hydrogen_max=hydrogen_max,
        heteroatom_max=heteroatom_max,
        elements=elements,
    )


def discover_sitemap(
        path=None, accept_data_terms=False, request_delay=3.0, timeout=30.0,
        max_attempts=3, limit=None, max_pages=None, replace=True,
        start_url=None):
    '''Discover sitemap seeds into a local cache directory.

    Args:
        path: Optional local index directory.
        accept_data_terms: Explicit acknowledgement that generated local data
            are local user artifacts.
        request_delay: Delay between NIST WebBook requests in seconds.
        timeout: Request timeout in seconds.
        max_attempts: Maximum attempts for each request.
        limit: Optional maximum number of seeds to collect.
        max_pages: Optional maximum number of robots/sitemap documents to
            visit.
        replace: If False, raise an error when seeds.csv exists.
        start_url: Optional robots.txt or sitemap URL to start from.

    Returns:
        pandas.DataFrame: Written discovery seed table.
    '''
    builder = LocalIndexBuilder(
        path=path,
        strategy=SITEMAP_DISCOVERY_STRATEGY,
        capabilities=('compound_discovery_seeds',),
        accept_data_terms=accept_data_terms,
    )
    return builder.discover_sitemap(
        request_delay=request_delay,
        timeout=timeout,
        max_attempts=max_attempts,
        limit=limit,
        max_pages=max_pages,
        replace=replace,
        start_url=start_url,
    )


def enrich_index_from_seeds(
        path=None, seeds_path=None, accept_data_terms=False,
        request_delay=3.0, timeout=30.0, max_attempts=3, limit=None,
        resume=True, replace=True, request_func=None, strategy=None,
        include_cas=None):
    '''Enrich local discovery seeds into a final local index.

    Args:
        path: Optional local index directory.
        seeds_path: Optional explicit discovery seed CSV path.
        accept_data_terms: Explicit acknowledgement that generated local data
            are local user artifacts.
        request_delay: Delay between NIST WebBook requests in seconds.
        timeout: Request timeout in seconds.
        max_attempts: Maximum attempts for each request.
        limit: Optional maximum number of seeds to process.
        resume: If True, reuse existing partial enrichment rows.
        replace: If False, raise an error when index.csv exists.
        request_func: Optional request function for tests.
        strategy: Optional strategy override. If omitted, use the existing
            local manifest when available.
        include_cas: Optional CAS RN inclusion override. If omitted, use the
            existing local manifest when available.

    Returns:
        WebBookIndex: Loaded final local index object.
    '''
    resolved_path = _resolve_index_path(path)
    manifest = _read_json_file(resolved_path / MANIFEST_FILENAME)
    inferred_strategy = strategy or manifest.get(
        'strategy', DEFAULT_DISCOVERY_STRATEGY
    )
    inferred_include_cas = include_cas
    if inferred_include_cas is None:
        inferred_include_cas = manifest.get('include_cas', True)

    builder = LocalIndexBuilder(
        path=resolved_path,
        strategy=inferred_strategy,
        include_cas=bool(inferred_include_cas),
        accept_data_terms=accept_data_terms,
    )
    return builder.enrich_from_seeds(
        seeds_path=seeds_path,
        request_delay=request_delay,
        timeout=timeout,
        max_attempts=max_attempts,
        limit=limit,
        resume=resume,
        replace=replace,
        request_func=request_func,
    )


def build_index(
        path=None, strategy=DEFAULT_DISCOVERY_STRATEGY, source_csv=None,
        include_cas=True, accept_data_terms=False, replace=True,
        request_delay=3.0, timeout=30.0, max_attempts=3, limit=None,
        max_pages=None, resume=True, start_url=None, max_queries=None,
        carbon_start=1, carbon_end=None, hydrogen_max=149,
        heteroatom_max=50, elements=None):
    '''Build or import a user-local WebBook index.

    Args:
        path: Optional destination local index directory.
        strategy: Compound-discovery strategy. The current network builder
            implements ``formula-browser``, ``formula-search``, and
            ``sitemap``.
        source_csv: Optional existing local CSV file to import instead of
            running network discovery/enrichment.
        include_cas: Whether the local index intentionally includes CAS RN
            values.
        accept_data_terms: Explicit acknowledgement that generated/imported
            local data are local user artifacts.
        replace: If False, raise an error when destination artifacts exist.
        request_delay: Delay between NIST WebBook requests in seconds.
        timeout: Request timeout in seconds.
        max_attempts: Maximum attempts for each request.
        limit: Optional maximum number of seeds to discover/enrich.
        max_pages: Optional maximum number of discovery pages/documents to
            visit.
        resume: If True, reuse existing partial enrichment rows.
        start_url: Optional formula-browser, robots.txt, or sitemap URL to
            start from.
        max_queries: Optional maximum number of formula-search queries to
            run.
        carbon_start: First carbon count to scan for formula-search
            discovery.
        carbon_end: Last carbon count to scan for formula-search discovery.
        hydrogen_max: Maximum hydrogen count for formula-search refinement.
        heteroatom_max: Maximum one-heteroelement count for formula-search
            refinement.
        elements: Optional formula-search element list.

    Returns:
        WebBookIndex: Loaded local index object.
    '''
    if source_csv is not None:
        return import_index_csv(
            source_csv,
            path=path,
            include_cas=include_cas,
            accept_data_terms=accept_data_terms,
            replace=replace,
        )

    if strategy not in (
            DEFAULT_DISCOVERY_STRATEGY,
            FORMULA_SEARCH_DISCOVERY_STRATEGY,
            SITEMAP_DISCOVERY_STRATEGY,
    ):
        raise NistChemPyIndexBuildError(unavailable_discovery_message())

    builder = LocalIndexBuilder(
        path=path,
        strategy=strategy,
        include_cas=include_cas,
        accept_data_terms=accept_data_terms,
    )
    build_method = builder.build_formula_browser_index
    build_kwargs = {
        'request_delay': request_delay,
        'timeout': timeout,
        'max_attempts': max_attempts,
        'limit': limit,
        'max_pages': max_pages,
        'resume': resume,
        'replace': replace,
        'start_url': start_url,
    }
    if strategy == FORMULA_SEARCH_DISCOVERY_STRATEGY:
        build_method = builder.build_formula_search_index
        build_kwargs = {
            'request_delay': request_delay,
            'timeout': timeout,
            'max_attempts': max_attempts,
            'limit': limit,
            'max_queries': max_queries,
            'resume': resume,
            'replace': replace,
            'carbon_start': carbon_start,
            'carbon_end': carbon_end,
            'hydrogen_max': hydrogen_max,
            'heteroatom_max': heteroatom_max,
            'elements': elements,
        }
    elif strategy == SITEMAP_DISCOVERY_STRATEGY:
        build_method = builder.build_sitemap_index

    return build_method(**build_kwargs)


def import_index_csv(
        csv_path, path=None, include_cas=True, accept_data_terms=False,
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
    '''Return the message for unsupported network index builders.'''
    return (
        'Supported network build strategies are formula-browser, '
        'formula-search, and sitemap. Use --from-csv to import an existing '
        'local CSV index.'
    )


def unavailable_discovery_message() -> str:
    '''Return the message for unsupported discovery-only builders.'''
    return (
        'Supported discovery strategies are formula-browser, formula-search, '
        'and sitemap.'
    )


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


def _file_sha256(path: _Path) -> str:
    hasher = _hashlib.sha256()
    with open(path, 'rb') as infile:
        for chunk in iter(lambda: infile.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def _read_json_file(path: _Path) -> dict:
    if not path.exists():
        return {}
    try:
        return _json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


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
