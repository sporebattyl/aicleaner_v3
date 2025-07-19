# Real-time Configuration Synchronization

This module provides real-time configuration synchronization capabilities for AICleaner v3, enabling configuration changes to be synchronized across multiple instances in real-time.

## Features

- **Event-driven Synchronization**: Automatically detects and syncs configuration changes
- **WebSocket Communication**: Real-time bidirectional communication between instances
- **Conflict Resolution**: Last-write-wins strategy with timestamp-based resolution
- **Version Management**: Integration with configuration versioning system
- **Network Resilience**: Graceful handling of network failures and reconnections
- **Home Assistant Optimized**: Designed for Home Assistant addon deployment

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Instance A    │    │   Instance B    │    │   Instance C    │
│                 │    │                 │    │                 │
│ ConfigWatcher   │    │ ConfigWatcher   │    │ ConfigWatcher   │
│ ConfigSyncServer│◄──►│ ConfigSyncClient│◄──►│ ConfigSyncClient│
│ ConfigSyncClient│    │ ConfigSyncServer│    │ ConfigSyncServer│
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Components

### SyncMessage

Data structure for configuration sync messages:

```python
@dataclass
class SyncMessage:
    type: str  # 'config_update', 'config_request', 'config_response', 'heartbeat'
    timestamp: float
    instance_id: str
    config_hash: str
    config_data: Optional[Dict[str, Any]] = None
    conflict_resolution: str = "last_write_wins"
```

### ConfigWatcher

Monitors configuration files for changes:

```python
watcher = ConfigWatcher(config_path, callback)
await watcher.start_watching()
```

### ConfigSyncServer

WebSocket server for configuration synchronization:

```python
server = ConfigSyncServer(port=8765, instance_id='server1')
await server.start()
```

### ConfigSyncClient

WebSocket client for configuration synchronization:

```python
client = ConfigSyncClient('ws://localhost:8765/sync', 'client1')
await client.start()
```

### ConfigSyncManager

Main synchronization manager:

```python
manager = ConfigSyncManager(
    config_path='/path/to/config.json',
    config_base_dir='/path/to/config',
    sync_port=8765,
    peer_urls=['ws://peer1:8765/sync'],
    enable_server=True
)
await manager.start()
```

## Usage Examples

### Single Instance (No Sync)

```python
from sync import create_single_instance_sync

manager = create_single_instance_sync(
    config_path='/data/config.json',
    config_base_dir='/data'
)

await manager.start()
```

### Home Assistant Addon

```python
from sync import create_ha_addon_sync

# Default configuration (no peers)
manager = create_ha_addon_sync(
    config_path='/data/config.json',
    config_base_dir='/data'
)

# With addon options
addon_options = {
    'sync_port': 8765,
    'peer_urls': ['ws://192.168.1.100:8765/sync'],
    'enable_sync_server': True
}

manager = create_ha_addon_sync(
    config_path='/data/config.json',
    config_base_dir='/data',
    addon_options=addon_options
)

await manager.start()
```

### Development Environment

```python
from sync import create_development_sync

manager = create_development_sync(
    config_path='/dev/config.json',
    config_base_dir='/dev'
)

await manager.start()
```

### Manual Configuration

```python
from sync import ConfigSyncManager

manager = ConfigSyncManager(
    config_path='/path/to/config.json',
    config_base_dir='/path/to/config',
    sync_port=8765,
    peer_urls=[
        'ws://peer1.example.com:8765/sync',
        'ws://peer2.example.com:8765/sync'
    ],
    enable_server=True,
    instance_id='my_instance'
)

# Add callback for configuration updates
async def on_config_update(config):
    print(f"Configuration updated: {config}")

manager.add_config_update_callback(on_config_update)

await manager.start()
```

## Configuration Options

### Addon Options

```python
addon_options = {
    'sync_port': 8765,                    # Port for sync server
    'peer_urls': [],                      # List of peer URLs
    'enable_sync_server': False,          # Enable sync server
    'rate_limit_requests_per_minute': 60, # Rate limiting
    'rate_limit_block_duration': 120,    # Block duration
    'rate_limit_whitelist_local': True   # Whitelist local network
}
```

### Environment Variables

```bash
# Sync configuration
AICLEANER_SYNC_PORT=8765
AICLEANER_SYNC_PEERS=ws://peer1:8765/sync,ws://peer2:8765/sync
AICLEANER_SYNC_ENABLE_SERVER=true

# Instance identification
AICLEANER_INSTANCE_ID=instance_001
```

## Conflict Resolution

The system uses a "last-write-wins" strategy for conflict resolution:

1. **Timestamp Comparison**: Messages with newer timestamps take precedence
2. **Hash Verification**: Configuration hashes are used to detect conflicts
3. **Backup and Recovery**: Original configuration is backed up before applying changes
4. **Rollback Support**: Failed synchronizations can be rolled back

## Network Communication

### WebSocket Protocol

The system uses WebSocket connections for real-time communication:

- **Endpoint**: `/sync`
- **Protocol**: JSON-based message format
- **Reconnection**: Automatic reconnection with exponential backoff
- **Health Checks**: `/health` endpoint for monitoring

