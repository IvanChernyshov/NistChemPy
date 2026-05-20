'''Command-line interface for NistChemPy.'''

from __future__ import annotations

import argparse as _argparse
import json as _json
import sys as _sys

from nistchempy.indexing.cache import resolve_index_path as _resolve_index_path
from nistchempy.exceptions import NistChemPyDataTermsError
from nistchempy.exceptions import NistChemPyIndexBuildError
from nistchempy.exceptions import NistChemPyIndexNotFoundError
from nistchempy.indexing.core import MANIFEST_FILENAME
from nistchempy.indexing.core import WebBookIndex
from nistchempy.indexing.schema import PARTIAL_INDEX_FILENAME
from nistchempy.indexing.schema import SEEDS_FILENAME
from nistchempy.indexing.schema import VALID_DISCOVERY_STRATEGIES


_NOTICE = '''NistChemPy does not ship a prebuilt NIST Chemistry WebBook index.
Local index files are user-generated artifacts and are not covered by the
NistChemPy software license. Full section-availability indexes may require
visiting one WebBook compound page per compound and can take about
3.5-5+ days with a polite 3 second request delay before retries and
network overhead.'''


def _add_path_argument(parser):
    parser.add_argument(
        '--path',
        default=None,
        help=(
            'Local WebBook index directory or CSV file. Overrides '
            'NISTCHEMPY_INDEX_PATH.'
        ),
    )


def _cmd_index_path(args) -> int:
    print(_resolve_index_path(args.path))
    return 0


def _cmd_index_notice(args) -> int:
    print(_NOTICE)
    return 0


def _cmd_index_status(args) -> int:
    path = _resolve_index_path(args.path)
    if WebBookIndex.exists(path):
        index = WebBookIndex.from_cache(path)
        print(f'Path: {index.path}')
        print(f'Rows: {len(index.data)}')
        strategy = index.manifest.get(
            'strategy', index.manifest.get('mode', 'unknown')
        )
        print(f'Strategy: {strategy}')
        capabilities = index.manifest.get('capabilities', [])
        if capabilities:
            print('Capabilities: ' + ', '.join(capabilities))
        return 0

    manifest = _read_manifest_if_available(path)
    seeds_path = path / SEEDS_FILENAME
    partial_path = path / PARTIAL_INDEX_FILENAME
    if seeds_path.exists():
        print(f'Path: {path}')
        print(f'Seeds: {seeds_path}')
        if partial_path.exists():
            print(f'Partial index: {partial_path}')
        if manifest:
            strategy = manifest.get('strategy', 'unknown')
            print(f'Strategy: {strategy}')
            seed_count = manifest.get('seed_count', 'unknown')
            print(f'Seed rows: {seed_count}')
            print(f'Status: {manifest.get("status", "unknown")}')
        print('Final index: missing')
        return 0

    if partial_path.exists():
        print(f'Path: {path}')
        print(f'Partial index: {partial_path}')
        print('Final index: missing')
        return 0

    print(f'No local WebBook index found at {path}.', file=_sys.stderr)
    return 1


def _cmd_index_search(args) -> int:
    try:
        index = WebBookIndex.from_cache(args.path)
    except NistChemPyIndexNotFoundError as exc:
        print(str(exc), file=_sys.stderr)
        return 1

    fields = args.field if args.field else None
    sections = args.has_section if args.has_section else None
    result = index.search(
        args.query,
        fields=fields,
        sections=sections,
        limit=args.limit,
    )

    if args.format == 'csv':
        print(result.to_csv(index=False), end='')
    elif args.format == 'json':
        print(result.to_json(orient='records'))
    else:
        print(result.to_string(index=False))
    return 0


