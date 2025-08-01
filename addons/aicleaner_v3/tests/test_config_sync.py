"""
Tests for Real-time Configuration Synchronization System
"""

import asyncio
import json
import os
import tempfile
import shutil
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from sync.config_sync import (
    SyncMessage,
    ConfigWatcher,
    ConfigSyncServer,
    ConfigSyncClient,
    ConfigSyncManager,
    create_single_instance_sync,
    create_ha_addon_sync,
    create_development_sync
)

class TestSyncMessage:
    """Test SyncMessage dataclass."""
    
    def test_sync_message_creation(self):
        """Test creating a SyncMessage."""
        message = SyncMessage(
            type='config_update',
            timestamp=time.time(),
            instance_id='test_instance',
            config_hash='abc123',
            config_data={'key': 'value'}
        )
        
        assert message.type == 'config_update'
        assert message.instance_id == 'test_instance'
        assert message.config_hash == 'abc123'
        assert message.config_data == {'key': 'value'}
        assert message.conflict_resolution == 'last_write_wins'
    
    def test_sync_message_serialization(self):
        """Test message serialization to dict."""
        message = SyncMessage(
            type='heartbeat',
            timestamp=1234567890.0,
            instance_id='test',
            config_hash='hash123'
        )
        
        from dataclasses import asdict
        data = asdict(message)
        
        assert data['type'] == 'heartbeat'
        assert data['timestamp'] == 1234567890.0
        assert data['instance_id'] == 'test'
        assert data['config_hash'] == 'hash123'


class TestConfigWatcher:
    """Test ConfigWatcher class."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file."""
        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump({'initial': 'config'}, f)
            yield path
        finally:
            if os.path.exists(path):
                os.unlink(path)
    
    @pytest.fixture
    def mock_callback(self):
        """Create a mock callback function."""
        return AsyncMock()
    
    def test_config_watcher_initialization(self, temp_config_file, mock_callback):
        """Test ConfigWatcher initialization."""
        watcher = ConfigWatcher(temp_config_file, mock_callback)
        
        assert watcher.config_path == temp_config_file
        assert watcher.callback == mock_callback
        assert watcher.running is False
        assert watcher.last_modified == 0
        assert watcher.last_hash == ""
    
    def test_config_hash_generation(self, temp_config_file, mock_callback):
        """Test configuration hash generation."""
        watcher = ConfigWatcher(temp_config_file, mock_callback)
        
        config1 = {'a': 1, 'b': 2}
        config2 = {'b': 2, 'a': 1}  # Same content, different order
        config3 = {'a': 1, 'b': 3}  # Different content
        
        hash1 = watcher._get_config_hash(config1)
        hash2 = watcher._get_config_hash(config2)
        hash3 = watcher._get_config_hash(config3)
        
        assert hash1 == hash2  # Same content should have same hash
        assert hash1 != hash3  # Different content should have different hash
    
    def test_load_config_success(self, temp_config_file, mock_callback):
        """Test successful configuration loading."""
        watcher = ConfigWatcher(temp_config_file, mock_callback)
        
        config = watcher._load_config()
        
        assert config is not None
        assert config == {'initial': 'config'}
    
    def test_load_config_missing_file(self, mock_callback):
        """Test loading config from non-existent file."""
        watcher = ConfigWatcher('/nonexistent/file.json', mock_callback)
        
        config = watcher._load_config()
        
        assert config is None
    
    def test_load_config_invalid_json(self, mock_callback):
        """Test loading config with invalid JSON."""
        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with os.fdopen(fd, 'w') as f:
                f.write('invalid json content')
            
            watcher = ConfigWatcher(path, mock_callback)
            config = watcher._load_config()
            
            assert config is None
        finally:
            os.unlink(path)
    
    @pytest.mark.asyncio
    async def test_start_stop_watching(self, temp_config_file, mock_callback):
        """Test starting and stopping the watcher."""
        watcher = ConfigWatcher(temp_config_file, mock_callback)
        
        # Start watching
        await watcher.start_watching()
        
        assert watcher.running is True
        assert watcher.watch_task is not None
        
        # Stop watching
        await watcher.stop_watching()
        
        assert watcher.running is False


