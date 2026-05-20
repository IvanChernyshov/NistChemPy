'''Tests for structured record export helpers.'''

import json

import pandas as pd
import pytest

from nistchempy.records import ChromatogramRecord
from nistchempy.records import CompoundRecord
from nistchempy.records import SpectrumRecord
from nistchempy.records import record_to_dict
from nistchempy.records import records_to_dicts
from nistchempy.records import write_records_json
from nistchempy.records import write_records_jsonl


def test_record_to_dict_omits_spectrum_raw_text_when_requested():
    record = SpectrumRecord(
        compound_id='C1',
        spectrum_type='MS',
        spectrum_index='0',
        jdx_text='##TITLE=Dummy spectrum',
    )

    data = record_to_dict(record, include_raw=False)

    assert data['record_type'] == 'spectrum'
    assert data['spectrum_type'] == 'MS'
    assert 'jdx_text' not in data


def test_record_to_dict_uses_chromatogram_orient():
    record = ChromatogramRecord(
        compound_id='C1',
        data=pd.DataFrame({'temperature': [300.0], 'RI': [1000.0]}),
    )

    data = record_to_dict(record, orient='list')

    assert data['record_type'] == 'gas_chromatography'
    assert data['data'] == {'temperature': [300.0], 'RI': [1000.0]}


def test_records_to_dicts_accepts_records_and_mappings():
    records = [
        CompoundRecord(compound_id='C1', name='Dummy'),
        {'record_type': 'custom', 'compound_id': 'C2'},
    ]

    data = records_to_dicts(records)

    assert data[0]['record_type'] == 'compound'
    assert data[1]['record_type'] == 'custom'


def test_record_to_dict_rejects_invalid_object():
    with pytest.raises(TypeError, match='Unsupported record object'):
        record_to_dict(object())


def test_record_to_dict_rejects_invalid_to_dict_result():
    class BadRecord:
        def to_dict(self):
            return ['not', 'a', 'mapping']

    with pytest.raises(TypeError, match='must return a mapping'):
        record_to_dict(BadRecord())


def test_write_records_json(tmp_path):
    path = tmp_path / 'records.json'
    records = [CompoundRecord(compound_id='C1', name='Dummy')]

    write_records_json(records, path)

    data = json.loads(path.read_text(encoding='utf-8'))
    assert data[0]['record_type'] == 'compound'
    assert data[0]['ID'] == 'C1'


def test_write_records_jsonl(tmp_path):
    path = tmp_path / 'records.jsonl'
    records = [
        CompoundRecord(compound_id='C1', name='Dummy 1'),
        CompoundRecord(compound_id='C2', name='Dummy 2'),
    ]

    write_records_jsonl(records, path)

    lines = path.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])['ID'] == 'C1'
    assert json.loads(lines[1])['ID'] == 'C2'
