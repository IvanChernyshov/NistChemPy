'''The module contains compound-related functionality'''

#%% Imports

from __future__ import annotations

import os as _os

import nistchempy.requests as _ncpr
import nistchempy.parsing as _parsing

import dataclasses as _dcs
import typing as _tp


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
    
    
    def save(self, name = None, path_dir = None):
        '''
        Saves spectrum in JDX format
        '''
        path = name if name else f'{self.compound.ID}_{self.spec_type}_{self.spec_idx}.jdx'
        if path_dir:
            path = _os.path.join(path_dir, path)
        with open(path, 'w') as outf:
            outf.write(self.jdx_text)
    
    
    def __str__(self):
        pretty_names = {'IR': 'IR spectrum', 'TZ': 'THz IR spectrum',
                         'MS': 'Mass spectrum', 'UV': 'UV-Vis spectrum'}
        
        return f'Spectrum({self.compound.ID}, {pretty_names[self.spec_type]} #{self.spec_idx})'
    
    
    def __repr__(self):
        return self.__str__()



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
    
    
    
    
    
    pass



#%% Initialization

def compound_from_response(nr: _ncpr.NistResponse) -> _tp.Optional[NistCompound]:
    '''Initializes NistCompound object from the corresponding response
    
    Arguments:
        nr (_ncpr.NistResponse): response to the GET request for a compound
    
    Returns:
        _tp.Optional[NistCompound]: NistCompound object, and None if there are
        several compounds corresponding to the given ID
    
    '''
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


# class Compound():
#     '''
#     Object for NIST Chemistry WebBook compound
#     '''
    
#     # NIST URLs
#     _NIST_URL = 'https://webbook.nist.gov'
#     _COMP_ID = '/cgi/cbook.cgi'
    
#     # mappings for spectra
#     _MASKS = {'1': 'cTG', '2': 'cTC', '4': 'cTP', '8': 'cTR', '10': 'cSO',
#               '20': 'cIE', '40': 'cIC', '80': 'cIR', '100': 'cTZ', '200': 'cMS',
#               '400': 'cUV', '800': 'cES', '1000': 'cDI', '2000': 'cGC'}
#     _SPECS = {'IR': 'IR', 'TZ': 'THz', 'MS': 'Mass', 'UV': 'UVVis'}
    
#     def _load_compound_info(self):
#         '''
#         Loads main compound info
#         '''
#         r = _requests.get(self._NIST_URL + self._COMP_ID, {'ID': self.ID, 'Units': 'SI'})
#         if not r.ok:
#             raise ConnectionError(f'Bad NIST response, status code: {r.status_code}')
#         # check if it is compound page
#         soup = _bs4.BeautifulSoup(_re.sub('clss=', 'class=', r.text),
#                                   features = 'html.parser')
#         header = soup.findAll('h1', {'id': 'Top'})
#         if not header:
#             raise ValueError(f'Bad compound ID: {self.ID}')
#         header = header[0]
#         # get info
#         info = header.findNext('ul')
#         if not info:
#             raise ValueError(f'Bad compound ID: {self.ID}')
#         # name
#         self.name = header.text
#         # synonyms
#         hits = info.findChildren(text = _re.compile('Other names'))
#         if hits:
#             text = hits[0].findParent('li').text.replace('Other names:', '')
#             synonyms = [_.strip(';').strip() for _ in text.split('\n')]
#             self.synonyms = [_ for _ in synonyms if _]
#         # formula
#         hits = info.findChildren(text = _re.compile('Formula'))
#         if hits:
#             text = hits[0].findParent('li').text.replace('Formula:', '')
#             self.formula = _re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text.strip())
#         # mol weight
#         hits = info.findChildren(text = _re.compile('Molecular weight'))
#         if hits:
#             text = hits[0].findParent('li').text.replace('Molecular weight:', '')
#             self.mol_weight = float(text)
#         # InChI and InChI key
#         hits = info.findChildren(attrs = {'class': 'inchi-text'})
#         if hits:
#             for hit in hits:
#                 if 'InChI=' in hit.text:
#                     self.inchi = hit.text
#                 elif _re.search(r'', hit.text):
#                     self.inchi_key = hit.text
#         # CAS RN
#         hits = info.findChildren(text = _re.compile('CAS Registry Number:'))
#         if hits:
#             text = hits[0].findParent('li').text.replace('CAS Registry Number:', '')
#             self.cas_rn = text.strip()
#         # 2D structure
#         hits = info.findChildren(attrs = {'href': _re.compile('Str2File')})
#         if hits:
#             self.data_refs['mol2D'] = self._NIST_URL + hits[0].attrs['href']
#         # 3D structure
#         hits = info.findChildren(attrs = {'href': _re.compile('Str3File')})
#         if hits:
#             self.data_refs['mol3D'] = self._NIST_URL + hits[0].attrs['href']
#         # other data and spectroscopy
#         hits = info.findChildren(attrs = {'href': _re.compile('/cgi/cbook.cgi.*Mask=\d')})
#         for hit in hits:
#             mask = _re.search('Mask=(\d+)', hit.attrs['href']).group(1)
#             key = self._MASKS.get(mask, hit.text)
#             if key in self.data_refs:
#                 self.data_refs[key] += [self._NIST_URL + hit.attrs['href']]
#             else:
#                 self.data_refs[key] = [self._NIST_URL + hit.attrs['href']]
    