def _cmd_index_build(args) -> int:
    try:
        index = WebBookIndex.build(
            path=args.path,
            strategy=args.strategy,
            source_csv=args.from_csv,
            include_cas=not args.exclude_cas,
            accept_data_terms=args.accept_data_terms,
            replace=not args.no_replace,
            request_delay=args.request_delay,
            timeout=args.timeout,
            max_attempts=args.max_attempts,
            limit=args.limit,
            max_pages=args.max_pages,
            resume=not args.no_resume,
            start_url=args.start_url,
            max_queries=args.max_queries,
            carbon_start=args.formula_carbon_start,
            carbon_end=args.formula_carbon_end,
            hydrogen_max=args.formula_hydrogen_max,
            heteroatom_max=args.formula_heteroatom_max,
            elements=args.formula_elements,
        )
    except (NistChemPyDataTermsError, NistChemPyIndexBuildError) as exc:
        print(str(exc), file=_sys.stderr)
        return 1

    print(f'Local WebBook index written to {index.path}.')
    print(f'Rows: {len(index.data)}')
    return 0


def _cmd_index_update(args) -> int:
    try:
        index = WebBookIndex.update(
            path=args.path,
            strategy=args.strategy,
            source_csv=args.from_csv,
            include_cas=not args.exclude_cas,
            accept_data_terms=args.accept_data_terms,
            request_delay=args.request_delay,
            timeout=args.timeout,
            max_attempts=args.max_attempts,
            limit=args.limit,
            max_pages=args.max_pages,
            resume=not args.no_resume,
            start_url=args.start_url,
            max_queries=args.max_queries,
            carbon_start=args.formula_carbon_start,
            carbon_end=args.formula_carbon_end,
            hydrogen_max=args.formula_hydrogen_max,
            heteroatom_max=args.formula_heteroatom_max,
            elements=args.formula_elements,
        )
    except (NistChemPyDataTermsError, NistChemPyIndexBuildError) as exc:
        print(str(exc), file=_sys.stderr)
        return 1

    print(f'Local WebBook index updated at {index.path}.')
    print(f'Rows: {len(index.data)}')
    return 0


def _cmd_index_discover(args) -> int:
    try:
        seeds = WebBookIndex.discover(
            path=args.path,
            strategy=args.strategy,
            accept_data_terms=args.accept_data_terms,
            request_delay=args.request_delay,
            timeout=args.timeout,
            max_attempts=args.max_attempts,
            limit=args.limit,
            max_pages=args.max_pages,
            replace=not args.no_replace,
            start_url=args.start_url,
            max_queries=args.max_queries,
            carbon_start=args.formula_carbon_start,
            carbon_end=args.formula_carbon_end,
            hydrogen_max=args.formula_hydrogen_max,
            heteroatom_max=args.formula_heteroatom_max,
            elements=args.formula_elements,
        )
    except (NistChemPyDataTermsError, NistChemPyIndexBuildError) as exc:
        print(str(exc), file=_sys.stderr)
        return 1

    path = _resolve_index_path(args.path)
    print(f'Local discovery seeds written to {path}.')
    print(f'Seed rows: {len(seeds)}')
    return 0


def _cmd_index_enrich(args) -> int:
    try:
        index = WebBookIndex.enrich(
            path=args.path,
            seeds_path=args.seeds,
            accept_data_terms=args.accept_data_terms,
            request_delay=args.request_delay,
            timeout=args.timeout,
            max_attempts=args.max_attempts,
            limit=args.limit,
            resume=not args.no_resume,
            replace=not args.no_replace,
        )
    except (NistChemPyDataTermsError, NistChemPyIndexBuildError) as exc:
        print(str(exc), file=_sys.stderr)
        return 1

    print(f'Local WebBook index written to {index.path}.')
    print(f'Rows: {len(index.data)}')
    return 0


def _add_strategy_argument(parser):
    parser.add_argument(
        '--strategy',
        choices=VALID_DISCOVERY_STRATEGIES,
        default='formula-browser',
        help='Compound-ID discovery strategy for network builds.',
    )


