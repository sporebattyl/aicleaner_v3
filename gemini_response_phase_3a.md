Okay, I understand the requirements for Phase 3A of AICleaner v3. This is a substantial task involving device detection enhancement. I will work with Claude to create a comprehensive implementation plan, generate code diffs, provide integration notes, define a testing strategy, and outline the necessary documentation.

**1. IMPLEMENTATION PLAN**

The implementation will involve creating new modules and modifying existing ones within the `X:\aicleaner_v3\addons\aicleaner_v3\` directory.  Here's a breakdown of the plan and file structure. I will collaborate with Claude to refine the following, and create the necessary files, with code diffs detailed below.

*   **Core Modules:**

    *   `device_discovery.py`:  Central module for device discovery. Contains the `DeviceDiscoveryManager` class, which orchestrates the different discovery protocols.
    *   `protocols/`: Directory containing individual protocol implementations.
        *   `protocols/zeroconf_discovery.py`: Zeroconf/mDNS discovery implementation.
        *   `protocols/upnp_discovery.py`: SSDP/UPnP discovery implementation.
        *   `protocols/ble_discovery.py`: Bluetooth LE discovery implementation.
        *   `protocols/ip_scan_discovery.py`: IP subnet scanning implementation.
    *   `capability_analysis.py`: Module for device capability analysis. Contains the `CapabilityAnalyzer` class.
    *   `device_state.py`: Module for real-time device state monitoring. Contains the `DeviceStateManager` class.
    *   `onboarding.py`: Module for automated device onboarding. Contains the `OnboardingManager` class.
    *   `database/device_database.py`: Module managing the device signature database.
    *   `error_reporting.py`: Handles user-facing error reporting.
    *   `logging_config.py`: Configures structured logging.
    *   `security.py`: Implements security measures.
    *   `metrics.py`: Collects and reports performance metrics.
*   **Configuration and Integration:**

    *   `config_flow.py`:  (Modified) Updates the configuration flow to include device detection settings.
    *   `__init__.py`: (Modified) Integrates the new modules into the AICleaner v3 addon.
    *   `ha_integration.py`: Integrates detected devices with the Home Assistant device registry.

*   **Testing:**

    *   `tests/`: Directory containing unit and integration tests.
        *   `tests/test_device_discovery.py`: Tests for the `device_discovery.py` module.
        *   `tests/test_capability_analysis.py`: Tests for the `capability_analysis.py` module.
        *   `tests/test_device_state.py`: Tests for the `device_state.py` module.
        *   `tests/test_onboarding.py`: Tests for the `onboarding.py` module.

**Detailed Breakdown:**

1.  **`device_discovery.py`**:
    *   `DeviceDiscoveryManager`:
        *   Initializes with a list of enabled discovery protocols.
        *   `start_discovery()`: Starts all enabled discovery protocols in parallel using `asyncio.gather`.
        *   `stop_discovery()`: Stops all running discovery protocols.
        *   `register_device(device_info)`: Registers a discovered device, triggering capability analysis and onboarding.
    *   Configuration options for enabling/disabling specific discovery methods in `config_flow.py`.
    *   Integrates with `error_reporting.py` to report discovery failures.

2.  **`protocols/`**:
    *   Each protocol implementation (e.g., `zeroconf_discovery.py`, `upnp_discovery.py`, etc.) will:
        *   Implement an `async` `discover_devices()` function that performs the device discovery using the appropriate protocol libraries (e.g., `zeroconf`, `upnpclient`, `bleak`, `python-nmap`).
        *   Handle protocol-specific errors and timeouts.
        *   Return a list of `DeviceInfo` objects, which contain standardized information about discovered devices (MAC address, IP address, device type, etc.).
    *   Leverage `security.py` for secure scanning (e.g., encrypted Bluetooth communication if available).

3.  **`capability_analysis.py`**:
    *   `CapabilityAnalyzer`:
        *   `analyze_capabilities(device_info)`: Analyzes a device's capabilities by inspecting its API endpoints, service descriptions, etc.
        *   Uses a device signature database (`database/device_database.py`) to identify known device types and capabilities.
        *   Generates a device profile containing the detected capabilities.
        *   Implements feature compatibility assessment based on the device profile.
    *   Integrates with `metrics.py` to track capability detection accuracy.

4.  **`device_state.py`**:
    *   `DeviceStateManager`:
        *   `start_monitoring(device_info)`: Starts monitoring the state of a discovered device using protocol-specific methods.
        *   Detects state changes and updates the HA entity registry via `ha_integration.py`.
        *   Implements availability detection (e.g., pinging the device, checking its connection status).
        *   Handles connection health monitoring.
    *   Leverages `logging_config.py` for detailed state monitoring logs.

5.  **`onboarding.py`**:
    *   `OnboardingManager`:
        *   `onboard_device(device_info)`: Automates the device onboarding process by generating configuration snippets, recommending integrations, and guiding the user through the setup.
        *   Uses a setup wizard (likely implemented within the HA frontend via a custom panel).
        *   Validates the generated configuration.
    *   Integrates with `error_reporting.py` to report onboarding failures and provide recovery guidance.

6.  **`database/device_database.py`**:
    *   Manages the device signature database, which contains information about known device types and their capabilities.
    *   Provides methods for querying the database, adding new device signatures, and updating existing ones.
    *   The database can be a simple JSON file or a more sophisticated database like SQLite.

7.  **`error_reporting.py`**:
    *   Handles user-facing error reporting according to the progressive error disclosure strategy.
    *   Provides simple error messages for end users, detailed status information for troubleshooting, and comprehensive logs for developers.
    *   Includes a "Copy Device Detection Details" button for easy sharing of device information.

8.  **`logging_config.py`**:
    *   Configures structured JSON logging using Python's `logging` module.
    *   Defines log levels (DEBUG, INFO, WARN, ERROR, CRITICAL) and log format standards.
    *   Includes contextual information in the logs (device MAC address, IP address, discovery protocol, etc.).

9.  **`security.py`**:
    *   Implements security measures to protect against malicious device spoofing and network attacks.
    *   Uses secure device discovery protocols where supported (e.g., encrypted Bluetooth communication).
    *   Validates device authentication and authorization.

10. **`metrics.py`**:
    *   Collects and reports performance metrics, such as device discovery success rate, detection speed, capability analysis accuracy, and onboarding success rate.
    *   Provides performance baselines for comparison.
    *   Integrates with HA system health for device detection status monitoring.

11. **`config_flow.py`**:
    *   (Modified) Adds configuration options to enable/disable specific device discovery protocols.
    *   Allows the user to configure network scanning parameters.
    *   Provides options for configuring logging levels.

12. **`ha_integration.py`**:
    *   Integrates the detected devices with the Home Assistant device registry.
    *   Creates HA entities for each detected device, representing its capabilities and state.
    *   Handles state updates from the `device_state.py` module.

**2. CODE DIFFS**

I will provide code diffs for all files mentioned above. These are not complete working examples but are intended to give a good overview of the scope of each file and a representative example of changes. These are intended to be a starting point and I will work with Claude to create the rest of the required files and fill out the functionality.

***

**`device_discovery.py`**

```diff
 --- a/aicleaner_v3/device_discovery.py
 +++ b/aicleaner_v3/device_discovery.py
 @@ -1,10 +1,25 @@
 import asyncio
