Development workflows
=====================

This page records the recommended local checks for contributors and release
preparation. The default workflow is offline and deterministic. Live NIST
Chemistry WebBook checks are kept separate because failures may reflect network
availability or upstream HTML changes rather than a package regression.

Offline tests
-------------

Install development dependencies and run the default suite:

.. code-block:: bash

   python -m pip install -e ".[dev]"
   pytest -q

The default suite uses synthetic/sanitized fixtures and does not contact the
NIST Chemistry WebBook.

Coverage
--------

For a coverage report:

.. code-block:: bash

   coverage run -m pytest -q
   coverage report -m

The index subsystem, request wrappers, search parsing, compound objects, and
implemented property parsers should remain covered by offline tests. New parser
features should normally add synthetic or sanitized fixture pages under
``tests/fixtures/``.

Online tests
------------

Live integration tests are stored under ``tests/online`` and marked with
``network``. RDKit-dependent structural tests are additionally marked with
``rdkit``. Offline tests run by default; select live or RDKit-specific subsets
with pytest marker expressions:

.. code-block:: bash

   pytest -q -m network
   pytest -q -m "network and not rdkit"
   pytest -q -m "network and rdkit"
   pytest -q -m "rdkit and not network"

Long-running or broad WebBook reconstruction tests should not be added to the
normal online suite. Prefer small smoke tests with known stable pages. If a live
test fails, first check whether the upstream WebBook page or network behavior
changed before treating it as a package bug.

Notebook regeneration
---------------------

Documentation notebooks are committed with pregenerated outputs, while Sphinx is
configured with ``nbsphinx_execute = 'never'``. Regenerate notebooks manually
when examples or public APIs change:

.. code-block:: bash

   python -m pip install -e ".[docs,structure]"
   jupyter nbconvert --execute docs/source/basic_search.ipynb --inplace
   jupyter nbconvert --execute docs/source/compound_properties.ipynb --inplace
   jupyter nbconvert --execute docs/source/local_index.ipynb --inplace
   jupyter nbconvert --execute docs/source/structural_search.ipynb --inplace
   jupyter nbconvert --execute docs/source/requests_config.ipynb --inplace

User-facing notebooks may contain pregenerated live WebBook outputs. Sphinx
does not execute notebooks during documentation builds, so rerun notebooks
manually before release or after public API changes. Keep long-running or broad
index reconstruction outside notebooks; use tiny local CSV fixtures for local
index examples.

Documentation build
-------------------

Build the documentation locally with:

.. code-block:: bash

   python -m pip install -e ".[docs,structure]"
   cd docs
   make html

Release artifact check
----------------------

Before publishing a release, build the package and verify that no generated
WebBook-derived artifacts are included:

.. code-block:: bash

   python -m build
   python tools/check_package_artifacts.py dist/*

The release check rejects files such as ``nist_data.zip``, ``nist_data.csv``,
``compounds_data.json``, and package-internal ``nistchempy/data/`` contents.
