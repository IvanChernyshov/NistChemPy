Changelog
=========

1.0.5 (under development)
-------------------------

* TODO: update internal compound list :py:func:`nistchempy.compound_list.get_all_data`.


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


