'''The module contains search-related functionality'''

#%% Imports

import dataclasses as _dcs
import typing as _tp

import nistchempy.requests as _ncpr
import nistchempy.compound as _compound
import nistchempy.parsing as _parsing


#%% Search parameters helper

def get_search_parameters() -> _tp.Dict[str, str]:
    '''Returns search parameters and the corresponding keys
    
    Returns:
        _tp.Dict[str, str]: {short_key => search_parameter}
    
    '''
    info = {'use_SI': 'Units for thermodynamic data, "SI" if True and "calories" if False',
            'match_isotopes': 'Exactly match the specified isotopes (formula search only)',
            'allow_other': 'Allow elements not specified in formula (formula search only)',
            'allow_extra': 'Allow more atoms of elements in formula than specified (formula search only)',
            'no_ion': 'Exclude ions from the search (formula search only)',
            'cTG': 'Gas phase thermochemistry data',
            'cTC': 'Condensed phase thermochemistry data',
            'cTP': 'Phase change data',
            'cTR': 'Reaction thermochemistry data',
            'cIE': 'Gas phase ion energetics data',
            'cIC': 'Ion clustering data',
            'cIR': 'IR Spectrum',
            'cTZ': 'THz IR spectrum',
            'cMS': 'Mass spectrum (electron ionization)',
            'cUV': 'UV/Visible spectrum',
            'cGC': 'Gas Chromatography',
            'cES': 'Vibrational and/or electronic energy levels',
            'cDI': 'Constants of diatomic molecules',
            'cSO': 'Henry\'s Law data'}
    
    return info


def print_search_parameters() -> None:
    '''
    Prints available search parameters
    '''
    info = get_search_parameters()
    max_len = max([len(_) for _ in info])
    spaces = [' '*(max_len - len(_) + 1) for _ in info]
    for (key, val), space in zip(info.items(), spaces):
        print(f'{key}{space}:   {val}')



#%% Classes

@_dcs.dataclass
class NistSearchParameters():
    '''GET parameters for compound search of NIST Chemistry WebBook
    
    Attributes:
        use_SI (bool): if True, returns results in SI units. otherwise calories are used
        match_isotopes (bool): if True, exactly matches the specified isotopes (formula search only)
        allow_other (bool): if True, allows elements not specified in formula (formula search only)
        allow_extra (bool): if True, allows more atoms of elements in formula than specified (formula search only)
        no_ion (bool): if True, excludes ions from the search (formula search only)
        cTG (bool): if True, returns entries containing gas-phase thermodynamic data
        cTC (bool): if True, returns entries containing condensed-phase thermodynamic data
        cTP (bool): if True, returns entries containing phase-change thermodynamic data
        cTR (bool): if True, returns entries containing reaction thermodynamic data
        cIE (bool): if True, returns entries containing ion energetics thermodynamic data
        cIC (bool): if True, returns entries containing ion cluster thermodynamic data
        cIR (bool): if True, returns entries containing IR data
        cTZ (bool): if True, returns entries containing THz IR data
        cMS (bool): if True, returns entries containing MS data
        cUV (bool): if True, returns entries containing UV/Vis data
        cGC (bool): if True, returns entries containing gas chromatography data
        cES (bool): if True, returns entries containing vibrational and electronic energy levels
        cDI (bool): if True, returns entries containing constants of diatomic molecules
        cSO (bool): if True, returns entries containing info on Henry\'s law
    
    '''
    
    use_SI: bool = True # Units = SI/CAL
    match_isotopes: bool = False
    allow_other: bool = False
    allow_extra: bool = False
    no_ion: bool = False
    cTG: bool = False
    cTC: bool = False
    cTP: bool = False
    cTR: bool = False
    cIE: bool = False
    cIC: bool = False
    cIR: bool = False
    cTZ: bool = False
    cMS: bool = False
    cUV: bool = False
    cGC: bool = False
    cES: bool = False
    cDI: bool = False
    cSO: bool = False
    
    
    def __str__(self):
        params = [f'{k}={v}' for k, v in self.__dict__.items() if v]
        text = f'SearchParameters({", ".join(params)})'
        
        return text
    
    
    def __repr__(self):
        return self.__str__()
    
    
    def get_request_parameters(self) -> dict:
        '''Returns dictionary containing GET parameters
        
        Returns:
            dict: dictionary of GET parameters relevant to the search
        
        '''
        params = {'Units': 'SI' if self.use_SI else 'CAL'}
        for key, val in self.__dict__.items():
            if key == 'Units' or not val:
                continue
            params[key] = 'on'
        
        return params



@_dcs.dataclass(eq = False)
class NistSearch():
    '''Results of the compound search in NIST Chemistry WebBook
    
    Attributes:
        nist_response (NistResponse): NIST search response
        search_parameters (NistSearchParameters): used search parameters
        compound_ids (_tp.List[str]): NIST IDs of found compounds
        compounds (_tp.List[_compound.NistCompound]): NistCompound objects of found compounds
        success (bool): True if search request was successful
        num_compounds (int): number of found compounds
        lost (bool): True if search returns less compounds than there are in the database
    
    '''
    
    nist_response: _ncpr.NistResponse = _dcs.field(repr = False)
    search_parameters: NistSearchParameters = _dcs.field(repr = False)
    compound_ids: _tp.List[str] = _dcs.field(repr = False)
    compounds: _tp.List[_compound.NistCompound] = _dcs.field(init = False, repr = False)
    success: bool
    num_compounds: int = _dcs.field(init = False)
    lost: bool
    
    
    def __post_init__(self):
        self.compounds = []
        self.num_compounds = len(self.compound_ids)
    
    
    def _save_response_page(self, path: str = 'nist_search.html') -> None:
        '''Saves response page for testing purposes'''
        self.nist_response._save_response(path)
    
    
    def load_found_compounds(self, **kwargs) -> None:
        '''Loads found compounds
        
        Arguments:
            kwargs: requests.get kwargs parameters
        
        '''
        self.compounds = []
        for ID in self.compound_ids:
            X = _compound.get_compound(ID, **kwargs)
            self.compounds.append(X)



