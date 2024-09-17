'''The module contains compound-related functionality'''

#%% Imports

import os as _os


#%% Spectrum

class Spectrum():
    '''Class for IR, MS, and UV-Vis extracted from NIST Chemistry WebBook'''
    
    _pretty_names = {'IR': 'IR spectrum',
                     'TZ': 'THz IR spectrum',
                     'MS': 'Mass spectrum',
                     'UV': 'UV-Vis spectrum'}
    
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
            path = _os.path.join(path_dir, path)
        with open(path, 'w') as outf:
            outf.write(self.jdx_text)
    
    def __str__(self):
        return f'Spectrum({self.compound.ID}, {self._pretty_names[self.spec_type]} #{self.spec_idx})'
    
    def __repr__(self):
        return f'Spectrum({self.compound.ID}, {self._pretty_names[self.spec_type]} #{self.spec_idx})'


