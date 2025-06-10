"""Tests for aliases service functionality"""
import pytest
from unittest.mock import patch, MagicMock
from llamate.services.aliases import fetch_remote_aliases, get_model_aliases, CACHE_TTL
from llamate.utils.exceptions import ResourceError
import time

# Sample YAML content for testing
SAMPLE_YAML = """
gemma3:4b:
  hf_repo: "unsloth/gemma-3-4b-it-GGUF"
  hf_file: "gemma-3-4b-it-UD-Q4_K_XL.gguf"
  args:
    ctx-size: "8192"
"""

def test_fetch_remote_aliases_success():
    """Test successful YAML parsing of remote aliases"""
    with patch('llamate.services.aliases.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.text = SAMPLE_YAML
        mock_get.return_value = mock_response
        
        aliases = fetch_remote_aliases()
        assert aliases == {
            "gemma3:4b": {
                "hf_repo": "unsloth/gemma-3-4b-it-GGUF",
                "hf_file": "gemma-3-4b-it-UD-Q4_K_XL.gguf",
                "args": {
                    "ctx-size": "8192"
                }
            }
        }

def test_fetch_remote_aliases_failure():
    """Test fallback on network error"""
    with patch('llamate.services.aliases.requests.get') as mock_get:
        mock_get.side_effect = Exception("Network error")
        
        with pytest.raises(ResourceError):
            fetch_remote_aliases()

def test_get_model_aliases_caching():
    """Test caching mechanism works as expected"""
    with patch('llamate.services.aliases.fetch_remote_aliases') as mock_fetch, \
         patch('llamate.services.aliases.time') as mock_time:
        
        # Reset cache before test
        import llamate.services.aliases as aliases_module
        aliases_module._aliases_cache = None
        aliases_module._last_fetch = 0
        
        mock_fetch.return_value = {"test": "value"}
        mock_time.time.return_value = 1000.0
        
        # First call should fetch
        aliases = get_model_aliases()
        assert aliases == {"test": "value"}
        assert mock_fetch.call_count == 1
        
        # Second call within TTL should use cache
        aliases = get_model_aliases()
        assert aliases == {"test": "value"}
        assert mock_fetch.call_count == 1
        
        # After TTL expiration, should fetch again
        mock_time.time.return_value = 1000.0 + CACHE_TTL + 1
        aliases = get_model_aliases()
        assert mock_fetch.call_count == 2

def test_invalid_yaml_handling():
    """Test invalid YAML handling"""
    with patch('llamate.services.aliases.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.text = "invalid: yaml: here"
        mock_get.return_value = mock_response
        
        with pytest.raises(ResourceError):
            fetch_remote_aliases()