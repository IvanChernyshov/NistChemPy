'''Downloads NIST Chemistry WebBook sitemaps and extracts all compounds'''

#%% Imports

import os, shutil, gzip
import argparse

from urllib.robotparser import RobotFileParser
from urllib.request import urlopen, urlretrieve
from urllib.parse import unquote, urlparse, parse_qs

from bs4 import BeautifulSoup

import pandas as pd

import nistchempy as nist


#%% Functions

def donwload_nist_sitemaps(dir_data: str) -> None:
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



def get_nist_compounds_list(dir_data: str) -> None:
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


#%% Main functions

def get_arguments() -> argparse.Namespace:
    '''CLI wrapper
    
    Returns:
        argparse.Namespace: CLI arguments
    
    '''
    parser = argparse.ArgumentParser(description = 'Loads list of NIST Chemistry WebBook compounds to the given directory')
    parser.add_argument('dir_data', help = 'directory to save downloaded and extracted info on NIST compounds')
    args = parser.parse_args()
    
    return args


def check_arguments(args: argparse.Namespace) -> None:
    '''Tries to create dir_data if it does not exist and raizes error if dir_data is a file
    
    Arguments:
        args (argparse.Namespace): input parameters
    
    '''
    if not os.path.exists(args.dir_data):
        os.mkdir(args.dir_data) # FilexExistsError / FileNotFoundError
    if not os.path.isdir(args.dir_data):
        raise ValueError(f'Given dir_data argument is not a directory: {args.dir_data}')
    
    return


def main() -> None:
    '''Extracts info on NIST Chemistry WebBook compounds and saves to csv file'''
    # prepare arguments
    args = get_arguments()
    check_arguments(args)
    path_csv = os.path.join(args.dir_data, 'compounds.csv')
    # get list of compounds
    if not os.path.exists(path_csv):
        print('Downloading NIST Chemistry WebBook sitemaps ...')
        donwload_nist_sitemaps(args.dir_data)
        print('Extracting NIST compound list ...')
        get_nist_compounds_list(args.dir_data)
    
    return



#%% Main

if __name__ == '__main__':
    
    main()


