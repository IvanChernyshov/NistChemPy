NistChemPy API
==============

The public API is organized around four tasks: live WebBook search, compound
page parsing, user-local index access, and low-level request/parsing helpers.
Internal local-index implementation modules under ``nistchempy.indexing`` are
not documented here as public API.

Top-level package
-----------------

.. automodule:: nistchempy
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Search
------

.. automodule:: nistchempy.search
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Compounds
---------

.. automodule:: nistchempy.compound
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:


Structured records
------------------

.. automodule:: nistchempy.records
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

.. automodule:: nistchempy.records.compound
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

.. automodule:: nistchempy.records.molfile
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

.. automodule:: nistchempy.records.spectra
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

.. automodule:: nistchempy.records.chromatography
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Local indexes
-------------

.. automodule:: nistchempy.index
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Requests
--------

.. automodule:: nistchempy.requests
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Parsing helpers
---------------

The parsing modules are useful for maintainers and advanced users who need to
inspect or adapt WebBook HTML parsing behavior.

.. automodule:: nistchempy.parsing.compound
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

.. automodule:: nistchempy.parsing.gas_chromatography
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Utilities and exceptions
------------------------

.. automodule:: nistchempy.utils
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

.. automodule:: nistchempy.exceptions
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:
