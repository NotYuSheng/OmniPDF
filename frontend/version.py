"""Version information for OmniPDF frontend."""
import subprocess
import logging

logger = logging.getLogger(__name__)

def get_version() -> str:
    """
    Get the current version from git tags.
    Falls back to 'dev' if git is not available or no tags exist.
    """
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.debug(f"Could not get git version: {e}")

    return "dev"

__version__ = get_version()
