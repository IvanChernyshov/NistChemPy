'''Tries to download HTMLs for compounds available in old dataset but missing
in the current one'''

#%% Imports

import os, time
import argparse

import requests

import pandas as pd

from tqdm import tqdm

import nistchempy as nist

from typing import List


#%% Functions

def get_missing_entries(dir_data: str, path_old: str) -> List[str]:
    '''Extracts entries missing from the old data
    
    Arguments:
        dir_data (str): directory containing compound.csv file created by get_nist_compounds.py script
        path_old (str): old nist_data.csv file
    
    Returns:
        List[str]: list of compound IDs of missing compounds
    
    '''
    # read data
    path_new = os.path.join(dir_data, 'nist_data.csv')
    new = pd.read_csv(path_new)
    old = pd.read_csv(path_old)
    
    # get missing IDs
    IDs = set(old['ID']).difference(set(new['ID']))
    IDs = sorted(list(IDs))
    
    return IDs



def download_missing_htmls(IDs: List[str], dir_out: str,
                           crawl_delay: float = 5) -> None:
    '''Downloads compound pages for stereoisomers
    
    Arguments:
        IDs (List[str]): list of compound IDs of missing compounds
        dir_out (str): directory to save HTML pages of compounds
        crawl_delay (float): interval between HTTP requests, seconds
    
    '''
    # download cycle
    for ID in tqdm(IDs, total = len(IDs)):
        time.sleep(crawl_delay)
        path_html = os.path.join(dir_out, f'{ID}.html')
        url = nist.requests.SEARCH_URL + f'?ID={ID}'
        try:
            #nr = nist.requests.make_nist_request(url)
            nr = requests.get(url)
            if nr.text and nr.text.strip():
                with open(path_html, 'w') as outf:
                    outf.write(nr.text)
        except (KeyboardInterrupt, SystemError, SystemExit):
            raise
        except:
            tqdm.write(f'Error with downloading Compound: {ID}')
    
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
    
    # check old compounds.csv
    if not os.path.exists(args.path_old):
        raise ValueError(f'Given path_old argument does not exist: {args.path_old}')
    
    # check new compounds.csv
    path_new = os.path.join(args.dir_data, 'nist_data.csv')
    if not os.path.exists(path_new):
        raise ValueError('Given dir_data does not contain nist_data.csv file')
    
    # check old dir
    dir_out = os.path.join(args.dir_data, 'htmls_old')
    if not os.path.exists(dir_out):
        os.mkdir(dir_out)
    
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
    print('\nGetting missing IDs ...')
    IDs = get_missing_entries(args.dir_data, args.path_old)
    
    # download stereoisomers
    print('\nDownloading missing HTMLs ...')
    dir_out = os.path.join(args.dir_data, 'htmls_old')
    download_missing_htmls(IDs, dir_out, args.crawl_delay)
    print()
    
    return



#%% Main

if __name__ == '__main__':
    
    main()



