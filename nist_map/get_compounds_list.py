'''
Downloads list of all NIST Chemistry WebBook compounds from sitemap
'''

#%% Imports

import requests, gzip, json
from urllib import robotparser
from bs4 import BeautifulSoup


#%% Get NIST Chemistry WebBook site map

# get sitemap ref
rp = robotparser.RobotFileParser('https://webbook.nist.gov/robots.txt')
rp.read()
ref = rp.sitemaps[0]

# get sitemap xmls
r = requests.get(ref)
if not r.ok:
    raise 'Sitemap was not read'
soup = BeautifulSoup(r.text, features = 'html.parser')
sm_refs = [sm.findChild('loc').text for sm in soup.findChildren('sitemap')]

# get links
refs = []
for sm_ref in sm_refs:
    r = requests.get(sm_ref, stream = True)
    if not r.ok:
        raise 'Sitemap XML was not read'
    with gzip.open(r.raw, 'rb') as inpf:
        soup = BeautifulSoup(inpf.read(), features = 'html.parser')
    refs += [_.text for _ in soup.findChildren('loc')]

# get compounds IDs and InChIs
IDs = [ref.split('=')[-1] for ref in refs if 'ID=' in ref]
inchis = [ref.split('inchi/')[-1] for ref in refs if 'inchi/' in ref]

# save as json
with open('data/compounds.json', 'w') as outf:
    json.dump({'ID': IDs, 'inchi': inchis}, outf)


