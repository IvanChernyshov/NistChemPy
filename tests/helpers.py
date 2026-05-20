'''Shared test helpers for offline NistChemPy tests.'''

from pathlib import Path

import bs4

import nistchempy.requests as requests_module


FIXTURE_DIR = Path(__file__).parent / 'fixtures'
HTML_DIR = FIXTURE_DIR / 'html'
TEXT_DIR = FIXTURE_DIR / 'text'


class FakeResponse:
    '''Small requests.Response-like object for offline tests.'''

    def __init__(self, text='', ok=True, content_type='text/html'):
        self.text = text
        self.ok = ok
        self.headers = {}
        if content_type is not None:
            self.headers['content-type'] = content_type


def load_text(relative_path):
    '''Load a fixture text file.'''
    return (FIXTURE_DIR / relative_path).read_text()


def load_html(name):
    '''Load an HTML fixture file.'''
    return load_text(Path('html') / name)


def soup_from_fixture(name):
    '''Load an HTML fixture as BeautifulSoup.'''
    return bs4.BeautifulSoup(load_html(name), features='html.parser')


def nist_response_from_html(name, ok=True):
    '''Create a NistResponse from an HTML fixture.'''
    return requests_module.NistResponse(FakeResponse(load_html(name), ok=ok))
