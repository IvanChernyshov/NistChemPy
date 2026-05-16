# NistChemPy

Unofficial Python tools for querying NIST Chemistry WebBook pages and extracting molecular-property records.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20235917.svg)](https://doi.org/10.5281/zenodo.20235917)

> **Status:** usable research package / beta.  
> NistChemPy is an unofficial Python package for querying NIST Chemistry WebBook pages and extracting selected molecular-property records. It is not affiliated with, maintained by, or endorsed by NIST. Because the Chemistry WebBook does not provide a stable public web API for this package, functionality may depend on the current structure and behavior of the external web service.

NistChemPy automates selected search and data-extraction workflows for the [NIST Chemistry WebBook](https://webbook.nist.gov/). It currently supports extraction of basic compound metadata, selected spectral records (IR, THz, MS, and UV-Vis), and gas chromatography records where these are available from the corresponding WebBook pages. Additional properties may be reachable through source URLs stored by the package, but direct extraction is intentionally limited to the implemented record types.

For serious scientific use, users should verify retrieved records against the original NIST Chemistry WebBook pages and the primary literature references given there. Package output should not be treated as an official NIST data product, a complete database dump, or a stable production API.


## Main features

1. Search:

    - Search by [name](https://webbook.nist.gov/chemistry/name-ser/), [chemical formula](https://webbook.nist.gov/chemistry/form-ser/), [CAS RN](https://webbook.nist.gov/chemistry/cas-ser/), [InChI / InChI Key](https://webbook.nist.gov/chemistry/inchi-ser/): `nistchempy.run_search`.
    
    - Search by [structure](https://webbook.nist.gov/chemistry/str-file/), including substructural search: `nistchempy.run_structural_search`.
    
    - Search over the package-internal table of pre-extracted compound identifiers and metadata: `nistchempy.get_all_data`. This table is included to support NistChemPy workflows and should not be interpreted as an authoritative, complete, or independently licensed redistribution of the NIST Chemistry WebBook.


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
> You may need to update your nistchempy-based code or use the older nistchempy versions.


## How To

The primary features of NistChemPy, such as search capabilities and compound manipulations, are detailed in the [documentation](https://ivanchernyshov.github.io/NistChemPy/).


## Citation

If you use NistChemPy in research, please cite the software using the metadata in [CITATION.cff](CITATION.cff). The Zenodo concept DOI for citing NistChemPy across versions is [10.5281/zenodo.20235917](https://doi.org/10.5281/zenodo.20235917).
