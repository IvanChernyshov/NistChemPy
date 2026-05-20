'''Offline tests for RDKit-assisted local-index structural search.'''

from pathlib import Path

import pandas as pd
import pytest

import nistchempy as nist


pytestmark = pytest.mark.rdkit


def _example_index():
    pytest.importorskip('rdkit.Chem')
    path = Path(__file__).parent / 'fixtures' / 'index' / 'example_index.csv'
    return nist.get_local_index(path)


def test_local_index_exact_structural_search():
    index = _example_index()

    result = index.structural_search(smiles='c1ccccc1', mode='exact')

    assert list(result['ID']) == ['C71432']


def test_local_index_substructure_search():
    index = _example_index()

    result = index.structural_search(smiles='CCO', mode='substructure')

    assert 'C64175' in set(result['ID'])
    assert 'C71432' not in set(result['ID'])


def test_local_index_similarity_search():
    index = _example_index()

    result = index.structural_search(
        smiles='CCO',
        mode='similarity',
        threshold=0.1,
    )

    assert 'similarity' in result.columns
    assert list(result['similarity']) == sorted(result['similarity'], reverse=True)
    assert result.iloc[0]['ID'] == 'C64175'


def test_local_index_structural_search_skips_bad_inchi(tmp_path):
    pytest.importorskip('rdkit.Chem')
    csv_path = tmp_path / 'index.csv'
    pd.DataFrame([
        {
            'ID': 'BAD',
            'name': 'bad',
            'inchi': 'not an inchi',
            'inchi_key': '',
        },
        {
            'ID': 'C64175',
            'name': 'ethanol',
            'inchi': 'InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3',
            'inchi_key': 'LFQSCWFLJHTTHZ-UHFFFAOYSA-N',
        },
    ]).to_csv(csv_path, index=False)
    index = nist.get_local_index(csv_path)

    result = index.structural_search(smiles='CCO', mode='substructure')

    assert list(result['ID']) == ['C64175']


def test_local_index_structural_search_can_raise_bad_inchi(tmp_path):
    pytest.importorskip('rdkit.Chem')
    csv_path = tmp_path / 'index.csv'
    pd.DataFrame([
        {
            'ID': 'BAD',
            'name': 'bad',
            'inchi': 'not an inchi',
            'inchi_key': '',
        },
    ]).to_csv(csv_path, index=False)
    index = nist.get_local_index(csv_path)

    with pytest.raises(ValueError):
        index.structural_search(
            smiles='CCO',
            mode='substructure',
            errors='raise',
        )
