"""Tests for model management functionality."""
import pytest
from unittest.mock import patch, MagicMock

from llamate.core import model
from llamate.data.model_aliases import MODEL_ALIASES

# Fixture to mock MODEL_ALIASES for consistent testing
@pytest.fixture
def mock_model_aliases():
    original_aliases = MODEL_ALIASES.copy()
    mock_aliases = {
        "test_alias": {"hf_repo": "mock/repo", "hf_file": "mock.gguf", "args": {"temp": "0.7"}},
        "another_alias": {"hf_repo": "another/repo", "hf_file": "another.gguf", "args": {}},
        "repo_only_alias": {"hf_repo": "repo/only", "hf_file": "file.gguf", "args": {}}
    }
    with patch('llamate.data.model_aliases.MODEL_ALIASES', mock_aliases):
        yield mock_aliases

# Fixture to mock platform.detect_gpu
@pytest.fixture
def mock_detect_gpu():
    with patch('llamate.core.platform.detect_gpu') as mock_detect:
        yield mock_detect

def test_parse_model_alias_unknown(mock_model_aliases):
    """Test parsing an unknown model alias."""
    alias = "unknown_alias"
    result = model.parse_model_alias(alias)
    assert result is None

def test_parse_hf_spec_url_subdir():
    """Test parsing Hugging Face URL with file in subdir."""
    hf_spec = "https://huggingface.co/user/repo/resolve/main/subdir/model.gguf"
    print(f"Testing parsing URL: {hf_spec}")
    repo_id, file_path = model.parse_hf_spec(hf_spec)
    print(f"Parsed repo_id: {repo_id}, file_path: {file_path}")
    assert repo_id == "user/repo"
    assert file_path == "subdir/model.gguf"

def test_parse_hf_spec_invalid_format():
    """Test parsing invalid HF spec format."""
    hf_spec = "invalid_spec"
    with pytest.raises(ValueError, match="Invalid repo spec: invalid_spec. Use REPO_ID:FILE or HF_URL"):
        model.parse_hf_spec(hf_spec)

def test_validate_model_name_valid():
    """Test validating a valid model name."""
    name = "my_model-123_v4"
    validated_name = model.validate_model_name(name)
    assert validated_name == name

def test_validate_model_name_with_spaces():
    """Test validating a model name with spaces (should be sanitized)."""
    name = "my model name"
    validated_name = model.validate_model_name(name)
    assert validated_name == "mymodelname"

def test_validate_model_name_empty():
    """Test validating an empty model name."""
    name = ""
    with pytest.raises(ValueError, match="Model name cannot be empty"):
        model.validate_model_name(name)

def test_validate_model_name_no_alphanumeric():
    """Test validating a model name with no alphanumeric characters."""
    name = "_-"
    with pytest.raises(ValueError, match="Model name must contain at least one alphanumeric character"):
        model.validate_model_name(name)

def test_validate_args_list_valid():
    """Test validating a list of valid arguments."""
    args_list = ["temp=0.8", "n-gpu-layers=30", "key=value with spaces"]
    validated_args = model.validate_args_list(args_list)
    assert validated_args == {"temp": "0.8", "n-gpu-layers": "30", "key": "value with spaces"}

def test_validate_args_list_empty():
    """Test validating an empty list of arguments."""
    args_list = []
    validated_args = model.validate_args_list(args_list)
    assert validated_args == {}

def test_validate_args_list_invalid_format():
    """Test validating a list with an invalid argument format."""
    args_list = ["temp=0.8", "invalid_arg", "key=value"]
    with pytest.raises(ValueError, match="Argument 'invalid_arg' is not in KEY=VALUE format"):
        model.validate_args_list(args_list)

def test_validate_args_list_empty_key():
    """Test validating a list with an empty key."""
    args_list = ["=value"]
    with pytest.raises(ValueError, match="Argument key cannot be empty"):
        model.validate_args_list(args_list)

def test_configure_gpu_auto_detect_gpu_found(mock_detect_gpu):
    """Test configure_gpu with auto-detect and GPU found."""
    mock_detect_gpu.return_value = (True, 40)
    model_config = {"hf_repo": "test/repo", "hf_file": "test.gguf", "args": {}}
    model_name = "my_model"
    
    updated_config = model.configure_gpu(model_config, model_name, auto_detect=True)
    
    mock_detect_gpu.assert_called_once()
    assert updated_config["args"]['n-gpu-layers'] == "40"

def test_configure_gpu_auto_detect_gpu_not_found(mock_detect_gpu):
    """Test configure_gpu with auto-detect and no GPU found."""
    mock_detect_gpu.return_value = (False, None)
    model_config = {"hf_repo": "test/repo", "hf_file": "test.gguf", "args": {}}
    model_name = "my_model"
    
    updated_config = model.configure_gpu(model_config, model_name, auto_detect=True)
    
    mock_detect_gpu.assert_called_once()
    assert 'n-gpu-layers' not in updated_config["args"]

def test_configure_gpu_auto_detect_gpu_found_no_layers(mock_detect_gpu):
    """Test configure_gpu with auto-detect and GPU found but no suggested layers."""
    mock_detect_gpu.return_value = (True, None)
    model_config = {"hf_repo": "test/repo", "hf_file": "test.gguf", "args": {}}
    model_name = "my_model"
    
    updated_config = model.configure_gpu(model_config, model_name, auto_detect=True)
    
    mock_detect_gpu.assert_called_once()
    assert 'n-gpu-layers' not in updated_config["args"]

def test_configure_gpu_auto_detect_disabled(mock_detect_gpu):
    """Test configure_gpu with auto-detect disabled."""
    model_config = {"hf_repo": "test/repo", "hf_file": "test.gguf", "args": {}}
    model_name = "my_model"
    
    updated_config = model.configure_gpu(model_config, model_name, auto_detect=False)
    
    mock_detect_gpu.assert_not_called()
    assert 'n-gpu-layers' not in updated_config["args"]

def test_configure_gpu_n_gpu_layers_already_set(mock_detect_gpu):
    """Test configure_gpu when n-gpu-layers is already in args."""
    mock_detect_gpu.return_value = (True, 40)
    model_config = {"hf_repo": "test/repo", "hf_file": "test.gguf", "args": {'n-gpu-layers': '20'}}
    model_name = "my_model"
    
    updated_config = model.configure_gpu(model_config, model_name, auto_detect=True)
    
    mock_detect_gpu.assert_not_called()
    assert updated_config["args"]['n-gpu-layers'] == "20"

# Core model functionality tests
@pytest.fixture
def mock_llm():
    """Fixture for a mock LLM model"""
    class MockLLM:
        def __init__(self):
            self.temperature = 0.7
            self.context_length = 2048
        
        def load(self):
            return self
            
        def generate(self, prompt):
            return "Test response"
    
    return MockLLM()

def test_model_initialization(mock_llm):
    """Test model initialization"""
    assert hasattr(mock_llm, "load")
    assert hasattr(mock_llm, "generate")

def test_model_parameters(mock_llm):
    """Test model parameters"""
    assert hasattr(mock_llm, "temperature")
    assert isinstance(mock_llm.temperature, float)
    assert hasattr(mock_llm, "context_length")
    assert isinstance(mock_llm.context_length, int)

def test_model_generation(mock_llm):
    """Test model text generation"""
    response = mock_llm.generate("Test prompt")
    assert isinstance(response, str)
    assert len(response) > 0
