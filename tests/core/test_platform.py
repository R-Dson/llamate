"""Tests for platform detection functionality"""
import subprocess
import pytest
from unittest.mock import patch, MagicMock
from llamate.core.platform import is_windows, get_platform_arch, get_swap_platform, get_platform_info, detect_gpu, get_llama_server_bin_name

@pytest.fixture
def mock_platform():
    with (
        patch('platform.system') as mock_system,
        patch('platform.machine') as mock_machine
    ):
        yield {
            'system': mock_system,
            'machine': mock_machine
        }

def test_is_windows_true(mock_platform):
    """Test is_windows returns True on Windows platform"""
    mock_platform['system'].return_value = 'Windows'
    assert is_windows() is True

def test_is_windows_false(mock_platform):
    """Test is_windows returns False on non-Windows platform"""
    mock_platform['system'].return_value = 'Linux'
    assert is_windows() is False

def test_get_platform_arch_x86_64(mock_platform):
    """Test get_platform_arch for x86_64 architecture"""
    mock_platform['machine'].return_value = 'x86_64'
    assert get_platform_arch() == 'x64'

def test_get_platform_arch_amd64(mock_platform):
    """Test get_platform_arch for AMD64 architecture"""
    mock_platform['machine'].return_value = 'AMD64'
    assert get_platform_arch() == 'x64'

def test_get_platform_arch_arm64(mock_platform):
    """Test get_platform_arch for ARM64 architecture"""
    mock_platform['machine'].return_value = 'arm64'
    assert get_platform_arch() == 'arm64'

def test_get_platform_arch_aarch64(mock_platform):
    """Test get_platform_arch for aarch64 architecture"""
    mock_platform['machine'].return_value = 'aarch64'
    assert get_platform_arch() == 'arm64'

def test_get_platform_arch_unsupported(mock_platform):
    """Test get_platform_arch for unsupported architecture"""
    mock_platform['machine'].return_value = 'unsupported'
    with pytest.raises(ValueError, match='Unsupported architecture'):
        get_platform_arch()

def test_get_swap_platform_windows_x64(mock_platform):
    """Test get_swap_platform for Windows x64"""
    mock_platform['system'].return_value = 'Windows'
    mock_platform['machine'].return_value = 'AMD64'
    assert get_swap_platform() == 'windows-x64'

def test_get_swap_platform_linux_x64(mock_platform):
    """Test get_swap_platform for Linux x64"""
    mock_platform['system'].return_value = 'Linux'
    mock_platform['machine'].return_value = 'x86_64'
    assert get_swap_platform() == 'linux-x64'

def test_get_swap_platform_mac_arm64(mock_platform):
    """Test get_swap_platform for MacOS ARM64"""
    mock_platform['system'].return_value = 'Darwin'
    mock_platform['machine'].return_value = 'arm64'
    assert get_swap_platform() == 'macos-arm64'

def test_get_swap_platform_unsupported(mock_platform):
    """Test get_swap_platform for unsupported platform"""
    mock_platform['system'].return_value = 'BSD'
    mock_platform['machine'].return_value = 'x86_64'
    with pytest.raises(ValueError, match='Unsupported platform'):
        get_swap_platform()

@pytest.mark.parametrize("system, machine, expected_os, expected_arch", [
    ("Linux", "x86_64", "linux", "x64"),
    ("Linux", "aarch64", "linux", "arm64"),
    ("Darwin", "x86_64", "macos", "x64"),
    ("Darwin", "arm64", "macos", "arm64"),
    ("Windows", "AMD64", "windows", "x64"),
    ("FreeBSD", "x86_64", "freebsd", "x64"),
])
def test_get_platform_info_supported(mock_platform, system, machine, expected_os, expected_arch):
    """Test get_platform_info for supported platforms."""
    mock_platform['system'].return_value = system
    mock_platform['machine'].return_value = machine
    os_name, arch = get_platform_info()
    assert os_name == expected_os
    assert arch == expected_arch

