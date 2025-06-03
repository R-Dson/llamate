"""Tests for GPU utility functions."""
import pytest
from unittest.mock import patch, MagicMock
import subprocess

from llamate.utils import gpu

@pytest.fixture
def mock_subprocess_run():
    with patch('subprocess.run') as mock_run:
        yield mock_run

def test_get_nvidia_memory_success(mock_subprocess_run):
    """Test successful NVIDIA GPU memory detection."""
    # Mock nvidia-smi output showing 16384 MB memory
    mock_process = MagicMock()
    mock_process.stdout = "16384\n"
    mock_subprocess_run.return_value = mock_process

    memory = gpu.get_nvidia_memory()

    mock_subprocess_run.assert_called_once_with(
        ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
        capture_output=True, text=True, check=True
    )
    assert memory == 16.0  # 16384 MB = 16 GB

def test_get_nvidia_memory_not_found(mock_subprocess_run):
    """Test NVIDIA GPU memory detection when nvidia-smi is not found."""
    mock_subprocess_run.side_effect = FileNotFoundError()

    memory = gpu.get_nvidia_memory()

    mock_subprocess_run.assert_called_once()
    assert memory is None

def test_get_nvidia_memory_command_error(mock_subprocess_run):
    """Test NVIDIA GPU memory detection when command fails."""
    mock_subprocess_run.side_effect = subprocess.SubprocessError()

    memory = gpu.get_nvidia_memory()

    mock_subprocess_run.assert_called_once()
    assert memory is None

def test_get_nvidia_memory_invalid_output(mock_subprocess_run):
    """Test NVIDIA GPU memory detection with invalid output."""
    mock_process = MagicMock()
    mock_process.stdout = "invalid"
    mock_subprocess_run.return_value = mock_process

    memory = gpu.get_nvidia_memory()

    mock_subprocess_run.assert_called_once()
    assert memory is None

def test_get_amd_memory_success(mock_subprocess_run):
    """Test successful AMD GPU memory detection."""
    mock_process = MagicMock()
    mock_process.stdout = """
======================ROCm System Management Interface======================
=================Memory Usage (Utilization[%] / Used[GB])==================
GPU_MEMORY:     40% / 12.3GB
"""
    mock_subprocess_run.return_value = mock_process

    memory = gpu.get_amd_memory()

    mock_subprocess_run.assert_called_once_with(
        ['rocm-smi', '--showmeminfo'],
        capture_output=True, text=True, check=True
    )
    assert memory == 8.0  # Conservative estimate

def test_get_amd_memory_not_found(mock_subprocess_run):
    """Test AMD GPU memory detection when rocm-smi is not found."""
    mock_subprocess_run.side_effect = FileNotFoundError()

    memory = gpu.get_amd_memory()

    mock_subprocess_run.assert_called_once()
    assert memory is None

def test_get_amd_memory_command_error(mock_subprocess_run):
    """Test AMD GPU memory detection when command fails."""
    mock_subprocess_run.side_effect = subprocess.SubprocessError()

    memory = gpu.get_amd_memory()

    mock_subprocess_run.assert_called_once()
    assert memory is None

def test_get_amd_memory_no_gpu_info(mock_subprocess_run):
    """Test AMD GPU memory detection when no GPU info is found."""
    mock_process = MagicMock()
    mock_process.stdout = "No GPU information found"
    mock_subprocess_run.return_value = mock_process

    memory = gpu.get_amd_memory()

    mock_subprocess_run.assert_called_once()
    assert memory is None

def test_calculate_gpu_layers_minimum():
    """Test GPU layer calculation with minimum memory."""
    memory = 2.0  # 2GB
    layers = gpu.calculate_gpu_layers(memory)
    assert layers == 4  # Should use minimum of 4 layers

def test_calculate_gpu_layers_maximum():
    """Test GPU layer calculation with large memory."""
    memory = 48.0  # 48GB
    layers = gpu.calculate_gpu_layers(memory)
    assert layers == 32  # Should cap at maximum of 32 layers

def test_calculate_gpu_layers_typical():
    """Test GPU layer calculation with typical memory amount."""
    memory = 12.0  # 12GB
    layers = gpu.calculate_gpu_layers(memory)
    # Expected: 12GB / 0.75GB per layer = 16 layers
    assert layers == 16

def test_calculate_gpu_layers_exact():
    """Test GPU layer calculation with exact memory multiples."""
    memory = 24.0  # 24GB
    layers = gpu.calculate_gpu_layers(memory)
    # Expected: 24GB / 0.75GB per layer = 32 layers (capped)
    assert layers == 32