+import logging
+
+from .protocols import zeroconf_discovery, upnp_discovery, ble_discovery, ip_scan_discovery
+from .capability_analysis import CapabilityAnalyzer
+from .onboarding import OnboardingManager
+from .error_reporting import ErrorReporter
+
+_LOGGER = logging.getLogger(__name__)
+
+class DeviceInfo: # Placeholder for device information object
+    def __init__(self, mac_address, ip_address, device_type, discovery_protocol, raw_data=None):
+        self.mac_address = mac_address
+        self.ip_address = ip_address
+        self.device_type = device_type
+        self.discovery_protocol = discovery_protocol
+        self.raw_data = raw_data  # Store raw data for further analysis
+
 
 class DeviceDiscoveryManager:
-    def __init__(self):
-        self.discovery_protocols = [] # Placeholder
-
-    async def start_discovery(self):
-        # Start each discovery protocol
-        pass
+    def __init__(self, hass, config):
+        self.hass = hass
+        self.config = config
+        self.discovery_protocols = []
+        self.running = False
+        self.capability_analyzer = CapabilityAnalyzer(hass, config)
+        self.onboarding_manager = OnboardingManager(hass, config)
+        self.error_reporter = ErrorReporter(hass) # Instantiate the error reporter
+
+    async def start_discovery(self):
+        self.running = True
+        self.discovery_protocols = []
+
+        if self.config.get('zeroconf_enabled', True):
+            self.discovery_protocols.append(zeroconf_discovery.ZeroconfDiscovery(self.hass, self.config))
+        if self.config.get('upnp_enabled', True):
+            self.discovery_protocols.append(upnp_discovery.UPnPDiscovery(self.hass, self.config))
+        if self.config.get('ble_enabled', True):
+            self.discovery_protocols.append(ble_discovery.BleDiscovery(self.hass, self.config))
+        if self.config.get('ip_scan_enabled', True):
+            self.discovery_protocols.append(ip_scan_discovery.IPScanDiscovery(self.hass, self.config))
+
+        _LOGGER.info(f"Starting device discovery with protocols: {[p.__class__.__name__ for p in self.discovery_protocols]}")
+
+        async def run_protocol(protocol):
+            try:
+                await protocol.discover_devices()
+            except Exception as e:
+                 _LOGGER.exception(f"Error running {protocol.__class__.__name__}: {e}")
+                 self.error_reporter.report_error("device_discovery_failure",
+                                                   f"Error during {protocol.__class__.__name__}: {e}")
+
+        tasks = [run_protocol(protocol) for protocol in self.discovery_protocols]
+        await asyncio.gather(*tasks)
+        self.running = False
+        _LOGGER.info("Device discovery completed.")
+
+    async def stop_discovery(self):
+        _LOGGER.info("Stopping device discovery.")
+        self.running = False
+        for protocol in self.discovery_protocols:
+            if hasattr(protocol, 'stop'):
+                await protocol.stop() # type: ignore
+
+    async def register_device(self, device_info):
+        """Registers a discovered device, performs capability analysis, and initiates onboarding."""
+        _LOGGER.info(f"New device discovered: {device_info.mac_address} via {device_info.discovery_protocol}")
+        try:
+            capabilities = await self.capability_analyzer.analyze_capabilities(device_info)
+            device_info.capabilities = capabilities
+            await self.onboarding_manager.onboard_device(device_info)
+            # integrate with HA entity registry here, using HA integration
+            await self.hass.services.async_call('aicleaner_v3', 'log_message', {"message":f"Device discovered: {device_info.mac_address}"}) # example logging message
+        except Exception as e:
+            _LOGGER.exception(f"Error registering device {device_info.mac_address}: {e}")
+            self.error_reporter.report_error("device_registration_failure",
+                                               f"Failed to register {device_info.mac_address}: {e}")

