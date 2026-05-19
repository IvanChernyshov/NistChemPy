'''Unit tests for user-local WebBook index support.'''

import json

import pandas as pd
import pytest

import nistchempy as nist
from nistchempy.cache import resolve_index_path
from nistchempy.cli import main as cli_main
from nistchempy.index_builder import DiscoverySeed
from nistchempy.index_builder import LocalIndexBuilder


def _write_index(path):
    path.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        [
            {
                'ID': 'C71432',
                'name': 'benzene',
                'synonyms': 'benzol',
                'formula': 'C6H6',
                'mol_weight': '78.11',
                'inchi': 'InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H',
                'inchi_key': 'UHOVQNZJYSORNB-UHFFFAOYSA-N',
                'Mass spectrum (electron ionization)': (
                    '/cgi/cbook.cgi?ID=C71432&Mask=200'
                ),
            },
            {
                'ID': 'C64175',
                'name': 'ethanol',
                'synonyms': 'ethyl alcohol',
                'formula': 'C2H6O',
                'mol_weight': '46.07',
                'inchi': 'InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3',
                'inchi_key': 'LFQSCWFLJHTTHZ-UHFFFAOYSA-N',
                'Mass spectrum (electron ionization)': '',
            },
        ]
    )
    df.to_csv(path / 'index.csv', index=False)
    manifest = {
        'schema_version': 1,
        'strategy': 'local-csv',
        'capabilities': ['compound_discovery', 'section_availability'],
    }
    (path / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')


def test_resolve_index_path_prefers_explicit_path(monkeypatch, tmp_path):
    monkeypatch.setenv('NISTCHEMPY_INDEX_PATH', str(tmp_path / 'env-index'))
    assert resolve_index_path(tmp_path / 'explicit') == (
        tmp_path / 'explicit'
    ).resolve()


def test_resolve_index_path_uses_environment(monkeypatch, tmp_path):
    monkeypatch.setenv('NISTCHEMPY_INDEX_PATH', str(tmp_path / 'env-index'))
    assert resolve_index_path() == (tmp_path / 'env-index').resolve()


def test_load_local_index(tmp_path):
    _write_index(tmp_path)
    index = nist.WebBookIndex.from_cache(tmp_path)
    df = index.to_dataframe()
    assert len(df) == 2
    assert index.manifest['strategy'] == 'local-csv'
    assert index.has_capability('section_availability')
    assert df.loc[0, 'mol_weight'] == pytest.approx(78.11)


def test_load_local_index_from_csv_file(tmp_path):
    _write_index(tmp_path)
    csv_path = tmp_path / 'nist_data.csv'
    (tmp_path / 'index.csv').replace(csv_path)
    (tmp_path / 'manifest.json').unlink()

    index = nist.get_local_index(csv_path)

    assert list(index.search('benz', fields='name')['ID']) == ['C71432']
    assert index.manifest['strategy'] == 'legacy-csv'
    assert index.has_capability('compound_discovery')
    assert index.has_capability('section_availability')


def test_missing_local_index(tmp_path):
    with pytest.raises(nist.NistChemPyIndexNotFoundError):
        nist.WebBookIndex.from_cache(tmp_path / 'missing')


def test_local_index_search(tmp_path):
    _write_index(tmp_path)
    index = nist.WebBookIndex.from_cache(tmp_path)
    result = index.search('benz', fields='name')
    assert list(result['ID']) == ['C71432']


def test_local_index_section_filter(tmp_path):
    _write_index(tmp_path)
    index = nist.WebBookIndex.from_cache(tmp_path)
    result = index.filter(has_sections='Mass spectrum (electron ionization)')
    assert list(result['ID']) == ['C71432']


def test_get_local_index_convenience(tmp_path):
    _write_index(tmp_path)
    index = nist.get_local_index(tmp_path)
    assert index.get('C71432')['name'] == 'benzene'


def test_cli_status_and_search(capsys, tmp_path):
    _write_index(tmp_path)
    status = cli_main(['index', 'status', '--path', str(tmp_path)])
    assert status == 0
    assert 'Rows: 2' in capsys.readouterr().out

    search = cli_main([
        'index',
        'search',
        'benzene',
        '--path',
        str(tmp_path),
        '--format',
        'csv',
    ])
    assert search == 0
    assert 'C71432' in capsys.readouterr().out


def test_build_local_index_requires_data_terms(tmp_path):
    csv_path = tmp_path / 'source.csv'
    pd.DataFrame([{'ID': 'C71432', 'name': 'benzene'}]).to_csv(
        csv_path, index=False
    )

    with pytest.raises(nist.NistChemPyDataTermsError):
        nist.WebBookIndex.build(
            path=tmp_path / 'cache',
            source_csv=csv_path,
        )


def test_build_local_index_from_csv_writes_cache_layout(tmp_path):
    csv_path = tmp_path / 'source.csv'
    pd.DataFrame([{'ID': 'C71432', 'name': 'benzene'}]).to_csv(
        csv_path, index=False
    )

    index = nist.WebBookIndex.build(
        path=tmp_path / 'cache',
        source_csv=csv_path,
        accept_data_terms=True,
    )

    assert index.path == (tmp_path / 'cache').resolve()
    assert index.manifest['strategy'] == 'local-csv'
    assert index.manifest['row_count'] == 1
    assert index.has_capability('section_availability')
    assert (tmp_path / 'cache' / 'index.csv').exists()
    assert (tmp_path / 'cache' / 'manifest.json').exists()
    assert (tmp_path / 'cache' / 'state.jsonl').exists()


def test_cli_build_from_csv(capsys, tmp_path):
    csv_path = tmp_path / 'source.csv'
    pd.DataFrame([{'ID': 'C71432', 'name': 'benzene'}]).to_csv(
        csv_path, index=False
    )

    status = cli_main([
        'index',
        'build',
        '--path',
        str(tmp_path / 'cache'),
        '--from-csv',
        str(csv_path),
        '--accept-data-terms',
    ])

    assert status == 0
    assert 'Rows: 1' in capsys.readouterr().out
    index = nist.get_local_index(tmp_path / 'cache')
    assert list(index.search('benz', fields='name')['ID']) == ['C71432']


def test_cli_build_without_source_is_unavailable(capsys, tmp_path):
    status = cli_main([
        'index',
        'build',
        '--path',
        str(tmp_path / 'cache'),
        '--accept-data-terms',
    ])

    assert status == 2
    assert 'Network-based local index discovery and enrichment are not implemented' in (
        capsys.readouterr().err
    )


def test_local_index_builder_writes_discovery_seeds(tmp_path):
    builder = LocalIndexBuilder(
        path=tmp_path / 'cache',
        strategy='formula-browser',
        accept_data_terms=True,
    )

    seeds = builder.write_seeds([
        DiscoverySeed(
            lookup_key='C71432',
            lookup_url='/cgi/cbook.cgi?ID=C71432',
            webbook_id='C71432',
            name_hint='benzene',
            formula_hint='C6H6',
            source='formula-browser',
            source_query='C6H6',
        )
    ])

    assert list(seeds['webbook_id']) == ['C71432']
    assert (tmp_path / 'cache' / 'seeds.csv').exists()
    assert (tmp_path / 'cache' / 'manifest.json').exists()
    manifest = json.loads(
        (tmp_path / 'cache' / 'manifest.json').read_text(encoding='utf-8')
    )
    assert manifest['artifact'] == 'seeds'
    assert manifest['strategy'] == 'formula-browser'
    assert manifest['seed_count'] == 1


def test_cli_status_reports_discovery_seeds(capsys, tmp_path):
    builder = LocalIndexBuilder(
        path=tmp_path / 'cache',
        strategy='formula-browser',
        accept_data_terms=True,
    )
    builder.write_seeds([DiscoverySeed(lookup_key='C71432')])

    status = cli_main([
        'index',
        'status',
        '--path',
        str(tmp_path / 'cache'),
    ])

    assert status == 0
    output = capsys.readouterr().out
    assert 'Final index: missing' in output
    assert 'Seed rows: 1' in output



class _FakeResponse:
    def __init__(self, html):
        from bs4 import BeautifulSoup
        self.ok = True
        self.text = html
        self.soup = BeautifulSoup(html, features='html.parser')


def test_parse_formula_browser_page_extracts_prefixes_and_seeds():
    from nistchempy.discovery import parse_formula_browser_page

    html = '''
    <html><body><ul>
      <li><a href="/cgi/formula/C">C______</a> (10 species)</li>
      <li><a href="/cgi/formula?ID=C71432">C 6 H 6</a> (benzene)</li>
      <li><a href="/cgi/inchi/InChI%3D1S/CH4/h1H4">CH 4</a> (methane)</li>
      <li><a href="/cgi/cbook.cgi?ID=C64175">C 2 H 6 O</a> (ethanol)</li>
    </ul></body></html>
    '''

    page = parse_formula_browser_page(
        html, page_url='https://webbook.nist.gov/cgi/formula/'
    )

    assert page.prefix_urls == ['https://webbook.nist.gov/cgi/formula/C']
    assert [seed['webbook_id'] for seed in page.seeds] == [
        'C71432',
        '',
        'C64175',
    ]
    assert [seed['name_hint'] for seed in page.seeds] == [
        'benzene',
        'methane',
        'ethanol',
    ]


def test_formula_browser_discovery_traverses_prefix_pages():
    from nistchempy.discovery import discover_formula_browser

    pages = {
        'https://webbook.nist.gov/cgi/formula/': '''
            <ul>
              <li><a href="/cgi/formula/C">C______</a> (10 species)</li>
            </ul>
        ''',
        'https://webbook.nist.gov/cgi/formula/C': '''
            <ul>
              <li><a href="/cgi/formula?ID=C71432">C 6 H 6</a> (benzene)</li>
              <li><a href="/cgi/formula?ID=C64175">C 2 H 6 O</a> (ethanol)</li>
            </ul>
        ''',
    }

    def fake_request(url, config=None):
        _ = config
        return _FakeResponse(pages[url])

    seeds = discover_formula_browser(request_func=fake_request)

    assert [seed['webbook_id'] for seed in seeds] == ['C71432', 'C64175']


def test_cli_discover_writes_formula_browser_seeds(capsys, monkeypatch, tmp_path):
    from nistchempy import discovery as discovery_module

    def fake_discover_formula_browser(**kwargs):
        _ = kwargs
        return [
            {
                'lookup_key': 'C71432',
                'lookup_url': 'https://webbook.nist.gov/cgi/formula?ID=C71432',
                'webbook_id': 'C71432',
                'name_hint': 'benzene',
                'formula_hint': 'C 6 H 6',
                'source': 'formula-browser',
                'source_query': 'C',
                'needs_page_enrichment': True,
            }
        ]

    monkeypatch.setattr(
        discovery_module,
        'discover_formula_browser',
        fake_discover_formula_browser,
    )

    status = cli_main([
        'index',
        'discover',
        '--path',
        str(tmp_path / 'cache'),
        '--strategy',
        'formula-browser',
        '--limit',
        '1',
        '--max-pages',
        '2',
        '--accept-data-terms',
    ])

    assert status == 0
    assert 'Seed rows: 1' in capsys.readouterr().out
    seeds_path = tmp_path / 'cache' / 'seeds.csv'
    assert seeds_path.exists()
    seeds = pd.read_csv(seeds_path, dtype='str')
    assert list(seeds['webbook_id']) == ['C71432']


def _compound_page_html(compound_id='C71432', name='Benzene'):
    return f'''
    <html><body>
      <!-- /cgi/cbook.cgi?Form={compound_id}&Units=SI -->
      <h1 id="Top">{name}</h1>
      <ul>
        <li>Formula: C6H6</li>
        <li>Molecular weight: 78.11</li>
        <li>Other names:
          benzol;
          cyclohexatriene;
        </li>
        <li>CAS Registry Number: 71-43-2</li>
        <li><span>InChI:</span>
          <span class="inchi-text">InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H</span>
        </li>
        <li><span>InChIKey:</span>
          <span class="inchi-text">UHOVQNZJYSORNB-UHFFFAOYSA-N</span>
        </li>
        <li><a href="/cgi/cbook.cgi?Str2File={compound_id}">2D</a></li>
        <li><a href="/cgi/cbook.cgi?Str3File={compound_id}">3D</a></li>
        <li>Other data available:
          <ul>
            <li>
              <a href="/cgi/cbook.cgi?ID={compound_id}&Mask=200">
                Mass spectrum
              </a>
            </li>
            <li>
              <a href="/cgi/cbook.cgi?ID={compound_id}&Mask=800">
                Energy levels
              </a>
            </li>
          </ul>
        </li>
      </ul>
    </body></html>
    '''


def test_resolve_seed_url_supports_url_and_webbook_id():
    from nistchempy.index_builder import resolve_seed_url

    assert resolve_seed_url({'lookup_url': '/cgi/cbook.cgi?ID=C71432'}) == (
        'https://webbook.nist.gov/cgi/cbook.cgi?ID=C71432'
    )
    assert resolve_seed_url({'webbook_id': 'C71432'}) == (
        'https://webbook.nist.gov/cgi/cbook.cgi?ID=C71432'
    )


def test_flatten_compound_info_keeps_cas_and_renames_data_refs():
    from bs4 import BeautifulSoup
    from nistchempy.index_builder import flatten_compound_info
    from nistchempy.parsing import parse_compound_page

    soup = BeautifulSoup(_compound_page_html(), features='html.parser')
    row = flatten_compound_info(parse_compound_page(soup))

    assert row['ID'] == 'C71432'
    assert row['name'] == 'Benzene'
    assert row['cas_rn'] == '71-43-2'
    assert 'benzol' in row['synonyms']
    assert row['Mass spectrum (electron ionization)'].endswith('Mask=200')
    assert row['Vibrational and/or electronic energy levels'].endswith(
        'Mask=800'
    )
    assert row['mol2D'].endswith('Str2File=C71432')
    assert row['mol3D'].endswith('Str3File=C71432')


def test_enrich_from_seeds_writes_final_index(tmp_path):
    builder = LocalIndexBuilder(
        path=tmp_path / 'cache',
        strategy='formula-browser',
        include_cas=True,
        accept_data_terms=True,
    )
    builder.write_seeds([
        DiscoverySeed(
            lookup_key='C71432',
            lookup_url='/cgi/cbook.cgi?ID=C71432',
            webbook_id='C71432',
        )
    ])

    def fake_request(url, config=None):
        _ = url, config
        return _FakeResponse(_compound_page_html())

    index = builder.enrich_from_seeds(request_func=fake_request)

    assert list(index.data['ID']) == ['C71432']
    assert index.data.loc[0, 'cas_rn'] == '71-43-2'
    assert 'Mass spectrum (electron ionization)' in index.data.columns
    assert (tmp_path / 'cache' / 'index.csv').exists()
    assert (tmp_path / 'cache' / 'index.partial.jsonl').exists()
    manifest = json.loads(
        (tmp_path / 'cache' / 'manifest.json').read_text(encoding='utf-8')
    )
    assert manifest['artifact'] == 'index'
    assert manifest['include_cas'] is True
    assert manifest['row_count'] == 1


def test_enrich_from_seeds_logs_bad_seed_and_continues(tmp_path):
    builder = LocalIndexBuilder(
        path=tmp_path / 'cache',
        strategy='formula-browser',
        accept_data_terms=True,
    )
    builder.write_seeds([
        DiscoverySeed(lookup_key='bad-seed'),
        DiscoverySeed(
            lookup_key='C71432',
            lookup_url='/cgi/cbook.cgi?ID=C71432',
            webbook_id='C71432',
        ),
    ])

    def fake_request(url, config=None):
        _ = url, config
        return _FakeResponse(_compound_page_html())

    index = builder.enrich_from_seeds(request_func=fake_request)

    assert list(index.data['ID']) == ['C71432']
    errors = (tmp_path / 'cache' / 'errors.jsonl').read_text(encoding='utf-8')
    assert 'neither lookup_url nor webbook_id' in errors


def test_cli_enrich_from_seeds(capsys, monkeypatch, tmp_path):
    import nistchempy.index_builder as builder_module

    builder = LocalIndexBuilder(
        path=tmp_path / 'cache',
        strategy='formula-browser',
        accept_data_terms=True,
    )
    builder.write_seeds([
        DiscoverySeed(
            lookup_key='C71432',
            lookup_url='/cgi/cbook.cgi?ID=C71432',
            webbook_id='C71432',
        )
    ])

    original = builder_module.LocalIndexBuilder.enrich_from_seeds

    def fake_enrich(self, **kwargs):
        kwargs['request_func'] = lambda url, config=None: _FakeResponse(
            _compound_page_html()
        )
        return original(self, **kwargs)

    monkeypatch.setattr(
        builder_module.LocalIndexBuilder,
        'enrich_from_seeds',
        fake_enrich,
    )

    status = cli_main([
        'index',
        'enrich',
        '--path',
        str(tmp_path / 'cache'),
        '--accept-data-terms',
    ])

    assert status == 0
    assert 'Rows: 1' in capsys.readouterr().out
    index = nist.get_local_index(tmp_path / 'cache')
    assert index.get('C71432')['cas_rn'] == '71-43-2'
