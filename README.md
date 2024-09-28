# NistChemPy: Python API for NIST Chemistry WebBook

**NistChemPy** is an unofficial API for the [NIST Chemistry WebBook](https://webbook.nist.gov/).

This package not only automates the search and data extraction processes but also bypasses the WebBook's limitation of 400 compounds per search.

Currently, **NistChemPy** enables the extraction of basic compound properties as well as IR, THz, MS, and UV-Vis spectra.

Additional properties are available via URLs that link to their respective web pages, with potential support for direct extraction in future updates.


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