class TestConfigSyncServer:
    """Test ConfigSyncServer class."""
    
    def test_server_initialization(self):
        """Test server initialization."""
        server = ConfigSyncServer(port=8765, instance_id='test_server')
        
        assert server.port == 8765
        assert server.instance_id == 'test_server'
        assert server.running is False
        assert len(server.clients) == 0
    
    def test_server_default_instance_id(self):
        """Test server with default instance ID."""
        server = ConfigSyncServer()
        
        assert server.instance_id.startswith('instance_')
        assert server.port == 8765
    
    @pytest.mark.asyncio
    async def test_server_start_stop(self):
        """Test starting and stopping the server."""
        server = ConfigSyncServer(port=0)  # Use random port
        
        # Start server
        await server.start()
        assert server.running is True
        
        # Stop server
        await server.stop()
        assert server.running is False
        assert len(server.clients) == 0


class TestConfigSyncClient:
    """Test ConfigSyncClient class."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = ConfigSyncClient('ws://localhost:8765/sync', 'test_client')
        
        assert client.server_url == 'ws://localhost:8765/sync'
        assert client.instance_id == 'test_client'
        assert client.running is False
        assert len(client.message_callbacks) == 0
    
    def test_client_default_instance_id(self):
        """Test client with default instance ID."""
        client = ConfigSyncClient('ws://localhost:8765/sync')
        
        assert client.instance_id.startswith('client_')
    
    def test_add_message_callback(self):
        """Test adding message callbacks."""
        client = ConfigSyncClient('ws://localhost:8765/sync')
        
        callback1 = Mock()
        callback2 = Mock()
        
        client.add_message_callback(callback1)
        client.add_message_callback(callback2)
        
        assert len(client.message_callbacks) == 2
        assert callback1 in client.message_callbacks
        assert callback2 in client.message_callbacks
    
    @pytest.mark.asyncio
    async def test_client_start_stop(self):
        """Test starting and stopping the client."""
        client = ConfigSyncClient('ws://localhost:8765/sync')
        
        # Mock the reconnect loop to avoid actual connections
        with patch.object(client, '_reconnect_loop', new_callable=AsyncMock):
            await client.start()
            assert client.running is True
            
            await client.stop()
            assert client.running is False


class TestConfigSyncManager:
    """Test ConfigSyncManager class."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        config_dir = tempfile.mkdtemp()
        config_file = os.path.join(config_dir, 'config.json')
        
        # Create initial config
        with open(config_file, 'w') as f:
            json.dump({'test': 'config'}, f)
        
        try:
            yield config_dir, config_file
        finally:
            shutil.rmtree(config_dir)
    
    def test_manager_initialization(self, temp_dirs):
        """Test manager initialization."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            sync_port=8765,
            peer_urls=['ws://peer1:8765/sync'],
            enable_server=True,
            instance_id='test_manager'
        )
        
        assert manager.config_path == config_file
        assert manager.config_base_dir == config_dir
        assert manager.sync_port == 8765
        assert manager.peer_urls == ['ws://peer1:8765/sync']
        assert manager.enable_server is True
        assert manager.instance_id == 'test_manager'
        assert manager.running is False
        assert manager.sync_server is not None
        assert len(manager.sync_clients) == 1
    
    def test_manager_no_server_mode(self, temp_dirs):
        """Test manager without server enabled."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False
        )
        
        assert manager.sync_server is None
        assert len(manager.sync_clients) == 0
    
    def test_load_current_config(self, temp_dirs):
        """Test loading current configuration."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False
        )
        
        config = manager._load_current_config()
        
        assert config is not None
        assert config == {'test': 'config'}
    
    def test_load_nonexistent_config(self, temp_dirs):
        """Test loading non-existent configuration."""
        config_dir, _ = temp_dirs
        nonexistent_file = os.path.join(config_dir, 'nonexistent.json')
        
        manager = ConfigSyncManager(
            config_path=nonexistent_file,
            config_base_dir=config_dir,
            enable_server=False
        )
        
        config = manager._load_current_config()
        
        assert config is None
    
    def test_save_config(self, temp_dirs):
        """Test saving configuration."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False
        )
        
        new_config = {'new': 'configuration', 'value': 123}
        success = manager._save_config(new_config)
        
        assert success is True
        
        # Verify config was saved
        loaded_config = manager._load_current_config()
        assert loaded_config == new_config
    
    def test_save_config_backup_restore(self, temp_dirs):
        """Test config backup and restore on save failure."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False
        )
        
        # Mock open to raise exception during save
        with patch('builtins.open', side_effect=IOError("Save failed")):
            success = manager._save_config({'failed': 'config'})
            
            assert success is False
            
            # Original config should be restored
            config = manager._load_current_config()
            assert config == {'test': 'config'}
    
    def test_add_config_update_callback(self, temp_dirs):
        """Test adding configuration update callbacks."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False
        )
        
        callback1 = Mock()
        callback2 = Mock()
        
        manager.add_config_update_callback(callback1)
        manager.add_config_update_callback(callback2)
        
        assert len(manager.config_update_callbacks) == 2
        assert callback1 in manager.config_update_callbacks
        assert callback2 in manager.config_update_callbacks
    
    def test_get_sync_status(self, temp_dirs):
        """Test getting synchronization status."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            sync_port=8765,
            peer_urls=['ws://peer1:8765/sync'],
            enable_server=True,
            instance_id='test_manager'
        )
        
        status = manager.get_sync_status()
        
        assert status['running'] is False
        assert status['instance_id'] == 'test_manager'
        assert status['server_enabled'] is True
        assert status['server_port'] == 8765
        assert status['peer_count'] == 1
        assert status['peer_urls'] == ['ws://peer1:8765/sync']
        assert 'last_sync_time' in status
        assert 'config_versions' in status
    
    @pytest.mark.asyncio
    async def test_manager_start_stop(self, temp_dirs):
        """Test starting and stopping the manager."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False,  # Disable server for easier testing
            peer_urls=[]
        )
        
        # Mock the components to avoid actual networking
        manager.config_watcher.start_watching = AsyncMock()
        manager.config_watcher.stop_watching = AsyncMock()
        
        # Start manager
        await manager.start()
        
        assert manager.running is True
        manager.config_watcher.start_watching.assert_called_once()
        
        # Stop manager
        await manager.stop()
        
        assert manager.running is False
        manager.config_watcher.stop_watching.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_config_change(self, temp_dirs):
        """Test handling local configuration changes."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False,
            peer_urls=[]
        )
        
        # Mock the sync clients
        mock_client = Mock()
        mock_client.send_config_update = AsyncMock()
        manager.sync_clients = [mock_client]
        
        test_config = {'changed': 'config'}
        
        # Trigger config change
        await manager._on_config_change(test_config)
        
        # Should have attempted to sync to peer
        mock_client.send_config_update.assert_called_once_with(test_config)
    
    @pytest.mark.asyncio
    async def test_on_remote_config_update(self, temp_dirs):
        """Test handling remote configuration updates."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False,
            instance_id='local_instance'
        )
        
        # Mock callback
        callback = AsyncMock()
        manager.add_config_update_callback(callback)
        
        # Create remote update message
        remote_config = {'remote': 'update', 'value': 456}
        message = SyncMessage(
            type='config_update',
            timestamp=time.time() + 1,  # Future timestamp
            instance_id='remote_instance',
            config_hash='remote_hash',
            config_data=remote_config
        )
        
        # Handle remote update
        await manager._on_remote_config_update(message)
        
        # Should have updated local config
        updated_config = manager._load_current_config()
        assert updated_config == remote_config
        
        # Should have called callback
        callback.assert_called_once_with(remote_config)
    
    @pytest.mark.asyncio
    async def test_ignore_own_messages(self, temp_dirs):
        """Test ignoring messages from own instance."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False,
            instance_id='test_instance'
        )
        
        # Create message from same instance
        message = SyncMessage(
            type='config_update',
            timestamp=time.time(),
            instance_id='test_instance',  # Same as manager
            config_hash='hash',
            config_data={'test': 'data'}
        )
        
        original_config = manager._load_current_config()
        
        # Handle message
        await manager._on_remote_config_update(message)
        
        # Config should remain unchanged
        current_config = manager._load_current_config()
        assert current_config == original_config
    
    @pytest.mark.asyncio
    async def test_force_sync(self, temp_dirs):
        """Test forcing synchronization."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False
        )
        
        # Mock sync client
        mock_client = Mock()
        mock_client.send_config_update = AsyncMock()
        manager.sync_clients = [mock_client]
        
        # Force sync
        await manager.force_sync()
        
        # Should have sent config to peer
        mock_client.send_config_update.assert_called_once()
        call_args = mock_client.send_config_update.call_args[0]
        assert call_args[0] == {'test': 'config'}  # Current config


