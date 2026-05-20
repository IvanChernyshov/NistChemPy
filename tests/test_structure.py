'''Offline tests for optional structure helpers.'''

import importlib

import pytest

import nistchempy as nist
from nistchempy import structure


def test_missing_rdkit_error_message(monkeypatch):
    def fake_import_module(name):
        if name.startswith('rdkit'):
            raise ImportError('missing rdkit')
        return importlib.import_module(name)

    monkeypatch.setattr(structure._importlib, 'import_module', fake_import_module)

    with pytest.raises(nist.NistChemPyOptionalDependencyError) as exc:
        structure.mol_from_smiles('CCO')

    message = str(exc.value)
    assert 'RDKit is required' in message
    assert 'pip install rdkit' in message
    assert 'conda install -c conda-forge rdkit' in message


@pytest.mark.rdkit
def test_molblock_from_smiles_contains_atoms():
    pytest.importorskip('rdkit.Chem')

    molblock = nist.molblock_from_smiles('c1ccccc1')

    assert 'V2000' in molblock
    assert 'M  END' in molblock


@pytest.mark.rdkit
def test_molblock_from_inchi_contains_atoms():
    pytest.importorskip('rdkit.Chem')

    molblock = nist.molblock_from_inchi('InChI=1S/H2O/h1H2')

    assert 'V2000' in molblock
    assert 'M  END' in molblock


@pytest.mark.rdkit
def test_invalid_smiles_raises_value_error():
    pytest.importorskip('rdkit.Chem')

    with pytest.raises(ValueError):
        structure.mol_from_smiles('not a smiles')


@pytest.mark.rdkit
def test_query_mol_requires_exactly_one_input():
    pytest.importorskip('rdkit.Chem')

    with pytest.raises(ValueError):
        structure.query_mol_from_input()
    with pytest.raises(ValueError):
        structure.query_mol_from_input(smiles='CCO', inchi='InChI=1S/H2O/h1H2')
