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
        _pd.core.frame.DataFrame: dataframe containing pre-extracted compound info
    
    '''
    pkg = _importlib_resources.files('nistchempy')
    data_file = pkg / 'nist_data.zip'
    with _importlib_resources.as_file(data_file) as path:
        zf = _zipfile.ZipFile(path) 
        df = _pd.read_csv(zf.open('nist_data.csv'), dtype = 'str')
        df['mol_weight'] = df['mol_weight'].astype(float)
        zf.close()
    
    return df


