'''Offline tests for NistCompound behavior.'''

from pathlib import Path

import pytest

import nistchempy.compound as compound_module
import nistchempy.requests as request_module

from tests.helpers import FakeResponse, load_text, nist_response_from_html


def _compound():
    response = nist_response_from_html('compound_basic.html')
    return compound_module.compound_from_response(response)


def test_compound_from_response_builds_compound_object():
    compound = _compound()

    assert compound.ID == 'C111111'
    assert compound.name == 'Dummybenzene'
    assert compound.mol_weight == 78.11
    assert compound.mol2D is None
    assert not compound.ms_specs


def test_compound_from_response_rejects_non_compound_page():
    response = nist_response_from_html('search_results.html')

    assert compound_module.compound_from_response(response) is None


def test_get_molfile_loads_text(monkeypatch):
    compound = _compound()

    def fake_request(url, params=None, config=None):
        _ = url, params, config
        return request_module.NistResponse(
            FakeResponse(load_text(Path('text') / 'mol2d.mol'), content_type='text/plain')
        )

    monkeypatch.setattr(request_module, 'make_nist_request', fake_request)

    compound.get_mol2D()

    assert compound.mol2D.startswith('Dummy MOL')


def test_get_spectra_loads_unique_spectrum_indexes(monkeypatch):
    compound = _compound()
    calls = []

    def fake_request(url, params=None, config=None):
        _ = url, config
        calls.append(params)
        if params and 'JCAMP' in params:
            return request_module.NistResponse(
                FakeResponse(load_text(Path('text') / 'dummy.jdx'), content_type='text/plain')
            )
        return nist_response_from_html('spectra_listing.html')

    monkeypatch.setattr(request_module, 'make_nist_request', fake_request)

    compound.get_ms_spectra()

    assert len(compound.ms_specs) == 2
    assert [spec.spec_idx for spec in compound.ms_specs] == ['0', '1']
    assert calls[0] is None
    assert calls[1]['Index'] == '0'
    assert calls[2]['Index'] == '1'


def test_get_gas_chromatography_loads_tables(monkeypatch):
    compound = _compound()

    def fake_request(url, params=None, config=None):
        _ = params, config
        if 'Table=on' in url:
            return nist_response_from_html('gas_chromatography_table.html')
        return nist_response_from_html('gas_chromatography_page.html')

    monkeypatch.setattr(request_module, 'make_nist_request', fake_request)

    compound.get_gas_chromatography()

    assert len(compound.gas_chromat) == 1
    assert compound.gas_chromat[0].data.iloc[0]['Retention Index'] == '650'


def test_save_helpers_write_files(tmp_path):
    compound = _compound()
    compound.ms_specs = [compound_module.Spectrum(compound, 'MS', '0', 'dummy jdx')]
    compound.save_ms_spectra(str(tmp_path))

    output = tmp_path / 'C111111_MS_0.jdx'

    assert output.read_text() == 'dummy jdx'


def test_save_spectra_requires_existing_directory(tmp_path):
    compound = _compound()

    with pytest.raises(ValueError):
        compound.save_ms_spectra(str(tmp_path / 'missing'))


def test_get_spectrum_rejects_bad_type():
    compound = _compound()

    with pytest.raises(ValueError):
        compound.get_spectrum('BAD', '0')


def test_spectrum_and_chromatogram_repr(tmp_path):
    compound = _compound()
    spectrum = compound_module.Spectrum(compound, 'MS', '0', 'dummy jdx')
    chromat = compound_module.Chromatogram(
        compound,
        'Kovats RI',
        'non-polar',
        'isothermal',
        __import__('pandas').DataFrame({'A': [1]}),
    )

    assert 'Mass spectrum' in repr(spectrum)
    assert '1 data points' in repr(chromat)

    spectrum.save(path_dir=str(tmp_path))
    chromat.save(path_dir=str(tmp_path), index=False)

    assert (tmp_path / 'C111111_MS_0.jdx').exists()
    assert (tmp_path / 'C111111_Kovats RI_non-polar_isothermal.csv').exists()


def test_molfile_bad_dimension_and_missing_reference():
    compound = _compound()

    with pytest.raises(ValueError):
        compound.get_molfile(4)

    compound.mol_refs = {}
    compound.get_mol2D()

    assert compound.mol2D is None


