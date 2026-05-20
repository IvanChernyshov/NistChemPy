'''Tests for utility helpers.'''

import pytest

from nistchempy import utils


class DummyResponse:
    def __init__(self, text, ok=True):
        self.text = text
        self.ok = ok


def test_safe_filename_replaces_unsafe_characters():
    assert utils.safe_filename('a/b:c?.csv') == 'a_b_c_.csv'


def test_safe_filename_collapses_empty_names():
    assert utils.safe_filename('   .  ') == 'file'


def test_get_crawl_delay(monkeypatch):
    def fake_request(url, config=None):
        _ = url, config
        return DummyResponse('User-agent: *\nCrawl-delay: 7\n')

    monkeypatch.setattr(utils._requests, 'make_nist_request', fake_request)

    assert utils.get_crawl_delay() == 7


def test_get_crawl_delay_raises_on_bad_response(monkeypatch):
    def fake_request(url, config=None):
        _ = url, config
        return DummyResponse('bad', ok=False)

    monkeypatch.setattr(utils._requests, 'make_nist_request', fake_request)

    with pytest.raises(ConnectionError):
        utils.get_crawl_delay()
