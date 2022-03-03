# NistChemPy: Python API for NIST Chemistry WebBook

[NIST Chemistry WebBook](https://webbook.nist.gov/) is a public database containing physico-chemical data which was carifully verified by specialists. However, the only way to retrieve information is to use browser, and no API is available. Moreover, search results are limited to 400 found compounds which is convenient for manual search of several compounds but unsuitable for chemoinformatics.

NistChemPy is designed to solve this problem. It supports search by compound name, InChI/InChI-key, CAS RN, and chemical formula, and downloading key properties of retrieved compounds. Search object is designed in a way that it is easy to automate the search for all the necessary substances without exceeding the limit of 400 pieces.

At the moment the code only supports IR, MS and UV/Vis spectra; support for other thermodynamic properties may be added later.

## Installation

Install NistChemPy using:

```
pip install nistchempy
```

## How To

The main NistChemPy features including search and compound manipulations are shown in the [tutorial](https://github.com/EPiCs-group/NistChemPy/blob/main/tutorial.ipynb).
