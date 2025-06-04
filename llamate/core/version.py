from pathlib import Path

def get_version():
    try:
        # Try to read CI-generated version file
        version_file = Path(__file__).parent.parent.parent / 'VERSION'
        if version_file.exists():
            return version_file.read_text().strip()
    except Exception:
        pass
    
    # Fallback to static version
    from llamate import __version__
    return __version__