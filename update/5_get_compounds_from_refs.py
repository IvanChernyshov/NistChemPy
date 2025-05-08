'''The script uses previous data on NIST Chemistry WebBook compounds to fix
current errors, namely non-available compound pages from sitemaps'''

#%% Imports

import os, shutil, argparse

from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup

from tqdm import tqdm

import nistchempy as nist

from typing import List


#%% Functions

def move_missing_inchis(dir_root: str) -> None:
    '''Checks inchi-derived htmls and moves them to the main html folder
    based on the NIST Compound ID'''
    path1 = os.path.join(dir_root, 'htmls')
    path2 = os.path.join(dir_root, 'htmls_inchi')
    # get IDs
    IDs = set([f.replace('.html', '') for f in os.listdir(path1)])
    # check inchi files
    for f in tqdm(os.listdir(path2)):
        path_inp = os.path.join(path2, f)
        # get Compound
        with open(path_inp, 'r') as inpf:
            text = inpf.read()
        soup = BeautifulSoup(text, 'html.parser')
        if not nist.parsing.is_compound_page(soup):
            continue
        info = {
            '_request_config': nist.RequestConfig(),
            '_nist_response': None,
            **nist.parsing.parse_compound_page(soup)
        }
        X = nist.compound.NistCompound(**info)
        # check ID
        if X.ID not in IDs:
            path_out = os.path.join(path1, f'{X.ID}.html')
            shutil.copy2(path_inp, path_out)
    
    return


def get_IDs(soup: BeautifulSoup) -> List[str]:
    '''Extracts all IDs from the HTML page'''
    refs = soup.findAll('a')
    IDs = []
    for ref in refs:
        query = parse_qs(urlparse(ref.attrs['href']).query)
        if 'ID' in query:
            IDs += query['ID']
    IDs = sorted(list(set(IDs)))
    
    return IDs


def get_missing_IDs(dir_html: str) -> List[str]:
    '''Extracts additional IDs for each compound and returns those ones missing
    in the htmls directory
    
    Arguments:
        dir_html (str): directory containing HTML pages
    
    Returns:
        List[str]: list of compound IDs of missing stereoisomers, isotopologs, etc.
    
    '''
    IDs = []
    # cycle over files
    new_IDs = set()
    for f in tqdm(os.listdir(dir_html)):
        # get soup
        path = os.path.join(dir_html, f)
        with open(path, 'r') as inpf:
            text = nist.requests.fix_html(inpf.read())
        soup = BeautifulSoup(text, 'html.parser')
        # extract stereoisomers
        addend = get_IDs(soup)
        new_IDs.update(addend)
    # filter existing
    IDs = set([f.replace('.html', '') for f in os.listdir(dir_html)])
    new_IDs = new_IDs.difference(IDs)
    new_IDs = sorted(list(new_IDs))
    
    return new_IDs


def download_htmls(IDs: List[str], dir_html: str,
                   config: nist.RequestConfig) -> None:
    '''Downloads compound pages for stereoisomers
    
    Arguments:
        IDs (List[str]): list of compound IDs of missing stereoisomers
        dir_html (str): directory to save HTML pages of stereoisomers
        config (float): additional request parameters
    
    '''
    for ID in tqdm(IDs, total = len(IDs)):
        X = nist.get_compound(ID, config)
        path_html = os.path.join(dir_html, f'{ID}.html')
        with open(path_html, 'w') as outf:
            outf.write(X._nist_response.text)
    
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
    parser.add_argument('--crawl-delay', type = float, default = 1.0,
                        help = 'pause between HTTP requests, seconds')
    parser.add_argument('--max-attempts', type = int, default = 3,
                        help = 'max timeout for server response, seconds')
    parser.add_argument('--timeout', type = float, default = 30.0,
                        help = 'max timeout for server response, seconds')
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
    
    # check htmls dir
    dir_html = os.path.join(args.dir_root, 'htmls_inchi')
    if not os.path.exists(dir_html):
        raise ValueError('Given dir_root directory does not contain htmls_inchi/ folder')
    
    # crawl delay
    if args.crawl_delay < 0:
        raise ValueError(f'--crawl-delay must be positive: {args.crawl_delay}')
    
    # max_attempts
    if args.max_attempts < 1:
        raise ValueError(f'--max-attempts must be a positive integer: {args.max_attempts}')
    
    # timeout
    if args.timeout <= 0:
        raise ValueError(f'--timeout must be positive: {args.timeout}')
    
    return


def main() -> None:
    '''Updates the list of NIST compounds via downloaded HTML pages'''
    
    # prepare arguments
    args = get_arguments()
    check_arguments(args)
    
    # moving inchi htmls
    print('\nMoving InChI-derived HTMLs ...')
    move_missing_inchis(args.dir_root)
    
    # get new IDs
    print('\nExtracting IDs ...')
    dir_html = os.path.join(args.dir_root, 'htmls')
    IDs = get_missing_IDs(dir_html)
    print(f'Found {len(IDs)} compounds')
    
    # download stereoisomers
    print('\nDownloading compound HTML pages ...')
    config = nist.RequestConfig(args.crawl_delay, args.max_attempts,
                                {'timeout': args.timeout})
    download_htmls(IDs, dir_html, config)
    print()
    
    return



#%% Main

if __name__ == '__main__':
    
    main()



