<!-- ENHANCED via Advanced Prompt Enhancer - 2025-07-16 -->
<!-- Applied 3 implementation patches: SUPERVISOR_HEALTH_CHECKS, SERVICE_CALL_VALIDATION, PERFORMANCE_METRICS -->
<!-- Enhancement Type: Implementation-based improvements with specific technical details -->

<!--
GEMINI ENHANCEMENT ANALYSIS:

**ASSESSMENT**: Quality rating: 8/10, Implementation readiness: 85%

**STRENGTHS**: 
- Comprehensive technical framework with clear structure
- Good coverage of Home Assistant integration requirements
- Strong security considerations for addon development
- Well-defined performance metrics and monitoring

**CRITICAL IMPROVEMENTS**:
1. **Enhanced Async Patterns**: Need specific async/await implementation examples with proper error handling and timeout management
2. **HA Service Integration**: Require concrete HA service call patterns with error recovery and state synchronization
3. **Testing Framework**: Need comprehensive HA test environment simulation with mock fixtures and integration tests

**SPECIFIC CHANGES**:
- Add specific timeout values for HA operations (30s for service calls, 5s for entity updates)
- Include exponential backoff patterns for HA service call failures
- Specify entity state batching for performance optimization
- Add correlation IDs for request tracking across HA integration layers

**TECHNICAL GAPS**:
- Missing specific HA API version compatibility requirements
- Need concrete error handling patterns for HA Supervisor disconnection
- Lack of specific performance baselines for HA operations
- Missing HA addon lifecycle event handling specifications

**NEXT STEPS**:
1. High Priority: Add async/await implementation patterns with timeout handling
2. Medium Priority: Enhance testing framework with HA simulation environment
3. Low Priority: Improve documentation structure for developer experience

-->

# Phase 4A: Home Assistant Integration Improvement - 6-Section 100/100 Enhancement

## Core Implementation Requirements

### Core Tasks
1. **Home Assistant Supervisor Integration**
   - **Action**: Implement comprehensive HA Supervisor API integration with proper lifecycle management, service registration, and addon communication protocols
   - **Details**: Supervisor health checks, addon state management, configuration validation through Supervisor API, proper startup/shutdown sequences, resource monitoring integration.

     *   **Implementation Guidance for Supervisor Health Checks:** Implement health checks by querying the Supervisor API's `/health` endpoint. Expect a JSON response with a `status` field indicating the health status (e.g., `{"status": "ok"}`). A recommended timeout value is 10 seconds. Use `async/await` for non-blocking checks to prevent blocking the main event loop. Example:

         ```python
         import asyncio
         import aiohttp

         async def check_supervisor_health(supervisor_url):
             try:
                 async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                     async with session.get(f"{supervisor_url}/health") as response:
                         response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
                         data = await response.json()
                         if data.get("status") == "ok":
                             return True
                         else:
                             return False
             except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                 print(f"Supervisor health check failed: {e}")
                 return False

         async def main():
             supervisor_url = "http://supervisor:8080"  # Replace with your Supervisor URL
             is_healthy = await check_supervisor_health(supervisor_url)
             print(f"Supervisor health status: {is_healthy}")

         if __name__ == "__main__":
             asyncio.run(main())
         ```
   - **Validation**: Supervisor compatibility tests passing, addon lifecycle events properly logged, health check endpoints responding within 500ms

