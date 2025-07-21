# AICleaner v3 Testing Strategy

## Overview

AICleaner v3 uses a comprehensive two-tiered testing strategy that balances automated testing for rapid development with full integration testing for production readiness.

## Two-Tiered Testing Architecture

### Tier 1: Automated Component Integration Tests ⚡

**Purpose**: Fast, automated, repeatable tests for day-to-day development and CI/CD

**Scope**: 
- Core addon logic validation
- Home Assistant REST API integration
- MQTT discovery and communication
- State management and command handling
- Service health and connectivity

**Environment**:
- **Docker Compose orchestration** with real Home Assistant container
- **Components**: `homeassistant/home-assistant:stable`, `mosquitto`, `aicleaner-test`
- **Network isolation** for consistent testing
- **Automated cleanup** between test runs

**Limitations** (by design):
- ❌ No Home Assistant Supervisor (addon lifecycle testing not available)
- ❌ No addon store installation process
- ❌ No ingress/UI integration testing
- ✅ Tests core functionality and API integration

**Execution**: `./scripts/run-ha-tests.sh`

### Tier 2: Semi-Automated Addon Lifecycle Tests 🏠

**Purpose**: Full production deployment validation before releases

**Scope**:
- Complete addon installation from addon store
- Supervisor-managed lifecycle (install/start/stop/update/uninstall)
- Ingress and web UI integration
- Full Home Assistant OS environment
- Production configuration validation

**Environment**:
- **Home Assistant OS** in virtual machine (VirtualBox/QEMU)
- **Custom addon repository** with real installation process
- **Manual setup** with documented procedures

**Execution**: Manual process with guided documentation

## Quick Start Guide

### Prerequisites

1. **Docker and Docker Compose** installed and running
2. **Git repository** cloned locally
3. **Network access** for pulling Docker images

### Running Tier 1 Tests (Automated)

```bash
cd /path/to/aicleaner_v3/addons/aicleaner_v3

# First time setup - generate Home Assistant access token
./scripts/setup-ha-token.sh

# Run the complete test suite
./scripts/run-ha-tests.sh
```

### Setting Up Tier 2 Tests (Manual)

