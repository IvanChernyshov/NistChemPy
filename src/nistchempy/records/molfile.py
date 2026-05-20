'''Structured MOL file records.'''

from __future__ import annotations

import dataclasses as _dcs

from nistchempy.records.base import JsonDict
from nistchempy.records.base import RecordBase


@_dcs.dataclass
class MolfileRecord(RecordBase):
    '''Structured record for a downloaded MOL file.

    Args:
        compound_id: NIST Chemistry WebBook compound ID.
        dimension: MOL file dimensionality, usually 2 or 3.
        molfile: Raw MOL file text.
        source_url: URL used to download the MOL file.
        retrieved_at: Optional retrieval timestamp.
    '''

    record_type: str = 'molfile'
    dimension: int = 0
    molfile: str = ''

    def to_dict(self) -> JsonDict:
        '''Return the MOL file record as a JSON-friendly dictionary.

        Returns:
            dict: MOL file record.
        '''
        result = self.base_dict()
        result.update({
            'dimension': self.dimension,
            'molfile': self.molfile,
        })
        return result