***

**`protocols/zeroconf_discovery.py`**

```diff
--- a/aicleaner_v3/protocols/zeroconf_discovery.py
+++ b/aicleaner_v3/protocols/zeroconf_discovery.py
@@ -1,5 +1,33 @@
-def discover_zeroconf_devices():
-    # Zeroconf implementation here
-    pass
+import asyncio
+import logging
+import zeroconf
+
+from ..device_discovery import DeviceInfo
+
+_LOGGER = logging.getLogger(__name__)
+
+class ZeroconfDiscovery:
+    def __init__(self, hass, config):
+        self.hass = hass
+        self.config = config
+        self.zeroconf = zeroconf.Zeroconf()
+
+    async def discover_devices(self):
+        _LOGGER.info("Starting Zeroconf discovery...")
+        try:
+            services = self.zeroconf.discover_services('_http._tcp.local.')  # Example service type
+            for service in services:
+                _LOGGER.debug(f"Zeroconf service found: {service.name}")
+                # Extract device information from service
+                # Example:
+                device_info = DeviceInfo(mac_address="unknown", ip_address="unknown", device_type="Zeroconf Device", discovery_protocol="Zeroconf", raw_data=service)
+                await self.hass.async_add_executor_job(self.hass.data['device_discovery_manager'].register_device, device_info)
+
+            _LOGGER.info("Zeroconf discovery completed.")
+        except Exception as e:
+            _LOGGER.exception(f"Error during Zeroconf discovery: {e}")
+
+    async def stop(self):
+        _LOGGER.info("Stopping Zeroconf discovery.")
+        self.zeroconf.close()

***

**`capability_analysis.py`**

```diff
--- a/aicleaner_v3/capability_analysis.py
+++ b/aicleaner_v3/capability_analysis.py
@@ -1,4 +1,34 @@
-def analyze_device_capabilities():
-    # Device capability analysis implementation here
-    pass
+import asyncio
+import logging
+
+from .database import device_database
+
+_LOGGER = logging.getLogger(__name__)
+
+class CapabilityAnalyzer:
+    def __init__(self, hass, config):
+        self.hass = hass
+        self.config = config
+        self.device_db = device_database.DeviceDatabase()  # Load from file or create if it doesn't exist
+
+    async def analyze_capabilities(self, device_info):
+        """Analyzes device capabilities based on device info and database."""
+        _LOGGER.info(f"Analyzing capabilities for device: {device_info.mac_address}")
+
+        device_signature = self.device_db.get_device_signature(device_info.mac_address)
+
+        if device_signature:
+            _LOGGER.info(f"Found signature in database for {device_info.mac_address}")
+            capabilities = device_signature.get('capabilities', {})
+            return capabilities  # Return capabilities directly from the database
+        else:
+             _LOGGER.info(f"Signature NOT found in database for {device_info.mac_address}.  Performing deep analysis.")
+             # perform deeper API probing here to try and discover capabilities
+
+             capabilities = {} # Replace this with actual analysis results
+             return capabilities
+        return {"example": "Example capability"}
+
+class DeviceSignature:
+    pass
+
***