1. **Set up Home Assistant OS VM** (see [VM Setup Guide](#vm-setup-guide))
2. **Add custom addon repository** with AICleaner v3
3. **Install addon through HA interface**
4. **Validate all features** (see [Tier 2 Test Checklist](#tier-2-test-checklist))

## Test Environment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │   Home Assistant │  │   MQTT Broker    │  │ AICleaner  │ │
│  │   (Real HA Core) │◄─┤   (mosquitto)    ├─►│   Addon    │ │
│  │                  │  │                  │  │            │ │
│  │   Port: 8123     │  │   Port: 1883     │  │            │ │
│  └──────────────────┘  └──────────────────┘  └────────────┘ │
│           │                       │                ▲        │
│           ▼                       ▼                │        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │   Test Runner    │  │   MQTT Monitor   │  │   Health   │ │
│  │   (Validation)   │  │   (Debugging)    │  │   Checks   │ │
│  └──────────────────┘  └──────────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Test Configuration

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `HA_ACCESS_TOKEN` | Home Assistant long-lived access token | Yes | `eyJhbGc...` |
| `MQTT_HOST` | MQTT broker hostname | No | `mosquitto-test` |
| `MQTT_PORT` | MQTT broker port | No | `1883` |
| `DEVICE_ID` | Test device identifier | No | `aicleaner_v3_test` |

### Home Assistant Configuration

The test environment uses a minimal HA configuration optimized for fast startup:

- **Core components only** (no `default_config`)
- **MQTT integration** pre-configured for test broker
- **API access** enabled for test automation
- **Debug logging** for troubleshooting

## Test Scenarios Covered

### ✅ Service Health Checks
- MQTT broker connectivity
- Home Assistant API authentication
- Service startup and readiness

### ✅ MQTT Discovery Integration
- Device discovery message structure
- Entity registration in Home Assistant
- Discovery payload validation

### ✅ State Publishing
- Real-time state updates via MQTT
- State message format validation
- Timestamp and data accuracy

### ✅ Command Handling
- MQTT command processing (ON/OFF)
- State change responsiveness
- Error handling and recovery

### ✅ Home Assistant API Integration
- Authenticated API access
- Configuration retrieval
- Component availability verification

## Troubleshooting

### Common Issues

#### Token Authentication Fails
```bash
# Re-run token setup if authentication fails
./scripts/setup-ha-token.sh
```

#### Home Assistant Startup Slow
```bash
# Home Assistant can take 60-90 seconds to start
# The test script includes appropriate timeouts
```

#### Port Conflicts
```bash
# Check for existing services on port 8123
ss -tulpn | grep :8123

# Clean up any conflicting containers
docker-compose -f docker-compose.test.yml down -v
```

#### MQTT Connection Issues
```bash
# Verify MQTT broker is healthy
docker-compose -f docker-compose.test.yml ps | grep mosquitto

# Check MQTT logs
docker-compose -f docker-compose.test.yml logs mosquitto-test
```

### Debug Mode

Enable verbose logging by setting environment variables:

```bash
export LOG_LEVEL=debug
./scripts/run-ha-tests.sh
```

## Tier 2 Test Checklist

### VM Setup Guide

1. **Download Home Assistant OS**
   - Get latest HAOS image from [Home Assistant website](https://www.home-assistant.io/installation/)
   - Choose appropriate architecture (x86-64 for most VMs)

2. **Create Virtual Machine**
   - **VirtualBox**: 4GB RAM, 32GB disk minimum
   - **QEMU**: Similar specifications
   - **Network**: Bridged mode for external access

3. **Initial Setup**
   - Complete onboarding wizard
   - Create user account
   - Configure location and units

### Addon Installation Process

1. **Add Custom Repository**
   ```
   Configuration → Add-ons → Add-on Store → ⋮ → Repositories
   Add: https://github.com/your-username/aicleaner-v3-addon
   ```

2. **Install AICleaner v3**
   - Find addon in store
   - Click Install
   - Configure settings
   - Start addon

### Manual Test Cases

#### Installation & Lifecycle
- [ ] Addon appears in store
- [ ] Installation completes without errors
- [ ] Configuration UI loads correctly
- [ ] Addon starts successfully
- [ ] Logs show proper initialization

#### Integration Tests
- [ ] MQTT discovery creates entities
- [ ] Entities appear in Home Assistant
- [ ] State updates reflect in UI
- [ ] Commands from UI work correctly
- [ ] Ingress UI (if applicable) functions

#### Error Handling
- [ ] Invalid configuration handled gracefully
- [ ] Network interruptions recovered
- [ ] Addon restart works correctly
- [ ] Uninstallation cleans up properly

## Continuous Integration

The Tier 1 tests are designed to run in CI/CD environments:

```yaml
# Example GitHub Actions workflow
name: Integration Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Integration Tests
        run: |
          cd addons/aicleaner_v3
          # Set up token (in real CI, use secrets)
          echo "HA_ACCESS_TOKEN=${{ secrets.HA_ACCESS_TOKEN }}" > .env
          ./scripts/run-ha-tests.sh
```

## Development Workflow

### Day-to-Day Development
1. Make code changes
2. Run `./scripts/run-ha-tests.sh` 
3. Fix any failing tests
4. Commit changes

### Pre-Release Validation
1. Ensure all Tier 1 tests pass
2. Run Tier 2 manual tests
3. Document any new features
4. Tag release

### Performance Considerations

- **Tier 1 tests**: ~3-5 minutes total runtime
- **Home Assistant startup**: 60-90 seconds
- **Test execution**: 30-60 seconds
- **Cleanup**: 10-20 seconds

The testing strategy prioritizes fast feedback loops while ensuring comprehensive coverage through both automated and manual validation.