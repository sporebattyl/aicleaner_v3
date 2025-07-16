**Collaboration Initiated: Phase 3A Prompt Review**

Claude, connection established. Analyzing the request for Phase 3A: Device Detection Enhancement. My task is to construct the prompt and provide a detailed review from an expert's perspective. The goal is to produce a "diff" patch following a six-section, validated pattern, focusing on the core aspects of advanced device detection and automated onboarding within the Home Assistant (HA) ecosystem.

--- /dev/null
+++ b/Phase_3A.diff
@@ -1,130 +1,130 @@
 --- a/Phase_3A.diff
 +++ b/Phase_3A.diff
 @@ -1,9 +1,114 @@
-diff --git a/Phase_2B.diff b/Phase_3A.diff
-new file mode 100644
-index 0000000..0000000
---- a/Phase_2B.diff
-+++ b/Phase_3A.diff
-@@ -0,0 +1,10 @@
-+# Phase 3A: Device Detection Enhancement
-
-## Core Implementation Requirements
-
--   Core Task: Smart Device Discovery System
-    -   Action: Implement a multi-protocol network scanner.
-    -   Details: Support Zeroconf/Bonjour, mDNS, SSDP (for UPnP), Bluetooth LE, IP subnet scanning.
-    -   Validation: >95% detection rate for common protocols, discovery latency < 5 seconds.
-    
--   Core Task: Device Capability Detection & Classification
-    -   Action: Develop a device fingerprinting and capability analysis engine.
-    -   Details: Parse mDNS TXT records, query device APIs, device signature database. Classify into HA domains (light, switch, sensor, etc.).
-    -   Validation: >98% accuracy in classifying known device models, automatic classification for >90% of discovered devices.
-
--   Core Task: Device State Monitoring & Tracking
-    -   Action: Implement a real-time, resilient state tracking system.
-    -   Details: Polling fallback, WebSockets/MQTT subscriptions. Handle "unavailable" states.
-    -   Validation: State update latency < 500ms, >99.9% state accuracy.
-
--   Core Task: Device Compatibility & Integration Assessment
-    -   Action: Create an automated compatibility validation service.
-    -   Details: Cross-reference device models against HA integration list, API check. Clear user feedback.
-    -   Validation: Assessment in < 1 second, >99% success prediction.
-    
--   Core Task: Automated Device Onboarding & Configuration
-    -   Action: Build a "zero-touch" or "one-click" onboarding wizard.
-    -   Details: Pre-fill config details (IP, MAC), suggest HA integration, handle auth flows.
-    -   Validation: Reduce manual steps by >75%, >90% onboarding with one confirmation.
-
-## Technical Implementation & Component Design
-
--   Component: `DiscoveryManager` (network scanning and discovery). Use HA's `asyncio`.
--   Data Model: `DeviceProfile` (stores discovered device details, capabilities).
--   Service: `StateManager` (manages device state, polling, and event subscription).
--   Service: `CompatibilityEngine` (assesses compatibility).
-
-## Testing & Quality Assurance (TDD/AAA)
-
--   TDD: Write unit tests before implementation for all components.
--   AAA:
-    -   `DiscoveryManager`: Arrange (mock network), Act (discovery), Assert (mock devices found).
-    -   `DeviceProfile`: Arrange (test data), Act (parsing), Assert (valid profile created).
-    -   Use `pytest`, `unittest.mock`, integration tests, E2E in simulated HA.
-
-## MCP Server & API Integration
-
--   Use `WebFetch` to get the latest device signature database.
--   Use `Task.report_progress` to update the MCP on discovery progress.
--   Use `zen.log` for detailed logging.
--   Use `GitHub.create_issue` to report a new, unrecognized device.
-
-## Documentation & User Experience (UX)
-
--   Developer Docs: API documentation for all new components.
--   User Docs: README.md or UI explanation of how discovery works.
--   UI/UX: Show discovered devices, compatibility status, one-click onboarding.
-
-## Deployment & Risk Management