**`onboarding.py`**

```diff
--- a/aicleaner_v3/onboarding.py
+++ b/aicleaner_v3/onboarding.py
@@ -1,4 +1,21 @@
-def onboard_device():
-    # Device onboarding implementation here
-    pass
+import logging
+
+_LOGGER = logging.getLogger(__name__)
+
+class OnboardingManager:
+    def __init__(self, hass, config):
+        self.hass = hass
+        self.config = config
+
+    async def onboard_device(self, device_info):
+        """Onboards a device, automating configuration and integration setup."""
+        _LOGGER.info(f"Onboarding device: {device_info.mac_address}")
+
+        # 1. Generate Configuration:
+        configuration = self.generate_configuration(device_info)
+
+        # 2. Recommend Integrations:
+        integrations = self.recommend_integrations(device_info)
+
+    def generate_configuration(self, device_info):
+        return {} # Placeholder
+
***

**`database/device_database.py`**

```diff
--- a/aicleaner_v3/database/device_database.py
+++ b/aicleaner_v3/database/device_database.py
@@ -0,0 +1,25 @@
+import json
+import logging
+
+_LOGGER = logging.getLogger(__name__)
+
+class DeviceDatabase:
+    def __init__(self, db_file="device_signatures.json"):
+        self.db_file = db_file
+        self.signatures = self.load_database()
+
+    def load_database(self):
+        try:
+            with open(self.db_file, 'r') as f:
+                return json.load(f)
+        except FileNotFoundError:
+            _LOGGER.warning("Device signature database not found, creating a new one.")
+            return {}
+        except json.JSONDecodeError:
+             _LOGGER.error("Error decoding device signature database. Please check the file.")
+             return {}
+
+    def get_device_signature(self, mac_address):
+        """Retrieves a device signature from the database by MAC address."""
+        return self.signatures.get(mac_address)
+
***

**`error_reporting.py`**

