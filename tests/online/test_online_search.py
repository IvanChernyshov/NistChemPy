'''Unit tests for nistchempy.search'''

import os, tempfile

import pytest

import nistchempy as nist


pytestmark = pytest.mark.network


class TestSearch:
    
    def test_search_id(self):
        s = nist.run_search('C71432', 'id')
        assert len(s.compounds) == 1
        assert s.compounds[0].name.lower() == 'benzene'
    
    def test_search_casrn(self):
        s = nist.run_search('71-43-2', 'cas')
        assert len(s.compounds) == 1
        assert s.compounds[0].name.lower() == 'benzene'
    
    def test_search_name(self):
        s = nist.run_search('*butadiene*', 'name')
        assert len(s.compound_ids) > 0
        X = nist.get_compound(s.compound_ids[0])
        names = [X.name] + X.synonyms
        assert any(['butadiene' in name.lower() for name in names])
    
    def test_search_formula(self):
        s = nist.run_search('C6H?Cl3', 'formula')
        assert s.compound_ids
    
    def test_search_inchi(self):
        s = nist.run_search('InChI=1S/C10H14O2/c1-6-3-4-8-7(2)5-12-10(11)9(6)8/h5-6,8-9H,3-4H2,1-2H3', 'inchi')
        assert s.compound_ids
    
    def test_search_bad_inchi(self):
        s = nist.run_search('qwe-qwe-qwe', 'inchi')
        assert not s.compound_ids
    
    def test_search_lost(self):
        s = nist.run_search('C?H?O?', 'formula')
        assert s.lost
    
    def test_load_compounds(self):
        s = nist.run_search('InChI=1S/C10H14O2/c1-6-3-4-8-7(2)5-12-10(11)9(6)8/h5-6,8-9H,3-4H2,1-2H3', 'inchi')
        s.load_found_compounds()
        assert all([X.ID is not None for X in s.compounds])



@pytest.mark.rdkit
class TestStructuralSearch():
    
    def test_missing_mol(self):
        with pytest.raises(ValueError) as _:
            nist.run_structural_search(None, None, 'sub')
    
    def test_incorrect_search_type(self):
        with pytest.raises(ValueError) as _:
            nist.run_structural_search('x.mol', None, 'xyi')
    
    def test_search_molfile(self):
        with tempfile.NamedTemporaryFile(delete=False, mode='wt') as fp:
            fp.write(nist.molblock_from_smiles('CC(=O)OCC'))
            fp.close()
        s = nist.run_structural_search(molfile=fp.name, search_type='struct')
        os.remove(fp.name)
        assert s.compound_ids
    
    def test_search_molblock(self):
        s = nist.run_structural_search(molblock=nist.molblock_from_smiles('CC(=O)OCC'),
                                       search_type='struct')
        assert s.compound_ids
    
    def test_search_smiles(self):
        pytest.importorskip('rdkit.Chem')
        s = nist.run_structural_search(smiles='CC(=O)OCC',
                                       search_type='struct')
        assert s.compound_ids
    
    def test_search_substructure(self):
        s = nist.run_structural_search(molblock=nist.molblock_from_smiles('CC(=O)OCC'),
                                       search_type='sub')
        assert s.num_compounds > 100
    
    def test_incorrect_molblock(self):
        s = nist.run_structural_search(molblock='qwe\nrty\n',
                                       search_type='sub')
        assert not s.num_compounds


