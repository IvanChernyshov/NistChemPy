'''Structured compound metadata records.'''

from __future__ import annotations

import dataclasses as _dcs
import typing as _tp

from nistchempy.records.base import JsonDict
from nistchempy.records.base import RecordBase
from nistchempy.records.base import clean_mapping
from nistchempy.records.base import list_copy


@_dcs.dataclass
class CompoundRecord(RecordBase):
    '''Structured metadata record for a WebBook compound.

    Args:
        compound_id: NIST Chemistry WebBook compound ID.
        name: Preferred compound name.
        synonyms: Alternative compound names.
        formula: Molecular formula.
        mol_weight: Molecular weight.
        inchi: InChI string.
        inchi_key: InChIKey string.
        cas_rn: CAS Registry Number, when available.
        mol_refs: Links to MOL file resources.
        data_refs: Links to WebBook property sections.
        nist_public_refs: Links to public NIST-related resources.
        nist_subscription_refs: Links to subscription NIST-related resources.
        source_url: URL of the source WebBook page.
        retrieved_at: Optional retrieval timestamp.
    '''

    record_type: str = 'compound'
    name: str = ''
    synonyms: _tp.List[str] = _dcs.field(default_factory=list)
    formula: _tp.Optional[str] = None
    mol_weight: _tp.Optional[float] = None
    inchi: _tp.Optional[str] = None
    inchi_key: _tp.Optional[str] = None
    cas_rn: _tp.Optional[str] = None
    mol_refs: _tp.Dict[str, str] = _dcs.field(default_factory=dict)
    data_refs: _tp.Dict[str, str] = _dcs.field(default_factory=dict)
    nist_public_refs: _tp.Dict[str, str] = _dcs.field(default_factory=dict)
    nist_subscription_refs: _tp.Dict[str, str] = _dcs.field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        '''Return the compound record as a JSON-friendly dictionary.

        Returns:
            dict: Compound metadata record.
        '''
        result = self.base_dict()
        result.update({
            'ID': self.compound_id,
            'name': self.name,
            'synonyms': list_copy(self.synonyms),
            'formula': self.formula,
            'mol_weight': self.mol_weight,
            'inchi': self.inchi,
            'inchi_key': self.inchi_key,
            'cas_rn': self.cas_rn,
            'mol_refs': clean_mapping(self.mol_refs),
            'data_refs': clean_mapping(self.data_refs),
            'nist_public_refs': clean_mapping(self.nist_public_refs),
            'nist_subscription_refs': clean_mapping(self.nist_subscription_refs),
        })
        return result
