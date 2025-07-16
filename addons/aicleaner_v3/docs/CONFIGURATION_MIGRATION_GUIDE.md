# Configuration Migration Guide - Phase 1A

## Overview

This guide covers the migration from the legacy three-file configuration system to the new unified configuration schema in AICleaner v3. The migration system provides automatic consolidation with comprehensive backup and rollback capabilities.

## What's Changing

### Legacy Configuration (Before Phase 1A)
- **Three separate files**: `config.yaml`, `config.json`, and root `config.yaml`
- **Overlapping keys**: Same settings duplicated across files
- **Inconsistent formats**: Different schemas and validation rules
- **Manual maintenance**: Required manual synchronization

### Unified Configuration (After Phase 1A)
- **Single configuration file**: `config.yaml` following Home Assistant addon standards
- **Comprehensive schema**: All settings in one validated structure
- **Automatic validation**: Real-time validation with helpful error messages
- **Security enhancements**: Input sanitization and encryption for sensitive data

## Migration Process

### Automatic Migration

The migration process runs automatically when you upgrade to Phase 1A:

1. **Backup Creation**: All existing configuration files are backed up
2. **Configuration Merge**: Settings from all three files are intelligently merged
3. **Validation**: The merged configuration is validated against the new schema
4. **Unified Config Creation**: A new unified `config.yaml` is created
5. **Cleanup**: Original files are archived with `.old` extension

### Manual Migration

If you prefer to migrate manually or need to troubleshoot:

```python
from core.config_migration_manager import ConfigMigrationManager

# Initialize migration manager
migration_manager = ConfigMigrationManager()

# Perform migration
result = migration_manager.migrate_configuration()

if result.success:
    print("Migration completed successfully!")
else:
    print(f"Migration failed: {result.error_message}")
    # Rollback if needed
    if result.backup:
        rollback_result = migration_manager.rollback_migration(result.backup)
```

## Configuration Schema Changes

### Core Settings

#### Before (Multiple Files)
```yaml
# config.yaml
display_name: "User Name"
gemini_api_key: "key"

# config.json
{
  "options": {
    "display_name": "AI Cleaner",
    "gemini_api_key": "different_key"
  }
}
```

#### After (Unified)
```yaml
name: "AICleaner v3"
version: "3.0.0"
slug: "aicleaner_v3"
description: "AI-powered cleaning task management"

options:
  display_name: "User Name"
  gemini_api_key: "key"
  
  # MQTT Configuration
  mqtt:
    enabled: false
    host: "core-mosquitto"
    port: 1883
    username: ""
    password: ""
  
  # AI Enhancements
  ai_enhancements:
    advanced_scene_understanding: true
    predictive_analytics: true
    
    caching:
      enabled: true
      ttl_seconds: 300
      max_cache_entries: 1000
    
    local_llm:
      enabled: true
      ollama_host: "localhost:11434"
      preferred_models:
        vision: "llava:13b"
        text: "mistral:7b"
  
  # Zones
  zones:
    - name: "Kitchen"
      camera_entity: "camera.kitchen"
      todo_list_entity: "todo.kitchen_tasks"
      purpose: "Kitchen cleaning and organization"
```

### MQTT Configuration

#### Before
```yaml
# Various formats across files
mqtt_enabled: false
mqtt_host: "localhost"
enable_mqtt: false
mqtt_broker_host: "core-mosquitto"
```

#### After
```yaml
options:
  mqtt:
    enabled: false
    host: "core-mosquitto"
    port: 1883
    username: ""
    password: ""
```

### Zone Configuration

#### Before
```yaml
# Inconsistent zone formats
zones:
  - name: "Kitchen"
    camera_entity: "camera.kitchen"
    interval_minutes: 60
    # Some fields missing
```

#### After
```yaml
options:
  zones:
    - name: "Kitchen"
      camera_entity: "camera.kitchen"
      todo_list_entity: "todo.kitchen_tasks"
      purpose: "Kitchen cleaning and organization"
      interval_minutes: 60
      update_frequency: 1
      icon: "mdi:chef-hat"
      notifications_enabled: true
      notification_service: "notify.mobile_app"
      notification_personality: "default"
      notify_on_create: true
      notify_on_complete: true
      ignore_rules:
        - "Ignore items in sink if soaking"
```

## Migration Conflict Resolution

### Common Conflicts and Resolution

1. **API Key Conflicts**
   - **Issue**: Different API keys in different files
   - **Resolution**: Most recent/comprehensive value used
   - **Manual Fix**: Update to correct key after migration

2. **Display Name Conflicts**
   - **Issue**: Different display names across files
   - **Resolution**: User-facing value preferred over default
   - **Manual Fix**: Edit unified config if needed

3. **Zone Configuration Conflicts**
   - **Issue**: Incomplete zone definitions
   - **Resolution**: Fields merged and missing fields added with defaults
   - **Manual Fix**: Review and update zone configurations

4. **MQTT Settings Conflicts**
   - **Issue**: Different MQTT configurations
   - **Resolution**: Most complete configuration used
   - **Manual Fix**: Verify MQTT settings match your setup

## Rollback Procedures

### Automatic Rollback

If migration fails, automatic rollback is triggered:

```python
# Automatic rollback on failure
if not migration_result.success:
    rollback_result = migration_manager.rollback_migration(migration_result.backup)
```

### Manual Rollback

To manually rollback a migration:

