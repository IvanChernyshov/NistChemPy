Changelog
=========

Unreleased (2.0.0 development)
------------------------------

Index and data-distribution policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Removes the packaged WebBook-derived compound index from NistChemPy distributions.

* Removes the legacy ``get_all_data`` API. Local indexes are now loaded through :py:func:`nistchempy.get_local_index` or :py:class:`nistchempy.WebBookIndex`.

* Adds a user-local WebBook index/cache workflow. Generated local indexes, caches, CSV files, JSON exports, and related artifacts are user-local data artifacts and are not covered by the NistChemPy software license.

* Adds ``DATA_NOTICE.md`` and a documentation data-notice page to clarify the software/data boundary.

Local index functionality
~~~~~~~~~~~~~~~~~~~~~~~~~

* Adds local index CLI commands for path resolution, status, search, importing local CSV files, discovery, enrichment, and full index builds.

* Adds formula-browser, formula-search, and sitemap discovery strategies that create intermediate ``seeds.csv`` files before compound-page enrichment.

* Adds compound-page enrichment from ``seeds.csv`` into final ``index.csv`` files, with resumable ``index.partial.jsonl`` state.

* Keeps CAS RN in locally generated indexes by default.

* Adds local-index availability helpers such as ``available_properties()``, ``property_columns()``, and ``has_property()``.

Structured records and export helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Adds lightweight structured records for compound metadata, molfiles, spectra, and gas chromatography outputs.

* Adds ``to_record()``, ``to_dict()``, ``iter_records()``, and ``to_records()`` helpers for compound and loaded property objects.

* Adds JSON and JSON Lines export helpers for structured record collections.

Search, parsing, and request handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Adds optional RDKit-backed SMILES/InChI conversion helpers for live WebBook structural search.

* Adds RDKit-assisted local structural search over local-index ``inchi`` and ``inchi_key`` columns.

* Hardens compound-page parsing, request handling, search error reporting, and gas chromatography parsing against malformed pages and non-HTML responses.

* Fixes parser warnings and deprecated BeautifulSoup API usage.

* Makes live WebBook tests opt-in and keeps the default test suite offline.

Project structure and release safeguards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Moves local-index implementation into the ``nistchempy.indexing`` support package and removes legacy ``update/`` reconstruction scripts.

* Targets Python 3.9+ for the 2.0 development line.

* Adds a package-artifact release check to prevent generated WebBook-derived index/cache files from being shipped in wheels or source distributions.

Documentation and development workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Adds a structural-search notebook and a local-index workflow cookbook page.

* Restores user-facing notebooks to real online WebBook workflows with pregenerated outputs, while Sphinx still does not execute notebooks during documentation builds.

* Adds a tiny local-index CSV documentation fixture so users can see the generated-index schema without building a full cache.

* Adds development workflow documentation for offline tests, online tests, notebook regeneration, docs builds, and release artifact checks.

* Adds a public note on AI-assisted development.

1.0.6
-----

* Refreshes README wording and public project status description.

* Clarifies that NistChemPy is unofficial and is not affiliated with or endorsed by NIST.

* Softens references to NistChemData and frames it as a historical companion repository with provenance-sensitive data-use caveats.

* Updates PyPI-facing metadata, project description, keywords, and project links.

No runtime API changes are intended in this release.


1.0.5
-------------------------

* Updates the historical bundled compound list returned by ``nistchempy.compound_list.get_all_data``.

* Adds structural search via :py:func:`nistchempy.search.run_structural_search`.

* Fixes missing BeautifulSoup dependency - thanks to `stanleyjs <https://github.com/stanleyjs>`_!


1.0.4
-----

* Fixes bug with incorrect GET parameters within formula search.

* Adds :py:func:`nistchempy.utils.get_crawl_delay` function.

* Adds :py:meth:`nistchempy.requests.RequestConfig.max_attempts` attribute to soften impact from potential server response errors.

* Adds update scripts for crawling compounds via formula search.

* Refactors all update scripts.


1.0.3
-----

* Adds functionality to extract gas chromatography data via ``NistCompound.get_gas_chromatography``.

* Adds functionality to set up requests kwargs via :py:class:`nistchempy.requests.RequestConfig`.

* Switches to `src`-layout and `pyproject.toml`.

* Fixes small bugs.


1.0.2
-----

* Adds approximately 10,000 missing InChI strings to the historical pre-saved compound data returned by ``nistchempy.compound_list.get_all_data``.

* Fixes an update bug that resulted in approximately 10,000 missing InChI strings.

* Fixes chemical formula parser.

* Adds reference to repo containing data extracted from NIST Chemistry WebBook (`NistChemData <https://github.com/muCommons/NistChemData>`_).


1.0.1
-----

* Fixes bug with saving spectra.

* Fixes unintended spaces in chemical formula.


1.0.0
-----

First tracked release.


