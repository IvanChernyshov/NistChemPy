'''Offline tests for request wrappers.'''

import pytest

import nistchempy.requests as request_module

from tests.helpers import FakeResponse


def test_request_config_validates_delay_and_attempts():
    cfg = request_module.RequestConfig(delay='1.5', max_attempts=2)

    assert cfg.delay == 1.5
    assert cfg.max_attempts == 2
    assert cfg.kwargs['timeout'] == 30.0

    with pytest.raises(ValueError):
        request_module.RequestConfig(delay='bad')
    with pytest.raises(ValueError):
        request_module.RequestConfig(delay=-1)
    with pytest.raises(ValueError):
        request_module.RequestConfig(max_attempts=0)
    with pytest.raises(ValueError):
        request_module.RequestConfig(max_attempts=1.5)
    with pytest.raises(ValueError):
        request_module.RequestConfig(max_attempts=True)
    with pytest.raises(TypeError):
        request_module.RequestConfig(kwargs='bad')


def test_request_config_copies_kwargs_and_removes_params():
    kwargs = {'timeout': 5, 'params': {'bad': 'value'}}

    cfg = request_module.RequestConfig(kwargs=kwargs)

    assert cfg.kwargs == {'timeout': 5}
    assert kwargs == {'timeout': 5, 'params': {'bad': 'value'}}


def test_nist_response_parses_html_and_handles_missing_content_type():
    html = '<html><body clss="x">Dummy&nbsp;text</body></html>'

    html_response = request_module.NistResponse(FakeResponse(html))
    no_content_type = request_module.NistResponse(
        FakeResponse('plain text', content_type=None)
    )

    assert html_response.ok
    assert html_response.soup is not None
    assert 'class=' in html_response.text
    assert no_content_type.soup is None
    assert no_content_type.text == 'plain text'


def test_make_nist_request_uses_params_and_retries(monkeypatch):
    calls = []

    def fake_get(url, params=None, **kwargs):
        calls.append((url, params, kwargs))
        if len(calls) == 1:
            raise RuntimeError('temporary failure')
        return FakeResponse('<html><body>ok</body></html>')

    monkeypatch.setattr(request_module._requests, 'get', fake_get)
    monkeypatch.setattr(request_module._time, 'sleep', lambda delay: None)

    cfg = request_module.RequestConfig(max_attempts=2, kwargs={'timeout': 5})
    response = request_module.make_nist_request(
        'https://example.test', {'ID': 'C111111'}, cfg
    )

    assert response.ok
    assert len(calls) == 2
    assert calls[1][1] == {'ID': 'C111111'}
    assert calls[1][2]['timeout'] == 5


def test_make_nist_post_request_passes_payload(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse('<html><body>ok</body></html>')

    monkeypatch.setattr(request_module._requests, 'post', fake_post)
    monkeypatch.setattr(request_module._time, 'sleep', lambda delay: None)

    cfg = request_module.RequestConfig(kwargs={'timeout': 7})
    response = request_module.make_nist_post_request(
        'https://example.test',
        data={'x': '1'},
        files={'file': object()},
        config=cfg,
    )

    assert response.ok
    assert calls[0][1]['data'] == {'x': '1'}
    assert calls[0][1]['json'] is None
    assert 'files' in calls[0][1]
    assert calls[0][1]['timeout'] == 7
