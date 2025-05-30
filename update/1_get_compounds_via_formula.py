'''Makes chemical formula searches over NIST Chemistry WebBook to get all
available compounds, including those ones missing in the sitemaps'''

#%% Imports

import os, argparse

import pandas as pd

import nistchempy as nist


#%% Elements

ELEMS = [
    'He', 'Li', 'Be', 'B', 'N', 'O', 'F', 'Ne', 'Na', 'Mg',
    'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti',
    'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge',
    'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo',
    'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te',
    'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm',
    'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf',
    'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb',
    'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U',
    'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No',
    'Lr', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn',
    'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og'
]


#%% Functions

def run_search(formula, params, config, max_errors=3):
    '''Wrapper for NIST formula search'''
    err = 0
    while err < max_errors:
        try:
            res = nist.run_search(formula, 'formula', params, config)
            return res
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            print('error')
            err += 1
            continue
    
    raise None


def scan_formulas(nC: int, IDs: set, crawl_delay: float = 5.0,
                  max_attempts: int = 3, timeout: float = 30.0) -> None:
    '''Updates compound IDs with loaded chemical formulas
    
    Arguments:
        nC (int): number of carbons in formula
        IDs (set): set of found compound IDs
        crawl_delay (float): interval between HTTP requests, seconds
        max_attempts (int): number of max attempts to get server response
        timeout (float): max allowed server response time, seconds
    
    '''
    # search settings
    config = nist.RequestConfig(delay=crawl_delay, max_attempts=max_attempts,
                                kwargs={'timeout': timeout})
    params = nist.NistSearchParameters(allow_other=True, no_ion=True)
    # direct check
    res = nist.run_search(f'C{nC}', 'formula', params, config)
    if not res.success:
        print(f'C{nC} :(')
        return
    else:
        IDs.update(res.compound_ids)
        print(f'C{nC}')
        if not res.lost:
            return
    # check via other elements
    for nH in range(150):
        # direct formula
        res = nist.run_search(f'C{nC}H{nH}', 'formula', params, config)
        if not res.success:
            print(f'C{nC}H{nH} :(')
            continue
        else:
            IDs.update(res.compound_ids)
            print(f'C{nC}H{nH}')
            if not res.lost:
                continue
        # add other elems
        for elem in ELEMS:
            # direct formula
            res = nist.run_search(f'C{nC}H{nH}{elem}?', 'formula', params, config)
            if not res.success:
                print(f'C{nC}H{nH}{elem}? :(')
                continue
            else:
                IDs.update(res.compound_ids)
                print(f'C{nC}H{nH}{elem}?')
                if not res.lost:
                    continue
            # counts
            for nX in range(1, 51):
                res = nist.run_search(f'C{nC}H{nH}{elem}{nX}', 'formula',
                                      params, config)
                if not res.success:
                    print(f'C{nC}H{nH}{elem}{nX} :(')
                    continue
                else:
                    IDs.update(res.compound_ids)
                    print(f'C{nC}H{nH}{elem}{nX}')
                    if res.lost:
                        print('Lost :(')
    
    return



#%% Main functions

def get_arguments() -> argparse.Namespace:
    '''CLI wrapper
    
    Returns:
        argparse.Namespace: CLI arguments
    
    '''
    parser = argparse.ArgumentParser(description = 'Searches for carbon-containing compounds of NIST Chemistry WebBook')
    parser.add_argument('path_compounds',
                        help = 'text file containing list of found compounds')
    parser.add_argument('start_count', type = int,
                        help = 'start number of carbon atoms in chemical formula')
    parser.add_argument('end_count', type = int,
                        help = 'end number of carbon atoms in chemical formula')
    parser.add_argument('--crawl-delay', type = float, default = 1.0,
                        help = 'pause between HTTP requests, seconds')
    parser.add_argument('--max-attempts', type = int, default = 3,
                        help = 'max timeout for server response, seconds')
    parser.add_argument('--timeout', type = float, default = 30.0,
                        help = 'max timeout for server response, seconds')
    args = parser.parse_args()
    
    return args


def check_arguments(args: argparse.Namespace) -> None:
    '''Tries to create dir_data if it does not exist and raizes error if dir_data is a file
    
    Arguments:
        args (argparse.Namespace): input parameters
    
    '''
    
    # check compound list file
    if not os.path.exists(args.path_compounds):
        df = pd.DataFrame({'id': [], 'url': []})
        df.to_csv(args.path_compounds, index=None)
    
    # check carbon counts
    if args.start_count < 0:
        raise ValueError(f'start_count must be positive integer: {args.start_count}')
    if args.end_count < 0:
        raise ValueError(f'end_count must be positive integer: {args.end_count}')
    
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
    
    # load compounds
    df = pd.read_csv(args.path_compounds)
    IDs = set(df['id'])
    
    # scan formulas
    for nC in range(args.start_count, args.end_count + 1):
        scan_formulas(nC, IDs, args.crawl_delay, args.timeout)
        # save updated IDs
        idxs = sorted(list(IDs))
        df = pd.DataFrame({
            'id': idxs,
            'url': [f'{nist.requests.SEARCH_URL}?ID={idx}' for idx in idxs]
        })
        df.to_csv(args.path_compounds, index=None)
    
    return



#%% Main

if __name__ == '__main__':
    
    main()


