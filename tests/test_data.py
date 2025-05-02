'''Unit tests for the package data related functionality'''

import nistchempy as nist


def test_nist_data():
    df = nist.get_all_data()
    assert len(df) > 10**5


