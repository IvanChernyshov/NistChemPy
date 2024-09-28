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
    
    
    def save(self, name = None, path_dir = None):
        '''
        Saves spectrum in JDX format
        '''
        path = name if name else f'{self.compound.ID}_{self.spec_type}_{self.spec_idx}.jdx'
        if path_dir:
            path = _os.path.join(path_dir, path)
        with open(path, 'w') as outf:
            outf.write(self.jdx_text)



@_dcs.dataclass(eq = False, repr = False)
class NistCompound():
    '''Stores info on NIST Chemistry WebBook compound
    
    Attributes:
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
        nist_response (NistResponse): response to the GET request
        mol2D (_tp.Optional[str]): text block of a MOL-file containing 2D atomic coordinates
        mol3D (_tp.Optional[str]): text block of a MOL-file containing 3D atomic coordinates 
        ir_specs (_tp.List[Spectrum]): list pf IR Spectrum objects
        thz_specs (_tp.List[Spectrum]): list pf THz Spectrum objects
        ms_specs (_tp.List[Spectrum]): list pf MS Spectrum objects
        uv_specs (_tp.List[Spectrum]): list pf UV-Vis Spectrum objects
    
    '''
    
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
    nist_response: _ncpr.NistResponse
    mol2D: _tp.Optional[str] = _dcs.field(init = False)
    mol3D: _tp.Optional[str] = _dcs.field(init = False)
    ir_specs: _tp.List[Spectrum] = _dcs.field(init = False)
    thz_specs: _tp.List[Spectrum] = _dcs.field(init = False)
    ms_specs: _tp.List[Spectrum] = _dcs.field(init = False)
    uv_specs: _tp.List[Spectrum] = _dcs.field(init = False)
    
    
    def __post_init__(self):
        self.mol2D = None
        self.mol3D = None
        self.ir_specs = []
        self.thz_specs = []
        self.ms_specs = []
        self.uv_specs = []
    
    
    def __str__(self):
        return f'NistCompound(ID={self.ID})'
    
    
    def __repr__(self):
        return self.__str__()
    
    
##### Loading MOL-files #######################################################
    
    def get_molfile(self, dim: int, **kwargs) -> None:
        '''Loads text block of 2D / 3D molfile
        
        Arguments:
            dim (int): dimensionality of molfile (2D / 3D)
            kwargs: requests.get kwargs parameters
        
        '''
        if dim not in (2, 3):
            raise ValueError(f'Bad dimensionality (must be 2 or 3): {dim}')
        key = f'mol{dim}D'
        if key not in self.mol_refs:
            return
        nr = _ncpr.make_nist_request(self.mol_refs[key], **kwargs)
        if nr.ok:
            setattr(self, key, nr.text)
    
    
    def get_mol2D(self, **kwargs) -> None:
        '''Loads text block of 2D molfile
        
        Arguments:
            kwargs: requests.get kwargs parameters
        
        '''
        self.get_molfile(2, **kwargs)
    
    
    def get_mol3D(self, **kwargs) -> None:
        '''Loads text block of 2D molfile
        
        Arguments:
            kwargs: requests.get kwargs parameters
        
        '''
        self.get_molfile(3, **kwargs)
    
    
    def get_molfiles(self, **kwargs) -> None:
        '''Loads text block of all available molfiles
        
        Arguments:
            kwargs: requests.get kwargs parameters
        
        '''
        self.get_mol2D(**kwargs)
        self.get_mol3D(**kwargs)
    
    
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
        nr = _ncpr.make_nist_request(_ncpr.SEARCH_URL, params)
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
        nr = _ncpr.make_nist_request(self.data_refs[key])
        if not nr.ok:
            return None
        # extract spectra indexes
        refs = nr.soup.findAll(attrs = {'href': _re.compile('Index=')})
        refs = [ref.attrs['href'] for ref in refs]
        idxs = [parse_qs(urlparse(ref).query)['Index'][0] for ref in refs]
        idxs = sorted(list(set(idxs)))
        # load spectra
        key = ('thz' if spec_type == 'TZ' else spec_type.lower()) + '_specs'
        setattr(self, key, [])
        for idx in idxs:
            X = self.get_spectrum(spec_type, idx)
            if X: getattr(self, key).append(X)
    
    
    def get_ir_spectra(self):
        '''Loads all available IR spectra'''
        self.get_spectra('IR')
    
    
    def get_thz_spectra(self):
        '''Loads all available THz spectra'''
        self.get_spectra('TZ')
    
    
    def get_ms_spectra(self):
        '''Loads all available MS spectra'''
        self.get_spectra('MS')
    
    
    def get_uv_spectra(self):
        '''Loads all available UV-Vis spectra'''
        self.get_spectra('UV')
    
    
    def get_all_spectra(self):
        '''Loads all available spectra'''
        self.get_ir_spectra()
        self.get_thz_spectra()
        self.get_ms_spectra()
        self.get_uv_spectra()
    
    
    def save_spectra(self, spec_type, path_dir = './') -> None:
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
    
    
    def save_ir_spectra(self, path_dir = './') -> None:
        '''Saves IR spectra to the specified folder'''
        self.save_spectra('IR', path_dir)
    
    
    def save_thz_spectra(self, path_dir = './') -> None:
        '''Saves IR spectra to the specified folder'''
        self.save_spectra('TZ', path_dir)
    
    
    def save_ms_spectra(self, path_dir = './') -> None:
        '''Saves mass spectra to the specified folder'''
        self.save_spectra('MS', path_dir)
    
    
    def save_uv_spectra(self, path_dir = './') -> None:
        '''Saves all UV-Vis spectra to the specified folder'''
        self.save_spectra('UV', path_dir)
    
    
    def save_all_spectra(self, path_dir = './') -> None:
        '''Saves all UV-Vis spectra to the specified folder'''
        self.save_ir_spectra(path_dir)
        self.save_tz_spectra(path_dir)
        self.save_ms_spectra(path_dir)
        self.save_uv_spectra(path_dir)



#%% Initialization

def compound_from_response(nr: _ncpr.NistResponse) -> _tp.Optional[NistCompound]:
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
    info = {**_parsing.parse_compound_page(nr.soup),
            'nist_response': nr}
    nc = NistCompound(**info)
    
    return nc


def get_compound(ID: str, **kwargs) -> _tp.Optional[NistCompound]:
    '''Loads the main info on the given NIST compound
    
    Arguments:
        ID (str): NIST compound ID, CAS RN or InChI
        kwargs: requests.get kwargs parameters
    
    Returns:
        _tp.Optional[NistCompound]: NistCompound object, and None if there are
        several compounds corresponding to the given ID
    
    '''
    if ID[:6] == 'InChI=':
        url = f'{_ncpr.INCHI_URL}/{ID}'
        params = {}
    else:
        url = _ncpr.SEARCH_URL
        params = {'ID': ID}
    nr = _ncpr.make_nist_request(url, params, **kwargs)
    X = compound_from_response(nr)
    
    return X


