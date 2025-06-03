"""Tests for utility functions"""
import pytest
from pathlib import Path
import json

def test_path_handling(test_data_dir):
    """Test path handling utilities"""
    test_path = test_data_dir / "test_subdir"
    test_path.mkdir(exist_ok=True)
    assert test_path.exists()
    assert test_path.is_dir()
"""
def test_file_operations(test_data_dir):
    test_file = test_data_dir / "test.txt"
    content = "test content"
    test_file.write_text(content)
    assert test_file.exists()
    assert test_file.read_text() == content"""