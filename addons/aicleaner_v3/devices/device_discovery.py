"""
Phase 3A: Device Detection Enhancement - Device Discovery Manager
Comprehensive multi-protocol device discovery system with automated classification.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any

from .protocols import zeroconf_discovery, upnp_discovery, ble_discovery, ip_scan_discovery
from .capability_analysis import CapabilityAnalyzer
from .onboarding import OnboardingManager
from .error_reporting import ErrorReporter
from .ha_integration import register_device_in_ha

_LOGGER = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Enhanced device information with complete metadata."""
    # Core identification
    mac_address: str
    ip_address: str
    device_type: str
    discovery_protocol: str

    # Enhanced metadata
    device_name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None

    # Discovery context
    discovery_time: datetime = field(default_factory=datetime.now)
    signal_strength: Optional[float] = None
    port_info: Dict[int, str] = field(default_factory=dict)
    services: List[str] = field(default_factory=list)

    # Analysis results
    capabilities: Dict[str, Any] = field(default_factory=dict)
    compatibility_score: float = 0.0
    suggested_integrations: List[str] = field(default_factory=list)

    # State tracking
    last_seen: datetime = field(default_factory=datetime.now)
    availability_status: str = "unknown"

    # Raw data
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'mac_address': self.mac_address,
            'ip_address': self.ip_address,
            'device_type': self.device_type,
            'discovery_protocol': self.discovery_protocol,
            'device_name': self.device_name,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'firmware_version': self.firmware_version,
            'discovery_time': self.discovery_time.isoformat(),
            'signal_strength': self.signal_strength,
            'port_info': self.port_info,
            'services': self.services,
            'capabilities': self.capabilities,
            'compatibility_score': self.compatibility_score,
            'suggested_integrations': self.suggested_integrations,
            'last_seen': self.last_seen.isoformat(),
            'availability_status': self.availability_status
        }


