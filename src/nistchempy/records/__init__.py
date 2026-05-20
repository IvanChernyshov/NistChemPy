'''Structured JSON-like records returned by NistChemPy.'''

from nistchempy.records.compound import CompoundRecord
from nistchempy.records.molfile import MolfileRecord
from nistchempy.records.spectra import SpectrumRecord
from nistchempy.records.chromatography import ChromatogramRecord
from nistchempy.records.io import record_to_dict
from nistchempy.records.io import records_to_dicts
from nistchempy.records.io import write_records_json
from nistchempy.records.io import write_records_jsonl

__all__ = [
    'CompoundRecord',
    'MolfileRecord',
    'SpectrumRecord',
    'ChromatogramRecord',
    'record_to_dict',
    'records_to_dicts',
    'write_records_json',
    'write_records_jsonl',
]
