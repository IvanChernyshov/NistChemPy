'''Offline tests for structured NistChemPy records.'''

import pandas as pd

from nistchempy.records import ChromatogramRecord
from nistchempy.records import CompoundRecord
from nistchempy.records import MolfileRecord
from nistchempy.records import SpectrumRecord


def test_compound_record_to_dict():
    record = CompoundRecord(
        compound_id='C111111',
        name='Dummybenzene',
        synonyms=['Dummy benzol'],
        formula='C6H6',
        mol_weight=78.11,
        inchi='InChI=1S/dummy',
        inchi_key='DUMMYKEY',
        cas_rn='000-00-0',
        mol_refs={'mol2D': 'https://example.test/mol2d'},
        data_refs={'cMS': 'https://example.test/ms'},
        source_url='https://example.test/compound',
    )

    data = record.to_dict()

    assert data['record_type'] == 'compound'
    assert data['ID'] == 'C111111'
    assert data['synonyms'] == ['Dummy benzol']
    assert data['data_refs']['cMS'].endswith('/ms')


def test_molfile_record_to_dict():
    record = MolfileRecord(
        compound_id='C111111',
        dimension=2,
        molfile='Dummy MOL',
        source_url='https://example.test/mol2d',
    )

    data = record.to_dict()

    assert data['record_type'] == 'molfile'
    assert data['dimension'] == 2
    assert data['molfile'] == 'Dummy MOL'


def test_spectrum_record_to_dict_can_omit_raw_text():
    record = SpectrumRecord(
        compound_id='C111111',
        spectrum_type='MS',
        spectrum_index='0',
        jdx_text='##TITLE=Dummy',
        source_url='https://example.test/ms',
    )

    full = record.to_dict()
    metadata = record.to_dict(include_raw=False)

    assert full['jdx_text'] == '##TITLE=Dummy'
    assert 'jdx_text' not in metadata
    assert metadata['parsed'] == {}


def test_chromatogram_record_to_dict():
    record = ChromatogramRecord(
        compound_id='C111111',
        ri_type='Kovats RI',
        column_type='non-polar',
        temp_regime='isothermal',
        data=pd.DataFrame({'Retention Index': ['650']}),
        source_url='https://example.test/gc',
    )

    data = record.to_dict()

    assert data['record_type'] == 'gas_chromatography'
    assert data['data'][0]['Retention Index'] == '650'
