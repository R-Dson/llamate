"""Tests for platform detection functionality"""
import pytest
from unittest.mock import patch, MagicMock
from llamate.core.platform import is_windows, get_platform_arch, get_swap_platform

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
