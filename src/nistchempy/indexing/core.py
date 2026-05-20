'''User-local NIST Chemistry WebBook index support.'''

from __future__ import annotations

import json as _json
import typing as _tp
from pathlib import Path as _Path

import pandas as _pd

from nistchempy.indexing.cache import resolve_index_path as _resolve_index_path
from nistchempy.exceptions import NistChemPyIndexError
from nistchempy.exceptions import NistChemPyIndexNotFoundError
from nistchempy.indexing.schema import DEFAULT_SEARCH_FIELDS
from nistchempy.indexing.schema import INDEX_FILENAME
from nistchempy.indexing.schema import MANIFEST_FILENAME


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
        'artifact': 'index',
        'strategy': 'legacy-csv',
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
    def default_path(cls):
        '''Return the default user-local WebBook index directory.

        Returns:
            pathlib.Path: Resolved default local index cache directory.
        '''
        return _resolve_index_path(None)

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

        manifest = {}
        if csv_path.name == INDEX_FILENAME:
            manifest = _read_manifest(index_path)
        if not manifest:
            manifest = _infer_manifest(data, csv_path)

        return cls(index_path, data, manifest)

    @classmethod
    def discover(
            cls, path=None, strategy='formula-browser',
            accept_data_terms=False, request_delay=3.0, timeout=30.0,
            max_attempts=3, limit=None, max_pages=None, replace=True,
            start_url=None, max_queries=None, carbon_start=1,
            carbon_end=None, hydrogen_max=149, heteroatom_max=50,
            elements=None):
        '''Discover intermediate seeds for a user-local WebBook index.

        Discovery creates ``seeds.csv`` and does not create a final local
        ``index.csv``. Compound-page enrichment is implemented separately.

        Args:
            path: Optional destination local index directory.
            strategy: Compound-discovery strategy. This development step
                implements ``formula-browser``, ``formula-search``, and
                ``sitemap``.
            accept_data_terms: Explicit acknowledgement that generated local
                data are local user artifacts.
            request_delay: Delay between NIST WebBook requests in seconds.
            timeout: Request timeout in seconds.
            max_attempts: Maximum attempts for each request.
            limit: Optional maximum number of seeds to collect.
            max_pages: Optional maximum number of discovery pages/documents to
                visit.
            replace: If False, raise an error when seeds.csv exists.
            start_url: Optional formula-browser, robots.txt, or sitemap URL to
                start from.
            max_queries: Optional maximum number of formula-search queries
                to run.
            carbon_start: First carbon count to scan for formula-search
                discovery.
            carbon_end: Last carbon count to scan for formula-search discovery.
            hydrogen_max: Maximum hydrogen count for formula-search refinement.
            heteroatom_max: Maximum one-heteroelement count for formula-search
                refinement.
            elements: Optional formula-search element list.

        Returns:
            pandas.DataFrame: Written discovery seed table.
        '''
        from nistchempy.exceptions import NistChemPyIndexBuildError
        from nistchempy.indexing.schema import DEFAULT_DISCOVERY_STRATEGY
        from nistchempy.indexing.schema import FORMULA_SEARCH_DISCOVERY_STRATEGY
        from nistchempy.indexing.schema import SITEMAP_DISCOVERY_STRATEGY
        from nistchempy.indexing.build import discover_formula_browser
        from nistchempy.indexing.build import discover_formula_search
        from nistchempy.indexing.build import discover_sitemap
        from nistchempy.indexing.build import unavailable_discovery_message

        if strategy == DEFAULT_DISCOVERY_STRATEGY:
            return discover_formula_browser(
                path=path,
                accept_data_terms=accept_data_terms,
                request_delay=request_delay,
                timeout=timeout,
                max_attempts=max_attempts,
                limit=limit,
                max_pages=max_pages,
                replace=replace,
                start_url=start_url,
            )
        if strategy == FORMULA_SEARCH_DISCOVERY_STRATEGY:
            return discover_formula_search(
                path=path,
                accept_data_terms=accept_data_terms,
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
        if strategy == SITEMAP_DISCOVERY_STRATEGY:
            return discover_sitemap(
                path=path,
                accept_data_terms=accept_data_terms,
                request_delay=request_delay,
                timeout=timeout,
                max_attempts=max_attempts,
                limit=limit,
                max_pages=max_pages,
                replace=replace,
                start_url=start_url,
            )
        raise NistChemPyIndexBuildError(unavailable_discovery_message())

    @classmethod
    def enrich(
            cls, path=None, seeds_path=None, accept_data_terms=False,
            request_delay=3.0, timeout=30.0, max_attempts=3, limit=None,
            resume=True, replace=True, strategy=None, include_cas=None):
        '''Enrich discovery seeds into a final local WebBook index.

        This method visits compound pages listed in ``seeds.csv`` and writes
        the final ``index.csv`` table. Long-running enrichment can be resumed
        from ``index.partial.jsonl``.

        Args:
            path: Optional local index directory. Direct CSV paths are not
                valid for enrichment because this operation needs cache
                artifacts such as seeds.csv and index.partial.jsonl.
            seeds_path: Optional explicit seed CSV file. If omitted, use the
                cache-local ``seeds.csv``.
            accept_data_terms: Explicit acknowledgement that generated local
                data are local user artifacts.
            request_delay: Delay between NIST WebBook requests in seconds.
            timeout: Request timeout in seconds.
            max_attempts: Maximum request attempts per seed.
            limit: Optional maximum number of seeds to process.
            resume: If True, reuse existing partial enrichment rows.
            replace: If False, raise an error when index.csv exists.
            strategy: Optional discovery strategy override. If omitted, use
                the existing local manifest when available.
            include_cas: Optional CAS RN inclusion override. If omitted, use
                the existing local manifest when available.

        Returns:
            WebBookIndex: Loaded final local index object.
        '''
        from nistchempy.indexing.build import enrich_index_from_seeds

        return enrich_index_from_seeds(
            path=path,
            seeds_path=seeds_path,
            accept_data_terms=accept_data_terms,
            request_delay=request_delay,
            timeout=timeout,
            max_attempts=max_attempts,
            limit=limit,
            resume=resume,
            replace=replace,
            strategy=strategy,
            include_cas=include_cas,
        )

    @classmethod
    def build(
            cls, path=None, strategy='formula-browser', source_csv=None,
            include_cas=True, accept_data_terms=False, replace=True,
            request_delay=3.0, timeout=30.0, max_attempts=3, limit=None,
            max_pages=None, resume=True, start_url=None, max_queries=None,
            carbon_start=1, carbon_end=None, hydrogen_max=149,
            heteroatom_max=50, elements=None):
        '''Build or import a user-local WebBook index.

        If ``source_csv`` is provided, the CSV is imported into the local cache
        layout. Otherwise, the current network builder runs formula-browser
        discovery followed by compound-page enrichment.

        Args:
            path: Optional destination local index directory.
            strategy: Compound-discovery strategy. The current network builder
                implements ``formula-browser``, ``formula-search``, and
                ``sitemap``.
            source_csv: Optional existing local CSV file to import.
            include_cas: Whether the local index intentionally includes CAS RN
                values.
            accept_data_terms: Explicit acknowledgement that generated/imported
                local data are local user artifacts.
            replace: If False, raise an error when destination artifacts exist.
            request_delay: Delay between NIST WebBook requests in seconds.
            timeout: Request timeout in seconds.
            max_attempts: Maximum request attempts per WebBook page.
            limit: Optional maximum number of seeds to discover/enrich.
            max_pages: Optional maximum number of discovery pages/documents to
                visit during discovery.
            resume: If True, reuse existing partial enrichment rows.
            start_url: Optional formula-browser, robots.txt, or sitemap URL to
                start from.
            max_queries: Optional maximum number of formula-search queries
                to run.
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
        from nistchempy.indexing.build import build_index

        return build_index(
            path=path,
            strategy=strategy,
            source_csv=source_csv,
            include_cas=include_cas,
            accept_data_terms=accept_data_terms,
            replace=replace,
            request_delay=request_delay,
            timeout=timeout,
            max_attempts=max_attempts,
            limit=limit,
            max_pages=max_pages,
            resume=resume,
            start_url=start_url,
            max_queries=max_queries,
            carbon_start=carbon_start,
            carbon_end=carbon_end,
            hydrogen_max=hydrogen_max,
            heteroatom_max=heteroatom_max,
            elements=elements,
        )

    @classmethod
    def update(
            cls, path=None, strategy='formula-browser', source_csv=None,
            include_cas=True, accept_data_terms=False, request_delay=3.0,
            timeout=30.0, max_attempts=3, limit=None, max_pages=None,
            resume=True, start_url=None, max_queries=None, carbon_start=1,
            carbon_end=None, hydrogen_max=149, heteroatom_max=50,
            elements=None):
        '''Update a user-local WebBook index.

        Updating reruns the same local build/import operation with replacement
        enabled. For network builds, this means seed discovery followed by
        compound-page enrichment.

        Args:
            path: Optional destination local index directory.
            strategy: Compound-discovery strategy. The current network builder
                implements ``formula-browser``, ``formula-search``, and
                ``sitemap``.
            source_csv: Optional existing local CSV file to import.
            include_cas: Whether the local index intentionally includes CAS RN
                values.
            accept_data_terms: Explicit acknowledgement that generated/imported
                local data are local user artifacts.
            request_delay: Delay between NIST WebBook requests in seconds.
            timeout: Request timeout in seconds.
            max_attempts: Maximum request attempts per WebBook page.
            limit: Optional maximum number of seeds to discover/enrich.
            max_pages: Optional maximum number of discovery pages/documents to
                visit during discovery.
            resume: If True, reuse existing partial enrichment rows.
            start_url: Optional formula-browser, robots.txt, or sitemap URL to
                start from.
            max_queries: Optional maximum number of formula-search queries
                to run.
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
        return cls.build(
            path=path,
            strategy=strategy,
            source_csv=source_csv,
            include_cas=include_cas,
            accept_data_terms=accept_data_terms,
            replace=True,
            request_delay=request_delay,
            timeout=timeout,
            max_attempts=max_attempts,
            limit=limit,
            max_pages=max_pages,
            resume=resume,
            start_url=start_url,
            max_queries=max_queries,
            carbon_start=carbon_start,
            carbon_end=carbon_end,
            hydrogen_max=hydrogen_max,
            heteroatom_max=heteroatom_max,
            elements=elements,
        )

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
            raise KeyError(
                f'Compound ID not found in local index: {compound_id}'
            )
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

    def property_columns(self) -> _tp.List[str]:
        '''Return local-index columns describing downloadable resources.

        Metadata columns such as names, formula, identifiers, and molecular
        weight are excluded. Structure links such as ``mol2D`` and ``mol3D``
        are treated as available resource columns.

        Returns:
            list[str]: Property/resource column names present in the index.
        '''
        metadata = set(DEFAULT_SEARCH_FIELDS) | {'mol_weight'}
        return [column for column in self.data.columns if column not in metadata]


    def available_properties(self, compound_id: str) -> _tp.Dict[str, str]:
        '''Return non-empty local-index resource URLs for a compound.

        Args:
            compound_id: NIST Chemistry WebBook compound ID.

        Returns:
            dict: Mapping of property/resource column names to local-index URL
            values.

        Raises:
            KeyError: If the compound ID is absent from the local index.
        '''
        row = self.get(compound_id)
        result = {}
        for column in self.property_columns():
            value = row.get(column, '')
            if _pd.isna(value):
                continue
            value = str(value).strip()
            if value:
                result[column] = value
        return result


    def has_property(self, compound_id: str, property_name: str) -> bool:
        '''Return whether a compound has a non-empty local-index property.

        Args:
            compound_id: NIST Chemistry WebBook compound ID.
            property_name: Local-index property/resource column name.

        Returns:
            bool: True if the property column exists and has a non-empty value
            for the compound.
        '''
        if property_name not in self.data.columns:
            return False
        return property_name in self.available_properties(compound_id)



    def structural_search(
            self, *, smiles=None, inchi=None, molblock=None, molfile=None,
            mode='substructure', threshold=0.7, limit=None, errors='ignore'):
        '''Run RDKit-assisted structural search over the local index.

        Local structural search is a lightweight linear scan over the
        index ``inchi`` / ``inchi_key`` columns. It is useful for small and
        medium local indexes, but it is not a persistent fingerprint database.

        Args:
            smiles: Optional SMILES query.
            inchi: Optional InChI query.
            molblock: Optional MOL block query.
            molfile: Optional path to a MOL file query.
            mode: Search mode: ``exact``, ``substructure``, or ``similarity``.
            threshold: Minimum Tanimoto similarity for ``similarity`` mode.
            limit: Optional maximum number of rows to return.
            errors: Error policy for invalid indexed InChI values: ``ignore``
                or ``raise``.

        Returns:
            pandas.DataFrame: Matching local index rows. Similarity results
            include a ``similarity`` column sorted from highest to lowest.

        Raises:
            ValueError: If mode/errors are invalid or the query is invalid.
            NistChemPyOptionalDependencyError: If RDKit is unavailable.
        '''
        if mode not in {'exact', 'substructure', 'similarity'}:
            raise ValueError(
                'mode must be one of exact, substructure, or similarity'
            )
        if errors not in {'ignore', 'raise'}:
            raise ValueError('errors must be one of ignore or raise')

        import nistchempy.structure as _structure

        query_mol = _structure.query_mol_from_input(
            smiles=smiles,
            inchi=inchi,
            molblock=molblock,
            molfile=molfile,
        )

        if mode == 'exact':
            if 'inchi_key' not in self.data.columns:
                return self.data.iloc[0:0].copy()
            query_key = _structure.mol_to_inchi_key(query_mol)
            values = self.data['inchi_key'].fillna('').astype(str).str.strip()
            result = self.data[values == query_key].copy()
            if limit is not None:
                result = result.head(limit)
            return result

        if 'inchi' not in self.data.columns:
            return self.data.iloc[0:0].copy()

        if mode == 'similarity':
            query_fp = _structure.morgan_fingerprint(query_mol)

        matches = []
        for idx, row in self.data.iterrows():
            row_inchi = row.get('inchi', '')
            if _pd.isna(row_inchi) or not str(row_inchi).strip():
                continue
            try:
                row_mol = _structure.mol_from_inchi(str(row_inchi).strip())
            except Exception:
                if errors == 'raise':
                    raise
                continue

            if mode == 'substructure':
                if row_mol.HasSubstructMatch(query_mol):
                    matches.append((idx, None))
            else:
                row_fp = _structure.morgan_fingerprint(row_mol)
                similarity = _structure.tanimoto_similarity(query_fp, row_fp)
                if similarity >= threshold:
                    matches.append((idx, similarity))

        indices = [idx for idx, _ in matches]
        result = self.data.loc[indices].copy()
        if mode == 'similarity':
            scores = [score for _, score in matches]
            result['similarity'] = scores
            result = result.sort_values('similarity', ascending=False)
        if limit is not None:
            result = result.head(limit)
        return result

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
            sections: Optional section column name or iterable of section
                column names required to be non-empty in returned rows.
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
            raise KeyError(
                f'Search columns not found in local index: {missing}'
            )

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
        WebBookIndex | None: Loaded local index object, or None when missing
        and require is False.
    '''
    return WebBookIndex.from_cache(path=path, require=require)