#     def get_2D(self):
#         '''
#         Loads 2D structure in MOL2 format
#         '''
#         if 'mol2D' not in self.data_refs:
#             return
#         r = _requests.get(self.data_refs['mol2D'])
#         if r.ok:
#             self.mol2D = r.text
    
#     def get_3D(self):
#         '''
#         Loads 3D structure in MOL2 format
#         '''
#         if 'mol3D' not in self.data_refs:
#             return
#         r = _requests.get(self.data_refs['mol3D'])
#         if r.ok:
#             self.mol3D = r.text
    
#     def get_spectra(self, spec_type):
#         '''
#         Loads available mass spectra in JCAMP-DX format
#         '''
#         if spec_type not in self._SPECS:
#             raise ValueError(f'Bad spec_type value: {spec_type}')
#         if 'c'+spec_type not in self.data_refs:
#             return
#         r = _requests.get(self.data_refs['c'+spec_type][0])
#         if not r.ok:
#             return
#         soup = _bs4.BeautifulSoup(_re.sub('clss=', 'class=', r.text),
#                                   features = 'html.parser')
#         # get available spectrum indexes
#         idxs = soup.findAll(attrs = {'href': _re.compile('Index=')})
#         idxs = [_re.search(r'Index=(\d+)', _.attrs['href']).group(1) for _ in idxs]
#         idxs = sorted(list(set(idxs)))
#         # load jdxs
#         for idx in idxs:
#             spec = _requests.get(self._NIST_URL + self._COMP_ID,
#                                  {'JCAMP': self.ID, 'Index': idx,
#                                   'Type': self._SPECS[spec_type]})
#             if spec.ok:
#                 spec = Spectrum(self, spec_type, idx, spec.text)
#                 getattr(self, spec_type).append(spec)
    
#     def get_ir_spectra(self):
#         '''
#         Loads available IR spectra in JCAMP-DX format
#         '''
        
#         return self.get_spectra('IR')
    
#     def get_tz_spectra(self):
#         '''
#         Loads available IR spectra in JCAMP-DX format
#         '''
        
#         return self.get_spectra('TZ')
    
#     def get_ms_spectra(self):
#         '''
#         Loads available mass spectra in JCAMP-DX format
#         '''
        
#         return self.get_spectra('MS')
    
#     def get_uv_spectra(self):
#         '''
#         Loads available UV-Vis spectra in JCAMP-DX format
#         '''
        
#         return self.get_spectra('UV')
    
#     def get_all_spectra(self):
#         '''
#         Loads available spectroscopic data
#         '''
#         self.get_ir_spectra()
#         self.get_tz_spectra()
#         self.get_ms_spectra()
#         self.get_uv_spectra()
    
#     def get_all_data(self):
#         '''
#         Loads available structural and spectroscopic data
#         '''
#         self.get_2D()
#         self.get_3D()
#         self.get_all_spectra()
    
#     def save_spectra(self, spec_type, path_dir = './'):
#         '''
#         Saves all spectra of given type to the specified folder
#         '''
#         if not _os.path.isdir(path_dir):
#             raise ValueError(f'"{path_dir}" must be directory')
#         for spec in getattr(self, spec_type):
#             spec.save(f'{self.ID}_{spec_type}_{spec.spec_idx}.jdx', path_dir)
    
#     def save_ir_spectra(self, path_dir = './'):
#         '''
#         Saves IR spectra to the specified folder
#         '''
#         self.save_spectra('IR', path_dir)
    
#     def save_tz_spectra(self, path_dir = './'):
#         '''
#         Saves IR spectra to the specified folder
#         '''
#         self.save_spectra('TZ', path_dir)
    
#     def save_ms_spectra(self, path_dir = './'):
#         '''
#         Saves mass spectra to the specified folder
#         '''
#         self.save_spectra('MS', path_dir)
    
#     def save_uv_spectra(self, path_dir = './'):
#         '''
#         Saves all UV-Vis spectra to the specified folder
#         '''
#         self.save_spectra('UV', path_dir)
    
#     def save_all_spectra(self, path_dir = './'):
#         '''
#         Saves all UV-Vis spectra to the specified folder
#         '''
#         self.save_ir_spectra(path_dir)
#         self.save_tz_spectra(path_dir)
#         self.save_ms_spectra(path_dir)
#         self.save_uv_spectra(path_dir)
    
#     def __init__(self, ID):
#         self.ID = ID
#         for prop, val in [('name', None), ('synonyms', []), ('formula', None), ('mol_weight', None),
#                           ('inchi', None), ('inchi_key', None), ('cas_rn', None),
#                           ('IR', []), ('TZ', []), ('MS', []), ('UV', []),
#                           ('mol2D', None), ('mol3D', None),
#                           ('data_refs', {})]:
#             setattr(self, prop, val)
#         self._load_compound_info()
    
#     def __str__(self):
#         return f'Compound({self.ID})'
    
#     def __repr__(self):
#         return f'Compound({self.ID})'


