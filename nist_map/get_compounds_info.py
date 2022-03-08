'''
Downloads main info for all NIST Chemistry WebBook compounds
'''

#%% Imports

import json, os
from urllib.parse import unquote
import pandas as pd
import nistchempy as nist


#%% Parameters

# paths
path_json = 'data/compounds.json'
path_csv = 'data/data_raw.csv'

# data fields
cols = ['ID', 'name', 'synonyms', 'formula', 'mol_weight', 'inchi', 'inchi_key',
        'cas_rn', 'ir', 'ms', 'uvvis', 'mol2d', 'mol3d', 'data_refs']


#%% Load data

# load csv
if os.path.exists(path_csv):
    df = pd.read_csv(path_csv, dtype = {'inchi': str})
else:
    df = pd.DataFrame(columns = cols)

# load compounds
with open(path_json, 'r') as inpf:
    compounds = json.load(inpf)

# download list
IDs = sorted(list(set(compounds['ID']).difference(set(df.ID))))
inchis = [unquote(_) for _ in compounds['inchi']]
inchis = sorted(list(set(inchis).difference(set(df.inchi))))


#%% Loading IDs

data = []
for i, ID in enumerate(IDs):
    if not i % 10:
        print(i)
    try:
        X = nist.Compound(ID)
    except ValueError:
        print(f'Bad compound ID: {ID}')
        continue
    info = X.__dict__
    info['data_refs'] = ';;'.join(info['data_refs'].keys())
    data.append(info)


#%% Loading InChIs

search = nist.Search()
for i, inchi in enumerate(inchis):
    if not i % 10:
        print(i)
    try:
        search.find_compounds(inchi, 'inchi')
    except (ValueError, AttributeError):
        print(f'Bad InChI: {inchi}')
        continue
    if not search.success or search.lost:
        print(f'Bad InChI: {inchi}')
        continue
    for ID in search.IDs:
        try:
            X = nist.Compound(ID)
        except ValueError:
            print(f'Bad compound ID: {ID}')
            continue
        info = X.__dict__
        print(info['name'])
        info['data_refs'] = ';;'.join(info['data_refs'].keys())
        data.append(info)


#%% Save data

add = pd.DataFrame(data)
df = pd.concat([df, add], ignore_index = True)
df.to_csv(path_csv, index = None)


