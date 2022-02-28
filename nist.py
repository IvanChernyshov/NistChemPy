'''
Python API for NIST Chemistry WebBook
'''

#%% Imports

import re, os, requests
from bs4 import BeautifulSoup


#%% Objects

class Spectrum():
    '''
    Class for IR, MS, and UV-Vis extracted from NIST Chemistry WebBook
    '''
    
    _pretty_names = {'ir': 'IR spectrum',
                     'ms': 'Mass spectrum',
                     'uvvis': 'UV-Vis spectrum'}
    
    def __init__(self, compound, spec_type, spec_idx, jdx):
        self.compound = compound
        self.spec_type = spec_type
        self.spec_idx = spec_idx
        self.jdx_text = jdx
    
    def save(self, name = None, path_dir = None):
        '''
        Saves spectrum in JDX format
        '''
        path = name if name else f'{self.compound.ID}_{self.spec_type}_{self.spec_idx}.jdx'
        if path_dir:
            path = os.path.join(path_dir, path)
        with open(path, 'w') as outf:
            outf.write(self.jdx_text)
    
    def __str__(self):
        return f'Compound({self.compound.ID}, {self._pretty_names[self.spec_type]} #{self.spec_idx})'
    
    def __repr__(self):
        return f'Compound({self.compound.ID}, {self._pretty_names[self.spec_type]} #{self.spec_idx})'


