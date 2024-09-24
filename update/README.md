# NistChemPy Update Scripts

This directory contains script those functionality is to update the pre-downloaded info on NIST Chemistry WebBook compounds.


## Requirements

All requirements are listed in [requirements.txt](requirements.txt).

[tqdm](https://tqdm.github.io/) is the only addition to NistChemPy and its dependences.


## How to use

Update scripts use NIST Chemistry WebBook sitemaps to get URLs of compound web pages and use them to extract data.

All scripts require a root directory to store all interim data which is the first CLI parameter.

The data update pipeline consists of the following steps:

1. [get_nist_compounds.py](get_nist_compounds.py): downloads sitemaps, extracts and saves compound URLs.

2. [get_compound_htmls.py](get_compound_htmls.py): downloads HTML-pages of found compounds.

3. [check_compound_initialization.py](check_compound_initialization.py): initializes Compound object from downloaded HTML-files.
Possible errors must be manually verified to fix bugs in NistChemPy code.

4. [process_nonload_errors.py](process_nonload_errors.py): processes errors related to broken links in sitemaps.

5. [get_missing_stereoisomers.py](get_missing_stereoisomers.py): extracts info on stereoisomers for each pre-downloaded compounds. This fixes almost all errors with broken compound URLs.

6. [extract_info_from_htmls.py](extract_info_from_htmls.py): extracts info on compounds from prepared compound HTMLs and saves it as if final nist_data.csv final required for the package.