class DeviceDiscoveryManager:
    """
    Main device discovery manager coordinating all discovery protocols.
    Provides comprehensive multi-protocol device discovery with automated classification.
    """

    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.discovery_protocols = []
        self.running = False
        self.discovered_devices = {}  # MAC -> DeviceInfo
        
        # Initialize components
        self.capability_analyzer = CapabilityAnalyzer(hass, config)
        self.onboarding_manager = OnboardingManager(hass, config)
        self.error_reporter = ErrorReporter(hass)
        
        # Discovery statistics
        self.discovery_stats = {
            'devices_discovered': 0,
            'protocols_active': 0,
            'last_discovery_time': None,
            'discovery_duration': 0.0
        }

    async def start_discovery(self) -> Dict[str, Any]:
        """
        Start comprehensive device discovery across all enabled protocols.
        
        Returns:
            Discovery results with statistics and discovered devices
        """
        discovery_start_time = datetime.now()
        self.running = True
        self.discovery_protocols = []

        _LOGGER.info("Starting comprehensive device discovery...")

        # Initialize enabled protocols
        if self.config.get('zeroconf_enabled', True):
            self.discovery_protocols.append(
                zeroconf_discovery.ZeroconfDiscovery(self.hass, self.config, self)
            )
        if self.config.get('upnp_enabled', True):
            self.discovery_protocols.append(
                upnp_discovery.UPnPDiscovery(self.hass, self.config, self)
            )
        if self.config.get('ble_enabled', True):
            self.discovery_protocols.append(
                ble_discovery.BleDiscovery(self.hass, self.config, self)
            )
        if self.config.get('ip_scan_enabled', True):
            self.discovery_protocols.append(
                ip_scan_discovery.IPScanDiscovery(self.hass, self.config, self)
            )

        self.discovery_stats['protocols_active'] = len(self.discovery_protocols)
        
        _LOGGER.info(f"Starting device discovery with protocols: {[p.__class__.__name__ for p in self.discovery_protocols]}")

        # Phase 2C Integration: Start discovery monitoring
        if 'ai_performance_monitor' in self.hass.data:
            self.hass.data['ai_performance_monitor'].track_request(
                f"device_discovery_{discovery_start_time.timestamp()}",
                "device_discovery",
                {'protocols': len(self.discovery_protocols)}
            )

        async def run_protocol(protocol):
            """Run individual protocol discovery with error handling."""
            try:
                await protocol.discover_devices()
            except Exception as e:
                _LOGGER.exception(f"Error running {protocol.__class__.__name__}: {e}")
                self.error_reporter.report_error(
                    "device_discovery_failure",
                    f"Error during {protocol.__class__.__name__}: {e}",
                    {'protocol': protocol.__class__.__name__}
                )

        # Run all protocols concurrently
        tasks = [run_protocol(protocol) for protocol in self.discovery_protocols]
        await asyncio.gather(*tasks)
        
        # Finalize discovery
        discovery_end_time = datetime.now()
        self.discovery_stats['last_discovery_time'] = discovery_end_time
        self.discovery_stats['discovery_duration'] = (discovery_end_time - discovery_start_time).total_seconds()
        self.running = False

        # Phase 2C Integration: Complete discovery monitoring
        if 'ai_performance_monitor' in self.hass.data:
            self.hass.data['ai_performance_monitor'].complete_request(
                f"device_discovery_{discovery_start_time.timestamp()}",
                True,
                {
                    'devices_found': len(self.discovered_devices),
                    'discovery_duration': self.discovery_stats['discovery_duration'],
                    'protocols_used': len(self.discovery_protocols)
                }
            )

        _LOGGER.info(f"Device discovery completed. Found {len(self.discovered_devices)} devices in {self.discovery_stats['discovery_duration']:.2f}s")

        return {
            'success': True,
            'devices_discovered': len(self.discovered_devices),
            'discovery_duration': self.discovery_stats['discovery_duration'],
            'protocols_active': self.discovery_stats['protocols_active'],
            'devices': [device.to_dict() for device in self.discovered_devices.values()]
        }

    async def stop_discovery(self):
        """Stop all running discovery protocols."""
        _LOGGER.info("Stopping device discovery.")
        self.running = False
        
        for protocol in self.discovery_protocols:
            if hasattr(protocol, 'stop'):
                try:
                    await protocol.stop()
                except Exception as e:
                    _LOGGER.error(f"Error stopping {protocol.__class__.__name__}: {e}")

    async def register_device(self, device_info: DeviceInfo):
        """
        Register a discovered device with comprehensive processing.
        
        Args:
            device_info: Device information from discovery protocol
        """
        _LOGGER.info(f"New device discovered: {device_info.mac_address} via {device_info.discovery_protocol}")
        
        try:
            # Avoid duplicate registration
            if device_info.mac_address in self.discovered_devices:
                existing_device = self.discovered_devices[device_info.mac_address]
                existing_device.last_seen = datetime.now()
                existing_device.availability_status = "available"
                _LOGGER.debug(f"Updated existing device: {device_info.mac_address}")
                return

            # Phase 2C Integration: Report device discovery event
            if 'ai_performance_monitor' in self.hass.data:
                self.hass.data['ai_performance_monitor'].record_cache_hit()  # Device discovery success

            # Perform capability analysis
            capabilities = await self.capability_analyzer.analyze_capabilities(device_info)
            device_info.capabilities = capabilities
            
            # Calculate compatibility score
            device_info.compatibility_score = self._calculate_compatibility_score(device_info)
            
            # Store discovered device
            self.discovered_devices[device_info.mac_address] = device_info
            self.discovery_stats['devices_discovered'] += 1

            # Start device onboarding process
            await self.onboarding_manager.onboard_device(device_info)
            
            # Register with Home Assistant device registry
            await register_device_in_ha(self.hass, device_info)

            _LOGGER.info(f"Device successfully registered: {device_info.mac_address} ({device_info.device_name or device_info.device_type})")

        except Exception as e:
            _LOGGER.exception(f"Error registering device {device_info.mac_address}: {e}")
            self.error_reporter.report_error(
                "device_registration_failure",
                f"Failed to register {device_info.mac_address}: {e}",
                {'device_info': device_info.to_dict()}
            )

    def _calculate_compatibility_score(self, device_info: DeviceInfo) -> float:
        """Calculate compatibility score based on device capabilities and HA integration support."""
        score = 0.0
        
        # Base score for successful discovery
        score += 0.3
        
        # Score for known device type
        if device_info.device_type != "Unknown":
            score += 0.2
        
        # Score for manufacturer identification
        if device_info.manufacturer:
            score += 0.1
        
        # Score for capabilities detection
        if device_info.capabilities:
            score += 0.2 * min(1.0, len(device_info.capabilities) / 5.0)
        
        # Score for integration suggestions
        if device_info.suggested_integrations:
            score += 0.2
        
        return min(1.0, score)

    async def get_device_status(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Get current status of a discovered device."""
        if mac_address in self.discovered_devices:
            device = self.discovered_devices[mac_address]
            return {
                'device_info': device.to_dict(),
                'online': (datetime.now() - device.last_seen).total_seconds() < 300,  # 5 minutes
                'capabilities_detected': len(device.capabilities),
                'compatibility_score': device.compatibility_score
            }
        return None

    def get_discovery_statistics(self) -> Dict[str, Any]:
        """Get comprehensive discovery statistics."""
        return {
            'total_devices_discovered': self.discovery_stats['devices_discovered'],
            'protocols_active': self.discovery_stats['protocols_active'],
            'last_discovery_time': self.discovery_stats['last_discovery_time'].isoformat() if self.discovery_stats['last_discovery_time'] else None,
            'discovery_duration': self.discovery_stats['discovery_duration'],
            'currently_running': self.running,
            'devices_by_protocol': self._get_devices_by_protocol(),
            'devices_by_type': self._get_devices_by_type(),
            'average_compatibility_score': self._get_average_compatibility_score()
        }

    def _get_devices_by_protocol(self) -> Dict[str, int]:
        """Get device count by discovery protocol."""
        protocol_counts = {}
        for device in self.discovered_devices.values():
            protocol = device.discovery_protocol
            protocol_counts[protocol] = protocol_counts.get(protocol, 0) + 1
        return protocol_counts

    def _get_devices_by_type(self) -> Dict[str, int]:
        """Get device count by device type."""
        type_counts = {}
        for device in self.discovered_devices.values():
            device_type = device.device_type
            type_counts[device_type] = type_counts.get(device_type, 0) + 1
        return type_counts

    def _get_average_compatibility_score(self) -> float:
        """Get average compatibility score across all devices."""
        if not self.discovered_devices:
            return 0.0
        
        total_score = sum(device.compatibility_score for device in self.discovered_devices.values())
        return total_score / len(self.discovered_devices)

    async def refresh_device_states(self):
        """Refresh availability status for all discovered devices."""
        _LOGGER.info("Refreshing device states...")
        
        refresh_tasks = []
        for device in self.discovered_devices.values():
            refresh_tasks.append(self._refresh_single_device_state(device))
        
        await asyncio.gather(*refresh_tasks, return_exceptions=True)
        _LOGGER.info("Device state refresh completed")

    async def _refresh_single_device_state(self, device: DeviceInfo):
        """Refresh state for a single device."""
        try:
            # Simple ping test for availability
            import subprocess
            result = await asyncio.create_subprocess_exec(
                'ping', '-n', '1', '-w', '1000', device.ip_address,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await result.wait()
            
            if result.returncode == 0:
                device.availability_status = "available"
                device.last_seen = datetime.now()
            else:
                device.availability_status = "unavailable"
                
        except Exception as e:
            _LOGGER.debug(f"Error refreshing state for {device.mac_address}: {e}")
            device.availability_status = "unknown"


# Example usage and testing
if __name__ == "__main__":
    async def test_device_discovery():
        """Test device discovery system."""
        
        # Mock Home Assistant object
        class MockHass:
            def __init__(self):
                self.data = {}
        
        hass = MockHass()
        config = {
            'zeroconf_enabled': True,
            'upnp_enabled': True,
            'ble_enabled': False,  # Disable BLE for testing
            'ip_scan_enabled': True
        }
        
        # Initialize discovery manager
        discovery_manager = DeviceDiscoveryManager(hass, config)
        
        # Test device registration
        test_device = DeviceInfo(
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.100",
            device_type="Smart Light",
            discovery_protocol="Test",
            device_name="Test Smart Light",
            manufacturer="Test Manufacturer"
        )
        
        await discovery_manager.register_device(test_device)
        
        # Get statistics
        stats = discovery_manager.get_discovery_statistics()
        print(f"Discovery Statistics: {stats}")
        
        # Check device status
        status = await discovery_manager.get_device_status("00:11:22:33:44:55")
        print(f"Device Status: {status}")
    
    # Run test
    asyncio.run(test_device_discovery())