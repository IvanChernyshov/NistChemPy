Changelog
=========

Unreleased
----------

* Removes the packaged WebBook-derived compound index from NistChemPy distributions.

* Adds a user-local WebBook index API via :py:class:`nistchempy.index.WebBookIndex` and :py:func:`nistchempy.index.get_local_index`.

* Adds local index CLI commands for path resolution, status, search, importing local CSV files, discovery, enrichment, and full index builds.

* Adds formula-browser, formula-search, and sitemap discovery strategies that create intermediate ``seeds.csv`` files before compound-page enrichment.

* Adds compound-page enrichment from ``seeds.csv`` into final ``index.csv`` files, with resumable ``index.partial.jsonl`` state.

* Keeps CAS RN in locally generated indexes by default while keeping generated local data outside the NistChemPy software license.

* Adds a package-artifact release check to prevent generated WebBook-derived index/cache files from being shipped in wheels or source distributions.

* Removes the legacy ``get_all_data`` compatibility API; local indexes are loaded through :py:func:`nistchempy.get_local_index` or :py:class:`nistchempy.WebBookIndex`.

* Removes legacy ``update/`` reconstruction scripts in favor of the supported ``nistchempy index`` CLI workflow.

* Targets Python 3.9+ for the 2.0 development line.

* Adds ``DATA_NOTICE.md`` and configures Sphinx to render pregenerated notebooks without live execution during documentation builds.

* Rewrites documentation notebooks around synthetic/offline examples and adds maintainer workflow documentation for tests, notebook regeneration, docs builds, and release artifact checks.

1.0.6
-----

* Refreshes README wording and public project status description.

* Clarifies that NistChemPy is unofficial and is not affiliated with or endorsed by NIST.

* Softens references to NistChemData and frames it as a historical companion repository with provenance-sensitive data-use caveats.

* Updates PyPI-facing metadata, project description, keywords, and project links.

* Prepares the repository metadata for the post-DOI PyPI release.

No runtime API changes are intended in this release.


1.0.5
-------------------------

* Updates internal compound list returned by :py:func:`nistchempy.compound_list.get_all_data`.

* Adds structural search via :py:func:`nistchempy.search.run_structural_search`.

* Fixes missing BeautifulSoup dependence - thanks to [stanleyjs](https://github.com/stanleyjs)!


1.0.4
-----

* Fixes bug with incorrect GET parameters within formula search.

* Adds :py:func:`nistchempy.utils.get_crawl_delay` function.

* Adds :py:meth:`nistchempy.requests.RequestConfig.max_attempts` attribute to soften impact from potential server response errors.

* Adds update script scrawling compounds vis formula search.

* Refactors all update scripts.


1.0.3
-----

* Adds functionality to extract gas chromatogaraphy data via :py:meth:`nistchempy.compound.Compound.get_gas_chromatography`.

* Adds functionality to set up requests kwargs via :py:class:`nistchempy.requests.RequestConfig`.

* Switches to `src`-layout and `pyproject.toml`.

* Fixes small bugs.


1.0.2
-----

* Adds c.a. 10 000 of missing InChI strings to the pre-saved data on compounds (:py:func:`nistchempy.compound_list.get_all_data`).

* Fixes bug in update resulted in c.a. 10 000 of missing InChI strings.

* Fixes chemical formula parser.

* Adds reference to repo containing data extracted from NIST Chemistry WebBook (`NistChemData <https://github.com/IvanChernyshov/NistChemData>`_).


1.0.1
-----

* Fixes bug with saving spectra.

* Fixes unintended spaces in chemical formula.


1.0.0
-----

First tracked release.


