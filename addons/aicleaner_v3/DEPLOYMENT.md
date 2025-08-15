# AICleaner V3 Deployment Guide

This document provides comprehensive deployment instructions for the AICleaner V3 Home Assistant Add-on.

## 📋 Pre-Deployment Checklist

### Repository Requirements
- [ ] All source code committed to GitHub repository
- [ ] Repository is public or accessible to target audience
- [ ] README.md is comprehensive and up-to-date
- [ ] CHANGELOG.md reflects current version
- [ ] License file is present (MIT recommended)
- [ ] Icon and logo files are present (PNG format, 512x512 recommended)

### Add-on Structure Validation
- [ ] `config.yaml` with proper version and configuration schema
- [ ] `Dockerfile` with multi-architecture support
- [ ] `build.yaml` for Home Assistant build system
- [ ] `requirements.txt` with pinned dependencies
- [ ] `run.sh` startup script with proper error handling
- [ ] Source code in `src/` directory

### Configuration Validation
- [ ] All environment variables properly handled
- [ ] Configuration schema matches addon options
- [ ] Default values are sensible
- [ ] Required vs optional fields clearly defined

## 🚀 Deployment Methods

### Method 1: Home Assistant Add-on Store (Recommended)

**For Official Store Submission:**
1. **Repository Setup**:
   ```bash
   # Ensure clean repository structure
   git clone https://github.com/sporebattyl/aicleaner_v3.git
   cd aicleaner_v3
   git checkout main
   ```

