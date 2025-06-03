"""Tests for model aliases functionality"""
import pytest
from unittest.mock import patch
from llamate.data.model_aliases import MODEL_ALIASES

@pytest.fixture
def mock_model_aliases():
    """Mock model aliases for testing"""
    mock_aliases = {
        "test:4b": {
            "hf_repo": "test/model-4b",
            "hf_file": "model-4b-q4.gguf",
            "args": {
                "ctx-size": "4096"
            }
        },
        "test:8b": {
            "hf_repo": "test/model-8b",
            "hf_file": "model-8b-q4.gguf",
            "args": {
                "ctx-size": "8192"
            }
        }
    }
    with patch('llamate.data.model_aliases.MODEL_ALIASES', mock_aliases):
        yield mock_aliases

def test_model_aliases_structure():
    """Test that MODEL_ALIASES has the correct structure"""
    for alias, config in MODEL_ALIASES.items():
        assert isinstance(alias, str)
        assert isinstance(config, dict)
        assert "hf_repo" in config
        assert "hf_file" in config
        assert "args" in config
        assert isinstance(config["args"], dict)

def test_model_aliases_naming_convention():
    """Test that model aliases follow expected naming conventions"""
    for alias in MODEL_ALIASES.keys():
        # Should contain model name and size/variant separated by colon
        assert ":" in alias
        model_name, variant = alias.split(":")
        assert len(model_name) > 0
        assert len(variant) > 0

def test_model_aliases_repo_format():
    """Test that repository paths follow expected format"""
    for config in MODEL_ALIASES.values():
        repo = config["hf_repo"]
        assert "/" in repo  # Should be in format "owner/repo"
        owner, repo_name = repo.split("/")
        assert len(owner) > 0
        assert len(repo_name) > 0

def test_model_aliases_file_format():
    """Test that model file names follow expected format"""
    for config in MODEL_ALIASES.values():
        file_name = config["hf_file"]
        assert file_name.endswith(".gguf")  # Should be a GGUF file
        assert len(file_name) > 5  # Should have a name before .gguf

def test_model_aliases_required_args():
    """Test that model configs have required arguments"""
    for config in MODEL_ALIASES.values():
        args = config["args"]
        # Context size should be specified for all models
        assert "ctx-size" in args
        # Context size should be a string representing a number
        assert args["ctx-size"].isdigit()

def test_model_aliases_consistency():
    """Test that model aliases are consistent across related models"""
    # Group models by their base name
    model_groups = {}
    for alias, config in MODEL_ALIASES.items():
        base_name = alias.split(":")[0]
        if base_name not in model_groups:
            model_groups[base_name] = []
        model_groups[base_name].append((alias, config))

    # Check consistency within each group
    for base_name, models in model_groups.items():
        if len(models) > 1:
            # Check that related models use the same repo owner
            repo_owners = {config["hf_repo"].split("/")[0] for _, config in models}
            assert len(repo_owners) == 1, f"Models in {base_name} group use different repo owners"

            # Check that file naming follows similar pattern
            file_patterns = {config["hf_file"].split(".")[0].split("-")[0] for _, config in models}
            assert len(file_patterns) == 1, f"Models in {base_name} group use inconsistent file naming"
