'''User-local NIST Chemistry WebBook index support.'''

from __future__ import annotations

import json as _json
import typing as _tp
from pathlib import Path as _Path

import pandas as _pd

from nistchempy.cache import resolve_index_path as _resolve_index_path
from nistchempy.exceptions import NistChemPyIndexError
from nistchempy.exceptions import NistChemPyIndexNotFoundError


INDEX_FILENAME = 'index.csv'
MANIFEST_FILENAME = 'manifest.json'
DEFAULT_SEARCH_FIELDS = (
    'ID',
    'name',
    'synonyms',
    'formula',
    'inchi',
    'inchi_key',
)


def _format_missing_index_message(path: _Path) -> str:
    return (
        'No user-local NIST Chemistry WebBook index was found at '
        f'{path}. NistChemPy no longer ships a prebuilt WebBook index. '
        'Create or point to a local index before using local index search. '
        'Full section-availability indexes may require visiting one WebBook '
        'compound page per compound and can take several days with a polite '
        'request delay.'
    )


def _resolve_index_files(path=None) -> _tp.Tuple[_Path, _Path]:
    index_path = _resolve_index_path(path)
    if index_path.suffix.lower() == '.csv' or index_path.is_file():
        return index_path.parent, index_path
    return index_path, index_path / INDEX_FILENAME


def _read_manifest(path: _Path) -> dict:
    manifest_path = path / MANIFEST_FILENAME
    if not manifest_path.exists():
        return {}
    with open(manifest_path, 'r', encoding='utf-8') as infile:
        return _json.load(infile)


def _infer_manifest(data: _pd.DataFrame, csv_path: _Path) -> dict:
    section_columns = [
        column for column in data.columns
        if column not in DEFAULT_SEARCH_FIELDS
        and column not in ('mol_weight', 'mol2D', 'mol3D', 'cas_rn')
    ]
    capabilities = ['compound_discovery']
    if section_columns:
        capabilities.append('section_availability')

    return {
        'schema_version': 1,
        'mode': 'legacy_csv',
        'capabilities': capabilities,
        'source_path': str(csv_path),
    }


def _as_list(value) -> _tp.List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


