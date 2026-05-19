'''User-local WebBook index build/write helpers.'''

from __future__ import annotations

import datetime as _datetime
import json as _json
import shutil as _shutil
import typing as _tp
import uuid as _uuid
from pathlib import Path as _Path

import pandas as _pd

from nistchempy.cache import resolve_index_path as _resolve_index_path
from nistchempy.exceptions import NistChemPyDataTermsError
from nistchempy.exceptions import NistChemPyIndexBuildError
from nistchempy.index import INDEX_FILENAME
from nistchempy.index import MANIFEST_FILENAME
from nistchempy.index import WebBookIndex

STATE_FILENAME = 'state.jsonl'
ERRORS_FILENAME = 'errors.jsonl'
TMP_DIR_NAME = 'tmp'
VALID_INDEX_MODES = ('discovery', 'availability', 'full')
DEFAULT_SOURCE_NOTICE = 'NIST Chemistry WebBook / SRD 69'


class LocalIndexBuilder:
    '''Write user-local NIST Chemistry WebBook index artifacts.

    This class contains the local cache writing layer used by index builders.
    It does not itself implement WebBook traversal. Network discovery and
    section-availability enrichment should feed rows into this writer.

    Args:
        path: Optional local index directory.
        mode: Index mode. Supported values are ``discovery``,
            ``availability``, and ``full``.
        capabilities: Optional capability names to store in the manifest. If
            omitted, capabilities are inferred from ``mode``.
        include_cas: Whether the index intentionally includes CAS RN values.
        accept_data_terms: Explicit acknowledgement that generated local data
            are local user artifacts and are not redistributed by NistChemPy.
    '''

    def __init__(
            self, path=None, mode='discovery', capabilities=None,
            include_cas=False, accept_data_terms=False):
        self.path = _resolve_index_path(path)
        self.mode = mode
        self.capabilities = list(capabilities or _capabilities_for_mode(mode))
        self.include_cas = include_cas
        self.accept_data_terms = accept_data_terms

        if self.mode not in VALID_INDEX_MODES:
            valid = ', '.join(VALID_INDEX_MODES)
            raise ValueError(f'Unsupported local index mode: {mode}. {valid}')

    @property
    def index_path(self) -> _Path:
        '''Return the local index CSV path.'''
        return self.path / INDEX_FILENAME

    @property
    def manifest_path(self) -> _Path:
        '''Return the local manifest path.'''
        return self.path / MANIFEST_FILENAME

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
        '''Write a local index CSV and manifest atomically.

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
        )
        tmp_manifest = self._temporary_path(MANIFEST_FILENAME)
        tmp_manifest.write_text(
            _json.dumps(manifest, indent=2, sort_keys=True) + '\n',
            encoding='utf-8',
        )
        tmp_manifest.replace(self.manifest_path)

        self.append_state(
            'index_written',
            {
                'row_count': len(dataframe),
                'mode': self.mode,
                'status': status,
            },
        )
        return WebBookIndex.from_cache(self.path)

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
            status='complete') -> dict:
        now = _utc_timestamp()
        manifest = {
            'schema_version': 1,
            'mode': self.mode,
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


def import_index_csv(
        csv_path, path=None, mode='availability', capabilities=None,
        include_cas=False, accept_data_terms=False, replace=True):
    '''Create a local index cache layout from an existing local CSV file.

    Args:
        csv_path: Existing local CSV file.
        path: Optional destination local index directory.
        mode: Local index mode to store in the manifest.
        capabilities: Optional capability names. If omitted, capabilities are
            inferred from ``mode``.
        include_cas: Whether the local CSV intentionally includes CAS RN data.
        accept_data_terms: Explicit acknowledgement that generated/imported
            local data are local user artifacts.
        replace: If False, raise an error when destination index.csv exists.

    Returns:
        WebBookIndex: Loaded local index object.
    '''
    builder = LocalIndexBuilder(
        path=path,
        mode=mode,
        capabilities=capabilities,
        include_cas=include_cas,
        accept_data_terms=accept_data_terms,
    )
    return builder.copy_from_csv(csv_path, replace=replace)


def unavailable_network_build_message() -> str:
    '''Return the current message for unavailable network index builders.'''
    return (
        'Network-based local index building is not implemented in this '
        'development step yet. Use --from-csv to import an existing local CSV '
        'index, or wait for the discovery/availability builder patch.'
    )


def _capabilities_for_mode(mode: str) -> _tp.Tuple[str, ...]:
    if mode == 'discovery':
        return ('compound_discovery',)
    if mode == 'availability':
        return ('compound_discovery', 'section_availability')
    if mode == 'full':
        return (
            'compound_discovery',
            'section_availability',
            'extended_metadata',
        )
    return ()


def _as_dataframe(data) -> _pd.DataFrame:
    if isinstance(data, _pd.DataFrame):
        return data.copy()
    return _pd.DataFrame(list(data))


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
