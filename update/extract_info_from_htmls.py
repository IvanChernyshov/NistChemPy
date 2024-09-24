'''Extracts compound info from previously downloaded HTML-files'''

#%% Imports

import os, argparse, json

from bs4 import BeautifulSoup

import pandas as pd

from tqdm import tqdm

import nistchempy as nist



#%% Functions

def get_compounds_info(dir_data: str) -> None:
    '''Extracts compound info from HTML-files
    
    Arguments:
        dir_data (str): root data dump directory
    
    '''
    
    # get list of htmls
    fs = []
    for d in ('htmls', 'htmls_stereo'):
        for f in os.listdir(os.path.join(dir_data, d)):
            path = os.path.join(dir_data, d, f)
            fs.append(path)
    
    # run extraction
    data = []
    for f in tqdm(fs):
        with open(f, 'r') as inpf:
            soup = BeautifulSoup(inpf.read(), 'html.parser')
        if not nist.parsing.is_compound_page(soup):
            continue
        info = nist.parsing.parse_compound_page(soup)
        data.append(info)
    
    # save data
    path_out = os.path.join(dir_data, 'compounds_data.json')
    with open(path_out, 'w') as outf:
        json.dump(data, outf, indent = 2)
    
    return



def get_columns(data: list) -> dict:
    '''Extracts columns from compound data
    
    Arguments:
        data (list): contents of compounds_data.json
    
    Returns:
        list: column names
    
    '''
    cols = [k for k in data[0].keys() if '_refs' not in k]
    # get unique ref keys
    keys = {k: set() for k in data[0].keys() if '_refs' in k}
    for item in data:
        for k1 in keys:
            for k2 in item[k1].keys():
                keys[k1].add(k2)
    keys = {k: sorted(list(v)) for k, v in keys.items()}
    # fix data_refs
    ps = nist.search.get_search_parameters()
    data_refs = [v for k, v in ps.items() if len(k) == 3]
    data_refs += [k for k in keys['data_refs'] if len(k) != 3]
    keys['data_refs'] = data_refs
    # final columns
    for k, v in keys.items():
        cols += v
    
    return cols



def prepare_dataset(dir_data: str) -> None:
    '''Transforms extracted data to nist_data.csv and nist_data_full.csv
    
    Arguments:
        dir_data (str): root data dump directory
    
    '''
    
    # load data
    path_json = os.path.join(dir_data, 'compounds_data.json')
    with open(path_json, 'r') as inpf:
        data = json.load(inpf)
    
    # prepare
    ref_keys = [k for k in data[0].keys() if '_refs' in k]
    ps = nist.search.get_search_parameters()
    ps = {k: v for k, v in ps.items() if len(k) == 3}
    cols = get_columns(data)
    df = []
    
    # get rows
    for item in data:
        add = {k: v for k, v in item.items() if '_refs' not in k}
        add['synonyms'] = '\\n'.join(add['synonyms'])
        for k in ref_keys:
            add.update(item[k])
        df.append(add)
    
    # process dataframe
    df = pd.DataFrame(df)
    df = df.rename(columns = ps)
    df = df.sort_values('ID', ignore_index = True)
    df = df[cols]
    
    # save
    path_out = os.path.join(dir_data, 'nist_data.csv')
    df.to_csv(path_out, index = None)
    
    return



#%% Main functions

def get_arguments() -> argparse.Namespace:
    '''CLI wrapper
    
    Returns:
        argparse.Namespace: CLI arguments
    
    '''
    parser = argparse.ArgumentParser(description = 'Downloads HTML-pages of NIST Chemistry WebBook compounds')
    parser.add_argument('dir_data',
                        help = 'directory containing compound.csv file created by get_nist_compounds.py script')
    args = parser.parse_args()
    
    return args


def check_arguments(args: argparse.Namespace) -> None:
    '''Tries to create dir_data if it does not exist and raizes error if dir_data is a file
    
    Arguments:
        args (argparse.Namespace): input parameters
    
    '''
    # check root dir
    if not os.path.exists(args.dir_data):
        raise ValueError(f'Given dir_data argument does not exist: {args.dir_data}')
    if not os.path.isdir(args.dir_data):
        raise ValueError(f'Given dir_data argument is not a directory: {args.dir_data}')
    # check htmls dir
    dir_html = os.path.join(args.dir_data, 'htmls')
    if not os.path.exists(dir_html):
        raise ValueError('Given dir_data directory does not contain htmls/ folder')
    # check stereo dir
    dir_stereo = os.path.join(args.dir_data, 'htmls_stereo')
    if not os.path.exists(dir_stereo):
        os.mkdir(dir_stereo)
    
    return


def main() -> None:
    '''Updates the list of NIST compounds via downloaded HTML pages'''
    
    # prepare arguments
    args = get_arguments()
    check_arguments(args)
    
    # extract info
    print('\nExtracting info from HTML-files ...')
    path_json = os.path.join(args.dir_data, 'compounds_data.json')
    if not os.path.exists(path_json):
        get_compounds_info(args.dir_data)
    
    # transform to dataframes
    print('\nTransforming to dataframe ...')
    prepare_dataset(args.dir_data)
    print()
    
    return



#%% Main

if __name__ == '__main__':
    
    main()