def _add_formula_search_arguments(parser):
    parser.add_argument(
        '--formula-carbon-start',
        type=int,
        default=1,
        help='First carbon count for formula-search discovery.',
    )
    parser.add_argument(
        '--formula-carbon-end',
        type=int,
        default=None,
        help=(
            'Last carbon count for formula-search discovery. Required when '
            'using --strategy formula-search.'
        ),
    )
    parser.add_argument(
        '--formula-hydrogen-max',
        type=int,
        default=149,
        help='Maximum hydrogen count for formula-search refinement.',
    )
    parser.add_argument(
        '--formula-heteroatom-max',
        type=int,
        default=50,
        help='Maximum one-heteroelement count for formula-search refinement.',
    )
    parser.add_argument(
        '--formula-elements',
        default=None,
        help=(
            'Comma-separated element symbols for formula-search refinement. '
            'If omitted, use the legacy non-C/non-H element list.'
        ),
    )
    parser.add_argument(
        '--max-queries',
        type=int,
        default=None,
        help='Maximum number of formula-search queries to run.',
    )


def _add_build_arguments(parser):
    _add_path_argument(parser)
    _add_strategy_argument(parser)
    parser.add_argument(
        '--from-csv',
        default=None,
        help=(
            'Import an existing local CSV file into the cache layout instead '
            'of running network discovery and enrichment.'
        ),
    )
    parser.add_argument(
        '--exclude-cas',
        action='store_true',
        help='Record that the imported/generated local index omits CAS RN.',
    )
    parser.add_argument(
        '--accept-data-terms',
        action='store_true',
        help=(
            'Acknowledge that generated/imported WebBook-derived local data '
            'are local user artifacts and are not redistributed or licensed '
            'by NistChemPy.'
        ),
    )
    parser.add_argument(
        '--request-delay',
        type=float,
        default=3.0,
        help='Delay between NIST WebBook requests in seconds.',
    )
    parser.add_argument(
        '--timeout',
        type=float,
        default=30.0,
        help='Request timeout in seconds.',
    )
    parser.add_argument(
        '--max-attempts',
        type=int,
        default=3,
        help='Maximum request attempts per WebBook page.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of discovery seeds to discover/enrich.',
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=None,
        help='Maximum number of discovery pages/documents to visit.',
    )
    parser.add_argument(
        '--start-url',
        default=None,
        help=(
            'Optional formula-browser, robots.txt, or sitemap URL to '
            'start from.'
        ),
    )
    _add_formula_search_arguments(parser)
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Do not reuse existing partial enrichment rows.',
    )


def _read_manifest_if_available(path):
    manifest_path = path / MANIFEST_FILENAME
    if not manifest_path.exists():
        return {}
    with open(manifest_path, 'r', encoding='utf-8') as infile:
        return _json.load(infile)