```diff
--- a/aicleaner_v3/error_reporting.py
+++ b/aicleaner_v3/error_reporting.py
@@ -0,0 +1,24 @@
+import logging
+
+_LOGGER = logging.getLogger(__name__)
+
+class ErrorReporter:
+    def __init__(self, hass):
+        self.hass = hass
+
+    def report_error(self, error_type, message, device_info=None):
+        """Reports an error to the user and logs it."""
+
+        if error_type == "device_discovery_failure":
+            # User-friendly message
+            user_message = "Device discovery failed. Please check your network connection and try again."
+            # Log the error
+            _LOGGER.error(f"Device discovery failed: {message}")
+            # Optionally send a notification to the user (Home Assistant integration)
+            self.hass.async_create_task(
+                self.hass.services.async_call(
+                    'persistent_notification', 'create',
+                    {'notification_id': 'device_discovery_error',
+                     'title': 'AICleaner Device Discovery Error',
+                     'message': user_message}))
+
***

**`logging_config.py`**

```diff
--- a/aicleaner_v3/logging_config.py
+++ b/aicleaner_v3/logging_config.py
@@ -0,0 +1,26 @@
+import logging
+import json
+
+def configure_logging(hass, level=logging.INFO):
+    """Configures structured JSON logging."""
+
+    logger = logging.getLogger()
+    logger.setLevel(level)
+
+    # JSON formatter
+    class JsonFormatter(logging.Formatter):
+        def format(self, record):
+            log_data = {
+                'level': record.levelname,
+                'name': record.name,
+                'message': record.getMessage(),
+                'timestamp': self.formatTime(record),
+                # Add more contextual information here as needed
+            }
+            return json.dumps(log_data)
+
+    # Handler
+    handler = logging.StreamHandler()
+    handler.setFormatter(JsonFormatter())
+
+    logger.addHandler(handler)
***

**`security.py`**

```diff
--- a/aicleaner_v3/security.py
+++ b/aicleaner_v3/security.py
@@ -0,0 +1,11 @@
+import logging
+
+_LOGGER = logging.getLogger(__name__)
+
+class SecurityManager:
+    def __init__(self, hass, config):
+        self.hass = hass
+        self.config = config
+
+    def validate_device(self, device_info):
+        # Placeholder
***

**`metrics.py`**

```diff
--- a/aicleaner_v3/metrics.py
+++ b/aicleaner_v3/metrics.py
@@ -0,0 +1,13 @@
+import logging
+
+_LOGGER = logging.getLogger(__name__)
+
+class MetricsManager:
+    def __init__(self, hass, config):
+        self.hass = hass
+        self.config = config
+
+    def record_discovery_success(self):
+        # Implement the logic to track key metrics, such as discovery success rates, device detection speeds, capability analysis accuracy, onboarding success rates, and user satisfaction
+        # Also track performance baselines such as device discovery latency per protocol, memory usage during device detection, concurrent device discovery capability
+        pass
***

**`config_flow.py`**

```diff
--- a/aicleaner_v3/config_flow.py
+++ b/aicleaner_v3/config_flow.py
@@ -15,6 +15,12 @@
     async def async_step_user(self, user_input=None):
         """Handle the initial step."""
         errors = {}
+
+        if user_input is not None:
+            return self.async_create_entry(title="AICleaner v3", data=user_input)
+
+        data_schema = vol.Schema({
+            vol.Optional('zeroconf_enabled', default=True): bool,
+            vol.Optional('upnp_enabled', default=True): bool,
+            vol.Optional('ble_enabled', default=True): bool,
+            vol.Optional('ip_scan_enabled', default=True): bool,
+        })
```

**`__init__.py`**