### Message Types

1. **config_update**: Configuration change notification
2. **config_request**: Request for current configuration
3. **config_response**: Response to configuration request
4. **heartbeat**: Keep-alive message

## Security Considerations

1. **Local Network Only**: Default configuration restricts to local network
2. **Rate Limiting**: Built-in rate limiting to prevent abuse
3. **Validation**: Configuration validation before applying changes
4. **Logging**: Security events are logged for audit trails

## Integration with AICleaner v3

### Startup Integration

```python
from sync import create_ha_addon_sync

class AICleaner:
    def __init__(self):
        self.config_sync = create_ha_addon_sync(
            config_path=self.config_path,
            config_base_dir=self.config_base_dir,
            addon_options=self.addon_options
        )
        
        # Add callback for config changes
        self.config_sync.add_config_update_callback(self.on_config_change)
    
    async def start(self):
        await self.config_sync.start()
        # ... other startup tasks
    
    async def stop(self):
        await self.config_sync.stop()
        # ... other shutdown tasks
    
    async def on_config_change(self, config):
        # Reload configuration
        await self.reload_config(config)
```

### Configuration Versioning

The sync system integrates with the existing configuration versioning:

```python
# Automatic version creation on sync
manager = ConfigSyncManager(...)
await manager.start()

# Manual version management
versions = manager.config_versioning.list_versions()
latest = manager.config_versioning.get_latest_version()
specific = manager.config_versioning.get_version('config_20240101120000.json')
```

## Testing

### Unit Tests

```bash
# Run all sync tests
pytest tests/test_config_sync.py -v

# Run specific test class
pytest tests/test_config_sync.py::TestConfigSyncManager -v

# Run with coverage
pytest tests/test_config_sync.py --cov=sync --cov-report=html
```

### Integration Tests

```python
# Test real synchronization
async def test_real_sync():
    # Start server
    server_manager = ConfigSyncManager(
        config_path='/tmp/server_config.json',
        config_base_dir='/tmp/server',
        sync_port=8765,
        enable_server=True
    )
    await server_manager.start()
    
    # Start client
    client_manager = ConfigSyncManager(
        config_path='/tmp/client_config.json',
        config_base_dir='/tmp/client',
        peer_urls=['ws://localhost:8765/sync'],
        enable_server=False
    )
    await client_manager.start()
    
    # Test synchronization
    # ... test code ...
```

## Performance Considerations

1. **File Watching**: Uses efficient file system watching
2. **Batching**: Configuration changes are batched to reduce network traffic
3. **Compression**: Large configurations can be compressed for transmission
4. **Caching**: Configuration hashes are cached to avoid redundant operations

## Troubleshooting

### Common Issues

1. **Connection Refused**: Check if sync server is running and port is open
2. **Configuration Not Syncing**: Verify peer URLs and network connectivity
3. **Conflicts Not Resolving**: Check timestamp synchronization between instances
4. **High Memory Usage**: Reduce configuration version retention

### Debug Logging

```python
import logging
from sync import setup_sync_logging

# Enable debug logging
setup_sync_logging('DEBUG')

# Or set environment variable
export AICLEANER_LOG_LEVEL=DEBUG
```

### Health Monitoring

```python
# Check sync status
status = manager.get_sync_status()
print(f"Running: {status['running']}")
print(f"Peers: {status['peer_count']}")
print(f"Last sync: {status['last_sync_time']}")

# Force synchronization
await manager.force_sync()
```

## Deployment Examples

### Home Assistant Addon

```yaml
# addon/config.yaml
options:
  sync_port: 8765
  peer_urls: []
  enable_sync_server: false
  
schema:
  sync_port: int(1,65535)
  peer_urls: [str]
  enable_sync_server: bool
```

### Docker Compose

```yaml
version: '3.8'
services:
  aicleaner1:
    image: aicleaner:latest
    environment:
      - AICLEANER_SYNC_PORT=8765
      - AICLEANER_SYNC_ENABLE_SERVER=true
    ports:
      - "8765:8765"
  
  aicleaner2:
    image: aicleaner:latest
    environment:
      - AICLEANER_SYNC_PEERS=ws://aicleaner1:8765/sync
    depends_on:
      - aicleaner1
```

### Kubernetes

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aicleaner-sync-config
data:
  sync_port: "8765"
  peer_urls: "ws://aicleaner-1:8765/sync,ws://aicleaner-2:8765/sync"
  enable_sync_server: "true"
```

## API Reference

### ConfigSyncManager Methods

- `start()`: Start the synchronization manager
- `stop()`: Stop the synchronization manager
- `force_sync()`: Force synchronization with all peers
- `get_sync_status()`: Get current synchronization status
- `add_config_update_callback(callback)`: Add configuration update callback

### Factory Functions

- `create_single_instance_sync(config_path, config_base_dir)`: Single instance
- `create_ha_addon_sync(config_path, config_base_dir, addon_options)`: HA addon
- `create_development_sync(config_path, config_base_dir)`: Development environment

## License

This module is part of AICleaner v3 and is subject to the same license terms.