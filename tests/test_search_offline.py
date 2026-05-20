'''Offline tests for search response parsing.'''

import nistchempy.search as search_module
import nistchempy.requests as request_module

from tests.helpers import nist_response_from_html


def _params():
    return search_module.NistSearchParameters()


def _config():
    return request_module.RequestConfig()


def test_search_from_response_parses_result_ids():
    response = nist_response_from_html('search_results.html')

    result = search_module.search_from_response(response, _params(), _config())

    assert result.success
    assert not result.lost
    assert result.compound_ids == ['C111111', 'C222222']
    assert result.num_compounds == 2


def test_search_from_response_parses_lost_results():
    response = nist_response_from_html('search_lost.html')

    result = search_module.search_from_response(response, _params(), _config())

    assert result.success
    assert result.lost
    assert result.compound_ids == ['C111111']


def test_search_from_response_detects_error_page():
    response = nist_response_from_html('search_not_found.html')

    result = search_module.search_from_response(response, _params(), _config())

    assert not result.success
    assert not result.compound_ids
    assert result.message == 'Name Not Found'


def test_search_from_response_parses_direct_compound_page():
    response = nist_response_from_html('compound_basic.html')

    result = search_module.search_from_response(response, _params(), _config())

    assert result.success
    assert result.compound_ids == ['C111111']
    assert result.compounds[0].name == 'Dummybenzene'


def test_failed_search_request_is_unsuccessful():
    response = nist_response_from_html('search_results.html', ok=False)

    result = search_module.search_from_response(response, _params(), _config())

    assert not result.success
    assert result.message == 'Search request failed.'


def test_run_search_builds_expected_get_parameters(monkeypatch):
    calls = []

    def fake_request(url, params=None, config=None):
        calls.append((url, params, config))
        return nist_response_from_html('search_results.html')

    monkeypatch.setattr(search_module._ncpr, 'make_nist_request', fake_request)

    result = search_module.run_search(
        'C6H6', 'formula', allow_other=True, cMS=True, use_SI=False
    )

    assert result.compound_ids == ['C111111', 'C222222']
    assert calls[0][1]['Formula'] == 'C6H6'
    assert calls[0][1]['Units'] == 'CAL'
    assert calls[0][1]['AllowOther'] == 'on'
    assert calls[0][1]['cMS'] == 'on'


def test_run_search_ignores_formula_options_for_name_search(monkeypatch):
    calls = []

    def fake_request(url, params=None, config=None):
        calls.append(params)
        return nist_response_from_html('search_results.html')

    monkeypatch.setattr(search_module._ncpr, 'make_nist_request', fake_request)

    search_module.run_search('dummy', 'name', allow_other=True)

    assert calls[0]['Name'] == 'dummy'
    assert 'AllowOther' not in calls[0]


def test_run_search_rejects_bad_search_type():
    import pytest

    with pytest.raises(ValueError):
        search_module.run_search('dummy', 'bad')


def test_run_structural_search_posts_molblock(monkeypatch):
    calls = []

    def fake_post(url, data=None, files=None, config=None):
        calls.append((url, data, files, config))
        return nist_response_from_html('search_results.html')

    monkeypatch.setattr(search_module._ncpr, 'make_nist_post_request', fake_post)

    result = search_module.run_structural_search(
        molblock='dummy molblock', search_type='sub', cGC=True
    )

    assert result.compound_ids == ['C111111', 'C222222']
    assert calls[0][1]['Type'] == 'Sub'
    assert calls[0][1]['cGC'] == 'on'
    assert 'MolFile' in calls[0][2]


def test_run_structural_search_rejects_missing_structure():
    import pytest

    with pytest.raises(ValueError):
        search_module.run_structural_search(search_type='sub')
    with pytest.raises(ValueError):
        search_module.run_structural_search(molblock='dummy', search_type='bad')
