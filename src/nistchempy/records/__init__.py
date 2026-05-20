'''Structured JSON-like records returned by NistChemPy.'''

from nistchempy.records.compound import CompoundRecord
from nistchempy.records.molfile import MolfileRecord
from nistchempy.records.spectra import SpectrumRecord
from nistchempy.records.chromatography import ChromatogramRecord

__all__ = [
    'CompoundRecord',
    'MolfileRecord',
    'SpectrumRecord',
    'ChromatogramRecord',
]
