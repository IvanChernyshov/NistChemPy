'''Command-line interface for NistChemPy.'''

from __future__ import annotations

import argparse as _argparse
import sys as _sys

from nistchempy.cache import resolve_index_path as _resolve_index_path
from nistchempy.exceptions import NistChemPyIndexNotFoundError
from nistchempy.index import WebBookIndex


_NOTICE = '''NistChemPy does not ship a prebuilt NIST Chemistry WebBook index.
Local index files are user-generated artifacts and are not covered by the
NistChemPy software license. Full section-availability indexes may require
visiting one WebBook compound page per compound and can take several days with
a polite request delay.'''


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
    if not WebBookIndex.exists(path):
        print(f'No local WebBook index found at {path}.', file=_sys.stderr)
        return 1

    index = WebBookIndex.from_cache(path)
    print(f'Path: {index.path}')
    print(f'Rows: {len(index.data)}')
    mode = index.manifest.get('mode', 'unknown')
    print(f'Mode: {mode}')
    capabilities = index.manifest.get('capabilities', [])
    if capabilities:
        print('Capabilities: ' + ', '.join(capabilities))
    return 0


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