class Compound():
    '''
    Object for NIST Chemistry WebBook compound
    '''
    
    # NIST URLs
    _NIST_URL = 'https://webbook.nist.gov'
    _COMP_ID = '/cgi/cbook.cgi'
    
    # mappings for spectra
    _MASKS = {'80': 'ir', '200': 'ms', '400': 'uvvis'}
    _SPECS = {'ir': 'IR', 'ms': 'Mass', 'uvvis': 'UVVis'}
    
    def _load_compound_info(self):
        '''
        Loads main compound info
        '''
        r = requests.get(self._NIST_URL + self._COMP_ID, {'ID': self.ID, 'Units': 'SI'})
        if not r.ok:
            raise ConnectionError(f'Bad NIST response, status code: {r.status_code}')
        # check if it is compound page
        soup = BeautifulSoup(re.sub('clss=', 'class=', r.text),
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
        hits = info.findChildren(text = re.compile('Other names'))
        if hits:
            text = hits[0].findParent('li').text.replace('Other names:', '')
            self.synonyms = [_.strip(';') for _ in text.split()]
        # formula
        hits = info.findChildren(text = re.compile('Formula'))
        if hits:
            text = hits[0].findParent('li').text.replace('Formula:', '')
            self.formula = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text.strip())
        # mol weight
        hits = info.findChildren(text = re.compile('Molecular weight'))
        if hits:
            text = hits[0].findParent('li').text.replace('Molecular weight:', '')
            self.mol_weight = float(text)
        # InChI and InChI key
        hits = info.findChildren(attrs = {'class': 'inchi-text'})
        if hits:
            for hit in hits:
                if 'InChI=' in hit.text:
                    self.inchi = hit.text
                elif re.search(r'', hit.text):
                    self.inchi_key = hit.text
        # CAS RN
        hits = info.findChildren(text = re.compile('CAS Registry Number:'))
        if hits:
            text = hits[0].findParent('li').text.replace('CAS Registry Number:', '')
            self.cas_rn = text.strip()
        # 2D structure
        hits = info.findChildren(attrs = {'href': re.compile('Str2File')})
        if hits:
            self.data_refs['mol2d'] = self._NIST_URL + hits[0].attrs['href']
        # 3D structure
        hits = info.findChildren(attrs = {'href': re.compile('Str3File')})
        if hits:
            self.data_refs['mol3d'] = self._NIST_URL + hits[0].attrs['href']
        # other data and spectroscopy
        hits = info.findChildren(attrs = {'href': re.compile('/cgi/cbook.cgi.*Mask=\d')})
        for hit in hits:
            mask = re.search('Mask=(\d+)', hit.attrs['href']).group(1)
            key = self._MASKS.get(mask, hit.text)
            self.data_refs[key] = self._NIST_URL + hit.attrs['href']
    
    def get_2d(self):
        '''
        Loads 2D structure in MOL2 format
        '''
        r = requests.get(self.data_refs['mol2d'])
        if r.ok:
            self.mol2d = r.text
    
    def get_3d(self):
        '''
        Loads 3D structure in MOL2 format
        '''
        r = requests.get(self.data_refs['mol3d'])
        if r.ok:
            self.mol3d = r.text
    
    def get_spectra(self, spec_type):
        '''
        Loads available mass spectra in JDX format
        '''
        if spec_type not in self._SPECS:
            raise ValueError(f'Bad spec_type value: {spec_type}')
        if spec_type not in self.data_refs:
            return
        r = requests.get(self.data_refs[spec_type])
        if not r.ok:
            return
        soup = BeautifulSoup(re.sub('clss=', 'class=', r.text),
                             features = 'html.parser')
        # get available spectrum indexes
        idxs = soup.findAll(attrs = {'href': re.compile('Index=')})
        idxs = [re.search(r'Index=(\d+)', _.attrs['href']).group(1) for _ in idxs]
        idxs = sorted(list(set(idxs)))
        # load jdxs
        for idx in idxs:
            spec = requests.get(self._NIST_URL + self._COMP_ID,
                                {'JCAMP': self.ID, 'Index': idx,
                                 'Type': self._SPECS[spec_type]})
            if spec.ok:
                spec = Spectrum(self, spec_type, idx, spec.text)
                getattr(self, spec_type).append(spec)
    
    def get_ir_spectra(self):
        '''
        Loads available IR spectra in JDX format
        '''
        
        return self.get_spectra('ir')
    
    def get_mass_spectra(self):
        '''
        Loads available mass spectra in JDX format
        '''
        
        return self.get_spectra('ms')
    
    def get_uvvis_spectra(self):
        '''
        Loads available UV-Vis spectra in JDX format
        '''
        
        return self.get_spectra('uvvis')
    
    def get_all_spectra(self):
        '''
        Loads available spectroscopic data
        '''
        self.get_mass_spectra()
        self.get_ir_spectra()
        self.get_uvvis_spectra()
    
    def get_all_data(self):
        '''
        Loads available structural and spectroscopic data
        '''
        self.get_2d()
        self.get_3d()
        self.get_all_spectra()
    
    def save_spectra(self, spec_type, path_dir = './'):
        '''
        Saves all spectra of given type to the specified folder
        '''
        if not os.path.isdir(path_dir):
            raise ValueError(f'"{path_dir}" must be directory')
        for spec in getattr(self, spec_type):
            spec.save(f'{self.ID}_{spec_type}_{spec.spec_idx}.jdx', path_dir)
    
    def save_ir_spectra(self, path_dir = './'):
        '''
        Saves IR spectra to the specified folder
        '''
        self.save_spectra('ir', path_dir)
    
    def save_ms_spectra(self, path_dir = './'):
        '''
        Saves mass spectra to the specified folder
        '''
        self.save_spectra('ms', path_dir)
    
    def save_uvvis_spectra(self, path_dir = './'):
        '''
        Saves all UV-Vis spectra to the specified folder
        '''
        self.save_spectra('uvvis', path_dir)
    
    def save_all_spectra(self, path_dir = './'):
        '''
        Saves all UV-Vis spectra to the specified folder
        '''
        self.save_ir_spectra(path_dir)
        self.save_ms_spectra(path_dir)
        self.save_uvvis_spectra(path_dir)
    
    def __init__(self, ID):
        self.ID = ID
        for prop, val in [('name', None), ('synonyms', []), ('formula', None), ('mol_weight', None),
                          ('inchi', None), ('inchi_key', None), ('cas_rn', None),
                          ('ir', []), ('ms', []), ('uvvis', []),
                          ('mol2d', None), ('mol3d', None),
                          ('data_refs', {})]:
            setattr(self, prop, val)
        self._load_compound_info()
    
    def __str__(self):
        return f'Compound({self.ID})'
    
    def __repr__(self):
        return f'Compound({self.ID})'



#%% Main functions





