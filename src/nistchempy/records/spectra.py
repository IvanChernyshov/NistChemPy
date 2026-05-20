'''Structured spectrum records.'''

from __future__ import annotations

import dataclasses as _dcs
import typing as _tp

from nistchempy.records.base import JsonDict
from nistchempy.records.base import RecordBase
from nistchempy.records.base import clean_mapping


@_dcs.dataclass
class SpectrumRecord(RecordBase):
    '''Structured record for a WebBook spectrum.

    NistChemPy currently preserves raw JCAMP-DX text and does not digitize it.
    A future release may add optional JCAMP parsing/digitization.

    Args:
        compound_id: NIST Chemistry WebBook compound ID.
        spectrum_type: Spectrum type abbreviation, such as ``IR`` or ``MS``.
        spectrum_index: WebBook spectrum index.
        jdx_text: Raw JCAMP-DX text.
        parsed: Optional parsed/digitized representation. Currently unused by
            core NistChemPy and normally empty.
        source_url: URL used to download the spectrum.
        retrieved_at: Optional retrieval timestamp.
    '''

    record_type: str = 'spectrum'
    spectrum_type: str = ''
    spectrum_index: str = ''
    jdx_text: str = ''
    parsed: _tp.Optional[_tp.Dict] = None

    def to_dict(self, include_raw: bool = True) -> JsonDict:
        '''Return the spectrum record as a JSON-friendly dictionary.

        Args:
            include_raw: If True, include raw JCAMP-DX text in the output.

        Returns:
            dict: Spectrum record.
        '''
        result = self.base_dict()
        result.update({
            'spectrum_type': self.spectrum_type,
            'spectrum_index': self.spectrum_index,
            'parsed': clean_mapping(self.parsed or {}),
        })
        if include_raw:
            result['jdx_text'] = self.jdx_text
        return result
