Local index workflow
====================

NistChemPy no longer ships a prebuilt NIST Chemistry WebBook index. The local
index is a user-generated cache that helps with broad compound discovery,
property-availability filtering, and local search.

The local index is not an official NIST product and is not covered by the
NistChemPy software license. It is a local artifact created by the user from
NIST Chemistry WebBook pages.

What the index contains
-----------------------

A completed local index is a CSV table, usually named ``index.csv``. It contains
compound identifiers, basic metadata, structure-file links, and WebBook section
availability URLs. Typical columns include:

* ``ID``
* ``name``
* ``synonyms``
* ``formula``
* ``mol_weight``
* ``inchi``
* ``inchi_key``
* ``cas_rn``
* ``mol2D`` and ``mol3D``
* section columns such as ``Mass spectrum (electron ionization)`` and
  ``Gas Chromatography``

The tiny ``example_index.csv`` fixture used in the documentation has the same
kind of column layout, but it is not a replacement for a locally generated
index.

Where the index is stored
-------------------------

By default, NistChemPy stores the local index in the platform-specific user
cache directory under ``nistchempy/webbook-index``. The exact path depends on
the operating system.

Print the resolved default path with:

.. code-block:: bash

   nistchempy index path

The same path is available from Python:

.. code-block:: python

   import nistchempy as nist

   nist.WebBookIndex.default_path()

Use ``--path`` to build or read an index at a project-local location:

.. code-block:: bash

   nistchempy index build --path ./webbook-index --accept-data-terms
   nistchempy index search benzene --path ./webbook-index

Project-local index directories should normally be added to ``.gitignore``.
Do not commit generated full indexes, raw page caches, or other large
WebBook-derived artifacts to public repositories.

How to check status
-------------------

Use the status command if you built an index earlier and forgot where it is, or
if you want to check whether a build completed:

.. code-block:: bash

   nistchempy index status
   nistchempy index status --path ./webbook-index

How the index is formed
-----------------------

A full local-index build has two conceptual stages:

.. code-block:: text

   discovery strategy -> seeds.csv -> compound-page enrichment -> index.csv

The discovery stage finds candidate WebBook compounds and writes
``seeds.csv``. The enrichment stage visits compound pages and extracts metadata,
structure links, and section availability URLs into ``index.csv``.

Supported discovery strategies are:

``formula-browser``
    Traverses the WebBook formula browser and is the default general-purpose
    strategy.

``sitemap``
    Reads WebBook sitemap files when available. It is useful as an audit or
    supplementary source.

``formula-search``
    Uses bounded formula-search subdivision. This strategy requires explicit
    formula bounds and records unresolved query regions for later inspection.

Build the default index with:

.. code-block:: bash

   nistchempy index build --accept-data-terms

.. warning::

   A full section-availability index can require visiting one WebBook page per
   compound.

   With a polite 3 second delay and roughly 100,000-150,000 pages, an initial
   rebuild can take about **3.5-5+ days** before retries and network overhead.

   Use ``--path`` for an explicit cache location and rerun the command to
   resume interrupted enrichment work.

Importing an existing local CSV
-------------------------------

If you already have a local index CSV, import it into the cache layout:

.. code-block:: bash

   nistchempy index build \
     --from-csv /path/to/index.csv \
     --path ./webbook-index \
     --accept-data-terms

This does not make the CSV redistributable. It only records it as a local user
artifact in NistChemPy's current cache layout.

Using the index from Python
---------------------------

.. code-block:: python

   import nistchempy as nist

   index = nist.get_local_index('./webbook-index')
   index.search('benzene')
   index.available_properties('C71432')

Local text and availability search
----------------------------------

The local index supports text search over metadata columns and filtering by
available WebBook sections:

.. code-block:: python

   index.search('benzene')
   index.filter(has_sections='Mass spectrum (electron ionization)')
   index.available_properties('C71432')

Local structural search
-----------------------

If RDKit is installed, the local index can also perform lightweight structural
screening using the indexed ``inchi`` and ``inchi_key`` columns:

.. code-block:: python

   index.structural_search(smiles='c1ccccc1', mode='exact')
   index.structural_search(smiles='CCO', mode='substructure')
   index.structural_search(smiles='CCO', mode='similarity')

This is a linear scan over the local index, not a persistent fingerprint
database. It is useful for small and medium local indexes and exploratory work.
For authoritative online structural search, use ``nist.run_structural_search``.