def _build_parser():
    parser = _argparse.ArgumentParser(prog='nistchempy')
    subparsers = parser.add_subparsers(dest='command')

    index_parser = subparsers.add_parser(
        'index', help='Manage user-local WebBook indexes.'
    )
    index_subparsers = index_parser.add_subparsers(dest='index_command')

    path_parser = index_subparsers.add_parser(
        'path', help='Print the resolved local index path.'
    )
    _add_path_argument(path_parser)
    path_parser.set_defaults(func=_cmd_index_path)

    notice_parser = index_subparsers.add_parser(
        'notice', help='Print the local data notice.'
    )
    notice_parser.set_defaults(func=_cmd_index_notice)

    status_parser = index_subparsers.add_parser(
        'status', help='Show local index status.'
    )
    _add_path_argument(status_parser)
    status_parser.set_defaults(func=_cmd_index_status)

    build_parser = index_subparsers.add_parser(
        'build', help='Build or import a user-local WebBook index.'
    )
    _add_build_arguments(build_parser)
    build_parser.add_argument(
        '--no-replace',
        action='store_true',
        help='Fail if the destination index.csv already exists.',
    )
    build_parser.set_defaults(func=_cmd_index_build)

    update_parser = index_subparsers.add_parser(
        'update', help='Update a user-local WebBook index.'
    )
    _add_build_arguments(update_parser)
    update_parser.set_defaults(func=_cmd_index_update)

    discover_parser = index_subparsers.add_parser(
        'discover', help='Create intermediate discovery seeds.'
    )
    _add_path_argument(discover_parser)
    _add_strategy_argument(discover_parser)
    discover_parser.add_argument(
        '--accept-data-terms',
        action='store_true',
        help='Acknowledge local data-generation terms.',
    )
    discover_parser.add_argument(
        '--request-delay',
        type=float,
        default=3.0,
        help='Delay between NIST WebBook requests in seconds.',
    )
    discover_parser.add_argument(
        '--timeout',
        type=float,
        default=30.0,
        help='Request timeout in seconds.',
    )
    discover_parser.add_argument(
        '--max-attempts',
        type=int,
        default=3,
        help='Maximum request attempts per discovery page/document.',
    )
    discover_parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of unique discovery seeds to collect.',
    )
    discover_parser.add_argument(
        '--max-pages',
        type=int,
        default=None,
        help='Maximum number of discovery pages/documents to visit.',
    )
    discover_parser.add_argument(
        '--start-url',
        default=None,
        help=(
            'Optional formula-browser, robots.txt, or sitemap URL to '
            'start from.'
        ),
    )
    _add_formula_search_arguments(discover_parser)
    discover_parser.add_argument(
        '--no-replace',
        action='store_true',
        help='Fail if the destination seeds.csv already exists.',
    )
    discover_parser.set_defaults(func=_cmd_index_discover)

    enrich_parser = index_subparsers.add_parser(
        'enrich', help='Enrich discovery seeds into a local WebBook index.'
    )
    _add_path_argument(enrich_parser)
    enrich_parser.add_argument(
        '--seeds',
        default=None,
        help='Optional explicit discovery seeds CSV file.',
    )
    enrich_parser.add_argument(
        '--accept-data-terms',
        action='store_true',
        help='Acknowledge local data-generation terms.',
    )
    enrich_parser.add_argument(
        '--request-delay',
        type=float,
        default=3.0,
        help='Delay between NIST WebBook requests in seconds.',
    )
    enrich_parser.add_argument(
        '--timeout',
        type=float,
        default=30.0,
        help='Request timeout in seconds.',
    )
    enrich_parser.add_argument(
        '--max-attempts',
        type=int,
        default=3,
        help='Maximum request attempts per compound page.',
    )
    enrich_parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of seeds to process.',
    )
    enrich_parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Discard existing partial enrichment rows before running.',
    )
    enrich_parser.add_argument(
        '--no-replace',
        action='store_true',
        help='Fail if the destination index.csv already exists.',
    )
    enrich_parser.set_defaults(func=_cmd_index_enrich)

    search_parser = index_subparsers.add_parser(
        'search', help='Search a local WebBook index.'
    )
    _add_path_argument(search_parser)
    search_parser.add_argument('query', help='Search query.')
    search_parser.add_argument(
        '--field', action='append', help='Index column to search.'
    )
    search_parser.add_argument(
        '--has-section', action='append', help='Require a non-empty section.'
    )
    search_parser.add_argument(
        '--limit', type=int, default=None, help='Maximum number of rows.'
    )
    search_parser.add_argument(
        '--format', choices=('table', 'csv', 'json'), default='table'
    )
    search_parser.set_defaults(func=_cmd_index_search)

    return parser


def main(argv=None) -> int:
    '''Run the NistChemPy command-line interface.

    Args:
        argv: Optional argument list. If omitted, sys.argv is used.

    Returns:
        int: Process exit status.
    '''
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, 'func'):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