2. **HA Service Call Integration** 
   - **Action**: Develop robust Home Assistant service call framework with automation integration, service discovery, and error handling
   - **Details**: Service registry implementation, automation trigger/condition integration, service call validation, response handling, state synchronization. Service call validation ensures that the input parameters passed to a service call are valid before the service logic is executed. This prevents errors and ensures the integrity of the system.

     - **Input Parameter Validation**: Implement validation of input parameters for service calls using JSON Schema or custom validation functions.

       - **JSON Schema Validation**: Define JSON Schemas for each service call to specify the expected data types, formats, and constraints for the input parameters. Use a JSON Schema validator library (e.g., `jsonschema` in Python) to validate the input parameters against the schema before executing the service call.

         ```python
         from jsonschema import validate, ValidationError

         def validate_service_call(service_name, params):
             schema = {
                 "type": "object",
                 "properties": {
                     "device_id": {"type": "string"},
                     "temperature": {"type": "number", "minimum": -50, "maximum": 100}
                 },
                 "required": ["device_id", "temperature"]
             }
             try:
                 validate(instance=params, schema=schema)
             except ValidationError as e:
                 return f"Validation error: {e.message}"
             return None

         def set_temperature(device_id, temperature):
             params = {"device_id": device_id, "temperature": temperature}
             validation_error = validate_service_call("set_temperature", params)
             if validation_error:
                 return f"Error: {validation_error}"
             # Service logic here
             return f"Temperature set to {temperature} for device {device_id}"

         # Example usage
         result = set_temperature("thermostat_123", 25)
         print(result)
         ```

       - **Custom Validation Functions**: Implement custom validation functions to perform more complex validation logic that cannot be expressed using JSON Schema. These functions can check for specific business rules or constraints.

         ```python
         def validate_device_id(device_id):
             if not device_id.startswith("device_"):
                 return "Device ID must start with 'device_'"
             return None

         def set_temperature(device_id, temperature):
             device_id_error = validate_device_id(device_id)
             if device_id_error:
                 return f"Error: {device_id_error}"
             if not -50 <= temperature <= 100:
                 return "Temperature must be between -50 and 100"
             # Service logic here
             return f"Temperature set to {temperature} for device {device_id}"

         # Example usage
         result = set_temperature("invalid_device_id", 25)
         print(result)
         result = set_temperature("device_123", 150)
         print(result)
         ```

     - **Handling Validation Errors**: When a validation error occurs, return an appropriate error message to the user. This message should clearly indicate the cause of the error and provide guidance on how to correct it. Ensure that the error messages are user-friendly and easy to understand.

       ```json
       {
           "status": "error",
           "message": "Invalid input parameters: Temperature must be between -50 and 100"
       }
       ```
   - **Validation**: All HA services accessible and responsive, automation integration functional, service call latency <200ms

3. **Entity Registration & Management**
   - **Action**: Implement complete entity lifecycle management with device discovery, entity registry integration, and state management
   - **Details**: Device/entity creation, state updates, attribute management, availability tracking, entity customization support, device class compliance
   - **Validation**: Entities properly registered in HA, state updates reflected in UI, device information accurate and complete

4. **Config Flow Implementation**
   - **Action**: Create user-friendly configuration flow with setup wizard, validation, and migration support for seamless user experience
   - **Details**: Multi-step configuration wizard, input validation, error handling, configuration migration, integration testing
   - **Validation**: Config flow completes successfully, user inputs validated, migration from legacy configurations functional

## 6-Section 100/100 Enhancement Framework

### 1. User-Facing Error Reporting Strategy
- **Error Classification**: HA Supervisor connection failures (API timeout, authentication issues, permission errors), HA service call errors (invalid service, parameter validation, execution failures), entity registration issues (duplicate entities, invalid device class, state update failures), config flow errors (validation failures, migration issues, setup wizard problems)
- **Progressive Error Disclosure**: Simple "Home Assistant connection issue - checking status" for end users, detailed HA integration status with specific service/entity information for troubleshooting, comprehensive HA API logs with request/response details and timing for developers
- **Recovery Guidance**: Automatic HA Supervisor reconnection with user notification and progress indicators, step-by-step HA configuration validation with direct links to HA integration troubleshooting documentation, "Copy HA Integration Details" button for community support and issue reporting
- **Error Prevention**: Proactive HA Supervisor health monitoring with early warning alerts, continuous HA service availability checking, automated HA entity state validation, pre-configuration validation for HA compatibility

