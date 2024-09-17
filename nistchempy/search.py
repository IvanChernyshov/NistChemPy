'''The module contains search-related functionality'''

#%% Imports

import re as _re

import requests as _requests
import urllib.parse as _uparse

import bs4 as _bs4

import nistchempy.compound as _compound


#%% Misc

def print_search_parameters() -> None:
    '''Prints available search parameters'''
    info = {'Units': 'Units for thermodynamic data, "SI" or "CAL" for calorie-based',
            'MatchIso': 'Exactly match the specified isotopes (formula search only)',
            'AllowOther': 'Allow elements not specified in formula (formula search only)',
            'AllowExtra': 'Allow more atoms of elements in formula than specified (formula search only)',
            'NoIon': 'Exclude ions from the search (formula search only)',
            'cTG': 'Contains gas-phase thermodynamic data',
            'cTC': 'Contains condensed-phase thermodynamic data',
            'cTP': 'Contains phase-change thermodynamic data',
            'cTR': 'Contains reaction thermodynamic data',
            'cIE': 'Contains ion energetics thermodynamic data',
            'cIC': 'Contains ion cluster thermodynamic data',
            'cIR': 'Contains IR data',
            'cTZ': 'Contains THz IR data',
            'cMS': 'Contains MS data',
            'cUV': 'Contains UV/Vis data',
            'cGC': 'Contains gas chromatography data',
            'cES': 'Contains vibrational and electronic energy levels',
            'cDI': 'Contains constants of diatomic molecules',
            'cSO': 'Contains info on Henry\'s law'}
    max_len = max([len(_) for _ in info])
    spaces = [' '*(max_len - len(_) + 1) for _ in info]
    for (key, val), space in zip(info.items(), spaces):
        print(f'{key}{space}:   {val}')


#%% Search

class SearchParameters():
    '''
    Object containing parameters for compound search in NIST WebBook
    To get the full description of available options please use
    "print_search_parameters" function
    '''
    info = {'Units': 'SI',
            'MatchIso': False, 'AllowOther': False, 'AllowExtra': False, 'NoIon': False,
            'cTG': False, 'cTC': False, 'cTP': False, 'cTR': False, 'cIE': False, 'cIC': False,
            'cIR': False, 'cTZ': False, 'cMS': False, 'cUV': False, 'cGC': False,
            'cES': False, 'cDI': False, 'cSO': False}
    
    def get_request_parameters(self):
        '''
        Returns dictionary with GET parameters
        '''
        params = {'Units': self.Units}
        for key in self.info:
            if key == 'Units':
                continue
            val = getattr(self, key)
            if val:
                params[key] = 'on'
        
        return params
    
    def __init__(self, **kwargs):
        # set default
        for key, val in self.info.items():
            setattr(self, key, val)
        # check kwargs
        for key, val in kwargs.items():
            if key not in self.info:
                raise TypeError(f'"{key}" is an invalid keyword argument for SearchParameters')
            if key == 'Units' and val not in ('SI', 'CAL'):
                raise ValueError(f'Bad value for "Units" parameter: {val}')
            if key != 'Units' and type(val) is not bool:
                raise ValueError(f'Bad value for "{key}" parameter: {val}')
            setattr(self, key, val)
    
    def __str__(self):
        sep = ', ' # ',\n' + ' '*17
        text = [f'SearchParameters(Units={self.Units}'] + \
               [f'{key}={getattr(self, key)}' for key in self.info if key != 'Units' and getattr(self, key)]
        text[-1] = text[-1] + ')'
        
        return sep.join(text)
    
    def __repr__(self):
        sep = ', ' # ',\n' + ' '*17
        text = [f'SearchParameters(Units={self.Units}'] + \
               [f'{key}={getattr(self, key)}' for key in self.info if key != 'Units' and getattr(self, key)]
        text[-1] = text[-1] + ')'
        
        return sep.join(text)


class Search():
    '''
    Object for searching in NIST Chemistry WebBook
    '''
    
    # NIST URLs
    _NIST_URL = 'https://webbook.nist.gov'
    _COMP_ID = '/cgi/cbook.cgi'
    
    # parameters data
    search_types = {'formula': 'Formula', 'name': 'Name', 'inchi': 'InChI', 'cas': 'ID'}
    formula_only = ('MatchIso', 'AllowOther', 'AllowExtra', 'NoIon')
    
    def __init__(self, **kwargs):
        self.parameters = SearchParameters(**kwargs)
        self.IDs = []
        self.compounds = []
        self.lost = False
        self.success = True
    
    def find_compounds(self, identifier, search_type, **kwargs):
        '''
        Search for species data by chemical name
        
        Arguments:
            identifier (str): compound ID / formula / name
            search_type (str): identifier type, available options are:
                - 'formula'
                - 'name'
                - 'inchi'
                - 'cas'
            clear_found: clear all found compounds
            raise_lost: raise exception if limit of 400 compounds per search
                        was achieved
        '''
        if search_type not in self.search_types:
            raise ValueError(f'Bad search_type value: {search_type}')
        # prepare GET parameters
        params = {self.search_types[search_type]: identifier}
        params.update(self.parameters.get_request_parameters())
        addend = SearchParameters(**kwargs)
        params.update(addend.get_request_parameters())
        # load webpage
        r = _requests.get(self._NIST_URL + self._COMP_ID, params)
        if not r.ok:
            self.success = False
            self.IDs = []
            self.compounds = []
            self.lost = False
            return
        soup = _bs4.BeautifulSoup(_re.sub('clss=', 'class=', r.text),
                                  features = 'html.parser')
        # check if no compounds
        if search_type == 'inchi':
            errs = ['information from the inchi', 'no matching species found']
        else:
            errs = ['not found']
        err_flag = False
        for err in errs:
            if sum([err in _.text.lower() for _ in soup.findAll('h1')]):
                err_flag = True
                break
        if err_flag:
            self.success = True
            self.IDs = []
            self.compounds = []
            self.lost = False
            return
        # check if one compound
        flag = _compound.is_compound_page(soup)
        if flag:
            self.success = True
            self.IDs = [flag]
            self.compounds = []
            self.lost = False
            return
        # extract IDs
        refs = soup.find('ol').findChildren('a', href = _re.compile(self._COMP_ID))
        IDs = [_uparse.parse_qs(_uparse.urlparse(a.attrs['href']).query)['ID'][0] for a in refs]
        self.IDs = IDs
        self.compounds = []
        self.success = True
        self.lost = 'Due to the large number of matching species' in soup.text
    
    def load_found_compounds(self):
        '''
        Loads compounds
        '''
        self.compounds = [_compound.Compound(ID) for ID in self.IDs]
    
    def __str__(self):
        return f'Search(Success={self.success}, Lost={self.lost}, Found={len(self.IDs)})'
    
    def __repr__(self):
        return f'Search(Success={self.success}, Lost={self.lost}, Found={len(self.IDs)})'


