'''Check built distributions for generated WebBook data artifacts.'''

from __future__ import annotations

import argparse
import fnmatch
import sys
import tarfile
import zipfile
from pathlib import Path


FORBIDDEN_PATTERNS = (
    '*/nistchempy/data/*',
    '*/src/nistchempy/data/*',
    '*/nist_data.zip',
    '*/nist_data.csv',
    'nist_data.zip',
    'nist_data.csv',
    '*/compounds_data.json',
    'compounds_data.json',
    '*/compound_htmls/*',
    '*/compound_htmls',
    'compound_htmls/*',
    'compound_htmls',
)

ARCHIVE_SUFFIXES = (
    '.tar',
    '.tar.gz',
    '.tgz',
    '.tar.bz2',
    '.tbz2',
    '.tar.xz',
    '.txz',
    '.whl',
    '.zip',
)


def normalize_artifact_name(name: str) -> str:
    '''Return a normalized archive member or filesystem path.

    Args:
        name: Archive member name or filesystem path.

    Returns:
        The normalized path-like name with forward slashes.
    '''
    return name.replace('\\', '/').lstrip('./')


def is_forbidden_artifact_name(name: str) -> bool:
    '''Return whether an artifact member name is forbidden.

    Args:
        name: Archive member name or filesystem path.

    Returns:
        True if the name matches a generated WebBook artifact pattern.
    '''
    normalized = normalize_artifact_name(name)
    return any(
        fnmatch.fnmatch(normalized, pattern)
        for pattern in FORBIDDEN_PATTERNS
    )


def iter_artifact_members(path: Path):
    '''Yield artifact member names from an archive or directory.

    Args:
        path: Distribution archive or directory to inspect.

    Yields:
        str: Path-like artifact member names.

    Raises:
        ValueError: If the file type is not supported.
    '''
    if path.is_dir():
        for item in path.rglob('*'):
            if item.is_file():
                yield item.relative_to(path).as_posix()
        return

    name = path.name.lower()
    if name.endswith(('.whl', '.zip')):
        with zipfile.ZipFile(path) as archive:
            yield from archive.namelist()
        return

    if any(name.endswith(suffix) for suffix in ARCHIVE_SUFFIXES):
        with tarfile.open(path) as archive:
            yield from archive.getnames()
        return

    raise ValueError(f'Unsupported artifact type: {path}')


def find_forbidden_artifacts(paths):
    '''Return forbidden entries found in distribution artifacts.

    Args:
        paths: Iterable of files or directories to inspect.

    Returns:
        list[tuple[str, str]]: Pairs of artifact path and forbidden member.
    '''
    findings = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            findings.append((str(path), '<missing artifact>'))
            continue
        for member in iter_artifact_members(path):
            if is_forbidden_artifact_name(member):
                findings.append((str(path), member))
    return findings


def _default_artifact_paths() -> list[Path]:
    '''Return default distribution artifact paths from ./dist.

    Returns:
        list[Path]: Existing distribution artifacts.
    '''
    dist = Path('dist')
    if not dist.exists():
        return []
    return [path for path in dist.iterdir() if path.is_file()]


def parse_args(argv=None):
    '''Parse command-line arguments.

    Args:
        argv: Optional command-line argument list.

    Returns:
        argparse.Namespace: Parsed arguments.
    '''
    parser = argparse.ArgumentParser(
        description=(
            'Check wheel/sdist artifacts for generated NIST Chemistry '
            'WebBook data files that must not be redistributed.'
        )
    )
    parser.add_argument(
        'artifacts',
        nargs='*',
        help=(
            'Distribution archives or directories to inspect. '
            'Defaults to dist/*.'
        ),
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    '''Run the package artifact check.

    Args:
        argv: Optional command-line argument list.

    Returns:
        Process exit code.
    '''
    args = parse_args(argv)
    paths = [Path(path) for path in args.artifacts]
    if not paths:
        paths = _default_artifact_paths()
    if not paths:
        print('No distribution artifacts found. Build with: python -m build')
        return 1

    try:
        findings = find_forbidden_artifacts(paths)
    except (tarfile.TarError, zipfile.BadZipFile, ValueError) as exc:
        print(f'Artifact check failed: {exc}', file=sys.stderr)
        return 1

    if findings:
        print(
            'Forbidden generated WebBook artifacts were found:',
            file=sys.stderr,
        )
        for artifact, member in findings:
            print(f'  {artifact}: {member}', file=sys.stderr)
        return 1

    print('OK: no forbidden generated WebBook artifacts found.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