2. **Submit to Home Assistant**:
   - Follow [Home Assistant Add-on Guidelines](https://developers.home-assistant.io/docs/add-ons)
   - Submit PR to [hassio-addons](https://github.com/hassio-addons) repository
   - Wait for review and approval

### Method 2: Custom Repository (Immediate Deployment)

**For Custom Repository Distribution:**
1. **Setup Repository**:
   - Ensure `repository.yaml` is in root directory
   - Verify addon is in `addons/aicleaner_v3/` structure
   
2. **Add to Home Assistant**:
   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Click **⋮** (three dots) → **Repositories**
   - Add: `https://github.com/sporebattyl/aicleaner_v3`
   - Find and install "AICleaner V3"

### Method 3: Local Development

**For Development/Testing:**
1. **Clone Repository**:
   ```bash
   git clone https://github.com/sporebattyl/aicleaner_v3.git
   cd aicleaner_v3
   ```

2. **Copy to Home Assistant**:
   ```bash
   # Copy addon to HA addons directory
   cp -r addons/aicleaner_v3 /usr/share/hassio/addons/local/
   
   # Or use symbolic link for development
   ln -s $(pwd)/addons/aicleaner_v3 /usr/share/hassio/addons/local/aicleaner_v3
   ```

3. **Restart Home Assistant Supervisor**:
   ```bash
   ha supervisor restart
   ```

## 🏗️ Build Process

### Docker Multi-Architecture Builds

The addon supports multiple architectures automatically via Home Assistant's build system:

- **amd64** - Intel/AMD 64-bit systems
- **aarch64** - ARM 64-bit (Raspberry Pi 4, etc.)
- **armhf** - ARM 32-bit (Raspberry Pi 3, etc.)
- **armv7** - ARMv7 32-bit systems

### Local Build Testing

```bash
# Test build for current architecture
docker build -t aicleaner_v3:test addons/aicleaner_v3/

# Test run
docker run --rm -it \
  -v $(pwd)/test_data:/data \
  -e LOG_LEVEL=debug \
  aicleaner_v3:test
```

### GitHub Actions (Optional)

Create `.github/workflows/build.yml` for automated testing:

```yaml
name: Build and Test

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build addon
        uses: home-assistant/builder@master
        with:
          args: |
            --target addons/aicleaner_v3
            --docker-hub-check
```

## 📊 Validation Process

### Pre-Deployment Testing

1. **Configuration Validation**:
   ```bash
   # Test configuration parsing
   cd addons/aicleaner_v3
   python3 src/config_mapper.py
   ```

2. **Dependency Check**:
   ```bash
   # Verify all dependencies are available
   docker build --target test .
   ```

3. **Startup Testing**:
   ```bash
   # Test startup sequence
   ./run.sh --test-mode
   ```

### Post-Deployment Verification

1. **Installation Test**:
   - Install addon from repository
   - Verify addon appears in store
   - Check installation logs for errors

2. **Configuration Test**:
   - Test all configuration options
   - Verify schema validation works
   - Test edge cases and invalid inputs

3. **Runtime Test**:
   - Start addon with minimal configuration
   - Verify logs show successful startup
   - Test web UI accessibility
   - Verify MQTT entity creation (if configured)

4. **API Testing**:
   ```bash
   # Test API endpoints
   curl http://homeassistant.local:8080/api/status
   curl -X POST http://homeassistant.local:8080/api/test_generation \
     -H "Content-Type: application/json" \
     -d '{"prompt": "test"}'
   ```

## 🔧 Troubleshooting Deployment Issues

### Common Issues

**1. Build Failures**
```bash
# Check Dockerfile syntax
docker build --no-cache addons/aicleaner_v3/

# Verify base image compatibility
grep BUILD_FROM addons/aicleaner_v3/build.yaml
```

**2. Configuration Schema Errors**
```bash
# Validate config.yaml
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Check schema format
jq '.schema' addons/aicleaner_v3/config.yaml
```

**3. Startup Failures**
```bash
# Check startup script
bash -x addons/aicleaner_v3/run.sh

# Verify permissions
chmod +x addons/aicleaner_v3/run.sh
```

**4. Dependency Issues**
```bash
# Update requirements
pip-compile requirements.in

# Check Alpine package availability
docker run --rm alpine:3.19 apk search python3
```

### Debug Mode Deployment

For debugging deployment issues:

1. Enable debug logging in `config.yaml`:
   ```yaml
   debug_mode: true
   log_level: debug
   ```

2. Add debug outputs to `run.sh`:
   ```bash
   set -x  # Enable debug output
   ```

3. Monitor logs during startup:
   ```bash
   # Follow addon logs
   ha addons logs aicleaner_v3 -f
   ```

## 🌐 Production Considerations

### Performance Optimization

1. **Image Size Optimization**:
   - Use multi-stage builds
   - Minimize installed packages
   - Use Alpine base images

2. **Resource Limits**:
   - Set appropriate memory limits in config.yaml
   - Consider CPU requirements for AI processing

3. **Network Configuration**:
   - Minimize exposed ports
   - Use ingress for web UI
   - Secure API endpoints

### Security Hardening

1. **Container Security**:
   - Run as non-root user
   - Minimize privileges
   - Use read-only file systems where possible

2. **API Security**:
   - Validate all inputs
   - Implement rate limiting
   - Use HTTPS for external APIs

3. **Configuration Security**:
   - Encrypt sensitive configuration
   - Validate configuration schemas
   - Provide secure defaults

### Monitoring and Maintenance

1. **Health Checks**:
   - Implement proper health endpoints
   - Monitor resource usage
   - Set up alerting for failures

2. **Updates**:
   - Plan regular dependency updates
   - Test updates in staging environment
   - Provide clear upgrade instructions

3. **Support**:
   - Maintain comprehensive documentation
   - Provide troubleshooting guides
   - Establish support channels

## 📈 Release Management

### Version Strategy

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

### Release Process

1. **Pre-Release**:
   ```bash
   # Update version in config.yaml
   # Update CHANGELOG.md
   # Test thoroughly
   git commit -am "Release v1.2.4"
   git tag v1.2.4
   ```

2. **Release**:
   ```bash
   git push origin main --tags
   ```

3. **Post-Release**:
   - Monitor deployment
   - Address any issues
   - Update documentation

### Rollback Procedures

If issues are discovered:

1. **Immediate Rollback**:
   ```bash
   git revert HEAD
   git push origin main
   ```

2. **User Communication**:
   - Notify users of issue
   - Provide workaround if available
   - Communicate fix timeline

This deployment guide ensures professional, reliable deployment of the AICleaner V3 addon to production Home Assistant environments.