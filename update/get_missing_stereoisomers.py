'''The script uses previous data on NIST Chemistry WebBook compounds to fix
current errors, namely non-available compound pages from sitemaps'''

#%% Imports

import re, os, sys, time
import argparse

from urllib.parse import urlparse, parse_qs

import requests

from bs4 import BeautifulSoup

from tqdm import tqdm

import nistchempy as nist

from typing import List


#%% Functions

def get_stereoisomers(soup: BeautifulSoup) -> List[str]:
    '''Extracts info on stereoisomers from compound's soup
    
    Arguments:
        soup (BeautifulSoup): compound web page's soup
    
    Returns:
        List[str]: list of compound IDs corresponding to the stereoisomers
    
    '''
    IDs = []
    # find stereoisomer refs
    hits = soup.findAll(string = re.compile('Stereoisomers'))
    if not hits:
        return IDs
    item = hits[0].find_parent('li')
    if not item:
        return IDs
    items = item.findChildren('a')
    # extract IDs
    IDs = [parse_qs(urlparse(a.attrs['href']).query) for a in items]
    IDs = [ps['ID'][0] for ps in IDs if 'ID' in ps]
    
    return IDs



def get_missing_stereoisomers(dir_html: str) -> List[str]:
    '''Extracts stereoisomers for each compound and returns those ones missing
    in the htmls directory
    
    Arguments:
        dir_html (str): directory containing HTML pages
    
    Returns:
        List[str]: list of compound IDs of missing stereoisomers
    
    '''
    IDs = []
    stereos = []
    # cycle over files
    for f in tqdm(os.listdir(dir_html)):
        # get soup
        path = os.path.join(dir_html, f)
        with open(path, 'r') as inpf:
            text = inpf.read()
        soup = BeautifulSoup(text, 'html.parser')
        # extract ID
        if nist.parsing.is_compound_page(soup):
            ID = nist.parsing.get_compound_id(soup)
            IDs.append(ID)
        # extract stereoisomers
        addend = get_stereoisomers(soup)
        stereos += addend
    # filter stereos
    stereos = set(stereos).difference(set(IDs))
    stereos = sorted(list(stereos))
    
    return stereos



def download_stereoisomer_htmls(IDs: List[str], dir_stereo: str,
                                crawl_delay: float = 5) -> None:
    '''Downloads compound pages for stereoisomers
    
    Arguments:
        IDs (List[str]): list of compound IDs of missing stereoisomers
        dir_stereo (str): directory to save HTML pages of stereoisomers
        crawl_delay (float): interval between HTTP requests, seconds
    
    '''
    # download cycle
    n_errs = 0
    for ID in tqdm(IDs, total = len(IDs)):
        time.sleep(crawl_delay)
        if n_errs >= 3:
            print('\n3 download errors in a row, stopping execution ...')
            sys.exit(0)
        path_html = os.path.join(dir_stereo, f'{ID}.html')
        url = nist.requests.SEARCH_URL + f'?ID={ID}'
        try:
            #nr = nist.requests.make_nist_request(url)
            nr = requests.get(url)
            if nr.text and nr.text.strip():
                with open(path_html, 'w') as outf:
                    outf.write(nr.text)
            n_errs = 0
        except (KeyboardInterrupt, SystemError, SystemExit):
            raise
        except:
            # n_errs += 1
            # time.sleep(max(60, 10*crawl_delay))
            pass
    
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
    # check htmls dir
    dir_html = os.path.join(args.dir_data, 'htmls')
    if not os.path.exists(dir_html):
        raise ValueError('Given dir_data directory does not contain htmls/ folder')
    # check stereo dir
    dir_stereo = os.path.join(args.dir_data, 'htmls_stereo')
    if not os.path.exists(dir_stereo):
        os.mkdir(dir_stereo)
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
    print('\nExtracting stereoisomers ...')
    path_stereo_ids = os.path.join(args.dir_data, 'stereoisomers.txt')
    if os.path.exists(path_stereo_ids):
        with open(path_stereo_ids, 'r') as inpf:
            IDs = [l.strip() for l in inpf.readlines()]
        IDs = [ID for ID in IDs if ID]
    else:
        dir_html = os.path.join(args.dir_data, 'htmls')
        IDs = get_missing_stereoisomers(dir_html)
        with open(path_stereo_ids, 'w') as outf:
            outf.write('\n'.join(IDs) + '\n')
    
    # download stereoisomers
    print('\nChecking downloaded stereoisomers ...')
    dir_stereo = os.path.join(args.dir_data, 'htmls_stereo')
    loaded = []
    for f in tqdm(os.listdir(dir_stereo)):
        with open(os.path.join(dir_stereo, f), 'r') as inpf:
            text = inpf.read()
            soup = BeautifulSoup(text, 'html.parser')
        if nist.parsing.is_compound_page(soup):
            ID = f.replace('.html', '')
            loaded.append(ID)
    IDs = [ID for ID in IDs if ID not in loaded]
    print('\nLoading stereoisomers ...')
    download_stereoisomer_htmls(IDs, dir_stereo, args.crawl_delay)
    print()
    
    return



#%% Main

if __name__ == '__main__':
    
    main()



