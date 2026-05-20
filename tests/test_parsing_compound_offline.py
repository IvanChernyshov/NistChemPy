'''Offline tests for compound-page parsing.'''

import bs4

import nistchempy.parsing.compound as parser

from tests.helpers import soup_from_fixture


def test_parse_compound_page_extracts_basic_fields():
    soup = soup_from_fixture('compound_basic.html')

    info = parser.parse_compound_page(soup)

    assert info['ID'] == 'C111111'
    assert info['name'] == 'Dummybenzene'
    assert info['synonyms'] == ['Dummy benzol', 'Dummy cyclohexatriene']
    assert info['formula'] == 'C6H6'
    assert info['mol_weight'] == 78.11
    assert info['inchi'] == 'InChI=1S/C6H6/dummy'
    assert info['inchi_key'] == 'DUMMYKEY123'
    assert info['cas_rn'] == '000-00-0'
    assert info['mol_refs']['mol2D'].endswith('Str2File=C111111')
    assert info['mol_refs']['mol3D'].endswith('Str3File=C111111')
    assert info['data_refs']['cMS'].endswith('Mask=200#Mass-Spec')
    assert info['data_refs']['cGC'].endswith('Mask=2000#GC')
    assert info['nist_public_refs']['Dummy public reference']
    assert info['nist_subscription_refs']['Dummy subscription reference']


def test_parse_compound_page_returns_none_for_non_compound_page():
    soup = bs4.BeautifulSoup('<html><body><h1>Search</h1></body></html>',
                             features='html.parser')

    assert parser.parse_compound_page(soup) is None
    assert not parser.is_compound_page(soup)
    assert not parser.is_compound_page(None)


def test_molecular_weight_without_numeric_value_returns_none():
    soup = soup_from_fixture('compound_no_mw.html')

    assert parser.get_compound_mol_weight(soup) is None


def test_get_found_compounds_is_safe_for_missing_markup():
    soup = bs4.BeautifulSoup('<html><body>No ordered list</body></html>',
                             features='html.parser')

    assert parser.get_found_compounds(None) == {'IDs': [], 'lost': False}
    assert parser.get_found_compounds(soup) == {'IDs': [], 'lost': False}
