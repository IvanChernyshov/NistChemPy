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
    info = {**nist.parsing.parse_compound_page(soup),
            'nist_response': None}
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
        idx = int(f.replace('.html', ''))
        path = os.path.join(dir_html, f)
        with open(path, 'r') as inpf:
            text = inpf.read()
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
    parser.add_argument('dir_data',
                        help = 'directory containing compounds.csv and htmls/')
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
    # check compounds.csv
    path_csv = os.path.join(args.dir_data, 'compounds.csv')
    if not os.path.exists(path_csv):
        raise ValueError('Given dir_data directory does not contain compounds.csv file')
    
    return


def main() -> None:
    '''Runs compound initialization'''
    print('Preparing data ...')
    # prepare arguments
    args = get_arguments()
    check_arguments(args)
    dir_html = os.path.join(args.dir_data, 'htmls/')
    path_csv = os.path.join(args.dir_data, 'compounds.csv')
    df = pd.read_csv(path_csv)
    # process compounds
    print('Running compound initialization ...')
    idxs = get_unreadable_compounds(dir_html)
    sub = df.loc[df.index.isin(idxs)]
    # save
    print('\nSaving data ...')
    path_out = os.path.join(args.dir_data, 'unreadable.csv')
    sub.to_csv(path_out)
    
    return



#%% Main

if __name__ == '__main__':
    
    main()


