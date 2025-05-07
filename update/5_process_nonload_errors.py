'''The script uses previous data on NIST Chemistry WebBook compounds to fix
current errors, namely non-available compound pages from sitemaps'''

#%% Imports

import re, os, time
import argparse

from tqdm import tqdm

import pandas as pd

import nistchempy as nist

from typing import List, Tuple


#%% Functions

def read_download_errors(path: str) -> List[str]:
    '''Returns list of URLS of not downloaded pages
    
    Arguments:
        path (str): path to download_htmls.err
    
    Returns:
        List[str]: list of not downloaded URLs
    
    '''
    with open(path, 'r') as inpf:
        lines = [l.strip() for l in inpf.readlines() if 'url=' in l]
    err_urls = [re.search('url=(.+)', l).group(1).strip() for l in lines]
    
    return err_urls




def get_errors_to_fix(dir_data: str, path_old: str) -> List[Tuple[str, str]]:
    '''Extract errors with loaded HTML pages which were parsed previously
    
    Arguments:
        dir_data (str): path to the directory with current parsing results
        path_old (str): old nist_data.csv file
    
    Returns:
        List[Tuple[str, str]]: list of (idx, url) tuples
    
    '''
    
    # paths
    path_new = os.path.join(dir_data, 'compounds.csv')
    path_non_load = os.path.join(dir_data, 'download_htmls.err')
    
    # read data
    old = pd.read_csv(path_old, low_memory = False)
    new = pd.read_csv(path_new)
    nload = read_download_errors(path_non_load)
    
    # treat non-load
    sub = new.loc[new.url.isin(nload)].copy()
    for idx, inchi in zip(sub.index, sub.id):
        if 'InChI=' not in inchi:
            continue
        IDs = old.loc[old.inchi == inchi, 'ID']
        if len(IDs) != 1:
            continue
        ID = old.loc[old.inchi == inchi, 'ID'].values[0]
        new_ref = nist.requests.SEARCH_URL + f'?ID={ID}'
        sub.loc[idx, 'url'] = new_ref
    
    # output
    urls = [(idx, url) for idx, url in zip(sub.index, sub.url)]
    
    return urls


def load_errors(errs: List[Tuple[str, str]], dir_data: str,
                crawl_delay: float = 5) -> None:
    '''Downloads previously errorneous compound pages if possible
    
    Arguments:
        errs (List[Tuple[str, str]]): list of (idx, url) tuples
        dir_data (str): path to the directory with current parsing results
        crawl_delay (float): interval between http requests
    
    '''
    for idx, url in tqdm(errs, total = len(errs)):
        nr = nist.requests.make_nist_request(url)
        if nr.ok:
            path_html = os.path.join(dir_data, 'htmls', f'{idx}.html')
            with open(path_html, 'w') as outf:
                outf.write(nr.text)
        time.sleep(crawl_delay)
    
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
    parser.add_argument('path_old',
                        help = 'old nist_data.csv file')
    parser.add_argument('--crawl-delay', type = float, default = 5,
                        help = 'pause between HTTP requests, seconds')
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
    # check download_htmls.err
    path_nload = os.path.join(args.dir_data, 'download_htmls.err')
    if not os.path.exists(path_nload):
        raise ValueError('Given dir_data directory does not contain download_htmls.err file')
    # check htmls dir
    dir_html = os.path.join(args.dir_data, 'htmls')
    if not os.path.exists(dir_html):
        raise ValueError('Given dir_data directory does not contain htmls/ folder')
    # check old data file
    if not os.path.exists(args.path_old):
        raise ValueError(f'Given path_old file does not exists: {args.path_old}')
    # crawl delay
    if args.crawl_delay < 0:
        raise ValueError(f'--crawl-delay must be positive: {args.crawl_delay}')
    
    return


def main() -> None:
    '''Updates the list of NIST compounds via downloaded HTML pages'''
    # prepare arguments
    args = get_arguments()
    check_arguments(args)
    # load compounds
    print('Preparing errors ...')
    errs = get_errors_to_fix(args.dir_data, args.path_old)
    print('Loading webpages ...')
    load_errors(errs, args.dir_data, args.crawl_delay)
    print()
    
    return



#%% Main

if __name__ == '__main__':
    
    main()



