'''Downloads HTML pages of NIST Chemistry WebBook compounds'''

#%% Imports

import re, os, sys, time
import argparse

from tqdm import tqdm

import pandas as pd

import nistchempy as nist


#%% Download functions

def download_compound_html(url: str, path_html: str, path_err: str) -> None:
    '''Downloads HTML page of the NIST compound
    
    Arguments:
        url (str): URL of compound page
        path_html (str): output HTML file
        path_err (str): errors file
    
    '''
    nr = nist.requests.make_nist_request(url)
    if nr.ok:
        with open(path_html, 'w') as outf:
            outf.write(nr.text)
    else:
        idx = os.path.basename(path_html).replace('.html', '')
        message = f'ID={idx}, code={nr.response.status_code}, url={url}\n'
        with open(path_err, 'a') as outf:
            outf.write(message)
    
    return


def download_compound_htmls(df: pd.core.frame.DataFrame, dir_html: str,
                            path_err: str, crawl_delay: float = 5) -> None:
    '''Main function for updating the list of NIST compounds
    
    Arguments:
        df (pd.core.frame.DataFrame): compounds' [ id / url ] dataframe
        dir_html (str): directory containing HTML pages
        path_err (str): errors file
        crawl_delay (float): interval between HTTP requests, seconds
    
    '''
    n_errs = 0
    # download cycle
    for i, url in tqdm(zip(df.index, df.url), total = len(df)):
        if n_errs >= 3:
            print('\n3 download errors in a row, stopping execution ...')
            sys.exit(0)
        path_html = os.path.join(dir_html, f'{i}.html')
        try:
            download_compound_html(url, path_html, path_err)
            n_errs = 0
            time.sleep(crawl_delay)
        except TimeoutError:
            n_errs += 1
            time.sleep(max(30, 10*crawl_delay))
    
    return



#%% Main function

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
    # check compounds.csv
    path_csv = os.path.join(args.dir_data, 'compounds.csv')
    if not os.path.exists(path_csv):
        raise ValueError('Given dir_data directory does not contain compounds.csv file')
    # crawl delay
    if args.crawl_delay < 0:
        raise ValueError(f'--crawl-delay must be positive: {args.crawl_delay}')
    
    return


def main() -> None:
    '''Main function for updating the list of NIST compounds via downloaded HTML pages
    
    Arguments:
        dir_data (str): directory for robots.txt and primary sitemap
    
    '''
    # prepare arguments
    args = get_arguments()
    check_arguments(args)
    
    # get NIST compounds
    print('Loading compounds data ...')
    path_csv = os.path.join(args.dir_data, 'compounds.csv')
    df = pd.read_csv(path_csv)
    
    # check html dir
    dir_html = os.path.join(args.dir_data, 'htmls')
    if not os.path.exists(dir_html):
        os.mkdir(dir_html)
    
    # check errors file
    path_err = os.path.join(args.dir_data, 'download_htmls.err')
    err_urls = []
    if os.path.exists(path_err):
        with open(path_err, 'r') as inpf:
            lines = [l.strip() for l in inpf.readlines()]
            lines = [l for l in lines if l]
        err_urls = [re.search('url=(.+)', l).group(1).strip() for l in lines]
    
    # filter downloaded systems
    loaded = [int(f.replace('.html', '')) for f in os.listdir(dir_html)]
    df = df.loc[~df.index.isin(loaded)]
    df = df.loc[~df.url.isin(err_urls)]
    
    # download
    print('Downloading NIST compound webpages ...')
    download_compound_htmls(df, dir_html, path_err, args.crawl_delay)
    
    return



#%% Main

if __name__ == '__main__':
    
    main()


