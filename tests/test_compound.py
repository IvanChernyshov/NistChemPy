'''Unit tests for nistchempy.compound'''

import nistchempy as nist


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
    
    X = nist.get_compound('C71432')
    
    def test_mol2D(self):
        assert self.X.mol2D is None
        self.X.get_mol2D()
        assert self.X.mol2D is not None
    
    def test_ms_spec(self):
        assert not self.X.ms_specs
        self.X.get_ms_spectra()
        assert self.X.ms_specs
        assert self.X.ms_specs[0].jdx_text is not None


