'''Structured gas chromatography records.'''

from __future__ import annotations

import dataclasses as _dcs
import typing as _tp

import pandas as _pd

from nistchempy.records.base import JsonDict
from nistchempy.records.base import RecordBase


@_dcs.dataclass
class ChromatogramRecord(RecordBase):
    '''Structured record for a gas chromatography table.

    Args:
        compound_id: NIST Chemistry WebBook compound ID.
        ri_type: Retention-index type.
        column_type: Column type.
        temp_regime: Temperature regime.
        data: Chromatography table as a DataFrame.
        source_url: URL used to download the table.
        retrieved_at: Optional retrieval timestamp.
    '''

    record_type: str = 'gas_chromatography'
    ri_type: str = ''
    column_type: str = ''
    temp_regime: str = ''
    data: _pd.DataFrame = _dcs.field(default_factory=_pd.DataFrame)

    def to_dict(self, orient: str = 'records') -> JsonDict:
        '''Return the chromatogram record as a JSON-friendly dictionary.

        Args:
            orient: DataFrame orientation passed to ``DataFrame.to_dict``.

        Returns:
            dict: Gas chromatography record.
        '''
        result = self.base_dict()
        result.update({
            'ri_type': self.ri_type,
            'column_type': self.column_type,
            'temp_regime': self.temp_regime,
            'data': self.data.to_dict(orient=orient),
        })
        return result
