"""
conftest.py local para testes de integração reais.

Remove o mock global de litellm injetado pelo conftest.py raiz,
permitindo chamadas reais à API.
"""

from contextlib import suppress
import importlib
import sys

import pytest


@pytest.fixture
def vcr_cassette():
    """Offline HTTP replay fixture; install ``vcrpy`` to record/replay cassettes."""
    vcr = pytest.importorskip("vcr")
    return vcr.VCR(
        cassette_library_dir="tests/integration/cassettes",
        record_mode="none",
        match_on=["method", "scheme", "host", "port", "path", "query"],
        filter_headers=["authorization", "x-api-key"],
    )


def pytest_configure(config):
    """Remove o mock de litellm antes dos testes de integração rodarem."""
    # Remove o módulo mockado do sys.modules para forçar import real
    for mod in list(sys.modules.keys()):
        if mod == "litellm" or mod.startswith("litellm."):
            del sys.modules[mod]

    # Reimporta o litellm real
    with suppress(ImportError):
        importlib.import_module("litellm")
