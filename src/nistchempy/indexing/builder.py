'''User-local WebBook index build/write helpers.'''

from __future__ import annotations

import json as _json
import typing as _tp
import uuid as _uuid
from pathlib import Path as _Path

import pandas as _pd

import nistchempy.indexing.discovery as _discovery
import nistchempy.parsing as _parsing
import nistchempy.requests as _requests
from nistchempy.indexing.cache import resolve_index_path as _resolve_index_path
from nistchempy.indexing.artifacts import file_sha256 as _file_sha256
from nistchempy.indexing.artifacts import read_json_file as _read_json_file
from nistchempy.indexing.artifacts import utc_timestamp as _utc_timestamp
from nistchempy.exceptions import NistChemPyDataTermsError
from nistchempy.exceptions import NistChemPyIndexBuildError
from nistchempy.indexing.core import WebBookIndex
from nistchempy.indexing.enrichment import _append_jsonl
from nistchempy.indexing.enrichment import _drop_cas_if_needed
from nistchempy.indexing.enrichment import _final_index_dataframe
from nistchempy.indexing.enrichment import _read_partial_index_rows
from nistchempy.indexing.enrichment import _seed_lookup_key
from nistchempy.indexing.enrichment import flatten_compound_info
from nistchempy.indexing.enrichment import resolve_seed_url
from nistchempy.indexing.schema import DEFAULT_DISCOVERY_STRATEGY
from nistchempy.indexing.schema import DEFAULT_INDEX_CAPABILITIES
from nistchempy.indexing.schema import INDEX_FILENAME
from nistchempy.indexing.schema import MANIFEST_FILENAME
from nistchempy.indexing.schema import DEFAULT_SOURCE_NOTICE
from nistchempy.indexing.schema import ERRORS_FILENAME
from nistchempy.indexing.schema import FORMULA_SEARCH_DISCOVERY_STRATEGY
from nistchempy.indexing.schema import LOCAL_CSV_STRATEGY
from nistchempy.indexing.schema import PARTIAL_INDEX_FILENAME
from nistchempy.indexing.schema import SEEDS_FILENAME
from nistchempy.indexing.schema import SITEMAP_DISCOVERY_STRATEGY
from nistchempy.indexing.schema import STATE_FILENAME
from nistchempy.indexing.schema import TMP_DIR_NAME
from nistchempy.indexing.schema import VALID_DISCOVERY_STRATEGIES
from nistchempy.indexing.schema import VALID_MANIFEST_STRATEGIES
from nistchempy.indexing.schema import DiscoverySeed
from nistchempy.indexing.schema import as_dataframe as _as_dataframe
from nistchempy.indexing.schema import as_seed_dataframe as _as_seed_dataframe
from nistchempy.requests import RequestConfig as _RequestConfig

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

        This method wraps the bounded carbon-formula search strategy as a
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
        lost_queries = []
        failed_queries = []
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
                lost_queries=lost_queries,
                failed_queries=failed_queries,
            )
        except ValueError as exc:
            raise NistChemPyIndexBuildError(str(exc)) from exc
        except Exception as exc:
            raise NistChemPyIndexBuildError(
                f'Formula-search discovery failed: {exc}'
            ) from exc

        seed_table = self.write_seeds(
            seeds,
            replace=replace,
            source='NIST Chemistry WebBook formula search',
            source_path=(
                f'C{carbon_start}..C{carbon_end}; '
                f'H0..H{hydrogen_max}; heteroatom<={heteroatom_max}'
            ),
            status='seeds_complete',
        )
        for lost_query in lost_queries:
            self.append_error(
                'formula_search_lost_query',
                lost_query.get('reason', 'Formula-search query was lost.'),
                lost_query,
            )
        for failed_query in failed_queries:
            self.append_error(
                'formula_search_failed_query',
                failed_query.get(
                    'reason', 'Formula-search query did not succeed.'
                ),
                failed_query,
            )
        if lost_queries:
            self.append_state(
                'formula_search_lost_queries_recorded',
                {'lost_query_count': len(lost_queries)},
            )
        if failed_queries:
            self.append_state(
                'formula_search_failed_queries_recorded',
                {'failed_query_count': len(failed_queries)},
            )
        return seed_table

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
        from the historical updater strategy. It discovers seed IDs first and then
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
