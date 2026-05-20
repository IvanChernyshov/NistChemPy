# NistChemPy

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20235917-blue.svg)](https://doi.org/10.5281/zenodo.20235917)

Unofficial Python tools for querying NIST Chemistry WebBook pages and extracting molecular-property records.


> [!WARNING]
> **Old PyPI releases scheduled for removal.**
>
> NistChemPy versions earlier than 2.0.0 may contain bundled WebBook-derived index data, including `nist_data.csv` / `nist_data.zip`. Starting with NistChemPy 2.0.0, the project follows a software-only distribution model and no longer redistributes prebuilt NIST Chemistry WebBook / SRD 69 indexes or bulk extracted WebBook-derived data.
>
> Affected old PyPI release files are scheduled to be removed on **June 1, 2026**. Please migrate to `nistchempy>=2.0.0` and build/import local indexes using the documented local-index workflows.


> **Project notice:** NistChemPy is an unofficial Python package for querying NIST Chemistry WebBook pages and extracting selected molecular-property records. It is not affiliated with, maintained by, or endorsed by NIST. Because the Chemistry WebBook does not provide a stable public web API for this package, functionality may depend on the current structure and behavior of the external web service.
>
> **Important index change:** NistChemPy no longer ships a prebuilt NIST Chemistry WebBook compound index. Live WebBook search and individual compound-page parsing remain separate functionality, but local index search now requires a user-generated local index/cache.
>
> Rebuilding a full section-availability index can require visiting one WebBook page per compound. With a polite 3 second delay and roughly 100,000-150,000 pages, the initial rebuild can take about **3.5-5+ days** before retries and network overhead.

NistChemPy automates selected search and data-extraction workflows for the [NIST Chemistry WebBook](https://webbook.nist.gov/). It currently supports extraction of basic compound metadata, selected spectral records (IR, THz, MS, and UV-Vis), and gas chromatography records where these are available from the corresponding WebBook pages. Additional properties may be reachable through source URLs stored by the package, but direct extraction is intentionally limited to the implemented record types.

For serious scientific use, users should verify retrieved records against the original NIST Chemistry WebBook pages and the primary literature references given there. Package output should not be treated as an official NIST data product, a complete database dump, or a stable production API.


## Main features

1. Search:

    - Search by [name](https://webbook.nist.gov/chemistry/name-ser/), [chemical formula](https://webbook.nist.gov/chemistry/form-ser/), [CAS RN](https://webbook.nist.gov/chemistry/cas-ser/), [InChI / InChI Key](https://webbook.nist.gov/chemistry/inchi-ser/): `nistchempy.run_search`.

    - Search by [structure](https://webbook.nist.gov/chemistry/str-file/), including substructural search: `nistchempy.run_structural_search`. RDKit is optional and is used for SMILES/InChI-to-MOL conversion helpers and local index structural search.

    - Search over a user-local compound index/cache with `nistchempy.WebBookIndex.from_cache()` or `nistchempy.get_local_index()`. NistChemPy does not redistribute a prebuilt WebBook-derived index.


2. Compound info (`nistchempy.compound.NistCompound`):

    - Object stores parsed properties and corresponding source URLs.

    - Supports extraction of selected records:

        - 2D and 3D atomic coordinates.

        - Spectral data (IR, MS, UV-Vis).

        - Gas chromatography data.

    - Parsed metadata and loaded property objects can be exported as structured records with `to_dict()`, `to_record()`, and `to_records()`. Record collections can be serialized with `nistchempy.records.write_records_json()` or `nistchempy.records.write_records_jsonl()`.

For more details see the Cookbook section of the [documentation](https://mucommons.github.io/NistChemPy/).


## Related project: NistChemData

[NistChemData](https://github.com/muCommons/NistChemData) is a companion repository for local reconstruction workflows and provenance-sensitive extraction scripts. It is not an official NIST product and is not promoted here as an authoritative, complete, current, or independently licensed redistribution of the NIST Chemistry WebBook.

Users should review the NistChemData data-use notice, original NIST Chemistry WebBook pages, applicable NIST terms, and source references before running those workflows or using generated local artifacts in scientific, commercial, or redistributed datasets.


## Installation

Install NistChemPy using [pip](https://pypi.org/project/NistChemPy/):

```
pip install nistchempy
```

> [!WARNING]
> Please note that versions starting with 1.0.0 are not backward compatible with the older alpha versions due to significant changes in the code structure.
> Version 2.0.0 removes the packaged WebBook-derived index. Code that previously used the old bundled index should migrate to a user-local index loaded with `nistchempy.WebBookIndex.from_cache()` or `nistchempy.get_local_index()`.


## Local WebBook index

NistChemPy can load a user-local WebBook index from either a cache directory
containing `index.csv` or from an explicit CSV file path:

```python
import nistchempy as nist

index = nist.get_local_index('/path/to/webbook-index')
# or, for a local CSV you already have locally:
index = nist.get_local_index('/path/to/local_webbook_index.csv')
```

NistChemPy can also build a user-local index by discovering candidate
compounds through the WebBook formula browser, formula search, or sitemaps
and then enriching discovered seeds from individual compound pages:

```bash
nistchempy index build \
  --strategy formula-browser \
  --path /path/to/webbook-index \
  --request-delay 3 \
  --accept-data-terms
```

The `sitemap` strategy is available as a secondary/audit discovery source.
The `formula-search` strategy wraps the legacy carbon-formula search
workflow as a bounded discovery strategy and therefore requires an explicit
carbon range, for example:

```bash
nistchempy index discover \
  --strategy formula-search \
  --formula-carbon-start 1 \
  --formula-carbon-end 20 \
  --accept-data-terms
```

A full page-enriched build may need to visit many compound pages. With a polite
3 second delay, a full initial rebuild can take about **3.5-5+ days** before
retries and network overhead.

Useful CLI commands for existing local indexes:

```bash
nistchempy index path
nistchempy index status
nistchempy index search benzene
```

The documentation includes a Local Index Workflow cookbook page explaining the
cache layout, discovery/enrichment pipeline, custom paths, CSV import, and
RDKit-assisted local structural search.

Generated local index/cache files are user-local artifacts and are not covered
by the NistChemPy software license. See [DATA_NOTICE.md](DATA_NOTICE.md) for the
repository-level data notice. For migration/testing, an existing local CSV can
also be imported into the new cache layout:

```bash
nistchempy index build \
  --from-csv /path/to/local_webbook_index.csv \
  --path /path/to/webbook-index \
  --accept-data-terms
```


## Development workflows

Default tests are offline and deterministic:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Live WebBook integration tests are opt-in:

```bash
pytest -q -m network
pytest -q -m "network and rdkit"
```

Documentation notebooks are committed with pregenerated outputs and are not
executed by Sphinx. Regenerate them manually after example/API changes:

```bash
jupyter nbconvert --execute docs/source/basic_search.ipynb --inplace
jupyter nbconvert --execute docs/source/compound_properties.ipynb --inplace
jupyter nbconvert --execute docs/source/structural_search.ipynb --inplace
jupyter nbconvert --execute docs/source/local_index.ipynb --inplace
jupyter nbconvert --execute docs/source/requests_config.ipynb --inplace
```

See the documentation development workflow page for the full test, docs, and
release checklist.


## Release checks

Before publishing a release, build the package and verify that no generated
WebBook-derived index/cache artifacts are included:

```bash
python -m build
python tools/check_package_artifacts.py dist/*
```

The check rejects files such as `nist_data.zip`, `nist_data.csv`,
`compounds_data.json`, and package-internal `nistchempy/data/` contents.


## Documentation

The primary features of NistChemPy, including WebBook search, compound parsing, structured records, and local index workflows, are detailed in the [documentation](https://mucommons.github.io/NistChemPy/).

## AI-assisted development

Starting with the 1.0.6 cleanup/update and continuing through the 2.0.0 development line, OpenAI coding agents were used to assist with implementation, refactoring, documentation, and tests. Other AI models were also used to discuss architecture and implementation details. See [AI_USE.md](AI_USE.md) for the project note on AI-assisted development.


## Citation


Please cite the Zenodo Concept DOI for NistChemPy:

[10.5281/zenodo.20235917](https://doi.org/10.5281/zenodo.20235917)

The Concept DOI is preferred for general citations because it represents the software across archived versions.

If you use NistChemPy in research, please cite the software using the metadata in [CITATION.cff](CITATION.cff).
