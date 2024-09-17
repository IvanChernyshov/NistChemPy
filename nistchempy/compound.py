'''The module contains compound-related functionality'''

#%% Imports

import re as _re
import os as _os

import requests as _requests

import bs4 as _bs4

import nistchempy.compound_data as _cmpd


#%% Parsing

def is_compound_page(soup):
    '''Checks if html is a single compound page and returns NIST Compound ID if so
    
    Arguments:
        soup: bs4-parsed web-page
    
    Returns:
        str: NIST Compound ID
    '''
    header = soup.findAll('h1', {'id': 'Top'})
    if not header:
        return None
    # get info
    header = header[0]
    info = header.findNext('ul')
    if not info:
        return None
    # extract NIST ID
    for comment in soup.findAll(text = lambda text: isinstance(text, _bs4.Comment)):
        comment = str(comment).replace('\r\n', '').replace('\n', '')
        if not '/cgi/cbook.cgi' in comment:
            continue
        return _re.search(r'/cgi/cbook.cgi\?Form=(.*?)&', comment).group(1)
    
    return None


#%% Main class

class Compound():
    '''
    Object for NIST Chemistry WebBook compound
    '''
    
    # NIST URLs
    _NIST_URL = 'https://webbook.nist.gov'
    _COMP_ID = '/cgi/cbook.cgi'
    
    # mappings for spectra
    _MASKS = {'1': 'cTG', '2': 'cTC', '4': 'cTP', '8': 'cTR', '10': 'cSO',
              '20': 'cIE', '40': 'cIC', '80': 'cIR', '100': 'cTZ', '200': 'cMS',
              '400': 'cUV', '800': 'cES', '1000': 'cDI', '2000': 'cGC'}
    _SPECS = {'IR': 'IR', 'TZ': 'THz', 'MS': 'Mass', 'UV': 'UVVis'}
    
    def _load_compound_info(self):
        '''
        Loads main compound info
        '''
        r = _requests.get(self._NIST_URL + self._COMP_ID, {'ID': self.ID, 'Units': 'SI'})
        if not r.ok:
            raise ConnectionError(f'Bad NIST response, status code: {r.status_code}')
        # check if it is compound page
        soup = _bs4.BeautifulSoup(_re.sub('clss=', 'class=', r.text),
                                  features = 'html.parser')
        header = soup.findAll('h1', {'id': 'Top'})
        if not header:
            raise ValueError(f'Bad compound ID: {self.ID}')
        header = header[0]
        # get info
        info = header.findNext('ul')
        if not info:
            raise ValueError(f'Bad compound ID: {self.ID}')
        # name
        self.name = header.text
        # synonyms
        hits = info.findChildren(text = _re.compile('Other names'))
        if hits:
            text = hits[0].findParent('li').text.replace('Other names:', '')
            synonyms = [_.strip(';').strip() for _ in text.split('\n')]
            self.synonyms = [_ for _ in synonyms if _]
        # formula
        hits = info.findChildren(text = _re.compile('Formula'))
        if hits:
            text = hits[0].findParent('li').text.replace('Formula:', '')
            self.formula = _re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text.strip())
        # mol weight
        hits = info.findChildren(text = _re.compile('Molecular weight'))
        if hits:
            text = hits[0].findParent('li').text.replace('Molecular weight:', '')
            self.mol_weight = float(text)
        # InChI and InChI key
        hits = info.findChildren(attrs = {'class': 'inchi-text'})
        if hits:
            for hit in hits:
                if 'InChI=' in hit.text:
                    self.inchi = hit.text
                elif _re.search(r'', hit.text):
                    self.inchi_key = hit.text
        # CAS RN
        hits = info.findChildren(text = _re.compile('CAS Registry Number:'))
        if hits:
            text = hits[0].findParent('li').text.replace('CAS Registry Number:', '')
            self.cas_rn = text.strip()
        # 2D structure
        hits = info.findChildren(attrs = {'href': _re.compile('Str2File')})
        if hits:
            self.data_refs['mol2D'] = self._NIST_URL + hits[0].attrs['href']
        # 3D structure
        hits = info.findChildren(attrs = {'href': _re.compile('Str3File')})
        if hits:
            self.data_refs['mol3D'] = self._NIST_URL + hits[0].attrs['href']
        # other data and spectroscopy
        hits = info.findChildren(attrs = {'href': _re.compile('/cgi/cbook.cgi.*Mask=\d')})
        for hit in hits:
            mask = _re.search('Mask=(\d+)', hit.attrs['href']).group(1)
            key = self._MASKS.get(mask, hit.text)
            if key in self.data_refs:
                self.data_refs[key] += [self._NIST_URL + hit.attrs['href']]
            else:
                self.data_refs[key] = [self._NIST_URL + hit.attrs['href']]
    
    def get_2D(self):
        '''
        Loads 2D structure in MOL2 format
        '''
        if 'mol2D' not in self.data_refs:
            return
        r = _requests.get(self.data_refs['mol2D'])
        if r.ok:
            self.mol2D = r.text
    
    def get_3D(self):
        '''
        Loads 3D structure in MOL2 format
        '''
        if 'mol3D' not in self.data_refs:
            return
        r = _requests.get(self.data_refs['mol3D'])
        if r.ok:
            self.mol3D = r.text
    
    def get_spectra(self, spec_type):
        '''
        Loads available mass spectra in JCAMP-DX format
        '''
        if spec_type not in self._SPECS:
            raise ValueError(f'Bad spec_type value: {spec_type}')
        if 'c'+spec_type not in self.data_refs:
            return
        r = _requests.get(self.data_refs['c'+spec_type][0])
        if not r.ok:
            return
        soup = _bs4.BeautifulSoup(_re.sub('clss=', 'class=', r.text),
                                  features = 'html.parser')
        # get available spectrum indexes
        idxs = soup.findAll(attrs = {'href': _re.compile('Index=')})
        idxs = [_re.search(r'Index=(\d+)', _.attrs['href']).group(1) for _ in idxs]
        idxs = sorted(list(set(idxs)))
        # load jdxs
        for idx in idxs:
            spec = _requests.get(self._NIST_URL + self._COMP_ID,
                                 {'JCAMP': self.ID, 'Index': idx,
                                  'Type': self._SPECS[spec_type]})
            if spec.ok:
                spec = _cmpd.Spectrum(self, spec_type, idx, spec.text)
                getattr(self, spec_type).append(spec)
    
    def get_ir_spectra(self):
        '''
        Loads available IR spectra in JCAMP-DX format
        '''
        
        return self.get_spectra('IR')
    
    def get_tz_spectra(self):
        '''
        Loads available IR spectra in JCAMP-DX format
        '''
        
        return self.get_spectra('TZ')
    
    def get_ms_spectra(self):
        '''
        Loads available mass spectra in JCAMP-DX format
        '''
        
        return self.get_spectra('MS')
    
    def get_uv_spectra(self):
        '''
        Loads available UV-Vis spectra in JCAMP-DX format
        '''
        
        return self.get_spectra('UV')
    
    def get_all_spectra(self):
        '''
        Loads available spectroscopic data
        '''
        self.get_ir_spectra()
        self.get_tz_spectra()
        self.get_ms_spectra()
        self.get_uv_spectra()
    
    def get_all_data(self):
        '''
        Loads available structural and spectroscopic data
        '''
        self.get_2D()
        self.get_3D()
        self.get_all_spectra()
    
    def save_spectra(self, spec_type, path_dir = './'):
        '''
        Saves all spectra of given type to the specified folder
        '''
        if not _os.path.isdir(path_dir):
            raise ValueError(f'"{path_dir}" must be directory')
        for spec in getattr(self, spec_type):
            spec.save(f'{self.ID}_{spec_type}_{spec.spec_idx}.jdx', path_dir)
    
    def save_ir_spectra(self, path_dir = './'):
        '''
        Saves IR spectra to the specified folder
        '''
        self.save_spectra('IR', path_dir)
    
    def save_tz_spectra(self, path_dir = './'):
        '''
        Saves IR spectra to the specified folder
        '''
        self.save_spectra('TZ', path_dir)
    
    def save_ms_spectra(self, path_dir = './'):
        '''
        Saves mass spectra to the specified folder
        '''
        self.save_spectra('MS', path_dir)
    
    def save_uv_spectra(self, path_dir = './'):
        '''
        Saves all UV-Vis spectra to the specified folder
        '''
        self.save_spectra('UV', path_dir)
    
    def save_all_spectra(self, path_dir = './'):
        '''
        Saves all UV-Vis spectra to the specified folder
        '''
        self.save_ir_spectra(path_dir)
        self.save_tz_spectra(path_dir)
        self.save_ms_spectra(path_dir)
        self.save_uv_spectra(path_dir)
    
    def __init__(self, ID):
        self.ID = ID
        for prop, val in [('name', None), ('synonyms', []), ('formula', None), ('mol_weight', None),
                          ('inchi', None), ('inchi_key', None), ('cas_rn', None),
                          ('IR', []), ('TZ', []), ('MS', []), ('UV', []),
                          ('mol2D', None), ('mol3D', None),
                          ('data_refs', {})]:
            setattr(self, prop, val)
        self._load_compound_info()
    
    def __str__(self):
        return f'Compound({self.ID})'
    
    def __repr__(self):
        return f'Compound({self.ID})'


