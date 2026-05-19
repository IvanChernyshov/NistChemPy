'''Unit tests for package data cleanup.'''

from pathlib import Path

import pytest

import nistchempy as nist


PACKAGE_DIR = Path(__file__).resolve().parents[1] / 'src' / 'nistchempy'


def test_bundled_nist_data_removed():
    assert not (PACKAGE_DIR / 'data' / 'nist_data.zip').exists()


def test_legacy_get_all_data_removed():
    assert not hasattr(nist, 'get_all_data')
    assert not (PACKAGE_DIR / 'compound_list.py').exists()
