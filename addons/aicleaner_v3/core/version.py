"""
Version information for AICleaner v3
"""

__version__ = "1.0.0"
__version_info__ = tuple(int(x) for x in __version__.split('.'))
__build_date__ = "2025-01-19T00:00:00Z"
__git_hash__ = "unknown"  # Will be updated during build

# Version components
MAJOR = __version_info__[0]
MINOR = __version_info__[1]
PATCH = __version_info__[2]

# Build information
BUILD_TYPE = "production"

def get_version_info():
    """Get comprehensive version information."""
    return {
        "version": __version__,
        "version_info": __version_info__,
        "major": MAJOR,
        "minor": MINOR,
        "patch": PATCH,
        "build_date": __build_date__,
        "build_type": BUILD_TYPE,
        "git_hash": __git_hash__
    }

def get_version_string():
    """Get formatted version string."""
    return f"AICleaner v3 - v{__version__} ({BUILD_TYPE})"