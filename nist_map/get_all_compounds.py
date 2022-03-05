'''
Python API for NIST Chemistry WebBook
'''

#%% Imports

import re, os, requests
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup


#%% Get NIST Chemistry WebBook site map



