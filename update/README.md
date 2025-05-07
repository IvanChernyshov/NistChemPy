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

2. [2_get_nist_compounds.py](2_get_nist_compounds.py): downloads sitemaps, extracts and saves compound URLs.

3. [3_get_compound_htmls.py](3_get_compound_htmls.py): downloads HTML-pages of found compounds.

4. [4_check_compound_initialization.py](4_check_compound_initialization.py): initializes Compound object from downloaded HTML-files.
Possible errors must be manually verified to fix bugs in NistChemPy code.

5. [5_process_nonload_errors.py](5_process_nonload_errors.py): processes errors related to broken links in sitemaps.

6. [6_get_missing_stereoisomers.py](6_get_missing_stereoisomers.py): extracts info on stereoisomers for each pre-downloaded compounds.
This fixes almost all errors with broken compound URLs.

7. [7_extract_info_from_htmls.py](7_extract_info_from_htmls.py): extracts info on compounds from prepared compound HTMLs and saves it as if final nist_data.csv final required for the package.

8. [8_get_old_IDs.py](8_get_old_IDs.py): tries to download HTML-pages of compounds that are missing in current nist_data.csv file, but is available in old versions.
If there are such entries, the previous script must be re-executed.