```diff
--- a/aicleaner_v3/__init__.py
+++ b/aicleaner_v3/__init__.py
@@ -1,11 +1,30 @@
 import asyncio
 import logging

+from homeassistant.config_entries import ConfigEntry
+from homeassistant.core import HomeAssistant
+
 from .aicleaner import AICleaner
+from .device_discovery import DeviceDiscoveryManager
+from .logging_config import configure_logging
+from .metrics import MetricsManager
+
+
+_LOGGER = logging.getLogger(__name__)
+
 PLATFORMS = ["sensor"]
+
+async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
+    """Set up AICleaner v3 from a config entry."""
+    configure_logging(hass)
+    config = entry.data
+    metrics_manager = MetricsManager(hass, config)
+    device_discovery_manager = DeviceDiscoveryManager(hass, config)
+    hass.data['device_discovery_manager'] = device_discovery_manager # store the manager for access elsewhere
+
+    asyncio.create_task(device_discovery_manager.start_discovery())
 
 async def async_unload_entry(hass, entry):
     """Unload a config entry."""
     return True
+
```

***

**3. INTEGRATION NOTES**

*   This phase builds upon previous phases by utilizing the configuration framework established in Phase 1A.  The `config_flow.py` is modified to add configuration options for the new device discovery features.
*   It leverages the AI provider integrations from Phase 1B to potentially use AI for advanced device capability analysis (e.g., using AI to analyze device API responses).
*   It uses the response quality enhancements from Phase 2B to ensure user-facing error messages are clear and helpful.
*   The AI performance monitoring from Phase 2C can be extended to monitor the performance of the device discovery process.

**4. TESTING STRATEGY**

The testing strategy follows the AAA (Arrange-Act-Assert) pattern.

*   **Unit Tests:**
    *   Test individual functions and classes in isolation.
    *   Mock external dependencies (e.g., network calls, database access) to ensure test reliability.
    *   Use `unittest` or `pytest` frameworks.

*   **Integration Tests:**
    *   Test the interaction between different modules (e.g., device discovery and capability analysis).
    *   Simulate real-world scenarios using test devices or virtual device environments.
    *   Verify that devices are correctly discovered, analyzed, and onboarded.

*   **Property-Based Testing:**
    *   Use `hypothesis` to generate a wide range of inputs for testing functions.
    *   Define properties that should always hold true, regardless of the input.
    *   This helps to uncover edge cases and unexpected behavior.

*   **Test Cases:**
    *   **Device Discovery:**
        *   Verify that devices are discovered using different protocols (Zeroconf, UPnP, Bluetooth LE, IP scanning).
        *   Test the discovery process with different network configurations.
        *   Simulate device connection/disconnection scenarios.
        *   Test error handling for network errors, timeouts, and authentication failures.
    *   **Capability Analysis:**
        *   Verify that device capabilities are correctly identified based on device information and database signatures.
        *   Test the analysis process with different device types and API responses.
        *   Test error handling for API access failures, unsupported device types, and malformed responses.
    *   **Device State Monitoring:**
        *   Verify that device states are correctly monitored and updated in real-time.
        *   Test the monitoring process with different device types and state change scenarios.
        *   Simulate device availability issues (e.g., connection lost).
        *   Test error handling for state update failures and availability detection problems.
    *   **Device Onboarding:**
        *   Verify that devices are correctly onboarded with automated configuration and integration setup.
        *   Test the onboarding process with different device types and user input.
        *   Simulate configuration validation failures and integration setup errors.
        *   Test error handling for onboarding failures.

**5. DOCUMENTATION**

*   **End-User Documentation:**
    *   Device detection setup guide with network configuration instructions and discovery optimization tips.
    *   Device compatibility guide with supported device types and integration recommendations.
    *   Troubleshooting guide for device detection issues with specific solutions.
    *   Device onboarding tutorial with step-by-step instructions.
    *   "What Devices Can Be Detected?" comprehensive compatibility matrix.

*   **Developer Documentation:**
    *   Device detection architecture documentation with detailed protocol implementation and discovery algorithms.
    *   Device capability analysis API documentation for custom device integrations.
    *   Device detection development guidelines and protocol extension procedures.
    *   Device testing procedures and mock environment setup.

**HA Compliance:**

The implementation will ensure full compliance with HA device detection requirements, HA device registry integration, HA IoT security guidelines, and HA device integration standards for addon certification.

**Next Steps:**

I have provided the initial files and code diffs. I will work with Claude to fill in the implementation, create test cases, and refine the documentation. We will also focus on ensuring the code adheres to the 100/100 readiness specifications.
