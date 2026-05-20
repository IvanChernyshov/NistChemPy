'''High-level local WebBook index build orchestration.'''

from __future__ import annotations

from pathlib import Path as _Path

from nistchempy.exceptions import NistChemPyIndexBuildError
from nistchempy.indexing.artifacts import read_json_file as _read_json_file
from nistchempy.indexing.builder import LocalIndexBuilder
from nistchempy.indexing.cache import resolve_index_path as _resolve_index_path
from nistchempy.indexing.core import MANIFEST_FILENAME
from nistchempy.indexing.schema import DEFAULT_DISCOVERY_STRATEGY
from nistchempy.indexing.schema import FORMULA_SEARCH_DISCOVERY_STRATEGY
from nistchempy.indexing.schema import LOCAL_CSV_STRATEGY
from nistchempy.indexing.schema import SITEMAP_DISCOVERY_STRATEGY


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
        path: Optional local index directory. Direct CSV paths are not
            valid because enrichment needs cache-local seed, state, and
            partial-index artifacts.
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
    if resolved_path.suffix.lower() == '.csv' or resolved_path.is_file():
        raise NistChemPyIndexBuildError(
            'Seed enrichment requires a local index directory, not a direct '
            f'CSV file path: {resolved_path}.'
        )
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
