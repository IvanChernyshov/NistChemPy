'''Unit tests for package data cleanup.'''

from pathlib import Path

import pytest

import nistchempy as nist


PACKAGE_DIR = Path(__file__).resolve().parents[1] / 'src' / 'nistchempy'


def test_bundled_nist_data_removed():
    assert not (PACKAGE_DIR / 'data' / 'nist_data.zip').exists()


def test_get_all_data_requires_local_index(monkeypatch, tmp_path):
    monkeypatch.setenv('NISTCHEMPY_INDEX_PATH', str(tmp_path / 'missing'))
    with pytest.deprecated_call():
        with pytest.raises(nist.NistChemPyIndexNotFoundError):
            nist.get_all_data()
