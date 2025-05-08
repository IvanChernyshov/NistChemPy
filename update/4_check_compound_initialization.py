'''Check compound initialization using preloaded html-files'''

#%% Imports

import os, argparse

from tqdm import tqdm

import pandas as pd

from bs4 import BeautifulSoup

import nistchempy as nist

from typing import List


#%% Functions

def check_soup(soup: BeautifulSoup) -> bool:
    '''Returns False if something is wrong with the compound's soup
    
    Arguments:
        soup (BeautifulSoup): bs4-parsed web-page
    
    Returns:
        bool: True if compound page is OK
    
    '''
    if not nist.parsing.is_compound_page(soup):
        return False
    # extract data
    info = {
        '_request_config': nist.RequestConfig(),
        '_nist_response': None,
        **nist.parsing.parse_compound_page(soup)
    }
    X = nist.compound.NistCompound(**info)
    
    return X is not None


def get_unreadable_compounds(dir_html: str) -> List[str]:
    '''Iterates through loaded HTML-files and returns names of non-readable ones
    
    Arguments:
        dir_html: path to the directory containing compound HTML-files
    
    Returns:
        List[str]: list of non-readable HTML files corresponding to compounds.csv row indexes
    
    '''
    errors = []
    # cycle over files
    fs = os.listdir(dir_html)
    for f in tqdm(fs, total = len(fs)):
        # prepare
        idx = f.replace('.html', '')
        path = os.path.join(dir_html, f)
        with open(path, 'r') as inpf:
            text = nist.requests.fix_html(inpf.read())
        soup = BeautifulSoup(text, 'html.parser')
        # check
        flag = check_soup(soup)
        if not flag:
            errors.append(idx)
    
    return errors



#%% Main functions

def get_arguments() -> argparse.Namespace:
    '''CLI wrapper
    
    Returns:
        argparse.Namespace: CLI arguments
    
    '''
    parser = argparse.ArgumentParser(description = 'Runs compound initialization from pre-loaded HTML-pages')
    parser.add_argument('dir_root',
                        help = 'directory containing compounds.csv and htmls/')
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
    # check compounds.csv
    path_csv1 = os.path.join(args.dir_root, 'compounds_combined.csv')
    if not os.path.exists(path_csv1):
        raise ValueError('Given dir_root directory does not contain compounds_combined.csv file')
    path_csv2 = os.path.join(args.dir_root, 'compounds_combined_inchi.csv')
    if not os.path.exists(path_csv2):
        raise ValueError('Given dir_root directory does not contain compounds_combined_inchi.csv file')
    
    return


def main() -> None:
    '''Runs compound initialization'''
    print('Preparing data ...')
    # prepare arguments
    args = get_arguments()
    check_arguments(args)
    
    # inchi
    print('Processing InChI-derived compounds ...')
    dir_html = os.path.join(args.dir_root, 'htmls_inchi/')
    path_csv = os.path.join(args.dir_root, 'compounds_combined_inchi.csv')
    df = pd.read_csv(path_csv)
    # process compounds
    idxs = get_unreadable_compounds(dir_html)
    idxs = [int(idx) for idx in idxs]
    sub = df.loc[df.index.isin(idxs)]
    # save
    path_out = os.path.join(args.dir_root, 'unreadable_inchi.csv')
    sub.to_csv(path_out)
    
    # ID
    print('Processing ID-derived compounds ...')
    dir_html = os.path.join(args.dir_root, 'htmls/')
    path_csv = os.path.join(args.dir_root, 'compounds_combined.csv')
    df = pd.read_csv(path_csv)
    # process compounds
    idxs = get_unreadable_compounds(dir_html)
    sub = df.loc[df['id'].isin(idxs)]
    # save
    path_out = os.path.join(args.dir_root, 'unreadable.csv')
    sub.to_csv(path_out)
    
    return



#%% Main

if __name__ == '__main__':
    
    main()


