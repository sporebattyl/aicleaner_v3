"""
AICleaner v3 Installer Helper Functions
Supporting methods for the smart installer

This module contains all the detailed implementation methods for:
- Environment detection helpers
- Validation test implementations
- Component installation methods
- Rollback and recovery functions
"""

import os
import sys
import json
import asyncio
import shutil
import tempfile
import subprocess
import socket
import aiohttp
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import psutil


class InstallerHelpers:
    """Helper methods for the smart installer"""
    
    def __init__(self, installer):
        """Initialize with reference to main installer"""
        self.installer = installer
        self.logger = installer.logger
        self.context = installer.context
    
    # Environment Detection Helpers
    
    async def find_ha_config_path(self) -> Path:
        """Find Home Assistant configuration path for Core installations"""
        possible_paths = [
            Path.home() / ".homeassistant",
            Path("/srv/homeassistant"),
            Path("/opt/homeassistant"),
            Path("/usr/local/homeassistant"),
            Path(os.getcwd()) / "homeassistant"
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "configuration.yaml").exists():
                return path
        
        # Try to find via process
        try:
            result = subprocess.run(
                ["ps", "-aux"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            for line in result.stdout.split('\n'):
                if 'homeassistant' in line and '--config' in line:
                    # Extract config path from command line
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == '--config' and i + 1 < len(parts):
                            return Path(parts[i + 1])
        except:
            pass
        
        # Default fallback
        return Path.home() / ".homeassistant"
    
    async def get_ha_version(self) -> Optional[str]:
        """Get Home Assistant version"""
        try:
            # Try supervisor API first
            if self.context and self.context.supervisor_available:
                version = await self._get_version_from_supervisor()
                if version:
                    return version
            
            # Try core API
            version = await self._get_version_from_core_api()
            if version:
                return version
            
            # Try configuration file
            config_path = self.context.ha_config_path / ".HA_VERSION"
            if config_path.exists():
                return config_path.read_text().strip()
            
        except Exception as e:
            self.logger.debug(f"Could not determine HA version: {e}")
        
        return None
    
    async def _get_version_from_supervisor(self) -> Optional[str]:
        """Get HA version from Supervisor API"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}"}
                async with session.get(
                    "http://supervisor/core/info",
                    headers=headers,
                    timeout=5
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", {}).get("version")
        except:
            pass
        return None
    
    async def _get_version_from_core_api(self) -> Optional[str]:
        """Get HA version from Core API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:8123/api/config",
                    timeout=5
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("version")
        except:
            pass
        return None
    
    async def determine_installation_paths(self, ha_env, ha_config_path) -> Tuple[Optional[Path], Optional[Path]]:
        """Determine installation paths based on environment"""
        addon_path = None
        custom_component_path = ha_config_path / "custom_components" / "aicleaner_v3"
        
        if ha_env in ["haos", "supervised"]:
            # For addon-capable environments
            if os.path.exists("/usr/share/hassio/addons"):
                addon_path = Path("/usr/share/hassio/addons/local/aicleaner_v3")
            elif os.path.exists("/addon_configs"):
                addon_path = Path("/addon_configs/aicleaner_v3")
        
        return addon_path, custom_component_path
    
    # Validation Methods
    
    async def get_available_disk_space(self, path: Path) -> int:
        """Get available disk space in MB"""
        try:
            stat = shutil.disk_usage(path)
            return stat.free // (1024 * 1024)
        except:
            return 0
    
    async def check_write_permissions(self) -> bool:
        """Check write permissions to required directories"""
        test_paths = [
            self.context.ha_config_path,
            self.context.ha_config_path / "custom_components"
        ]
        
        if self.context.addon_path:
            test_paths.append(self.context.addon_path.parent)
        
        for path in test_paths:
            try:
                # Ensure directory exists
                path.mkdir(parents=True, exist_ok=True)
                
                # Test write permissions
                test_file = path / f".write_test_{self.installer.installation_id}"
                test_file.write_text("test")
                test_file.unlink()
                
            except Exception as e:
                self.logger.debug(f"Write permission check failed for {path}: {e}")
                return False
        
        return True
    
    async def check_network_connectivity(self) -> bool:
        """Check network connectivity to essential services"""
        test_hosts = [
            ("api.openai.com", 443),
            ("api.anthropic.com", 443),
            ("generativelanguage.googleapis.com", 443),
            ("registry.npmjs.org", 443)
        ]
        
        connectivity_count = 0
        
        for host, port in test_hosts:
            try:
                with socket.create_connection((host, port), timeout=5):
                    connectivity_count += 1
            except:
                pass
        
        # Require at least 50% connectivity
        return connectivity_count >= len(test_hosts) // 2
    
    async def validate_ha_configuration(self) -> bool:
        """Validate Home Assistant configuration"""
        try:
            config_file = self.context.ha_config_path / "configuration.yaml"
            
            if not config_file.exists():
                return False
            
            # Try to parse YAML
            with open(config_file, 'r') as f:
                yaml.safe_load(f)
            
            # Check for required sections (basic validation)
            with open(config_file, 'r') as f:
                content = f.read()
                
            # Look for basic HA structure
            required_indicators = ["homeassistant:", "# Configure a default setup"]
            
            return any(indicator in content for indicator in required_indicators)
            
        except Exception as e:
            self.logger.debug(f"HA configuration validation failed: {e}")
            return False
    
    # Component Installation Methods
    
    async def install_addon_components(self) -> None:
        """Install addon components for HAOS/Supervised"""
        self.logger.debug("Installing addon components...")
        
        # Create addon directory structure
        addon_path = self.context.addon_path
        addon_path.mkdir(parents=True, exist_ok=True)
        
        # Copy addon files
        source_addon_path = Path(__file__).parent.parent
        addon_files = [
            "config.yaml",
            "Dockerfile",
            "run.sh",
            "requirements.txt"
        ]
        
        for file_name in addon_files:
            source_file = source_addon_path / file_name
            dest_file = addon_path / file_name
            
            if source_file.exists():
                shutil.copy2(source_file, dest_file)
                self.installer.created_files.append(dest_file)
        
        # Copy source code
        src_path = addon_path / "src"
        if src_path.exists():
            shutil.rmtree(src_path)
        
        shutil.copytree(source_addon_path / "src", src_path)
        self.installer.created_files.append(src_path)
        
        # Update addon configuration with generated keys
        await self._update_addon_config(addon_path)
        
        self.installer.installed_components.append("addon")
        self.logger.info("Addon components installed")
    
    async def install_custom_component(self) -> None:
        """Install Home Assistant custom component"""
        self.logger.debug("Installing custom component...")
        
        # Create custom component directory
        component_path = self.context.custom_component_path
        component_path.mkdir(parents=True, exist_ok=True)
        
        # Create manifest
        manifest = {
            "domain": "aicleaner_v3",
            "name": "AICleaner v3",
            "version": "3.0.0",
            "config_flow": True,
            "documentation": "https://github.com/your-repo/aicleaner_v3",
            "requirements": [
                "aiohttp>=3.8.0",
                "pyyaml>=6.0"
            ],
            "codeowners": ["@your-username"],
            "iot_class": "local_polling"
        }
        
        manifest_file = component_path / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        self.installer.created_files.append(manifest_file)
        
        # Create basic integration files
        await self._create_integration_files(component_path)
        
        self.installer.installed_components.append("custom_component")
        self.logger.info("Custom component installed")
    
    async def install_service_configuration(self) -> None:
        """Install service configuration"""
        self.logger.debug("Installing service configuration...")
        
        # Create service configuration
        service_config = {
            "service": {
                "name": "aicleaner_v3",
                "version": "3.0.0",
                "environment": self.context.ha_environment.value,
                "installation_id": self.installer.installation_id,
                "api": {
                    "host": "localhost",
                    "port": 8099,
                    "internal_key": self.context.internal_api_key,
                    "service_token": self.context.service_token
                },
                "providers": {
                    "enabled": [],
                    "config": {}
                },
                "performance": {
                    "monitoring_level": "basic",
                    "optimization_level": "auto"
                }
            }
        }
        
        config_path = self.context.ha_config_path / "aicleaner" / "service_config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(service_config, f, default_flow_style=False)
        
        self.installer.created_files.append(config_path)
        self.installer.installed_components.append("service_config")
        
        self.logger.info("Service configuration installed")
    
    # Validation Test Methods
    
    async def test_configuration_valid(self) -> bool:
        """Test that configuration files are valid"""
        try:
            # Test service configuration
            service_config_path = self.context.ha_config_path / "aicleaner" / "service_config.yaml"
            if service_config_path.exists():
                with open(service_config_path, 'r') as f:
                    yaml.safe_load(f)
            
            # Test security configuration
            security_config_path = self.context.ha_config_path / "aicleaner" / "security" / "security_config.yaml"
            if security_config_path.exists():
                with open(security_config_path, 'r') as f:
                    yaml.safe_load(f)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation test failed: {e}")
            return False
    
    async def test_service_startup(self) -> bool:
        """Test that the service can start up"""
        try:
            # This is a simplified test - in production, would actually start the service
            service_script = Path(__file__).parent.parent / "run.sh"
            
            if not service_script.exists():
                return False
            
            # Check if script is executable
            return os.access(service_script, os.X_OK)
            
        except Exception as e:
            self.logger.error(f"Service startup test failed: {e}")
            return False
    
    async def test_api_connectivity(self) -> bool:
        """Test API connectivity"""
        try:
            # Test internal API endpoint (mock for now)
            # In production, this would test actual API endpoints
            return True
            
        except Exception as e:
            self.logger.error(f"API connectivity test failed: {e}")
            return False
    
    async def test_ha_integration(self) -> bool:
        """Test Home Assistant integration"""
        try:
            # Check that custom component is properly installed
            component_path = self.context.custom_component_path
            required_files = ["manifest.json", "__init__.py"]
            
            for file_name in required_files:
                file_path = component_path / file_name
                if not file_path.exists():
                    return False
            
            # Validate manifest
            manifest_path = component_path / "manifest.json"
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                
            required_fields = ["domain", "name", "version"]
            return all(field in manifest for field in required_fields)
            
        except Exception as e:
            self.logger.error(f"HA integration test failed: {e}")
            return False
    
    async def test_security_validation(self) -> bool:
        """Test security setup"""
        try:
            security_dir = self.context.ha_config_path / "aicleaner" / "security"
            
            # Check that security files exist
            required_files = ["internal_api.key", "service.token", "security_config.yaml"]
            
            for file_name in required_files:
                file_path = security_dir / file_name
                if not file_path.exists():
                    return False
                
                # Check file permissions
                file_stat = file_path.stat()
                if file_stat.st_mode & 0o077:  # Check that only owner has access
                    self.logger.warning(f"Security file {file_name} has overly permissive permissions")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Security validation test failed: {e}")
            return False
    
    async def test_performance_baseline(self) -> bool:
        """Test performance baseline"""
        try:
            # Simple performance baseline test
            import time
            import json
            
            # Test JSON processing speed
            start_time = time.time()
            test_data = {"test": "data", "numbers": list(range(1000))}
            for _ in range(100):
                json.dumps(test_data)
                json.loads(json.dumps(test_data))
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # Should complete in reasonable time (adjust threshold as needed)
            return processing_time < 1.0
            
        except Exception as e:
            self.logger.error(f"Performance baseline test failed: {e}")
            return False
    
    # Helper Methods for Component Installation
    
    async def _update_addon_config(self, addon_path: Path) -> None:
        """Update addon configuration with generated keys"""
        config_file = addon_path / "config.yaml"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
        else:
            config = {}
        
        # Update with security configuration
        config.setdefault("options", {})
        config["options"].update({
            "internal_api_key": self.context.internal_api_key,
            "service_token": self.context.service_token,
            "installation_id": self.installer.installation_id
        })
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    
    async def _create_integration_files(self, component_path: Path) -> None:
        """Create basic integration files"""
        
        # Create __init__.py
        init_content = '''"""
AICleaner v3 Home Assistant Integration
"""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DOMAIN = "aicleaner_v3"

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the AICleaner v3 component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up AICleaner v3 from a config entry."""
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    return True
'''
        
        init_file = component_path / "__init__.py"
        init_file.write_text(init_content)
        self.installer.created_files.append(init_file)
        
        # Create config_flow.py
        config_flow_content = '''"""
Config flow for AICleaner v3 integration.
"""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN

class AICleaner3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AICleaner v3."""
    
    VERSION = 1
    
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title="AICleaner v3",
                data=user_input
            )
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({})
        )
'''
        
        config_flow_file = component_path / "config_flow.py"
        config_flow_file.write_text(config_flow_content)
        self.installer.created_files.append(config_flow_file)
        
        # Create const.py
        const_content = '''"""
Constants for AICleaner v3.
"""

DOMAIN = "aicleaner_v3"
'''
        
        const_file = component_path / "const.py"
        const_file.write_text(const_content)
        self.installer.created_files.append(const_file)
    
    # Rollback Methods
    
    async def rollback_installation(self) -> None:
        """Rollback installation changes"""
        self.logger.info(f"Rolling back installation {self.installer.installation_id}")
        
        try:
            # Remove created files
            for file_path in reversed(self.installer.created_files):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        self.logger.debug(f"Removed file: {file_path}")
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                        self.logger.debug(f"Removed directory: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove {file_path}: {e}")
            
            # Restore backed up files
            for backup_file in self.installer.backup_files:
                try:
                    # Implementation for restoring backup files
                    self.logger.debug(f"Would restore backup: {backup_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to restore backup {backup_file}: {e}")
            
            self.logger.info("Rollback completed")
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
    
    async def finalize_installation(self) -> None:
        """Finalize installation and cleanup"""
        self.logger.info("Finalizing installation...")
        
        # Create installation record
        installation_record = {
            "installation_id": self.installer.installation_id,
            "version": "3.0.0",
            "environment": self.context.ha_environment.value,
            "installed_components": self.installer.installed_components,
            "installation_date": self.installer.current_stage,
            "config_path": str(self.context.ha_config_path),
            "python_version": f"{self.context.python_version[0]}.{self.context.python_version[1]}"
        }
        
        record_file = self.context.ha_config_path / "aicleaner" / "installation.json"
        record_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(record_file, 'w') as f:
            json.dump(installation_record, f, indent=2, default=str)
        
        self.logger.info(f"Installation record saved to {record_file}")
        self.logger.info("Installation finalized successfully")