class TestFactoryFunctions:
    """Test factory functions for different deployment scenarios."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        config_dir = tempfile.mkdtemp()
        config_file = os.path.join(config_dir, 'config.json')
        
        with open(config_file, 'w') as f:
            json.dump({'test': 'config'}, f)
        
        try:
            yield config_dir, config_file
        finally:
            shutil.rmtree(config_dir)
    
    def test_create_single_instance_sync(self, temp_dirs):
        """Test creating single instance sync manager."""
        config_dir, config_file = temp_dirs
        
        manager = create_single_instance_sync(config_file, config_dir)
        
        assert manager.enable_server is False
        assert manager.sync_server is None
        assert len(manager.sync_clients) == 0
        assert len(manager.peer_urls) == 0
    
    def test_create_ha_addon_sync_default(self, temp_dirs):
        """Test creating HA addon sync manager with defaults."""
        config_dir, config_file = temp_dirs
        
        manager = create_ha_addon_sync(config_file, config_dir)
        
        assert manager.sync_port == 8765
        assert len(manager.peer_urls) == 0
        assert manager.enable_server is False  # No peers = no server
    
    def test_create_ha_addon_sync_with_peers(self, temp_dirs):
        """Test creating HA addon sync manager with peers."""
        config_dir, config_file = temp_dirs
        
        addon_options = {
            'sync_port': 9999,
            'peer_urls': ['ws://peer1:8765/sync', 'ws://peer2:8765/sync'],
            'enable_sync_server': True
        }
        
        manager = create_ha_addon_sync(config_file, config_dir, addon_options)
        
        assert manager.sync_port == 9999
        assert len(manager.peer_urls) == 2
        assert manager.enable_server is True
        assert len(manager.sync_clients) == 2
    
    def test_create_development_sync(self, temp_dirs):
        """Test creating development sync manager."""
        config_dir, config_file = temp_dirs
        
        manager = create_development_sync(config_file, config_dir)
        
        assert manager.sync_port == 8765
        assert manager.enable_server is True
        assert len(manager.peer_urls) == 0
        assert manager.sync_server is not None


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        config_dir = tempfile.mkdtemp()
        config_file = os.path.join(config_dir, 'config.json')
        
        with open(config_file, 'w') as f:
            json.dump({'initial': 'config'}, f)
        
        try:
            yield config_dir, config_file
        finally:
            shutil.rmtree(config_dir)
    
    @pytest.mark.asyncio
    async def test_single_instance_scenario(self, temp_dirs):
        """Test single instance deployment scenario."""
        config_dir, config_file = temp_dirs
        
        # Create single instance manager
        manager = create_single_instance_sync(config_file, config_dir)
        
        # Mock components for testing
        manager.config_watcher.start_watching = AsyncMock()
        manager.config_watcher.stop_watching = AsyncMock()
        
        # Start manager
        await manager.start()
        
        assert manager.running is True
        assert manager.sync_server is None
        assert len(manager.sync_clients) == 0
        
        # Config changes should be handled locally only
        test_config = {'updated': 'config'}
        await manager._on_config_change(test_config)
        
        # Should have saved version but not attempted sync
        versions = manager.config_versioning.list_versions()
        assert len(versions) >= 1
        
        await manager.stop()
        assert manager.running is False
    
    @pytest.mark.asyncio
    async def test_ha_addon_scenario(self, temp_dirs):
        """Test Home Assistant addon scenario."""
        config_dir, config_file = temp_dirs
        
        # Simulate addon options
        addon_options = {
            'sync_port': 8765,
            'peer_urls': [],
            'enable_sync_server': False
        }
        
        manager = create_ha_addon_sync(config_file, config_dir, addon_options)
        
        # Mock components
        manager.config_watcher.start_watching = AsyncMock()
        manager.config_watcher.stop_watching = AsyncMock()
        
        await manager.start()
        
        # Should handle configuration changes
        callback = AsyncMock()
        manager.add_config_update_callback(callback)
        
        # Update config
        new_config = {'ha_addon': 'config', 'devices': ['vacuum', 'lights']}
        success = manager._save_config(new_config)
        
        assert success is True
        
        # Should have versioned the config
        versions = manager.config_versioning.list_versions()
        assert len(versions) >= 1
        
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_development_environment(self, temp_dirs):
        """Test development environment scenario."""
        config_dir, config_file = temp_dirs
        
        manager = create_development_sync(config_file, config_dir)
        
        # Mock components
        manager.config_watcher.start_watching = AsyncMock()
        manager.config_watcher.stop_watching = AsyncMock()
        
        if manager.sync_server:
            manager.sync_server.start = AsyncMock()
            manager.sync_server.stop = AsyncMock()
        
        await manager.start()
        
        # Should have started with server enabled
        assert manager.enable_server is True
        assert manager.sync_server is not None
        
        # Should handle status queries
        status = manager.get_sync_status()
        assert status['server_enabled'] is True
        assert status['server_port'] == 8765
        
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_conflict_resolution(self, temp_dirs):
        """Test conflict resolution scenario."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False,
            instance_id='local_instance'
        )
        
        # Set up callback to track updates
        callback = AsyncMock()
        manager.add_config_update_callback(callback)
        
        # Local config
        local_config = {'source': 'local', 'value': 1}
        manager._save_config(local_config)
        
        # Remote config update (newer timestamp)
        remote_config = {'source': 'remote', 'value': 2}
        remote_message = SyncMessage(
            type='config_update',
            timestamp=time.time() + 10,  # Future timestamp
            instance_id='remote_instance',
            config_hash='remote_hash',
            config_data=remote_config
        )
        
        # Handle remote update
        await manager._on_remote_config_update(remote_message)
        
        # Should have applied remote config (last write wins)
        current_config = manager._load_current_config()
        assert current_config == remote_config
        
        # Should have called callback
        callback.assert_called_once_with(remote_config)
    
    @pytest.mark.asyncio
    async def test_network_resilience(self, temp_dirs):
        """Test network resilience scenario."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False,
            peer_urls=['ws://unreachable:8765/sync']
        )
        
        # Mock client that fails to connect
        mock_client = Mock()
        mock_client.send_config_update = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client.start = AsyncMock()
        mock_client.stop = AsyncMock()
        manager.sync_clients = [mock_client]
        
        # Start manager
        await manager.start()
        
        # Should handle sync failures gracefully
        test_config = {'test': 'resilience'}
        await manager._on_config_change(test_config)
        
        # Should have attempted sync but not crashed
        mock_client.send_config_update.assert_called_once()
        
        # Force sync should also handle failures
        await manager.force_sync()
        
        await manager.stop()
    
    @pytest.mark.asyncio 
    async def test_version_management(self, temp_dirs):
        """Test configuration version management."""
        config_dir, config_file = temp_dirs
        
        manager = ConfigSyncManager(
            config_path=config_file,
            config_base_dir=config_dir,
            enable_server=False
        )
        
        # Mock the watcher
        manager.config_watcher.start_watching = AsyncMock()
        manager.config_watcher.stop_watching = AsyncMock()
        
        await manager.start()
        
        # Make several config changes
        configs = [
            {'version': 1, 'feature': 'basic'},
            {'version': 2, 'feature': 'advanced'},
            {'version': 3, 'feature': 'premium'}
        ]
        
        for config in configs:
            await manager._on_config_change(config)
        
        # Should have saved multiple versions
        versions = manager.config_versioning.list_versions()
        assert len(versions) >= 3
        
        # Should be able to retrieve latest
        latest = manager.config_versioning.get_latest_version()
        assert latest['version'] == 3
        assert latest['feature'] == 'premium'
        
        await manager.stop()