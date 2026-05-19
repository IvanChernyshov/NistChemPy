'''Unit tests for nistchempy.parsing formed from validation of NistChemPy
via all NIST Chemistry WebBook compounds'''

import pytest

import nistchempy as nist


pytestmark = pytest.mark.network


def test_mw():
    X = nist.get_compound('C25085534')
    assert X.mol_weight