```python
# Get migration history
history = migration_manager.get_migration_history()

# Rollback to specific backup
backup = history[-1]  # Latest backup
rollback_result = migration_manager.rollback_migration(backup)
```

### Rollback Verification

After rollback:

1. **File Restoration**: Original files restored from backup
2. **Integrity Check**: Backup integrity verified via checksum
3. **Configuration Validation**: Restored configuration validated
4. **Service Restart**: AICleaner service restarted with original config

## Troubleshooting

### Common Issues

#### Migration Fails with Validation Errors

**Problem**: Merged configuration fails validation
**Solution**:
1. Check migration logs for specific validation errors
2. Fix invalid values in original configuration files
3. Run migration again

```bash
# Check migration logs
tail -f logs/config_detailed.log

# Check for validation errors
grep "VALIDATION_ERROR" logs/config_structured.json
```

#### Backup Creation Fails

**Problem**: Cannot create backup directory or files
**Solution**:
1. Check file permissions
2. Ensure sufficient disk space
3. Verify no files are locked by other processes

```bash
# Check permissions
ls -la config_backups/

# Check disk space
df -h

# Check file locks
lsof | grep config
```

#### Performance Issues During Migration

**Problem**: Migration takes too long or uses excessive memory
**Solution**:
1. Close other applications during migration
2. Check system resources
3. Use manual migration for better control

```python
# Monitor migration performance
from core.config_performance_monitor import performance_monitor

with performance_monitor.measure_operation(
    PerformanceMetric.MIGRATION_TIME,
    "manual_migration"
):
    result = migration_manager.migrate_configuration()
```

### Error Codes and Solutions

| Error Code | Description | Solution |
|------------|-------------|----------|
| `MIGRATION_BACKUP_FAILED` | Cannot create backup | Check permissions and disk space |
| `MIGRATION_MERGE_FAILED` | Cannot merge configurations | Check file formats and syntax |
| `MIGRATION_VALIDATION_FAILED` | Merged config invalid | Fix validation errors in original files |
| `MIGRATION_WRITE_FAILED` | Cannot write unified config | Check file permissions |
| `ROLLBACK_INTEGRITY_FAILED` | Backup integrity compromised | Use different backup or restore manually |

## Post-Migration Checklist

### Immediate Actions

- [ ] Verify AICleaner starts successfully
- [ ] Check all zones are properly configured
- [ ] Test MQTT connection (if enabled)
- [ ] Verify AI enhancements are working
- [ ] Check notification settings

### Configuration Review

- [ ] Review unified configuration file
- [ ] Update any incorrect values
- [ ] Add any missing zone configurations
- [ ] Test all integrations
- [ ] Verify performance is acceptable

### Backup Management

- [ ] Verify backup was created successfully
- [ ] Test rollback procedure (in test environment)
- [ ] Document any custom configurations
- [ ] Set up regular configuration backups

## Best Practices

### Before Migration

1. **Create Manual Backup**: Always create a manual backup before migration
2. **Document Custom Settings**: Note any custom configurations
3. **Test Environment**: Run migration in test environment first
4. **System Resources**: Ensure adequate system resources

### During Migration

1. **Monitor Progress**: Watch migration logs for issues
2. **Avoid Interruption**: Don't interrupt migration process
3. **Resource Monitoring**: Monitor system resources
4. **Error Handling**: Be prepared to handle errors

### After Migration

1. **Validate Configuration**: Thoroughly test all functionality
2. **Performance Check**: Monitor performance metrics
3. **Documentation Update**: Update any configuration documentation
4. **Backup Schedule**: Set up regular configuration backups

## Support

### Getting Help

1. **Check Logs**: Review migration logs for specific errors
2. **Documentation**: Refer to configuration documentation
3. **Community**: Ask questions in project discussions
4. **Issues**: Report bugs via GitHub issues

### Reporting Issues

When reporting migration issues, include:

- Migration logs from `logs/config_detailed.log`
- Error messages from `logs/config_errors.log`
- Original configuration files (redacted for security)
- System information (OS, Python version, etc.)

### Recovery Procedures

If migration fails completely:

1. **Restore from Backup**: Use automatic rollback
2. **Manual Restoration**: Restore files manually if needed
3. **Fresh Installation**: Start with fresh configuration if necessary
4. **Contact Support**: Reach out for assistance

## Advanced Configuration

### Custom Migration Logic

For complex configurations, you can customize migration:

```python
# Custom migration with specific handling
migration_manager = ConfigMigrationManager()

# Override merge logic for specific fields
def custom_merge_zones(zones_list):
    # Custom zone merging logic
    return merged_zones

# Apply custom logic
migration_manager.custom_merge_handlers["zones"] = custom_merge_zones
```

### Performance Optimization

For large configurations:

```python
# Optimize migration performance
migration_manager.performance_mode = "optimized"
migration_manager.batch_size = 100
migration_manager.memory_limit = 512  # MB
```

### Security Considerations

- API keys and passwords are encrypted during migration
- Sensitive data is sanitized in logs
- Backup files are secured with appropriate permissions
- Configuration validation includes security checks

## Migration History

The migration system maintains a history of all migrations:

```python
# Get migration history
history = migration_manager.get_migration_history()

# View specific migration
migration_info = history[0]
print(f"Migration: {migration_info.timestamp}")
print(f"Stage: {migration_info.stage}")
print(f"Files: {migration_info.original_files}")
```

This comprehensive migration guide ensures a smooth transition to the unified configuration system while maintaining data integrity and providing robust error handling and recovery options.