@pytest.mark.parametrize("system, machine, error_match", [
    ("UnsupportedOS", "x86_64", "Unsupported platform"),
    ("Linux", "unsupported_arch", "Platform linux/None is not supported"),
    ("Windows", "arm64", "Platform windows/arm64 is not supported"), # Windows only supports x64
])
def test_get_platform_info_unsupported(mock_platform, system, machine, error_match):
    """Test get_platform_info for unsupported platforms."""
    mock_platform['system'].return_value = system
    mock_platform['machine'].return_value = machine
    with pytest.raises(ValueError, match=error_match):
        get_platform_info()

@patch('subprocess.run')
def test_detect_gpu_nvidia(mock_subprocess_run):
    """Test detect_gpu with NVIDIA GPU detected."""
    mock_result = MagicMock()
    mock_result.stdout = "4096\n" # 4GB
    mock_subprocess_run.return_value = mock_result
    has_gpu, suggested_layers = detect_gpu()
    assert has_gpu is True
    assert suggested_layers == 5 # min(32, max(4, int(4096/1024 / 0.75))) = min(32, max(4, int(4 / 0.75))) = min(32, max(4, 5)) = 5
    mock_subprocess_run.assert_called_with(
        ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
        capture_output=True, text=True, check=True
    )

@patch('subprocess.run', side_effect=FileNotFoundError)
def test_detect_gpu_no_nvidia_smi(mock_subprocess_run):
    """Test detect_gpu when nvidia-smi is not found."""
    has_gpu, suggested_layers = detect_gpu()
    assert has_gpu is False
    assert suggested_layers is None

@patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'cmd'))
def test_detect_gpu_nvidia_error(mock_subprocess_run):
    """Test detect_gpu when nvidia-smi returns an error."""
    has_gpu, suggested_layers = detect_gpu()
    assert has_gpu is False
    assert suggested_layers is None

@patch('subprocess.run')
def test_detect_gpu_amd(mock_subprocess_run):
    """Test detect_gpu with AMD GPU detected."""
    # Mock nvidia-smi to fail first
    mock_subprocess_run.side_effect = [
        subprocess.CalledProcessError(1, 'nvidia-smi'),
        MagicMock(stdout="GPU_MEMORY: 8192MB\n")
    ]
    has_gpu, suggested_layers = detect_gpu()
    assert has_gpu is True
    assert suggested_layers == 20
    # Check that rocm-smi was called after nvidia-smi failed
    mock_subprocess_run.assert_called_with(
        ['rocm-smi', '--showmeminfo'],
        capture_output=True, text=True, check=True
    )

@patch('subprocess.run', side_effect=FileNotFoundError)
def test_detect_gpu_no_amd_smi(mock_subprocess_run):
    """Test detect_gpu when rocm-smi is not found (after nvidia-smi also fails)."""
    # Mock nvidia-smi to fail first
    mock_subprocess_run.side_effect = [
        subprocess.CalledProcessError(1, 'nvidia-smi'),
        FileNotFoundError
    ]
    has_gpu, suggested_layers = detect_gpu()
    assert has_gpu is False
    assert suggested_layers is None

@patch('platform.system')
def test_get_llama_server_bin_name_windows(mock_system):
    """Test get_llama_server_bin_name on Windows."""
    mock_system.return_value = "Windows"
    assert get_llama_server_bin_name() == "llama-server.exe"

@patch('platform.system')
def test_get_llama_server_bin_name_linux(mock_system):
    """Test get_llama_server_bin_name on Linux."""
    mock_system.return_value = "Linux"
    assert get_llama_server_bin_name() == "llama-server"

@patch('platform.system')
def test_get_llama_server_bin_name_macos(mock_system):
    """Test get_llama_server_bin_name on macOS."""
    mock_system.return_value = "Darwin"
    assert get_llama_server_bin_name() == "llama-server"
