"""
Custom exceptions for the llamate project
"""

class LlamateError(Exception):
    """Base exception for all llamate-specific errors"""
    pass

class InvalidInputError(LlamateError, ValueError):
    """Raised when invalid input is provided"""
    pass

class ConfigValidationError(LlamateError):
    """Raised when configuration validation fails"""
    pass

class SecurityError(LlamateError):
    """Raised for security-related issues"""
    pass

class ResourceError(LlamateError):
    """Raised for resource management issues"""
    pass

class PlatformError(LlamateError):
    """Raised for platform-specific compatibility issues"""
    pass

class ModelNotFoundError(LlamateError):
    """Raised when a specified model doesn't exist"""
    pass

class DownloadError(LlamateError):
    """Raised for download-related errors"""
    pass

class InvalidAliasError(InvalidInputError):
    """Raised when an invalid alias is provided"""
    pass
    
class InvalidURLError(InvalidInputError):
    """Raised when an invalid URL is provided"""
    pass