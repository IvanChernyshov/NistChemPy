# NistChemPy: Python API for NIST Chemistry WebBook

**NistChemPy** is an unofficial API for the [NIST Chemistry WebBook](https://webbook.nist.gov/).

This package not only automates the search and data extraction processes but also bypasses the WebBook's limitation of 400 compounds per search.

Currently, **NistChemPy** enables the extraction of basic compound properties as well as IR, THz, MS, and UV-Vis spectra and gas chromatography data.

Additional properties are available via URLs that link to their respective web pages, with potential support for direct extraction in future updates.


## Main features

1. Search:

    - Search by [name](https://webbook.nist.gov/chemistry/name-ser/), [chemical formula](https://webbook.nist.gov/chemistry/form-ser/), [CAS RN](https://webbook.nist.gov/chemistry/cas-ser/), [InChI / InChI Key](https://webbook.nist.gov/chemistry/inchi-ser/): `nistchempy.run_search`.
    
    - Search by [structure](https://webbook.nist.gov/chemistry/str-file/), including substructural search: `nistchempy.run_structural_search`.
    
    - Search over the table of pre-extracted components: `nistchempy.get_all_data`. This is useful considering that NIST Chemistry WebBook returns maximum of 400 found compounds only.


2. Compound info (`nistchempy.compound.NistCompound`):
    
    - Object contains all properties and corresponding URLs.
    
    - Supports extraction of:
        
        - 2D and 3D atomic coordinates.
        
        - Spectral data (IR, MS, UV-Vis).
        
        - Gas chromatography data.
    
    - Extraction of other data is under development: it's a good idea to expect two feature updates per year.

For more details see the CookBook section of the [documentation](https://ivanchernyshov.github.io/NistChemPy/).


## Extracted data

Before using **NistChemPy**, please check [NistChemData](https://github.com/IvanChernyshov/NistChemData).

This repository contains information that has already been extracted from the WebBook using **NistChemPy** functionality.

By doing so, you can bypass the web-scraping stage and proceed directly to data manipulation.


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

