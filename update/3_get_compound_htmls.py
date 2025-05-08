'''Downloads HTML pages of NIST Chemistry WebBook compounds'''

#%% Imports

import os, argparse

from tqdm import tqdm

import pandas as pd

import nistchempy as nist


#%% Download functions

def combine_compounds(dir_root: str) -> None:
    '''Combines all csv-files containing compounds'''
    
    df0 = nist.get_all_data()
    
    # get formula-based compounds
    df1, path1 = None, os.path.join(dir_root, 'compounds_formula.csv')
    if os.path.exists(path1):
        df1 = pd.read_csv(path1)
    if df1 is not None:
        df1 = df1.loc[~df1['id'].isin(df0.ID)]
    
    # get sitemap-based compounds
    df2, path2 = None, os.path.join(dir_root, 'compounds_sitemaps.csv')
    if os.path.exists(path2):
        df2 = pd.read_csv(path2)
    if df2 is not None:
        df2 = df2.loc[~df2['id'].isin(df0.ID) & ~df2['id'].isin(df0.inchi.dropna())]
        df2 = df2.reset_index(drop=True)
    
    # combine sources
    df = pd.DataFrame({'id': df0.ID, 'url': [f'{nist.requests.SEARCH_URL}?ID={idx}' for idx in df0.ID]})
    dfs = [df]
    if df1 is not None: dfs.append(df1)
    if df2 is not None: dfs.append(df2)
    df = pd.concat(dfs)
    df = df.sort_values('id').reset_index(drop=True)
    
    return df


def download_compound_html(
        url: str, path_html: str, path_err: str,
        config: nist.RequestConfig = None
    ) -> None:
    '''Downloads HTML page of the NIST compound'''
    config = config or nist.RequestConfig()
    nr = nist.requests.make_nist_request(url, config=config)
    if nr.ok:
        with open(path_html, 'w', encoding='utf8') as outf:
            outf.write(nr.text)
    else:
        idx = os.path.basename(path_html).replace('.html', '')
        message = f'ID={idx}, code={nr.response.status_code}, url={url}\n'
        with open(path_err, 'a') as outf:
            outf.write(message)
    
    return


def download_compound_htmls(
        df: pd.core.frame.DataFrame,
        dir_html: str, path_err: str,
        config: nist.RequestConfig
    ) -> None:
    '''Main function for updating the list of NIST compounds
    
    Arguments:
        df (pd.core.frame.DataFrame): compounds' [ id / url ] dataframe
        dir_html (str): directory containing HTML pages
        path_err (str): errors file
        config (nist.RequestConfig): requests additional parameters
    
    '''
    # download cycle
    for i, idx, url in tqdm(zip(df.index, df['id'], df.url), total = len(df)):
        name = i if 'inchi' in url.lower() else idx
        path_html = os.path.join(dir_html, f'{name}.html')
        try:
            download_compound_html(url, path_html, path_err, config)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            tqdm.write(f'Error: {i}: {e}')
    
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
    
    # get NIST compounds
    print('Loading compounds data ...')
    path_csv1 = os.path.join(args.dir_root, 'compounds_combined_inchi.csv')
    path_csv2 = os.path.join(args.dir_root, 'compounds_combined.csv')
    if not os.path.exists(path_csv1) or not os.path.exists(path_csv2):
        df = combine_compounds(args.dir_root)
        df1 = df.loc[df['id'].str.contains('InChI')]
        df1 = df1.sort_values('id')
        df1.to_csv(path_csv1, index=None)
        df2 = df.loc[~df['id'].str.contains('InChI')]
        df2 = df2.sort_values('id')
        df2.to_csv(path_csv2, index=None)
    df1 = pd.read_csv(path_csv1)
    df2 = pd.read_csv(path_csv2)
    
    # check html dir
    dir_html = os.path.join(args.dir_root, 'htmls')
    if not os.path.exists(dir_html):
        os.mkdir(dir_html)
    dir_html_inchi = os.path.join(args.dir_root, 'htmls_inchi')
    if not os.path.exists(dir_html_inchi):
        os.mkdir(dir_html_inchi)
    
    # check errors
    path_err = os.path.join(args.dir_root, 'download_htmls.err')
    
    # set config
    config = nist.RequestConfig(
        delay=args.crawl_delay,
        max_attempts=args.max_attempts,
        kwargs={'timeout': args.timeout}
    )
    
    # download via inchis
    print('Downloading NIST compound webpages via InChI ...')
    loaded = [int(f.replace('.html', '')) for f in os.listdir(dir_html_inchi)]
    df1 = df1.loc[~df1.index.isin(loaded)]
    download_compound_htmls(df1, dir_html_inchi, path_err, config)
    print()
    
    # download
    print('Downloading NIST compound webpages ...')
    loaded = [f.replace('.html', '') for f in os.listdir(dir_html)]
    df2 = df2.loc[~df2['id'].isin(loaded)]
    download_compound_htmls(df2, dir_html, path_err, config)
    
    return



#%% Main

if __name__ == '__main__':
    
    main()