#%% Search

def run_search(identifier: str, search_type: str,
               search_parameters: _tp.Optional[NistSearchParameters] = None,
               use_SI: bool = True, match_isotopes: bool = False,
               allow_other: bool = False, allow_extra: bool = False,
               no_ion: bool = False, cTG: bool = False, cTC: bool = False,
               cTP: bool = False, cTR: bool = False, cIE: bool = False, 
               cIC: bool = False, cIR: bool = False, cTZ: bool = False, 
               cMS: bool = False, cUV: bool = False, cGC: bool = False, 
               cES: bool = False, cDI: bool = False, cSO: bool = False,
               **kwargs) -> NistSearch:
    '''Searches compounds in NIST Chemistry WebBook
    
    Arguments:
        identifier (str): NIST compound ID / formula / name / inchi / CAS RN
        search_type (str): identifier type, available options are:
            - 'formula'
            - 'name'
            - 'inchi'
            - 'cas'
            - 'id'
        search_parameters (_tp.Optional[NistSearchParameters]): search parameters; if provided, the following search parameter arguments are ignored
        use_SI (bool): if True, returns results in SI units. otherwise calories are used
        match_isotopes (bool): if True, exactly matches the specified isotopes (formula search only)
        allow_other (bool): if True, allows elements not specified in formula (formula search only)
        allow_extra (bool): if True, allows more atoms of elements in formula than specified (formula search only)
        no_ion (bool): if True, excludes ions from the search (formula search only)
        cTG (bool): if True, returns entries containing gas-phase thermodynamic data
        cTC (bool): if True, returns entries containing condensed-phase thermodynamic data
        cTP (bool): if True, returns entries containing phase-change thermodynamic data
        cTR (bool): if True, returns entries containing reaction thermodynamic data
        cIE (bool): if True, returns entries containing ion energetics thermodynamic data
        cIC (bool): if True, returns entries containing ion cluster thermodynamic data
        cIR (bool): if True, returns entries containing IR data
        cTZ (bool): if True, returns entries containing THz IR data
        cMS (bool): if True, returns entries containing MS data
        cUV (bool): if True, returns entries containing UV/Vis data
        cGC (bool): if True, returns entries containing gas chromatography data
        cES (bool): if True, returns entries containing vibrational and electronic energy levels
        cDI (bool): if True, returns entries containing constants of diatomic molecules
        cSO (bool): if True, returns entries containing info on Henry\'s law
        kwargs: requests.get parameters
    
    Returns:
        NistSearch: search object containing info on found compounds
    
    '''
    # parameters
    search_types = {'formula': 'Formula', 'name': 'Name',
                    'inchi': 'InChI', 'cas': 'ID', 'id': 'ID'}
    if search_type not in search_types:
        raise ValueError(f'Bad search_type value: {search_type}')
    # prepare search parameters
    if search_parameters is None:
        search_parameters = NistSearchParameters(use_SI = use_SI,
            match_isotopes = match_isotopes if search_type == 'formula' else False,
            allow_other = allow_other if search_type == 'formula' else False,
            allow_extra = allow_extra if search_type == 'formula' else False,
            no_ion = no_ion if search_type == 'formula' else False,
            cTG = cTG, cTC = cTC, cTP = cTP, cTR = cTR, cIE = cIE, cIC = cIC,
            cIR = cIR, cTZ = cTZ, cMS = cMS, cUV = cUV, cGC = cGC, cES = cES,
            cDI = cDI, cSO = cSO)
    # prepare GET parameters
    params = {search_types[search_type]: identifier,
              **search_parameters.get_request_parameters()}
    # load webpage
    nr = _ncpr.make_nist_request(_ncpr.SEARCH_URL, params, **kwargs)
    if not nr.ok:
        return NistSearch(nist_response = nr, search_parameters = search_parameters,
                          compound_ids = [], success = False, lost = False)
    
    # XXX: there are possible "search errors" which follows the <h1> tag:
    #     1) 'information from the inchi' and 'no matching species found'
    #         for inchi search
    #     2) 'not found' for other searches
    # possibly in the future we need to catch them explicitly
    
    # check if response is a compound page
    if _parsing.is_compound_page(nr.soup):
        X = _compound.compound_from_response(nr)
        nsearch = NistSearch(nist_response = nr, search_parameters = search_parameters,
                             compound_ids = [X.ID], success = True, lost = False)
        nsearch.compounds = [X]
        return nsearch
    # extract IDs
    info = _parsing.get_found_compounds(nr.soup)
    
    return NistSearch(nist_response = nr, search_parameters = search_parameters,
                      compound_ids = info['IDs'], success = True, lost = info['lost'])


