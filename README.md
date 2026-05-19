# NistChemPy

Unofficial Python tools for querying NIST Chemistry WebBook pages and extracting molecular-property records.


> **Status:** development branch / index cleanup in progress.
> NistChemPy is an unofficial Python package for querying NIST Chemistry WebBook pages and extracting selected molecular-property records. It is not affiliated with, maintained by, or endorsed by NIST. Because the Chemistry WebBook does not provide a stable public web API for this package, functionality may depend on the current structure and behavior of the external web service.
>
> **Important index change:** NistChemPy no longer ships a prebuilt NIST Chemistry WebBook compound index. Live WebBook search and individual compound-page parsing remain separate functionality, but local index search now requires a user-generated local index/cache. Rebuilding a full section-availability index can require visiting one WebBook page per compound; with a polite 3 second delay and roughly 100,000-150,000 pages, the initial rebuild can take about 3.5-5+ days before retries and network overhead.

NistChemPy automates selected search and data-extraction workflows for the [NIST Chemistry WebBook](https://webbook.nist.gov/). It currently supports extraction of basic compound metadata, selected spectral records (IR, THz, MS, and UV-Vis), and gas chromatography records where these are available from the corresponding WebBook pages. Additional properties may be reachable through source URLs stored by the package, but direct extraction is intentionally limited to the implemented record types.

For serious scientific use, users should verify retrieved records against the original NIST Chemistry WebBook pages and the primary literature references given there. Package output should not be treated as an official NIST data product, a complete database dump, or a stable production API.


## Main features

1. Search:

    - Search by [name](https://webbook.nist.gov/chemistry/name-ser/), [chemical formula](https://webbook.nist.gov/chemistry/form-ser/), [CAS RN](https://webbook.nist.gov/chemistry/cas-ser/), [InChI / InChI Key](https://webbook.nist.gov/chemistry/inchi-ser/): `nistchempy.run_search`.

    - Search by [structure](https://webbook.nist.gov/chemistry/str-file/), including substructural search: `nistchempy.run_structural_search`.

    - Search over a user-local compound index/cache with `nistchempy.WebBookIndex.from_cache()` or `nistchempy.get_local_index()`. NistChemPy does not redistribute a prebuilt WebBook-derived index.


2. Compound info (`nistchempy.compound.NistCompound`):

    - Object stores parsed properties and corresponding source URLs.

    - Supports extraction of selected records:

        - 2D and 3D atomic coordinates.

        - Spectral data (IR, MS, UV-Vis).

        - Gas chromatography data.

For more details see the CookBook section of the [documentation](https://ivanchernyshov.github.io/NistChemPy/).


## Related project: NistChemData

[NistChemData](https://github.com/IvanChernyshov/NistChemData) is a historical companion repository containing extracted data files and extraction scripts produced with earlier NistChemPy workflows. It is not an official NIST product and is not promoted here as an authoritative, complete, current, or independently licensed redistribution of the NIST Chemistry WebBook.

Users should review the NistChemData data-use notice, original NIST Chemistry WebBook pages, applicable NIST terms, and source references before using those files in scientific, commercial, or redistributed datasets.


## Installation

Install NistChemPy using [pip](https://pypi.org/project/NistChemPy/):

```
pip install nistchempy
```

> [!WARNING]
> Please note that versions starting with 1.0.0 are not backward compatible with the older alpha versions due to significant changes in the code structure.
> Development versions after 1.0.6 also remove the packaged WebBook-derived index. Code using `nistchempy.get_all_data()` should migrate to a user-local index loaded with `nistchempy.WebBookIndex.from_cache()` or `nistchempy.get_local_index()`.


## How To

The primary features of NistChemPy, such as search capabilities and compound manipulations, are detailed in the [documentation](https://ivanchernyshov.github.io/NistChemPy/).


## Citation

If you use NistChemPy in research, please cite the software using the metadata in [CITATION.cff](CITATION.cff).