### 2. Structured Logging Strategy
- **Log Levels**: DEBUG (HA API request/response details, entity state change tracking, service call parameter logging), INFO (HA Supervisor connection status, entity registration events, config flow progress), WARN (HA version compatibility warnings, service deprecation notices, entity unavailability), ERROR (HA API failures, entity registration failures, service call errors), CRITICAL (HA Supervisor connection lost, complete integration failure, security violations)
- **Log Format Standards**: Structured JSON logs with ha_integration_id (unique identifier propagated across all HA-related operations), supervisor_api_version, entity_id, service_name, device_id, ha_core_version, integration_status, api_response_time_ms, error_context with detailed HA-specific failure information
- **Contextual Information**: Home Assistant core version and integration compatibility, HA Supervisor API endpoints and response times, entity registry status and device information, HA service registry and automation integration status, HA configuration validation results
- **Integration Requirements**: Home Assistant Supervisor logging endpoint integration with structured log forwarding, HA addon log aggregation in Supervisor dashboard, configurable HA integration log levels, automated HA integration reporting, integration with HA system health for addon status monitoring

### 3. Enhanced Security Considerations
- **Continuous Security**: HA Supervisor API secure communication with proper authentication and authorization, HA addon sandbox compliance with restricted file system and network access, HA secrets management integration for API keys and sensitive configuration, protection against HA service abuse and unauthorized access
- **Secure Coding Practices**: HA Supervisor API authentication using addon tokens and secure API endpoints, HA secrets integration via Supervisor secrets API (never direct file access), input validation for all HA service calls and entity data, secure entity state handling without sensitive data exposure, OWASP security guidelines compliance for HA addon development
- **Dependency Vulnerability Scans**: Automated scanning of HA integration libraries (homeassistant, aiohttp, voluptuous) for known vulnerabilities, regular security updates for HA-related dependencies, secure HA API client libraries with proper certificate validation

### 4. Success Metrics & Performance Baselines
- **KPIs**: HA Supervisor connection uptime (target >99.9%), HA service call response time (target <200ms), entity state update latency (target <100ms), config flow completion rate (target >95%), HA integration user satisfaction measured via post-setup "Was the HA integration setup helpful? [👍/👎]" feedback (target >95% positive)
- **Performance Baselines**: HA API call latency benchmarks across different HA versions, memory usage during HA operations (<150MB per integration), HA entity update throughput (>100 entities/second), config flow completion time (<2 minutes), HA integration performance on low-power hardware (Raspberry Pi compatibility)
- **Benchmarking Strategy**: Continuous HA integration performance monitoring with automated regression detection, HA service call performance trending analysis, entity update latency tracking with automated alerts, HA compatibility testing across multiple HA versions

### 5. Developer Experience & Maintainability
- **Code Readability**: Clear HA integration architecture documentation with HA API usage examples, intuitive HA service call patterns with comprehensive error handling, HA entity lifecycle documentation with state management examples, standardized HA integration code formatting following HA development guidelines
- **Testability**: Comprehensive HA integration testing framework with HA test environment simulation, HA service call mocking utilities for testing without live HA instance, HA entity testing suites with state validation, property-based testing using hypothesis for generating diverse HA scenarios, isolated HA integration testing with docker-compose HA test environments
- **Configuration Simplicity**: One-click HA integration setup through HA config flow interface, automatic HA version compatibility detection and warnings, user-friendly HA entity configuration with intuitive naming and organization, simple HA automation integration with clear examples and templates
- **Extensibility**: Pluggable HA service modules for new HA service integrations, extensible HA entity framework supporting custom device classes, modular HA integration architecture following ha_integration_vX naming pattern executed by main HA coordinator, adaptable HA configuration supporting evolving HA capabilities

