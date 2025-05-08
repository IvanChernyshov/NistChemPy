'''Extracts compound info from previously downloaded HTML-files'''

#%% Imports

import os, argparse, json

from bs4 import BeautifulSoup

import pandas as pd

from tqdm import tqdm

import nistchempy as nist


#%% Functions

def get_compounds_info(dir_root: str) -> None:
    '''Extracts compound info from HTML-files
    
    Arguments:
        dir_root (str): root data dump directory
    
    '''
    
    # get list of htmls
    dir_html = os.path.join(dir_root, 'htmls')
    fs = [os.path.join(dir_html, f) for f in os.listdir(dir_html)]
    
    # run extraction
    data = []
    for f in tqdm(fs):
        with open(f, 'r') as inpf:
            text = nist.requests.fix_html(inpf.read())
            soup = BeautifulSoup(text, 'html.parser')
        if not nist.parsing.is_compound_page(soup):
            continue
        info = nist.parsing.parse_compound_page(soup)
        info = {'path': f, **info}
        data.append(info)
    
    # save data
    path_out = os.path.join(dir_root, 'compounds_data.json')
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
    cols = [k for k in data[0].keys() if '_refs' not in k and k != 'path']
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



def prepare_dataset(dir_root: str) -> None:
    '''Transforms extracted data to nist_data.csv
    
    Arguments:
        dir_root (str): root data dump directory
    
    '''
    
    # load data
    path_json = os.path.join(dir_root, 'compounds_data.json')
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
    for col in cols:
        if col not in df.columns:
            df[col] = None
    df = df[cols]
    df = df.drop_duplicates().sort_values('ID', ignore_index = True)
    
    # save
    path_out = os.path.join(dir_root, 'nist_data.csv')
    df.to_csv(path_out, index = None)
    
    return



#%% Main functions

def get_arguments() -> argparse.Namespace:
    '''CLI wrapper
    
    Returns:
        argparse.Namespace: CLI arguments
    
    '''
    parser = argparse.ArgumentParser(description = 'Downloads HTML-pages of NIST Chemistry WebBook compounds')
    parser.add_argument('dir_root',
                        help = 'directory containing compound.csv file created by get_nist_compounds.py script')
    args = parser.parse_args()
    
    return args


def check_arguments(args: argparse.Namespace) -> None:
    '''Tries to create dir_root if it does not exist and raizes error if dir_root is a file
    
    Arguments:
        args (argparse.Namespace): input parameters
    
    '''
    # check root dir
    if not os.path.exists(args.dir_root):
        raise ValueError(f'Given dir_root argument does not exist: {args.dir_root}')
    if not os.path.isdir(args.dir_root):
        raise ValueError(f'Given dir_root argument is not a directory: {args.dir_root}')
    # check htmls dir
    dir_html = os.path.join(args.dir_root, 'htmls')
    if not os.path.exists(dir_html):
        raise ValueError('Given dir_root directory does not contain htmls/ folder')
    # check stereo dir
    dir_stereo = os.path.join(args.dir_root, 'htmls_stereo')
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
    path_json = os.path.join(args.dir_root, 'compounds_data.json')
    if not os.path.exists(path_json):
        get_compounds_info(args.dir_root)
    
    # transform to dataframes
    print('\nTransforming to dataframe ...')
    prepare_dataset(args.dir_root)
    print()
    
    return



#%% Main

if __name__ == '__main__':
    
    main()



