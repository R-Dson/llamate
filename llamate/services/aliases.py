import requests
import time
import yaml
from typing import Dict, Any
from ..utils.exceptions import ResourceError

# Cache configuration
_aliases_cache = None
_last_fetch = 0
CACHE_TTL = 86400  # 24 hours

def fetch_remote_aliases() -> Dict[str, Any]:
    """Fetch latest aliases from GitHub with error handling"""
    url = "https://raw.githubusercontent.com/R-Dson/llamate-alias/refs/heads/main/model_aliases.yml"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse YAML content directly
        return yaml.safe_load(response.text)
    except Exception as e:
        raise ResourceError(f"Failed to fetch remote aliases: {str(e)}")

def get_model_aliases() -> Dict[str, Any]:
    """Get aliases with caching mechanism"""
    global _aliases_cache, _last_fetch
    
    # Return cached version if valid
    if _aliases_cache and (time.time() - _last_fetch) < CACHE_TTL:
        return _aliases_cache
    
    try:
        _aliases_cache = fetch_remote_aliases()
        _last_fetch = time.time()
        return _aliases_cache
    except ResourceError:
        raise ResourceError("Failed to fetch model aliases from remote source. Please check your network connection or try again later.")