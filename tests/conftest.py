"""Isolate generated datasets and run records in temporary directories."""
import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import create_app

_test_directory = None


def pytest_configure(config):
    """Avoid a shared pytest-of-user directory owned by another Windows context."""
    global _test_directory
    if config.option.basetemp is None:
        temporary_root = Path(tempfile.gettempdir()).resolve()
        _test_directory = tempfile.TemporaryDirectory(prefix="uniswap-pytest-", dir=temporary_root)
        owned_path = Path(_test_directory.name).resolve()
        assert owned_path.parent == temporary_root and owned_path.name.startswith("uniswap-pytest-")
        config.option.basetemp = str(owned_path)


def pytest_unconfigure(config):
    if _test_directory is not None:
        _test_directory.cleanup()


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(state_dir=tmp_path)) as connection:
        yield connection
