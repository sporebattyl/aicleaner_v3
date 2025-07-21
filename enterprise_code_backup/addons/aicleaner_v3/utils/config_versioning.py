"""
ConfigVersioning - A simple versioning system for configuration files.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigVersioning:
    """
    Manages simple file-based versioning for configuration dictionaries.
    """

    def __init__(self, config_base_dir: str, max_versions: int = 10):
        """
        Initialize the ConfigVersioning system.

        Args:
            config_base_dir: The base directory where configuration is stored.
                             A 'config_versions' subdirectory will be created here.
            max_versions: The maximum number of version backups to keep.
        """
        if not os.path.isdir(config_base_dir):
            # In a containerized environment like HA addon, the dir should exist.
            # If not, it's a significant setup problem.
            logger.error(f"Configuration base directory does not exist: {config_base_dir}")
            raise ValueError(f"Configuration base directory does not exist: {config_base_dir}")
            
        self.versions_dir = os.path.join(config_base_dir, 'config_versions')
        self.max_versions = max_versions
        
        try:
            os.makedirs(self.versions_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Error creating versions directory {self.versions_dir}: {e}")
            raise

    def save_version(self, config: Dict[str, Any]) -> Optional[str]:
        """
        Saves the given configuration as a new version.

        Args:
            config: The configuration dictionary to save.

        Returns:
            The path to the saved version file, or None if saving failed.
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        version_filename = f"config_{timestamp}.json"
        version_filepath = os.path.join(self.versions_dir, version_filename)

        try:
            with open(version_filepath, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Saved new configuration version: {version_filename}")
            self._cleanup_versions()
            return version_filepath
        except (IOError, TypeError) as e:
            logger.error(f"Failed to save configuration version to {version_filepath}: {e}")
            return None

    def list_versions(self) -> List[str]:
        """
        Lists all available configuration versions, sorted from newest to oldest.

        Returns:
            A list of version filenames.
        """
        try:
            files = [f for f in os.listdir(self.versions_dir) if f.startswith('config_') and f.endswith('.json')]
            # Sort descending by filename (which includes the timestamp)
            return sorted(files, reverse=True)
        except OSError as e:
            logger.error(f"Error listing versions from {self.versions_dir}: {e}")
            return []

    def get_version(self, version_filename: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific configuration version.

        Args:
            version_filename: The filename of the version to retrieve.

        Returns:
            The configuration dictionary, or None if the version is not found or invalid.
        """
        # Basic security check to prevent path traversal
        if not version_filename or '..' in version_filename or not os.path.basename(version_filename) == version_filename:
            logger.warning(f"Invalid or potentially unsafe version filename requested: {version_filename}")
            return None

        version_filepath = os.path.join(self.versions_dir, version_filename)

        if not os.path.exists(version_filepath):
            logger.error(f"Version file not found: {version_filepath}")
            return None

        try:
            with open(version_filepath, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to read or parse version file {version_filepath}: {e}")
            return None
            
    def get_latest_version(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the most recent configuration version.

        Returns:
            The latest configuration dictionary, or None if no versions are available.
        """
        latest_versions = self.list_versions()
        if not latest_versions:
            return None
        return self.get_version(latest_versions[0])

    def _cleanup_versions(self):
        """
        Removes the oldest configuration versions if the count exceeds max_versions.
        """
        versions = self.list_versions()
        if len(versions) > self.max_versions:
            versions_to_delete = versions[self.max_versions:]
            logger.info(f"Cleaning up {len(versions_to_delete)} old configuration versions.")
            for version_filename in versions_to_delete:
                version_filepath = os.path.join(self.versions_dir, version_filename)
                try:
                    os.remove(version_filepath)
                    logger.debug(f"Removed old version: {version_filename}")
                except OSError as e:
                    logger.error(f"Error removing old version file {version_filepath}: {e}")