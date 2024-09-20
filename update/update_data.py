'''Loads info on NIST Chemistry WebBook compounds'''

#%% Imports

import os, sys
sys.path = [os.getcwd() + '../'] + sys.path

import gzip, shutil, time
from tqdm import tqdm

from urllib.robotparser import RobotFileParser
from urllib.request import urlopen, urlretrieve
from urllib.parse import unquote, urlparse, parse_qs
from urllib.error import HTTPError

from bs4 import BeautifulSoup

import pandas as pd

import nistchempy as nist


#%% List of compounds

def donwload_nist_sitemaps(dir_data: str = 'data/') -> None:
    '''Downloads sitemaps from NIST Chemistry WebBook
    
    Arguments:
        dir_data (str): directory for robots.txt and primary sitemap
    
    '''
    dir_xmls = os.path.join(dir_data, 'sitemaps')
    # create dirs
    for path in (dir_data, dir_xmls):
        if not os.path.exists(path):
            os.mkdir(path)
    # save robots.txt
    ROBOTS_URL = nist.requests.BASE_URL + '/robots.txt'
    with open(os.path.join(dir_data, 'robots.txt'), 'w') as outf:
        text = urlopen(ROBOTS_URL).read().decode('utf-8')
        outf.write(text)
    # save initial sitemap
    robots = RobotFileParser(nist.requests.BASE_URL + '/robots.txt')
    robots.read()
    url = robots.site_maps()[0]
    fname = urlparse(url).path.split('/')[-1]
    text = urlopen(url).read().decode('utf-8')
    with open(os.path.join(dir_data, fname), 'w') as outf:
        outf.write(text)
    # download actual sitemaps
    xml = BeautifulSoup(text, 'xml')
    for item in xml.findAll('sitemap'):
        url = item.loc.text
        fname = urlparse(url).path.split('/')[-1]
        urlretrieve(url, os.path.join(dir_xmls, fname))
    # unzip archives
    for f in os.listdir(dir_xmls):
        f = os.path.join(dir_xmls, f)
        with gzip.open(f, 'rb') as inpf:
            with open(f.replace('.gz', ''), 'wb') as outf:
                shutil.copyfileobj(inpf, outf)
    # remove gzips
    for f in os.listdir(dir_xmls):
        f = os.path.join(dir_xmls, f)
        if f[-3:] != '.gz':
            continue
        os.remove(f)
    
    return



def is_compound_url(url: str) -> bool:
    ''' '''
    
    return 'cgi/inchi' in url or 'cgi/cbook.cgi?ID' in url



def get_compound_id(url: str) -> str:
    '''Extracts compound ID from NIST compound URL'''
    if 'cgi/cbook.cgi?ID' in url:
        ID = parse_qs(urlparse(url).query)['ID'][0]
    else:
        ID = urlparse(url).path.replace('/cgi/inchi/', '')
    
    return ID



def get_nist_compounds_list(dir_data: str = 'data/') -> None:
    '''Extracts NIST compounds from sitemap files
    
    Arguments:
        dir_data (str): directory for robots.txt and primary sitemap
    
    '''
    dir_xmls = os.path.join(dir_data, 'sitemaps')
    path_csv = os.path.join(dir_data, 'compounds.csv')
    # get compound urls
    urls = []
    for f in os.listdir(dir_xmls):
        # parse file
        with open(os.path.join(dir_xmls, f), 'r') as inpf:
            text = inpf.read()
        soup = BeautifulSoup(text, 'xml')
        # get urls
        add = [unquote(item.loc.text) for item in soup.findAll('url')]
        add = [url for url in add if is_compound_url(url)]
        urls += add
    # extract compound IDs
    IDs = [get_compound_id(url) for url in urls]
    # save as dataframe
    df = pd.DataFrame({'id': IDs, 'url': urls})
    df.to_csv(path_csv, index = None)
    
    return


def read_compounds(dir_data: str = 'data/') -> pd.core.frame.DataFrame:
    '''Reads compounds.csv or generate it loading info from WebBook's sitemap
    
    Arguments:
        dir_data (str): directory for robots.txt and primary sitemap
    
    Returns:
        pd.core.frame.DataFrame: [ id / url ] dataframe
    
    '''
    path_csv = os.path.join(dir_data, 'compounds.csv')
    # get list of compounds
    if not os.path.exists(path_csv):
        print('Downloading NIST Chemistry WebBook sitemaps ...')
        donwload_nist_sitemaps(dir_data)
        print('Extracting NIST compound list ...')
        get_nist_compounds_list(dir_data)
    # read csv
    print('Reading NIST compound list ...')
    df = pd.read_csv(path_csv)
    
    return df



#%% Loading compounds

def download_compound_htmls(df: pd.core.frame.DataFrame,
                            dir_data: str = 'data/',
                            crawl_delay: int = 5) -> None:
    '''Main function for updating the list of NIST compounds
    
    Arguments:
        df (pd.core.frame.DataFrame): compounds' [ id / url ] dataframe
        dir_data (str): directory for robots.txt and primary sitemap
    
    '''
    print('Downloading NIST compound webpages ...')
    # prepare dir
    dir_html = os.path.join(dir_data, 'htmls')
    if not os.path.exists(dir_html):
        os.mkdir(dir_html)
    # get loaded systems
    loaded = [int(f.replace('.html', '')) for f in os.listdir(dir_html)]
    df = df.loc[~df.index.isin(loaded)]
    # download htmls
    for i, url in tqdm(zip(df.index, df.url), total = len(df)):
        path_html = os.path.join(dir_html, f'{i}.html')
        n_errs = 0
        while n_errs < 3:
            try:
                urlretrieve(url, path_html)
                time.sleep(crawl_delay)
                break
            except HTTPError:
                n_errs += 1
                time.sleep(10*crawl_delay)
    
    return



#%% Main function

def main(dir_data: str = 'data/', crawl_delay = 5) -> None:
    '''Main function for updating the list of NIST compounds via downloaded HTML pages
    
    Arguments:
        dir_data (str): directory for robots.txt and primary sitemap
    
    '''
    df = read_compounds(dir_data)
    download_compound_htmls(df, dir_data, crawl_delay)
    
    
    
    return



#%% Main

if __name__ == '__main__':
    
    # parameters
    dir_data = 'D:/wd/NIST' # 'data/'
    crawl_delay = 4
    
    # run update
    main(dir_data, crawl_delay)


