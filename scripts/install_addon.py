#!/usr/bin/env python3
"""
AICleaner v3 Smart Installation Script
Implements "Intelligent Simplicity" - adaptive installer with environment detection

This script provides one-click installation across all Home Assistant environments:
- Home Assistant OS (HAOS)
- Home Assistant Supervised
- Home Assistant Core
- Home Assistant Container

Features:
- Automatic environment detection
- Pre-flight validation
- Secure key generation
- Rollback on failure
- Comprehensive validation
"""

import os
import sys
import json
import asyncio
import logging
import platform
import subprocess
import shutil
import tempfile
import secrets
import hashlib
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class HAEnvironment(Enum):
    """Home Assistant environment types"""
    HAOS = "haos"
    SUPERVISED = "supervised"
    CORE = "core"
    CONTAINER = "container"
    UNKNOWN = "unknown"


class InstallationStage(Enum):
    """Installation stages for progress tracking"""
    DETECTION = "environment_detection"
    VALIDATION = "prerequisite_validation"
    SECURITY = "security_setup"
    INSTALLATION = "component_installation"
    TESTING = "validation_testing"
    COMPLETION = "completion"


@dataclass
class InstallationContext:
    """Context information for the installation"""
    ha_environment: HAEnvironment
    ha_version: Optional[str]
    ha_config_path: Path
    python_version: Tuple[int, int]
    available_memory_gb: float
    docker_available: bool
    supervisor_available: bool
    addon_store_available: bool
    
    # Security context
    internal_api_key: str
    service_token: str
    
    # Installation paths
    addon_path: Optional[Path]
    custom_component_path: Optional[Path]
    backup_path: Path


