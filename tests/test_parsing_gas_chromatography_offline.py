'''Offline tests for gas chromatography parsing.'''

import pytest

import nistchempy.parsing.gas_chromatography as parser

from tests.helpers import soup_from_fixture


def test_get_chromatography_table_refs():
    soup = soup_from_fixture('gas_chromatography_page.html')

    refs = parser.get_chromatography_table_refs(soup)

    assert len(refs) == 1
    assert refs[0].startswith('https://webbook.nist.gov')
    assert parser.get_chromatography_table_refs(None) == []


def test_parse_chromatography_table():
    soup = soup_from_fixture('gas_chromatography_table.html')

    info = parser.parse_chromatography_table(soup)

    assert info['ri_type'] == 'Kovats RI'
    assert info['column_type'] == 'non-polar column'
    assert info['temp_regime'] == 'isothermal'
    assert info['data'].iloc[0]['Column'] == 'Dummy column'
    assert 'Dummy Author' in info['data'].iloc[0]['Reference']


def test_parse_chromatography_table_rejects_malformed_page():
    with pytest.raises(ValueError):
        parser.parse_chromatography_table(None)
