'''Tests for local-index cache path helpers.'''

from pathlib import Path, PurePath

from nistchempy.indexing import cache


def test_resolve_index_path_prefers_explicit_path(monkeypatch, tmp_path):
    monkeypatch.setenv(cache.INDEX_ENV_VAR, str(tmp_path / 'env'))

    result = cache.resolve_index_path(tmp_path / 'explicit')

    assert result == (tmp_path / 'explicit').resolve()


def test_resolve_index_path_uses_env(monkeypatch, tmp_path):
    monkeypatch.setenv(cache.INDEX_ENV_VAR, str(tmp_path / 'env'))

    result = cache.resolve_index_path()

    assert result == (tmp_path / 'env').resolve()


def test_default_index_path_uses_default_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, 'get_default_cache_dir', lambda: tmp_path)

    assert cache.get_default_index_path() == tmp_path / cache.INDEX_DIR_NAME


def test_fallback_cache_base_respects_xdg(monkeypatch):
    monkeypatch.setattr(cache._sys, 'platform', 'linux')
    monkeypatch.setattr(cache._os, 'name', 'posix')
    monkeypatch.setattr(cache, '_Path', PurePath)

    xdg_cache_home = '/tmp/nistchempy-xdg-cache'
    monkeypatch.setenv('XDG_CACHE_HOME', xdg_cache_home)

    assert cache._fallback_cache_base() == (
        PurePath(xdg_cache_home) / 'nistchempy'
    )


def test_fallback_cache_base_windows_localappdata(monkeypatch, tmp_path):
    monkeypatch.setattr(cache._sys, 'platform', 'win32')
    monkeypatch.setattr(cache._os, 'name', 'nt')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    monkeypatch.setattr(cache, '_Path', PurePath)

    assert cache._fallback_cache_base() == (
        PurePath(tmp_path / 'local') / 'nistchempy' / 'Cache'
    )


def test_fallback_cache_base_macos(monkeypatch, tmp_path):
    monkeypatch.setattr(cache._sys, 'platform', 'darwin')
    monkeypatch.setattr(cache._Path, 'home', lambda: tmp_path)

    assert cache._fallback_cache_base() == (
        tmp_path / 'Library' / 'Caches' / 'nistchempy'
    )