### 6. Documentation Strategy (User & Developer)
- **End-User Documentation**: HA integration setup guide with step-by-step configuration instructions and HA UI screenshots, HA entity configuration guide with automation examples, HA troubleshooting guide for common integration issues with specific solutions, HA automation templates and examples for common use cases, visual HA integration workflow using Mermaid.js diagrams, "What HA Features Are Available?" comprehensive integration guide
- **Developer Documentation**: HA integration architecture documentation with detailed API usage and design patterns, HA Supervisor API integration guidelines and best practices, HA entity development documentation with custom component examples, HA testing procedures and mock environment setup, architectural decision records for HA integration design choices
- **HA Compliance Documentation**: Home Assistant addon certification checklist with integration-specific requirements, HA Quality Scale compliance verification procedures, HA security requirements and sandbox compliance documentation, HA integration certification submission guidelines, HA community standards and contribution guidelines
- **Operational Documentation**: HA integration monitoring and health check procedures, HA version compatibility and migration runbooks, HA integration performance monitoring guidelines, HA community support and issue resolution procedures, HA addon store submission and maintenance documentation

## Integration with TDD/AAA Pattern
All HA integration components must follow Test-Driven Development with explicit Arrange-Act-Assert structure. Each HA service call and entity operation should have corresponding tests that validate HA integration behavior through comprehensive HA test environment simulation. HA compatibility should be validated through automated testing across multiple HA versions.

## MCP Server Integration Requirements
- **GitHub MCP**: Version control for HA integration configurations and HA compatibility tracking with automated HA testing on integration changes
- **WebFetch MCP**: Continuously monitor HA release notes and research latest HA integration requirements and best practices
- **zen MCP**: Collaborate on complex HA integration architecture decisions and HA certification strategies, arbitrate disagreements in HA integration approach
- **Task MCP**: Orchestrate HA integration testing workflows and HA compatibility monitoring automation

## Home Assistant Compliance
Full compliance with HA addon certification requirements, HA Quality Scale standards, HA Supervisor integration guidelines, HA security requirements, and HA community development best practices.

## Technical Specifications
- **Required Tools**: homeassistant, aiohttp, voluptuous, pytest-homeassistant-custom-component, hacs-integration
- **HA Integration**: Supervisor API v2023.06+, Config Flow v2023.06+, Entity Registry v2023.06+
- **Performance Requirements**:
  - **Service Call Latency**: Average response time for AI Cleaner service calls (e.g., `trigger_ai_analysis`, `set_zone_state`) should be less than 200ms. Measured using Home Assistant's built-in service call timing. Example:
    ```python
    # Example of measuring service call latency
    start_time = time.time()
    hass.services.call('aicleaner.aicleaner', 'trigger_ai_analysis', {'entity_id': 'camera.front_door'})
    end_time = time.time()
    latency = end_time - start_time
    ```
    Benchmark: <200ms average over 100 calls.
  - **Entity Update Latency**: Time taken to update the state of AI Cleaner-related entities (e.g., `binary_sensor.ai_motion_detected`, `sensor.object_count`) should be less than 100ms. Measured by tracking the time delta between state change requests and actual state updates in Home Assistant.
    Benchmark: <100ms for 95% of entity updates.
  - **Integration Uptime**: The AI Cleaner integration should maintain >99.9% uptime. Monitored using Home Assistant's system health sensors and external monitoring tools (e.g., UptimeRobot) that check for service availability.
    Configuration example in `configuration.yaml`:
    ```yaml
    sensor:
      - platform: uptime
        name: AI Cleaner Uptime
        entity_id: aicleaner.integration
    ```
    Alerting should be configured to notify administrators if uptime drops below 99.9%.
  - **CPU Usage**: The AI Cleaner integration should not exceed 10% average CPU usage on the Home Assistant instance. Monitored using system resource sensors.
    ```yaml
    sensor:
      - platform: systemmonitor
        resources:
          - type: cpu_usage
    ```
    Benchmark: <10% average CPU usage over a 24-hour period.
  - **Memory Usage**: The AI Cleaner integration should not exceed 50MB of RAM usage. Monitored using system resource sensors.
    ```yaml
    sensor:
      - platform: systemmonitor
        resources:
          - type: memory_use_percent
    ```
    Benchmark: <50MB RAM usage.
- **Certification**: HA Quality Scale compliance, HA addon store certification ready