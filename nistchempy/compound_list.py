'''Loads pre-prepared info on compounds structure and data availability'''

#%% Imports

import sys as _sys
if _sys.version_info < (3, 9):
    import importlib_resources as _importlib_resources
else:
    import importlib.resources as _importlib_resources

import zipfile as _zipfile
import pandas as _pd


#%% Functions

def get_all_data() -> _pd.core.frame.DataFrame:
    '''Returns pandas dataframe containing info on all NIST Chem WebBook compounds
    
    Returns:
        _pd.core.frame.DataFrame: dataframe containing the following compound info:
            - ID (str): internal NIST Chemistry WebBook Compound ID;
            - name (str): chemical name;
            - formula (str): chemical formula;
            - mol_weight (float): molecular weight;
            - inchi (str): InChI string;
            - inchi_key (str): InChI key string;
            - cas_rn (str): CAS Registry Number;
            - mol2D/mol3D (bool): availability of MOL-file with 2D/3D atomic coordinates;
            - cXX (bool): availability of various physical chemical data, for definitions
              execute the nistchempy.print_search_parameters function.
    
    '''
    dt0 = {'mol_weight': 'float64'}
    dt1 = {k: 'string' for k in ('ID', 'name', 'formula', 'inchi', 'inchi_key', 'cas_rn')}
    dt2 = {k: 'bool' for k in ('mol2D', 'mol3D', 'cIR', 'cTZ', 'cMS', 'cUV', 'cGC',
                               'cTG', 'cTC', 'cTP', 'cSO', 'cTR', 'cIE', 'cIC', 'cES', 'cDI')}
    dtypes = {**dt0, **dt1, **dt2}
    pkg = _importlib_resources.files('nistchempy')
    data_file = pkg / 'nist_data.zip'
    with _importlib_resources.as_file(data_file) as path:
        zf = _zipfile.ZipFile(path) 
        df = _pd.read_csv(zf.open('nist_data.csv'), dtype = dtypes)
        zf.close()
    
    return df


