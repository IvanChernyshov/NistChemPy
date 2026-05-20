'''Unit tests for nistchempy.compound'''

import pytest

import nistchempy as nist


pytestmark = pytest.mark.network


class TestCompoundInitialization:
    
    def test_correct_id(self):
        X = nist.get_compound('C71432')
        assert X is not None
    
    def test_correct_casrn(self):
        X = nist.get_compound('71-43-2')
        assert X is not None
    
    def test_correct_inchi(self):
        X = nist.get_compound('InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H')
        assert X is not None
    
    def test_nonunique_inchi(self):
        X = nist.get_compound('InChI=1S/C10H14O2/c1-6-3-4-8-7(2)5-12-10(11)9(6)8/h5-6,8-9H,3-4H2,1-2H3')
        assert X is None
    
    def test_incorrect_id(self):
        X = nist.get_compound('qwe-qwe-qwe')
        assert X is None



class TestPropertyExtraction:
    
    def test_mol2D(self):
        compound = nist.get_compound('C71432')
        assert compound.mol2D is None
        compound.get_mol2D()
        assert compound.mol2D is not None
    
    def test_ms_spec(self):
        compound = nist.get_compound('C71432')
        assert not compound.ms_specs
        compound.get_ms_spectra()
        assert compound.ms_specs
        assert compound.ms_specs[0].jdx_text is not None
    
    def test_gas_chromat(self):
        compound = nist.get_compound('C71432')
        assert not compound.gas_chromat
        compound.get_gas_chromatography()
        assert compound.gas_chromat
        assert len(compound.gas_chromat[0].data) > 0


