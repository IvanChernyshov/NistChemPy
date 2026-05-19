'''Pytest configuration for NistChemPy tests.'''

import os

import pytest


def pytest_collection_modifyitems(config, items):
    '''Skip live WebBook tests unless explicitly requested.'''
    _ = config
    if os.environ.get('NISTCHEMPY_RUN_NETWORK', '').lower() in {
            '1', 'true', 'yes'}:
        return

    skip_network = pytest.mark.skip(
        reason='Set NISTCHEMPY_RUN_NETWORK=1 to run live WebBook tests.'
    )
    for item in items:
        if 'network' in item.keywords:
            item.add_marker(skip_network)
