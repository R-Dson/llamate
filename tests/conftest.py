"""Test fixtures for Llamate"""
import pytest
from pathlib import Path
import os

@pytest.fixture
def test_data_dir():
    """Fixture for test data directory"""
    path = Path(__file__).parent / "test_data"
    path.mkdir(exist_ok=True)
    return path

@pytest.fixture
def runner():
    """Fixture for running CLI commands"""
    class CliRunner:
        def invoke(self, cli, args):
            """Run a CLI command with given arguments"""
            try:
                result = cli(args)
                return result
            except SystemExit as e:
                return e.code
            except Exception as e:
                return e
    return CliRunner()