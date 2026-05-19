'''Tests for release artifact safety checks.'''

import importlib.util
import tarfile
import zipfile
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / 'tools'
CHECK_SCRIPT = TOOLS_DIR / 'check_package_artifacts.py'

spec = importlib.util.spec_from_file_location(
    'check_package_artifacts', CHECK_SCRIPT
)
check_package_artifacts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_package_artifacts)


def test_forbidden_artifact_name_detection():
    assert check_package_artifacts.is_forbidden_artifact_name(
        'nistchempy/data/nist_data.zip'
    )
    assert check_package_artifacts.is_forbidden_artifact_name(
        'pkg/src/nistchempy/data/nist_data.csv'
    )
    assert check_package_artifacts.is_forbidden_artifact_name(
        'compound_htmls/C71432.html'
    )
    assert not check_package_artifacts.is_forbidden_artifact_name(
        'nistchempy/index.py'
    )


def test_artifact_check_accepts_clean_zip(tmp_path):
    archive_path = tmp_path / 'clean.whl'
    with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.writestr('nistchempy/index.py', '# clean package file\n')

    findings = check_package_artifacts.find_forbidden_artifacts([archive_path])

    assert findings == []


def test_artifact_check_rejects_bundled_index_in_zip(tmp_path):
    archive_path = tmp_path / 'dirty.whl'
    with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.writestr('nistchempy/data/nist_data.zip', 'payload')

    findings = check_package_artifacts.find_forbidden_artifacts([archive_path])

    assert findings == [(str(archive_path), 'nistchempy/data/nist_data.zip')]


def test_artifact_check_rejects_bundled_index_in_sdist(tmp_path):
    archive_path = tmp_path / 'dirty.tar.gz'
    payload_path = tmp_path / 'nist_data.csv'
    payload_path.write_text('ID,name\nC71432,benzene\n', encoding='utf-8')
    with tarfile.open(archive_path, 'w:gz') as archive:
        archive.add(
            payload_path,
            arcname='nistchempy-1.0.6/src/nistchempy/data/nist_data.csv',
        )

    findings = check_package_artifacts.find_forbidden_artifacts([archive_path])

    assert findings == [
        (
            str(archive_path),
            'nistchempy-1.0.6/src/nistchempy/data/nist_data.csv',
        )
    ]


def test_artifact_check_cli_returns_error_for_dirty_archive(tmp_path):
    archive_path = tmp_path / 'dirty.whl'
    with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.writestr('compounds_data.json', '{}')

    status = check_package_artifacts.main([str(archive_path)])

    assert status == 1
