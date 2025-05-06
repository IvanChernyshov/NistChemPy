==========================================
Welcome to the NistChemPy's documentation!
==========================================

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Cookbook:
   
   Basic Search <source/basic_search.ipynb>
   Compound Properties <source/compound_properties.ipynb>
   Advanced Search <source/advanced_search.ipynb>
   Requests Configuration <source/requests_config.ipynb>


.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Package details:
   
   Package API <source/api>
   Changelog <source/changelog>


**NistChemPy** is an unofficial API for the `NIST Chemistry WebBook`_.
This package not only automates the search and data extraction processes but also bypasses the WebBook's limitation of 400 compounds per search.
Currently, **NistChemPy** enables the extraction of basic compound properties as well as IR, THz, MS, UV-Vis spectra and gas chromatography data.
Additional properties are available via URLs that link to their respective web pages, with potential support for direct extraction in future updates.


Extracted data
==============

Before using **NistChemPy**, please check `NistChemData`_.
This repository contains information that has already been extracted from the WebBook using **NistChemPy** functionality.
By doing so, you can bypass the web-scraping stage and proceed directly to data manipulation.


Installation
============

**NistChemPy** can be installed as a `PyPI package`_:

.. code-block::
   
   > pip install nistchempy


Requirements
============

1. Python 3.7+;

2. requests;

3. bs4;

4. pandas;

5. importlib_resources (for Python 3.7 and 3.8).


Useful links
============

1. `NIST Chemistry WebBook`_: webapp accessing the NIST Chemistry WebBook database.
2. `GitHub`_: GitHub page of the package.
3. `NistChemData`_: Repository containing already extracted WebBook's data.
4. `PyPI package`_: PyPI page of the package.
5. `Update tools`_: script for semi-automatic update of structural information of new NIST Chemistry WebBook compounds.


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`



.. _NistChemData: https://github.com/IvanChernyshov/NistChemData
.. _NIST Chemistry WebBook: https://webbook.nist.gov/chemistry/
.. _GitHub: https://github.com/IvanChernyshov/NistChemPy
.. _PyPI package: https://pypi.org/project/nistchempy/
.. _Update tools: https://github.com/IvanChernyshov/NistChemPy/tree/main/update