def test_get_all_spectra_and_save_all_spectra(monkeypatch, tmp_path):
    compound = _compound()

    def fake_get_spectra(spec_type):
        attr = 'thz_specs' if spec_type == 'TZ' else f'{spec_type.lower()}_specs'
        setattr(
            compound,
            attr,
            [compound_module.Spectrum(compound, spec_type, '0', f'{spec_type} jdx')],
        )

    monkeypatch.setattr(compound, 'get_spectra', fake_get_spectra)

    compound.get_all_spectra()
    compound.save_all_spectra(str(tmp_path))

    assert (tmp_path / 'C111111_IR_0.jdx').read_text() == 'IR jdx'
    assert (tmp_path / 'C111111_TZ_0.jdx').read_text() == 'TZ jdx'
    assert (tmp_path / 'C111111_MS_0.jdx').read_text() == 'MS jdx'
    assert (tmp_path / 'C111111_UV_0.jdx').read_text() == 'UV jdx'


def test_get_compound_uses_inchi_url_and_id_params(monkeypatch):
    calls = []

    def fake_request(url, params=None, config=None):
        calls.append((url, params, config))
        return nist_response_from_html('compound_basic.html')

    monkeypatch.setattr(request_module, 'make_nist_request', fake_request)

    compound_module.get_compound('InChI=1S/dummy')
    compound_module.get_compound('C111111')

    assert calls[0][0].endswith('/cgi/inchi/InChI=1S/dummy')
    assert calls[0][1] == {}
    assert calls[1][1] == {'ID': 'C111111'}


def test_compound_to_record_and_to_dict():
    compound = _compound()

    record = compound.to_record()
    data = compound.to_dict()

    assert record.compound_id == 'C111111'
    assert data['ID'] == 'C111111'
    assert data['name'] == 'Dummybenzene'
    assert data['cas_rn'] == '000-00-0'


def test_compound_iter_records_includes_loaded_data(monkeypatch):
    compound = _compound()

    def fake_request(url, params=None, config=None):
        _ = params, config
        if 'Str2File' in url:
            return request_module.NistResponse(
                FakeResponse(
                    load_text(Path('text') / 'mol2d.mol'),
                    content_type='text/plain',
                    url='https://example.test/mol2d',
                )
            )
        if 'Table=on' in url:
            return nist_response_from_html('gas_chromatography_table.html')
        if 'Mask=2000' in url:
            return nist_response_from_html('gas_chromatography_page.html')
        if params and 'JCAMP' in params:
            return request_module.NistResponse(
                FakeResponse(
                    load_text(Path('text') / 'dummy.jdx'),
                    content_type='text/plain',
                    url='https://example.test/ms',
                )
            )
        return nist_response_from_html('spectra_listing.html')

    monkeypatch.setattr(request_module, 'make_nist_request', fake_request)

    compound.get_mol2D()
    compound.get_ms_spectra()
    compound.get_gas_chromatography()
    records = compound.to_records()
    record_types = [record.record_type for record in records]

    assert record_types == [
        'compound',
        'molfile',
        'spectrum',
        'spectrum',
        'gas_chromatography',
    ]
    assert records[1].source_url.endswith('Str2File=C111111')
    assert records[2].source_url == 'https://example.test/ms'


def test_spectrum_and_chromatogram_to_dict():
    compound = _compound()
    spectrum = compound_module.Spectrum(
        compound,
        'MS',
        '0',
        'dummy jdx',
        source_url='https://example.test/ms',
    )
    chromat = compound_module.Chromatogram(
        compound,
        'Kovats RI',
        'non-polar',
        'isothermal',
        __import__('pandas').DataFrame({'A': [1]}),
        source_url='https://example.test/gc',
    )

    assert spectrum.to_dict()['jdx_text'] == 'dummy jdx'
    assert chromat.to_dict()['data'][0]['A'] == 1


def test_loaders_return_loaded_objects(monkeypatch):
    compound = _compound()

    def fake_request(url, params=None, config=None):
        _ = url, config
        if params and 'JCAMP' in params:
            return request_module.NistResponse(
                FakeResponse(load_text(Path('text') / 'dummy.jdx'), content_type='text/plain')
            )
        return nist_response_from_html('spectra_listing.html')

    monkeypatch.setattr(request_module, 'make_nist_request', fake_request)

    spectra = compound.get_ms_spectra()
    all_spectra = compound.get_all_spectra()

    assert len(spectra) == 2
    assert [spec.spec_idx for spec in all_spectra['MS']] == ['0', '1']