class WebBookIndex:
    '''User-local NIST Chemistry WebBook compound index.

    The index is loaded from a directory created by a local reconstruction
    workflow, or from an explicit local CSV file. NistChemPy does not
    distribute a prebuilt WebBook-derived index.

    Attributes:
        path (pathlib.Path): Directory containing the local index files, or the
            parent directory of an explicitly loaded CSV file.
        data (pandas.DataFrame): Loaded local index table.
        manifest (dict): Local index metadata loaded from manifest.json.
    '''

    def __init__(self, path, data, manifest=None):
        '''Initialize a local WebBook index object.

        Args:
            path: Directory containing the local index files.
            data: Local index table.
            manifest: Optional local index manifest.
        '''
        self.path = _Path(path)
        self.data = data
        self.manifest = manifest or {}

    @classmethod
    def exists(cls, path=None) -> bool:
        '''Return whether a local WebBook index exists.

        Args:
            path: Optional local index directory or CSV file.

        Returns:
            bool: True if index.csv exists in the resolved index directory.
        '''
        _, csv_path = _resolve_index_files(path)
        return csv_path.exists()

    @classmethod
    def from_cache(cls, path=None, require=True):
        '''Load a user-local WebBook index.

        Args:
            path: Optional local index directory or CSV file.
            require: If True, raise an error when the index does not exist.
                If False, return None when the index is missing.

        Returns:
            WebBookIndex | None: Loaded index object, or None when missing and
            require is False.

        Raises:
            NistChemPyIndexNotFoundError: If the index is required but missing.
            NistChemPyIndexError: If the index file cannot be loaded.
        '''
        index_path, csv_path = _resolve_index_files(path)
        if not csv_path.exists():
            if require:
                raise NistChemPyIndexNotFoundError(
                    _format_missing_index_message(csv_path)
                )
            return None

        try:
            data = _pd.read_csv(csv_path, dtype='str')
        except Exception as exc:
            raise NistChemPyIndexError(
                f'Failed to load local WebBook index from {csv_path}.'
            ) from exc

        if 'mol_weight' in data.columns:
            data['mol_weight'] = _pd.to_numeric(
                data['mol_weight'], errors='coerce'
            )

        manifest = _read_manifest(index_path)
        if not manifest:
            manifest = _infer_manifest(data, csv_path)

        return cls(index_path, data, manifest)

    def to_dataframe(self, copy=True):
        '''Return the local index table as a pandas DataFrame.

        Args:
            copy: If True, return a copy of the internal DataFrame.

        Returns:
            pandas.DataFrame: Local index table.
        '''
        if copy:
            return self.data.copy()
        return self.data

    def has_capability(self, capability: str) -> bool:
        '''Return whether the local index manifest declares a capability.

        Args:
            capability: Capability name, such as ``section_availability``.

        Returns:
            bool: True if the capability is declared by the manifest.
        '''
        return capability in self.manifest.get('capabilities', [])

    def require_capability(self, capability: str) -> None:
        '''Raise an error if the local index lacks a capability.

        Args:
            capability: Required capability name.

        Raises:
            NistChemPyIndexError: If the capability is not declared.
        '''
        if not self.has_capability(capability):
            raise NistChemPyIndexError(
                'The local WebBook index does not declare the required '
                f'capability: {capability}.'
            )

    def get(self, compound_id: str):
        '''Return the row for one NIST Chemistry WebBook compound ID.

        Args:
            compound_id: NIST Chemistry WebBook compound ID.

        Returns:
            pandas.Series: First matching row.

        Raises:
            KeyError: If the ID column is missing or the compound is absent.
        '''
        if 'ID' not in self.data.columns:
            raise KeyError('The local WebBook index has no ID column.')

        rows = self.data[self.data['ID'] == compound_id]
        if rows.empty:
            raise KeyError(f'Compound ID not found in local index: {compound_id}')
        return rows.iloc[0]

    def filter(self, has_sections=None, ids=None, limit=None):
        '''Filter the local index table.

        Args:
            has_sections: Optional section column name or iterable of section
                column names. Rows must have non-empty values in all requested
                columns.
            ids: Optional compound ID or iterable of compound IDs.
            limit: Optional maximum number of returned rows.

        Returns:
            pandas.DataFrame: Filtered local index rows.
        '''
        result = self.data

        id_values = _as_list(ids)
        if id_values:
            if 'ID' not in result.columns:
                raise KeyError('The local WebBook index has no ID column.')
            result = result[result['ID'].isin(id_values)]

        for section in _as_list(has_sections):
            if section not in result.columns:
                raise KeyError(
                    f'Section column not found in local index: {section}'
                )
            values = result[section]
            result = result[values.notna() & values.astype(str).ne('')]

        if limit is not None:
            result = result.head(limit)

        return result.copy()

    def search(
            self, query: str, fields=None, case=False, regex=False,
            sections=None, limit=None):
        '''Search the local index table.

        Args:
            query: Search text or regular expression.
            fields: Optional column name or iterable of column names to search.
                By default, common identifier and metadata columns are searched
                when present.
            case: If True, perform case-sensitive matching.
            regex: If True, treat query as a regular expression.
            sections: Optional section column name or iterable of section column
                names required to be non-empty in returned rows.
            limit: Optional maximum number of returned rows.

        Returns:
            pandas.DataFrame: Matching local index rows.
        '''
        if not query:
            raise ValueError('query must be a non-empty string')

        search_fields = _as_list(fields)
        if not search_fields:
            search_fields = [
                field for field in DEFAULT_SEARCH_FIELDS
                if field in self.data.columns
            ]
        if not search_fields:
            raise NistChemPyIndexError(
                'The local WebBook index has no searchable columns.'
            )

        missing_fields = [
            field for field in search_fields if field not in self.data.columns
        ]
        if missing_fields:
            missing = ', '.join(missing_fields)
            raise KeyError(f'Search columns not found in local index: {missing}')

        mask = _pd.Series(False, index=self.data.index)
        for field in search_fields:
            values = self.data[field].fillna('').astype(str)
            mask = mask | values.str.contains(
                query, case=case, regex=regex, na=False
            )

        result = self.data[mask]
        if sections:
            result = WebBookIndex(self.path, result, self.manifest).filter(
                has_sections=sections
            )
        if limit is not None:
            result = result.head(limit)

        return result.copy()


def get_local_index(path=None, require=True):
    '''Load the user-local NIST Chemistry WebBook index.

    Args:
        path: Optional local index directory.
        require: If True, raise an error when the index does not exist. If
            False, return None when the index is missing.

    Returns:
        WebBookIndex | None: Loaded local index object, or None when missing and
        require is False.
    '''
    return WebBookIndex.from_cache(path=path, require=require)
