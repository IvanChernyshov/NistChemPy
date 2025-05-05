'''The module contains compound-related functionality

Attributes:
    SPEC_TYPES (dict): dictionary containing abbreviations for spectra types used
        in compound page (keys) or urls for downloading JDX-files (values)

'''

#%% Imports

from __future__ import annotations

import re as _re
import os as _os

from urllib.parse import urlparse, parse_qs

import pandas as _pd

import nistchempy.requests as _ncpr
import nistchempy.parsing as _parsing

import dataclasses as _dcs
import typing as _tp


#%% Attributes

SPEC_TYPES = {'IR': 'IR', 'TZ': 'THz', 'MS': 'Mass', 'UV': 'UVVis'}



#%% Classes

@_dcs.dataclass(eq = False, repr = False)
class Spectrum():
    '''Wrapper for IR, MS, and UV-Vis extracted from NIST Chemistry WebBook
    
    Attributes:
        compound (NistCompound): parent NistCompound object
        spec_type (str): IR / TZ (THz IR) / MS / UV (UV-Vis)
        spec_idx (str): index of the spectrum
        jdx_text (str): text block of the corresponding JDX-file
    
    '''
    
    compound: NistCompound
    spec_type: str
    spec_idx: str
    jdx_text: str
    
    
    def __str__(self):
        pretty_names = {'IR': 'IR spectrum', 'TZ': 'THz IR spectrum',
                         'MS': 'Mass spectrum', 'UV': 'UV-Vis spectrum'}
        
        return f'Spectrum({self.compound.ID}, {pretty_names[self.spec_type]} #{self.spec_idx})'
    
    
    def __repr__(self):
        return self.__str__()
    
    
    def save(self, name: str = None, path_dir: str = None) -> None:
        '''Saves spectrum in JDX format
        
        Attributes:
            name (str): custom filename (default name is formed from compound ID,
                spectrum type and index)
            path_dir (str): directory where output file will be saved
        
        '''
        path = name if name else f'{self.compound.ID}_{self.spec_type}_{self.spec_idx}.jdx'
        if path_dir:
            path = _os.path.join(path_dir, path)
        with open(path, 'w') as outf:
            outf.write(self.jdx_text)



@_dcs.dataclass(eq = False, repr = False)
class Chromatogram():
    '''Wrapper chromatography data extracted from NIST Chemistry WebBook
    
    Attributes:
        compound (NistCompound): parent NistCompound object
        ri_type (str): type of retention index: Kovatz, van den Dool & Kratz, etc.
        column_type (str): polar / non-polar
        temp_regime (str): temperature regime: isothermal / ramp / custom
        data (_pd.core.frame.DataFrame): experimental data
    
    '''
    
    compound: NistCompound
    ri_type: str
    column_type: str
    temp_regime: str
    data: _pd.core.frame.DataFrame
    
    
    def __str__(self):
        info = f'{self.compound.ID}, {self.ri_type}, {self.column_type}, {self.temp_regime}'
        return f'Chromatogram({info}: {len(self.data)} data points)'
    
    
    def __repr__(self):
        return self.__str__()
    
    
    def save(self, name: str = None, path_dir: str = None, **kwargs) -> None:
        '''Saves chromatograms in CSV format
        
        Attributes:
            name (str): custom filename (default name is formed from compound ID,
                spectrum type and index)
            path_dir (str): directory where output file will be saved
            kwargs: parameters for pandas DataFrame to_csv method
        
        '''
        path = name if name else f'{self.compound.ID}_{self.ri_type}_{self.column_type}_{self.temp_regime}.csv'
        if path_dir:
            path = _os.path.join(path_dir, path)
        self.data.to_csv(path, **kwargs)



@_dcs.dataclass(eq = False, repr = False)
class NistCompound():
    '''Stores info on NIST Chemistry WebBook compound
    
    Attributes:
        _request_config (_ncpr.RequestConfig): additional requests.get parameters
        _nist_response (_ncpr.NistResponse): response to the GET request
        ID (_tp.Optional[str]): NIST compound ID
        name (_tp.Optional[str]): chemical name
        synonyms (_tp.List[str]): synonyms of the chemical name
        formula (_tp.Optional[str]): chemical formula
        mol_weight (_tp.Optional[float]): molecular weigth, g/cm^3
        inchi (_tp.Optional[str]): InChI string
        inchi_key (_tp.Optional[str]): InChI key string
        cas_rn (_tp.Optional[str]): CAS registry number
        mol_refs (_tp.Dict[str, str]): references to 2D and 3D MOL-files
        data_refs (_tp.Dict[str, str]): references to the webpages containing
            physical chemical data for the given compound
        nist_public_refs (_tp.Dict[str, str]): references to webpages of other
            public NIST databases containing data for the given compound
        nist_subscription_refs (_tp.Dict[str, str]): references to webpages of
            subscription NIST databases containing data for the given compound
        mol2D (_tp.Optional[str]): text block of a MOL-file containing 2D atomic coordinates
        mol3D (_tp.Optional[str]): text block of a MOL-file containing 3D atomic coordinates 
        ir_specs (_tp.List[Spectrum]): list pf IR Spectrum objects
        thz_specs (_tp.List[Spectrum]): list pf THz Spectrum objects
        ms_specs (_tp.List[Spectrum]): list pf MS Spectrum objects
        uv_specs (_tp.List[Spectrum]): list pf UV-Vis Spectrum objects
        gas_chromat (_tp.List[Chromatogram]): list of Chromatogram objects
    
    '''
    
    _request_config: _ncpr.RequestConfig
    _nist_response: _ncpr.NistResponse
    ID: _tp.Optional[str]
    name: _tp.Optional[str]
    synonyms: _tp.List[str]
    formula: _tp.Optional[str]
    mol_weight: _tp.Optional[float]
    inchi: _tp.Optional[str]
    inchi_key: _tp.Optional[str]
    cas_rn: _tp.Optional[str]
    mol_refs: _tp.Dict[str, str]
    data_refs: _tp.Dict[str, str]
    nist_public_refs: _tp.Dict[str, str]
    nist_subscription_refs: _tp.Dict[str, str]
    mol2D: _tp.Optional[str] = _dcs.field(init = False)
    mol3D: _tp.Optional[str] = _dcs.field(init = False)
    ir_specs: _tp.List[Spectrum] = _dcs.field(init = False)
    thz_specs: _tp.List[Spectrum] = _dcs.field(init = False)
    ms_specs: _tp.List[Spectrum] = _dcs.field(init = False)
    uv_specs: _tp.List[Spectrum] = _dcs.field(init = False)
    gas_chromat: _tp.List[Chromatogram] = _dcs.field(init = False)
    
    
    def __post_init__(self):
        self.mol2D = None
        self.mol3D = None
        self.ir_specs = []
        self.thz_specs = []
        self.ms_specs = []
        self.uv_specs = []
        self.gas_chromat = []
    
    
    def __str__(self):
        return f'NistCompound(ID={self.ID})'
    
    
    def __repr__(self):
        return self.__str__()
    
    
##### Loading MOL-files #######################################################
    
    def get_molfile(self, dim: int) -> None:
        '''Loads text block of 2D / 3D molfile
        
        Arguments:
            dim (int): dimensionality of molfile (2D / 3D)
        
        '''
        if dim not in (2, 3):
            raise ValueError(f'Bad dimensionality (must be 2 or 3): {dim}')
        key = f'mol{dim}D'
        if key not in self.mol_refs:
            return
        nr = _ncpr.make_nist_request(self.mol_refs[key], config = self._request_config)
        if nr.ok:
            setattr(self, key, nr.text)
    
    
    def get_mol2D(self) -> None:
        '''Loads text block of 2D molfile'''
        self.get_molfile(2)
    
    
    def get_mol3D(self) -> None:
        '''Loads text block of 2D molfile'''
        self.get_molfile(3)
    
    
    def get_molfiles(self) -> None:
        '''Loads text block of all available molfiles'''
        self.get_mol2D()
        self.get_mol3D()
    
    
##### Loading spectra #########################################################
    
    def get_spectrum(self, spec_type: str, spec_idx: str) -> Spectrum:
        '''Loads spectrum of given type (IR / TZ / MS / UV) and index
        
        Arguments:
            spec_type (str): spectrum type [ IR / TZ / MS / UV ]
            spec_idx (str): spectrum index
        
        Returns:
            Spectrum: wrapper for the text block of JDX-formatted spectrum
        
        '''
        # prepare params
        if spec_type not in SPEC_TYPES:
            raise ValueError(f'spec_type must be one of IR / TZ / MS / UV: {spec_type}')
        params = {'JCAMP': self.ID, 'Index': spec_idx,
                  'Type': SPEC_TYPES[spec_type]}
        # request
        nr = _ncpr.make_nist_request(_ncpr.SEARCH_URL, params, config = self._request_config)
        spec = Spectrum(self, spec_type, spec_idx, nr.text) if nr.ok else None
        
        return spec
    
    
    def get_spectra(self, spec_type: str) -> None:
        '''Loads all available spectra of given type (IR / TZ / MS / UV)
        
        Arguments:
            spec_type (str): spectrum type [ IR / TZ / MS / UV ]
        
        '''
        # prepare
        if spec_type not in SPEC_TYPES:
            raise ValueError(f'spec_type must be one of IR / TZ / MS / UV: {spec_type}')
        key = 'c' + spec_type
        if key not in self.data_refs:
            return None
        # request
        nr = _ncpr.make_nist_request(self.data_refs[key], config = self._request_config)
        if not nr.ok:
            return None
        # extract spectra indexes
        refs = nr.soup.findAll(attrs = {'href': _re.compile('Index=')})
        refs = [ref.attrs['href'] for ref in refs]
        idxs = [parse_qs(urlparse(ref).query)['Index'][0] for ref in refs]
        idxs = sorted(list(set(idxs)))
        # load spectra
        key = ('thz' if spec_type == 'TZ' else spec_type.lower()) + '_specs'
        spectra = []
        for idx in idxs:
            X = self.get_spectrum(spec_type, idx)
            if X: spectra.append(X)
        setattr(self, key, spectra)
    
    
    def get_ir_spectra(self) -> None:
        '''Loads all available IR spectra'''
        self.get_spectra('IR')
    
    
    def get_thz_spectra(self) -> None:
        '''Loads all available THz spectra'''
        self.get_spectra('TZ')
    
    
    def get_ms_spectra(self) -> None:
        '''Loads all available MS spectra'''
        self.get_spectra('MS')
    
    
    def get_uv_spectra(self) -> None:
        '''Loads all available UV-Vis spectra'''
        self.get_spectra('UV')
    
    
    def get_all_spectra(self) -> None:
        '''Loads all available spectra'''
        self.get_ir_spectra()
        self.get_thz_spectra()
        self.get_ms_spectra()
        self.get_uv_spectra()
    
    
    def save_spectra(self, spec_type: str, path_dir: str = './') -> None:
        '''Saves all spectra of given type to the specified folder
        
        Arguments:
            spec_type (str): spectrum type [ IR / TZ / MS / UV ]
            path_dir (str): directory to save spectra
        
        '''
        # check input
        if spec_type not in SPEC_TYPES:
            raise ValueError(f'spec_type must be one of IR / TZ / MS / UV: {spec_type}')
        if not _os.path.isdir(path_dir):
            raise ValueError(f'"{path_dir}" must be a directory')
        # save
        key = 'thz' if spec_type == 'TZ' else spec_type.lower()
        key = f'{key}_specs'
        for spec in getattr(self, key):
            spec.save(f'{self.ID}_{spec_type}_{spec.spec_idx}.jdx', path_dir)
    
    
    def save_ir_spectra(self, path_dir: str = './') -> None:
        '''Saves IR spectra to the specified folder
        
        Arguments:
            path_dir (str): directory to save spectra
        
        '''
        self.save_spectra('IR', path_dir)
    
    
    def save_thz_spectra(self, path_dir: str = './') -> None:
        '''Saves IR spectra to the specified folder
        
        Arguments:
            path_dir (str): directory to save spectra
        
        '''
        self.save_spectra('TZ', path_dir)
    
    
    def save_ms_spectra(self, path_dir: str = './') -> None:
        '''Saves mass spectra to the specified folder
        
        Arguments:
            path_dir (str): directory to save spectra
        
        '''
        self.save_spectra('MS', path_dir)
    
    
    def save_uv_spectra(self, path_dir: str = './') -> None:
        '''Saves all UV-Vis spectra to the specified folder
        
        Arguments:
            path_dir (str): directory to save spectra
        
        '''
        self.save_spectra('UV', path_dir)
    
    
    def save_all_spectra(self, path_dir: str = './') -> None:
        '''Saves all UV-Vis spectra to the specified folder
        
        Arguments:
            path_dir (str): directory to save spectra
        
        '''
        self.save_ir_spectra(path_dir)
        self.save_tz_spectra(path_dir)
        self.save_ms_spectra(path_dir)
        self.save_uv_spectra(path_dir)
    
    
##### Gas chromatography ######################################################
    
    def get_gas_chromatography(self) -> None:
        '''Loads info on gas chromatography'''
        ref = self.data_refs.get('cGC', None)
        if not ref:
            return
        # request
        nr = _ncpr.make_nist_request(ref, config = self._request_config)
        if not nr.ok:
            return None
        # get distinct tables
        refs = _parsing.get_chromatography_table_refs(nr.soup)
        for ref in refs:
            # request table
            nrx = _ncpr.make_nist_request(ref, config = self._request_config)
            if not nrx.ok:
                return None
            # get Chromatogram
            info = _parsing.parse_chromatography_table(nrx.soup)
            X = Chromatogram(self, **info)
            self.gas_chromat.append(X)
    
    
    def save_gas_chromatography(self, path_dir: str = './', **kwargs) -> None:
        '''Saves all tables with data on gas chromatohraphy experiments
        
        Arguments:
            path_dir (str): directory to save spectra
        
        '''
        for chromat in self.gas_chromat:
            chromat.save(path_dir = path_dir, **kwargs)



#%% Initialization

def compound_from_response(
        nr: _ncpr.NistResponse,
        request_config: _tp.Optional[_ncpr.RequestConfig()] = None
    ) -> _tp.Optional[NistCompound]:
    '''Initializes NistCompound object from the corresponding response
    
    Arguments:
        nr (_ncpr.NistResponse): response to the GET request for a compound
    
    Returns:
        _tp.Optional[NistCompound]: NistCompound object, and None if there are
        several compounds corresponding to the given ID
    
    '''
    # check if it's compound page
    if not _parsing.is_compound_page(nr.soup):
        return None
    # extract data
    request_config = request_config or _ncpr.RequestConfig()
    info = {
        '_request_config': request_config,
        '_nist_response': nr,
        **_parsing.parse_compound_page(nr.soup)
    }
    nc = NistCompound(**info)
    
    return nc


def get_compound(
        ID: str,
        request_config: _tp.Optional[_ncpr.RequestConfig()] = None
    ) -> _tp.Optional[NistCompound]:
    '''Loads the main info on the given NIST compound
    
    Arguments:
        ID (str): NIST compound ID, CAS RN or InChI
        request_config (_tp.Optional[_ncpr.RequestConfig()]): additional requests.get parameters
    
    Returns:
        _tp.Optional[NistCompound]: NistCompound object, and None if there are
        several compounds corresponding to the given ID
    
    '''
    request_config = request_config or _ncpr.RequestConfig()
    if ID[:6] == 'InChI=':
        url = f'{_ncpr.INCHI_URL}/{ID}'
        params = {}
    else:
        url = _ncpr.SEARCH_URL
        params = {'ID': ID}
    nr = _ncpr.make_nist_request(url, params, config = request_config)
    X = compound_from_response(nr, request_config)
    
    return X


