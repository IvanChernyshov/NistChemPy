'''Unit tests for nistchempy.requests.RequestConfig'''

import pytest
import nistchempy as nist


class TestConfig:
    
    def test_incorrect_delay(self):
        with pytest.raises(Exception) as _:
            nist.RequestConfig(delay=-1)
        with pytest.raises(Exception) as _:
            nist.RequestConfig(delay='qwe')
    
    def test_incorrect_kwargs(self):
        cfg = nist.RequestConfig(kwargs={'timeout': 5, 'params': {}})
        assert cfg.kwargs.get('timeout', None)
        assert cfg.kwargs.get('params', None) is None



class TestCompound:
    
    ID = 'C71432'
    
    def test_low_timeout(self):
        # get_compound
        cfg = nist.RequestConfig(kwargs={'timeout': 0.01})
        with pytest.raises(Exception) as _:
            nist.get_compound(self.ID, cfg)
        # Compound methods
        X = nist.get_compound(self.ID)
        X._request_config = cfg
        with pytest.raises(Exception) as _:
            X.get_all_spectra()
        with pytest.raises(Exception) as _:
            X.get_mol2D()
        with pytest.raises(Exception) as _:
            X.get_gas_chromatography()
    
    def test_correct_config(self):
        cfg = nist.RequestConfig(delay=1.0, kwargs={'timeout': 30.0})
        X = nist.get_compound(self.ID, cfg)
        assert X is not None
        assert X._request_config.delay == 1.0
        assert X._request_config.kwargs['timeout'] == 30.0



class TestSearch:
    
    name = '1,2*butadiene'
    
    def test_low_timeout(self):
        # run_search
        cfg = nist.RequestConfig(delay=1.0, kwargs={'timeout': 0.01})
        with pytest.raises(Exception) as _:
            nist.run_search(self.name, 'name', request_config=cfg)
        # Search methods
        s = nist.run_search(self.name, 'name')
        s._request_config = cfg
        with pytest.raises(Exception) as _:
            s.load_found_compounds()
    
    def test_correct_config(self):
        cfg = nist.RequestConfig(delay=1.0, kwargs={'timeout': 30.0})
        s = nist.run_search(self.name, 'name', request_config=cfg)
        assert s._request_config.delay == 1.0
        assert s._request_config.kwargs['timeout'] == 30.0
        s.load_found_compounds()
        X = s.compounds[0]
        assert X._request_config.delay == 1.0
        assert X._request_config.kwargs['timeout'] == 30.0


