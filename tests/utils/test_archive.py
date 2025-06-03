"""Tests for archive handling utilities."""
import pytest
from pathlib import Path
import zipfile
import tarfile
from unittest.mock import patch
import platform

from llamate.utils.archive import extract_archive, get_platform_archive_ext

# Fixture to create dummy archive files
@pytest.fixture
def dummy_archives(tmp_path):
    # Create a dummy directory structure and files
    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()
    
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "file1.txt").write_text("content1")
    (data_dir / "subdir").mkdir()
    (data_dir / "subdir" / "file2.txt").write_text("content2")

    # Create a dummy zip file
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(data_dir / "file1.txt", arcname="file1.txt")
        zf.write(data_dir / "subdir" / "file2.txt", arcname="subdir/file2.txt")

    # Create a dummy tar.gz file
    tar_gz_path = tmp_path / "test.tar.gz"
    with tarfile.open(tar_gz_path, 'w:gz') as tf:
        tf.add(data_dir / "file1.txt", arcname="file1.txt")
        tf.add(data_dir / "subdir" / "file2.txt", arcname="subdir/file2.txt")

    yield {
        "tmp_path": tmp_path,
        "zip_path": zip_path,
        "tar_gz_path": tar_gz_path,
        "extract_dir": extract_dir,
        "data_dir": data_dir
    }

def test_extract_archive_zip(dummy_archives):
    """Test extracting a zip archive."""
    archives = dummy_archives
    extract_archive(archives["zip_path"], archives["extract_dir"])

    extracted_file1 = archives["extract_dir"] / "file1.txt"
    extracted_file2 = archives["extract_dir"] / "subdir" / "file2.txt"

    assert extracted_file1.exists()
    assert extracted_file1.read_text() == "content1"
    assert extracted_file2.exists()
    assert extracted_file2.read_text() == "content2"

def test_extract_archive_tar_gz(dummy_archives):
    """Test extracting a tar.gz archive."""
    archives = dummy_archives
    extract_archive(archives["tar_gz_path"], archives["extract_dir"])

    extracted_file1 = archives["extract_dir"] / "file1.txt"
    extracted_file2 = archives["extract_dir"] / "subdir" / "file2.txt"

    assert extracted_file1.exists()
    assert extracted_file1.read_text() == "content1"
    assert extracted_file2.exists()
    assert extracted_file2.read_text() == "content2"

def test_extract_archive_unsupported_format(dummy_archives):
    """Test extracting an unsupported archive format."""
    archives = dummy_archives
    unsupported_path = archives["tmp_path"] / "test.txt"
    unsupported_path.write_text("not an archive")

    with pytest.raises(ValueError, match="Unsupported archive format: .txt"):
        extract_archive(unsupported_path, archives["extract_dir"])

def test_extract_archive_zipslip_vulnerability(dummy_archives):
    """Test zipslip vulnerability protection for tar.gz."""
    archives = dummy_archives
    zipslip_tar_gz_path = archives["tmp_path"] / "zipslip.tar.gz"

    # Create a tar.gz with a malicious path
    with tarfile.open(zipslip_tar_gz_path, 'w:gz') as tf:
        # This path attempts to write outside the extract directory
        malicious_path = Path("../malicious.txt")
        # Create a TarInfo object manually
        tarinfo = tarfile.TarInfo(name=str(malicious_path))
        tarinfo.size = 0
        tf.addfile(tarinfo)

    with pytest.raises(ValueError, match="Attempted path traversal in archive"):
        extract_archive(zipslip_tar_gz_path, archives["extract_dir"])

def test_get_platform_archive_ext_windows():
    """Test get_platform_archive_ext on Windows."""
    with patch('platform.system', return_value='Windows'):
        assert get_platform_archive_ext() == '.zip'

def test_get_platform_archive_ext_linux():
    """Test get_platform_archive_ext on Linux."""
    with patch('platform.system', return_value='Linux'):
        assert get_platform_archive_ext() == '.tar.gz'

def test_get_platform_archive_ext_macos():
    """Test get_platform_archive_ext on macOS."""
    with patch('platform.system', return_value='Darwin'):
        assert get_platform_archive_ext() == '.tar.gz'