class SmartInstaller:
    """
    Smart installer implementing Intelligent Simplicity philosophy
    
    Provides:
    - Automatic environment detection
    - Adaptive installation strategy
    - Comprehensive validation
    - Graceful error handling with rollback
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Installation state
        self.context: Optional[InstallationContext] = None
        self.installation_id = secrets.token_hex(8)
        self.backup_files: List[Path] = []
        self.created_files: List[Path] = []
        self.installed_components: List[str] = []
        
        # Progress tracking
        self.current_stage = InstallationStage.DETECTION
        self.stage_progress = {}
        
        # Rollback state
        self._rollback_prepared = False
        self._original_state: Dict[str, Any] = {}
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the installer"""
        logger = logging.getLogger("aicleaner_installer")
        
        # Create logs directory
        log_dir = Path("/tmp/aicleaner_install_logs")
        log_dir.mkdir(exist_ok=True)
        
        # Setup file handler
        log_file = log_dir / f"install_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Setup formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)
        
        return logger
    
    async def install(self, progress_callback=None) -> bool:
        """
        Main installation method
        
        Args:
            progress_callback: Optional callback for progress updates (stage, progress)
        
        Returns:
            bool: Installation success
        """
        try:
            self.logger.info(f"Starting AICleaner v3 installation (ID: {self.installation_id})")
            
            # Stage 1: Environment Detection
            await self._update_progress(InstallationStage.DETECTION, 0.0, progress_callback)
            
            self.logger.info("Detecting Home Assistant environment...")
            self.context = await self._detect_environment()
            
            if self.context.ha_environment == HAEnvironment.UNKNOWN:
                raise RuntimeError("Unable to detect Home Assistant environment")
            
            self.logger.info(f"Detected environment: {self.context.ha_environment.value}")
            await self._update_progress(InstallationStage.DETECTION, 1.0, progress_callback)
            
            # Stage 2: Prerequisites Validation
            await self._update_progress(InstallationStage.VALIDATION, 0.0, progress_callback)
            
            self.logger.info("Validating prerequisites...")
            validation_result = await self._validate_prerequisites()
            
            if not validation_result["success"]:
                raise RuntimeError(f"Prerequisites validation failed: {validation_result['errors']}")
            
            await self._update_progress(InstallationStage.VALIDATION, 1.0, progress_callback)
            
            # Stage 3: Security Setup
            await self._update_progress(InstallationStage.SECURITY, 0.0, progress_callback)
            
            self.logger.info("Setting up security...")
            await self._setup_security()
            await self._update_progress(InstallationStage.SECURITY, 1.0, progress_callback)
            
            # Stage 4: Component Installation
            await self._update_progress(InstallationStage.INSTALLATION, 0.0, progress_callback)
            
            self.logger.info("Installing components...")
            await self._install_components()
            await self._update_progress(InstallationStage.INSTALLATION, 1.0, progress_callback)
            
            # Stage 5: Validation Testing
            await self._update_progress(InstallationStage.TESTING, 0.0, progress_callback)
            
            self.logger.info("Running validation tests...")
            test_result = await self._run_validation_tests()
            
            if not test_result["success"]:
                raise RuntimeError(f"Validation tests failed: {test_result['failures']}")
            
            await self._update_progress(InstallationStage.TESTING, 1.0, progress_callback)
            
            # Stage 6: Completion
            await self._update_progress(InstallationStage.COMPLETION, 1.0, progress_callback)
            
            self.logger.info("Installation completed successfully!")
            await self._finalize_installation()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            
            # Attempt rollback
            await self._rollback_installation()
            
            return False
    
    async def _detect_environment(self) -> InstallationContext:
        """
        Detect Home Assistant environment and gather system information
        
        Returns:
            InstallationContext with detected environment details
        """
        self.logger.debug("Starting environment detection...")
        
        # Check for Home Assistant OS
        if await self._check_haos():
            ha_env = HAEnvironment.HAOS
            ha_config_path = Path("/homeassistant")
        
        # Check for Home Assistant Supervised
        elif await self._check_supervised():
            ha_env = HAEnvironment.SUPERVISED
            ha_config_path = Path("/usr/share/hassio/homeassistant")
        
        # Check for Home Assistant Core
        elif await self._check_core():
            ha_env = HAEnvironment.CORE
            ha_config_path = await self._find_ha_config_path()
        
        # Check for Home Assistant Container
        elif await self._check_container():
            ha_env = HAEnvironment.CONTAINER
            ha_config_path = Path("/config")
        
        else:
            ha_env = HAEnvironment.UNKNOWN
            ha_config_path = Path("/tmp")
        
        # Gather system information
        system_info = await self._gather_system_info()
        
        # Generate security keys
        internal_api_key = secrets.token_urlsafe(32)
        service_token = secrets.token_hex(16)
        
        # Determine installation paths
        addon_path, custom_component_path = await self._determine_installation_paths(
            ha_env, ha_config_path
        )
        
        context = InstallationContext(
            ha_environment=ha_env,
            ha_version=await self._get_ha_version(),
            ha_config_path=ha_config_path,
            python_version=system_info["python_version"],
            available_memory_gb=system_info["available_memory_gb"],
            docker_available=system_info["docker_available"],
            supervisor_available=system_info["supervisor_available"],
            addon_store_available=system_info["addon_store_available"],
            internal_api_key=internal_api_key,
            service_token=service_token,
            addon_path=addon_path,
            custom_component_path=custom_component_path,
            backup_path=Path(f"/tmp/aicleaner_backup_{self.installation_id}")
        )
        
        self.logger.debug(f"Environment detection complete: {ha_env.value}")
        return context
    
    async def _validate_prerequisites(self) -> Dict[str, Any]:
        """
        Validate system prerequisites
        
        Returns:
            Dict with validation results
        """
        results = {"success": True, "errors": [], "warnings": []}
        
        # Python version check
        min_python = (3, 9)
        if self.context.python_version < min_python:
            results["errors"].append(
                f"Python {min_python[0]}.{min_python[1]}+ required, "
                f"found {self.context.python_version[0]}.{self.context.python_version[1]}"
            )
        
        # Memory check
        min_memory_gb = 1.0
        if self.context.available_memory_gb < min_memory_gb:
            results["errors"].append(
                f"Minimum {min_memory_gb}GB RAM required, "
                f"found {self.context.available_memory_gb:.1f}GB"
            )
        elif self.context.available_memory_gb < 2.0:
            results["warnings"].append(
                f"Limited memory detected ({self.context.available_memory_gb:.1f}GB). "
                "Performance may be reduced."
            )
        
        # Disk space check
        required_space_mb = 500
        available_space = await self._get_available_disk_space(self.context.ha_config_path)
        if available_space < required_space_mb:
            results["errors"].append(
                f"Minimum {required_space_mb}MB disk space required, "
                f"found {available_space}MB"
            )
        
        # Write permission check
        if not await self._check_write_permissions():
            results["errors"].append("Insufficient write permissions to Home Assistant directories")
        
        # Network connectivity check
        if not await self._check_network_connectivity():
            results["warnings"].append("Limited network connectivity detected")
        
        # Home Assistant configuration validation
        ha_config_valid = await self._validate_ha_configuration()
        if not ha_config_valid:
            results["warnings"].append("Home Assistant configuration may need manual updates")
        
        if results["errors"]:
            results["success"] = False
        
        # Log results
        if results["errors"]:
            self.logger.error(f"Prerequisites validation failed: {results['errors']}")
        if results["warnings"]:
            self.logger.warning(f"Prerequisites warnings: {results['warnings']}")
        
        return results
    
    async def _setup_security(self) -> None:
        """
        Setup security components
        """
        self.logger.debug("Setting up security...")
        
        # Create secure directories
        security_dir = self.context.ha_config_path / "aicleaner" / "security"
        security_dir.mkdir(parents=True, exist_ok=True)
        
        # Set directory permissions
        os.chmod(security_dir, 0o700)
        
        # Generate and store internal API key
        api_key_file = security_dir / "internal_api.key"
        api_key_file.write_text(self.context.internal_api_key)
        os.chmod(api_key_file, 0o600)
        
        # Generate and store service token
        token_file = security_dir / "service.token"
        token_file.write_text(self.context.service_token)
        os.chmod(token_file, 0o600)
        
        # Create security configuration
        security_config = {
            "version": "1.0",
            "installation_id": self.installation_id,
            "created": datetime.now().isoformat(),
            "environment": self.context.ha_environment.value,
            "key_rotation_enabled": True,
            "key_rotation_interval_days": 30
        }
        
        config_file = security_dir / "security_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(security_config, f, default_flow_style=False)
        
        os.chmod(config_file, 0o600)
        
        # Track created files for rollback
        self.created_files.extend([api_key_file, token_file, config_file])
        
        self.logger.info("Security setup completed")
    
    async def _install_components(self) -> None:
        """
        Install AICleaner components based on detected environment
        """
        self.logger.debug(f"Installing components for {self.context.ha_environment.value}")
        
        # Install based on environment type
        if self.context.ha_environment in [HAEnvironment.HAOS, HAEnvironment.SUPERVISED]:
            await self._install_addon_components()
        
        # Always install custom component for HA integration
        await self._install_custom_component()
        
        # Install service configuration
        await self._install_service_configuration()
        
        self.logger.info("Component installation completed")
    
    async def _run_validation_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive validation tests
        
        Returns:
            Dict with test results
        """
        results = {"success": True, "failures": [], "passed": []}
        
        tests = [
            ("configuration_valid", self._test_configuration_valid),
            ("service_startup", self._test_service_startup),
            ("api_connectivity", self._test_api_connectivity),
            ("ha_integration", self._test_ha_integration),
            ("security_validation", self._test_security_validation),
            ("performance_baseline", self._test_performance_baseline)
        ]
        
        for test_name, test_func in tests:
            try:
                self.logger.debug(f"Running test: {test_name}")
                test_result = await test_func()
                
                if test_result:
                    results["passed"].append(test_name)
                    self.logger.debug(f"Test passed: {test_name}")
                else:
                    results["failures"].append(test_name)
                    self.logger.warning(f"Test failed: {test_name}")
                    
            except Exception as e:
                results["failures"].append(f"{test_name}: {str(e)}")
                self.logger.error(f"Test error in {test_name}: {e}")
        
        if results["failures"]:
            results["success"] = False
        
        return results
    
    # Environment Detection Methods
    
    async def _check_haos(self) -> bool:
        """Check if running on Home Assistant OS"""
        return (
            Path("/usr/sbin/hassos-config").exists() or
            os.environ.get("HASSIO", "").lower() == "true"
        )
    
    async def _check_supervised(self) -> bool:
        """Check if running on Home Assistant Supervised"""
        return (
            Path("/usr/bin/ha").exists() and
            Path("/usr/share/hassio").exists()
        )
    
    async def _check_core(self) -> bool:
        """Check if running on Home Assistant Core"""
        try:
            import homeassistant
            return True
        except ImportError:
            # Check for typical HA Core installation locations
            core_paths = [
                Path.home() / ".homeassistant",
                Path("/srv/homeassistant"),
                Path("/opt/homeassistant")
            ]
            return any(path.exists() for path in core_paths)
    
    async def _check_container(self) -> bool:
        """Check if running in Home Assistant Container"""
        return (
            Path("/.dockerenv").exists() and
            Path("/config").exists()
        )
    
    async def _gather_system_info(self) -> Dict[str, Any]:
        """Gather system information"""
        import psutil
        
        # Python version
        python_version = (sys.version_info.major, sys.version_info.minor)
        
        # Memory info
        memory = psutil.virtual_memory()
        available_memory_gb = memory.available / (1024 ** 3)
        
        # Docker availability
        docker_available = shutil.which("docker") is not None
        
        # Supervisor availability
        supervisor_available = Path("/usr/bin/ha").exists()
        
        # Addon store availability
        addon_store_available = (
            supervisor_available and
            Path("/usr/share/hassio/addons").exists()
        )
        
        return {
            "python_version": python_version,
            "available_memory_gb": available_memory_gb,
            "docker_available": docker_available,
            "supervisor_available": supervisor_available,
            "addon_store_available": addon_store_available,
            "platform": platform.system(),
            "architecture": platform.machine()
        }
    
    # Helper Methods (continued in next message due to length...)
    
    async def _update_progress(self, stage: InstallationStage, progress: float, callback=None):
        """Update installation progress"""
        self.current_stage = stage
        self.stage_progress[stage] = progress
        
        if callback:
            callback(stage, progress)
        
        self.logger.debug(f"Progress: {stage.value} - {progress*100:.1f}%")


# Entry point for command-line usage
async def main():
    """Main entry point for the installer"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AICleaner v3 Smart Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install_addon.py                    # Interactive installation
  python install_addon.py --auto             # Automatic installation
  python install_addon.py --validate-only    # Validation only
        """
    )
    
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run automatic installation without prompts"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run validation checks only, do not install"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to installation configuration file"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level"
    )
    
    args = parser.parse_args()
    
    # Load configuration if provided
    config = {}
    if args.config:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    
    # Create installer
    installer = SmartInstaller(config)
    
    # Set log level
    installer.logger.setLevel(getattr(logging, args.log_level))
    
    # Progress callback
    def progress_callback(stage, progress):
        print(f"\r{stage.value}: {progress*100:.1f}%", end="", flush=True)
    
    try:
        if args.validate_only:
            # Run validation only
            context = await installer._detect_environment()
            installer.context = context
            
            validation_result = await installer._validate_prerequisites()
            
            if validation_result["success"]:
                print("\n✅ All prerequisites validated successfully!")
                if validation_result["warnings"]:
                    print("⚠️  Warnings:")
                    for warning in validation_result["warnings"]:
                        print(f"   - {warning}")
                return 0
            else:
                print("\n❌ Prerequisites validation failed!")
                print("Errors:")
                for error in validation_result["errors"]:
                    print(f"   - {error}")
                return 1
        
        else:
            # Run full installation
            if not args.auto:
                print("AICleaner v3 Smart Installer")
                print("============================")
                print()
                response = input("Continue with installation? [y/N]: ")
                if response.lower() not in ["y", "yes"]:
                    print("Installation cancelled.")
                    return 0
            
            success = await installer.install(progress_callback)
            
            print()  # New line after progress
            
            if success:
                print("✅ Installation completed successfully!")
                print()
                print("Next steps:")
                print("1. Restart Home Assistant")
                print("2. Check the AICleaner integration in Settings > Integrations")
                print("3. Configure your AI providers in the AICleaner settings")
                return 0
            else:
                print("❌ Installation failed!")
                print("Check the logs in /tmp/aicleaner_install_logs/ for details.")
                return 1
    
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        return 130
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))