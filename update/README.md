# NistChemPy Update Scripts

This directory contains script those functionality is to update the pre-downloaded info on NIST Chemistry WebBook compounds.


## Requirements

All requirements are listed in [requirements.txt](requirements.txt).

[tqdm](https://tqdm.github.io/) is the only addition to NistChemPy and its dependencies.


## How to use

Update scripts use NIST Chemistry WebBook sitemaps to get URLs of compound web pages and use them to extract data.

All scripts require a root directory to store all interim data which is the first CLI parameter.

The data update pipeline consists of the following steps:

1. [1_get_compounds_via_formula.py](1_get_compounds_via_formula.py): searches for compound IDs via scanning chemical formulas.
Alternative to the sitemap-based approach.

> [!NOTE]
> The recommended script parameters are:
>
> `> python 1_get_compounds_via_formula.py path/to/root/compounds_formula.csv 0 200`
>
> In this case the 3rd script won't need additional actions.

2. [2_get_compounds_via_sitemaps.py](2_get_compounds_via_sitemaps.py): downloads sitemaps, extracts and saves compound URLs.

> [!TIP]
> Since WebBook's sitemaps were last updated in 2018, one can safely ignore this script.

3. [3_get_compound_htmls.py](3_get_compound_htmls.py): downloads HTML-pages of found compounds.
Compound list is generated from results of the 1st (`compounds_formula.csv`) and the 2nd (`compounds_sitemaps.csv`) scripts along with already stored in the `nistchempy.get_all_data` function.
Those sources are combined and saved to the `compounds_combined.csv`.

4. [4_check_compound_initialization.py](4_check_compound_initialization.py): initializes Compound object from downloaded HTML-files.
Possible errors must be manually verified to fix bugs in NistChemPy code.

5. [5_get_compounds_from_refs.py](5_get_compounds_from_refs.py): extracts info on stereoisomers for each pre-downloaded compounds.

6. [6_extract_info_from_htmls.py](6_extract_info_from_htmls.py): extracts info on compounds from prepared compound HTMLs and saves it as if final nist_data.csv final required for the package.


