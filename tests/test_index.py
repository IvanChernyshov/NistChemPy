'''Unit tests for user-local WebBook index support.'''

import json

import pandas as pd
import pytest

import nistchempy as nist
from nistchempy.cache import resolve_index_path
from nistchempy.cli import main as cli_main


def _write_index(path):
    path.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        [
            {
                'ID': 'C71432',
                'name': 'benzene',
                'synonyms': 'benzol',
                'formula': 'C6H6',
                'mol_weight': '78.11',
                'inchi': 'InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H',
                'inchi_key': 'UHOVQNZJYSORNB-UHFFFAOYSA-N',
                'Mass spectrum (electron ionization)': (
                    '/cgi/cbook.cgi?ID=C71432&Mask=200'
                ),
            },
            {
                'ID': 'C64175',
                'name': 'ethanol',
                'synonyms': 'ethyl alcohol',
                'formula': 'C2H6O',
                'mol_weight': '46.07',
                'inchi': 'InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3',
                'inchi_key': 'LFQSCWFLJHTTHZ-UHFFFAOYSA-N',
                'Mass spectrum (electron ionization)': '',
            },
        ]
    )
    df.to_csv(path / 'index.csv', index=False)
    manifest = {
        'schema_version': 1,
        'mode': 'availability',
        'capabilities': ['compound_discovery', 'section_availability'],
    }
    (path / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')


def test_resolve_index_path_prefers_explicit_path(monkeypatch, tmp_path):
    monkeypatch.setenv('NISTCHEMPY_INDEX_PATH', str(tmp_path / 'env-index'))
    assert resolve_index_path(tmp_path / 'explicit') == (
        tmp_path / 'explicit'
    ).resolve()


def test_resolve_index_path_uses_environment(monkeypatch, tmp_path):
    monkeypatch.setenv('NISTCHEMPY_INDEX_PATH', str(tmp_path / 'env-index'))
    assert resolve_index_path() == (tmp_path / 'env-index').resolve()


def test_load_local_index(tmp_path):
    _write_index(tmp_path)
    index = nist.WebBookIndex.from_cache(tmp_path)
    df = index.to_dataframe()
    assert len(df) == 2
    assert index.manifest['mode'] == 'availability'
    assert index.has_capability('section_availability')
    assert df.loc[0, 'mol_weight'] == pytest.approx(78.11)


def test_load_local_index_from_csv_file(tmp_path):
    _write_index(tmp_path)
    csv_path = tmp_path / 'nist_data.csv'
    (tmp_path / 'index.csv').replace(csv_path)
    (tmp_path / 'manifest.json').unlink()

    index = nist.get_local_index(csv_path)

    assert list(index.search('benz', fields='name')['ID']) == ['C71432']
    assert index.manifest['mode'] == 'legacy_csv'
    assert index.has_capability('compound_discovery')
    assert index.has_capability('section_availability')


def test_missing_local_index(tmp_path):
    with pytest.raises(nist.NistChemPyIndexNotFoundError):
        nist.WebBookIndex.from_cache(tmp_path / 'missing')


def test_local_index_search(tmp_path):
    _write_index(tmp_path)
    index = nist.WebBookIndex.from_cache(tmp_path)
    result = index.search('benz', fields='name')
    assert list(result['ID']) == ['C71432']


def test_local_index_section_filter(tmp_path):
    _write_index(tmp_path)
    index = nist.WebBookIndex.from_cache(tmp_path)
    result = index.filter(has_sections='Mass spectrum (electron ionization)')
    assert list(result['ID']) == ['C71432']


def test_get_local_index_convenience(tmp_path):
    _write_index(tmp_path)
    index = nist.get_local_index(tmp_path)
    assert index.get('C71432')['name'] == 'benzene'


def test_cli_status_and_search(capsys, tmp_path):
    _write_index(tmp_path)
    status = cli_main(['index', 'status', '--path', str(tmp_path)])
    assert status == 0
    assert 'Rows: 2' in capsys.readouterr().out

    search = cli_main([
        'index',
        'search',
        'benzene',
        '--path',
        str(tmp_path),
        '--format',
        'csv',
    ])
    assert search == 0
    assert 'C71432' in capsys.readouterr().out
