"""
Real-time Configuration Synchronization System for AICleaner v3
Provides event-driven configuration sync across multiple instances
"""

import asyncio
import json
import logging
import os
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, asdict
from threading import Lock
import aiohttp
from aiohttp import web, WSMsgType
import weakref

from utils.unified_logger import get_logger, log_security_event
from utils.config_versioning import ConfigVersioning

logger = get_logger(__name__)

@dataclass
class SyncMessage:
    """Message format for configuration sync."""
    type: str  # 'config_update', 'config_request', 'config_response', 'heartbeat'
    timestamp: float
    instance_id: str
    config_hash: str
    config_data: Optional[Dict[str, Any]] = None
    conflict_resolution: str = "last_write_wins"
    
class ConfigWatcher:
    """Watches configuration files for changes."""
    
    def __init__(self, config_path: str, callback: Callable[[Dict[str, Any]], None]):
        self.config_path = config_path
        self.callback = callback
        self.last_modified = 0
        self.last_hash = ""
        self.running = False
        self.watch_task: Optional[asyncio.Task] = None
        
    def _get_config_hash(self, config: Dict[str, Any]) -> str:
        """Generate hash for configuration data."""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def _load_config(self) -> Optional[Dict[str, Any]]:
        """Load configuration from file."""
        try:
            if not os.path.exists(self.config_path):
                return None
                
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading config from {self.config_path}: {e}")
            return None
    
    async def start_watching(self):
        """Start watching for configuration changes."""
        if self.running:
            return
            
        self.running = True
        self.watch_task = asyncio.create_task(self._watch_loop())
        logger.info(f"Started watching config file: {self.config_path}")
    
    async def stop_watching(self):
        """Stop watching for configuration changes."""
        self.running = False
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped config watching")
    
    async def _watch_loop(self):
        """Main watching loop."""
        while self.running:
            try:
                if os.path.exists(self.config_path):
                    current_modified = os.path.getmtime(self.config_path)
                    
                    if current_modified > self.last_modified:
                        config = self._load_config()
                        if config:
                            config_hash = self._get_config_hash(config)
                            
                            if config_hash != self.last_hash:
                                self.last_hash = config_hash
                                self.last_modified = current_modified
                                
                                logger.info("Configuration change detected, triggering sync")
                                await self.callback(config)
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in config watch loop: {e}")
                await asyncio.sleep(5)  # Longer wait on error

class ConfigSyncServer:
    """WebSocket server for configuration synchronization."""
    
    def __init__(self, port: int = 8765, instance_id: str = None):
        self.port = port
        self.instance_id = instance_id or f"instance_{int(time.time())}"
        self.clients: Set[web.WebSocketResponse] = set()
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.running = False
        
        # Setup routes
        self.app.router.add_get('/sync', self.websocket_handler)
        self.app.router.add_get('/health', self.health_check)
        
    async def websocket_handler(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.clients.add(ws)
        logger.info(f"New sync client connected. Total clients: {len(self.clients)}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_message(data, ws)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received from client")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            logger.error(f"Error handling WebSocket client: {e}")
        finally:
            self.clients.discard(ws)
            logger.info(f"Sync client disconnected. Total clients: {len(self.clients)}")
        
        return ws
    
    async def health_check(self, request):
        """Health check endpoint."""
        return web.json_response({
            'status': 'healthy',
            'instance_id': self.instance_id,
            'connected_clients': len(self.clients),
            'timestamp': time.time()
        })
    
    async def _handle_message(self, data: Dict[str, Any], sender_ws: web.WebSocketResponse):
        """Handle incoming sync messages."""
        try:
            message = SyncMessage(**data)
            
            if message.type == 'config_update':
                logger.info(f"Received config update from {message.instance_id}")
                # Broadcast to all other clients
                await self._broadcast_message(message, exclude=sender_ws)
                
            elif message.type == 'config_request':
                logger.info(f"Received config request from {message.instance_id}")
                # Handle config request (would need access to current config)
                
            elif message.type == 'heartbeat':
                logger.debug(f"Heartbeat from {message.instance_id}")
                
        except Exception as e:
            logger.error(f"Error handling sync message: {e}")
    
    async def _broadcast_message(self, message: SyncMessage, exclude: web.WebSocketResponse = None):
        """Broadcast message to all connected clients."""
        if not self.clients:
            return
            
        message_data = json.dumps(asdict(message))
        disconnected = set()
        
        for client in self.clients:
            if client == exclude:
                continue
                
            try:
                await client.send_str(message_data)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected
    
    async def start(self):
        """Start the sync server."""
        if self.running:
            return
            
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, 'localhost', self.port)
            await self.site.start()
            
            self.running = True
            logger.info(f"Config sync server started on port {self.port}")
            
        except Exception as e:
            logger.error(f"Error starting sync server: {e}")
            raise
    
    async def stop(self):
        """Stop the sync server."""
        if not self.running:
            return
            
        self.running = False
        
        # Close all client connections
        for client in list(self.clients):
            await client.close()
        self.clients.clear()
        
        # Stop server
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
            
        logger.info("Config sync server stopped")

class ConfigSyncClient:
    """WebSocket client for configuration synchronization."""
    
    def __init__(self, server_url: str, instance_id: str = None):
        self.server_url = server_url
        self.instance_id = instance_id or f"client_{int(time.time())}"
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        self.reconnect_task: Optional[asyncio.Task] = None
        self.message_callbacks: List[Callable] = []
        
    def add_message_callback(self, callback: Callable[[SyncMessage], None]):
        """Add callback for received messages."""
        self.message_callbacks.append(callback)
    
    async def start(self):
        """Start the sync client."""
        if self.running:
            return
            
        self.running = True
        self.reconnect_task = asyncio.create_task(self._reconnect_loop())
        logger.info(f"Config sync client started, connecting to {self.server_url}")
    
    async def stop(self):
        """Stop the sync client."""
        if not self.running:
            return
            
        self.running = False
        
        if self.reconnect_task:
            self.reconnect_task.cancel()
            try:
                await self.reconnect_task
            except asyncio.CancelledError:
                pass
        
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
            
        logger.info("Config sync client stopped")
    
    async def send_config_update(self, config: Dict[str, Any]):
        """Send configuration update to server."""
        if not self.ws or self.ws.closed:
            logger.warning("Cannot send config update: not connected")
            return
            
        config_hash = hashlib.md5(json.dumps(config, sort_keys=True).encode()).hexdigest()
        
        message = SyncMessage(
            type='config_update',
            timestamp=time.time(),
            instance_id=self.instance_id,
            config_hash=config_hash,
            config_data=config
        )
        
        try:
            await self.ws.send_str(json.dumps(asdict(message)))
            logger.info("Sent config update to server")
        except Exception as e:
            logger.error(f"Error sending config update: {e}")
    
    async def _reconnect_loop(self):
        """Handle reconnection logic."""
        while self.running:
            try:
                await self._connect()
                await self._listen()
            except Exception as e:
                logger.error(f"Connection error: {e}")
                if self.running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
    
    async def _connect(self):
        """Connect to the sync server."""
        if self.session:
            await self.session.close()
            
        self.session = aiohttp.ClientSession()
        self.ws = await self.session.ws_connect(self.server_url)
        logger.info("Connected to config sync server")
    
    async def _listen(self):
        """Listen for messages from server."""
        async for msg in self.ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    message = SyncMessage(**data)
                    
                    for callback in self.message_callbacks:
                        try:
                            await callback(message)
                        except Exception as e:
                            logger.error(f"Error in message callback: {e}")
                            
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received from server")
            elif msg.type == WSMsgType.ERROR:
                logger.error(f"WebSocket error: {self.ws.exception()}")
                break

class ConfigSyncManager:
    """Main configuration synchronization manager."""
    
    def __init__(self, config_path: str, config_base_dir: str, 
                 sync_port: int = 8765, peer_urls: List[str] = None,
                 enable_server: bool = True, instance_id: str = None):
        
        self.config_path = config_path
        self.config_base_dir = config_base_dir
        self.sync_port = sync_port
        self.peer_urls = peer_urls or []
        self.enable_server = enable_server
        self.instance_id = instance_id or f"aicleaner_{int(time.time())}"
        
        # Initialize components
        self.config_versioning = ConfigVersioning(config_base_dir)
        self.config_watcher = ConfigWatcher(config_path, self._on_config_change)
        
        # Sync components
        self.sync_server: Optional[ConfigSyncServer] = None
        self.sync_clients: List[ConfigSyncClient] = []
        
        # State management
        self.running = False
        self.sync_lock = Lock()
        self.last_sync_time = 0
        self.config_update_callbacks: List[Callable] = []
        
        # Initialize server if enabled
        if enable_server:
            self.sync_server = ConfigSyncServer(sync_port, self.instance_id)
        
        # Initialize clients for peer connections
        for peer_url in self.peer_urls:
            client = ConfigSyncClient(peer_url, self.instance_id)
            client.add_message_callback(self._on_remote_config_update)
            self.sync_clients.append(client)
    
    def add_config_update_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for configuration updates."""
        self.config_update_callbacks.append(callback)
    
    async def start(self):
        """Start the configuration sync manager."""
        if self.running:
            return
            
        try:
            # Start server if enabled
            if self.sync_server:
                await self.sync_server.start()
            
            # Start clients
            for client in self.sync_clients:
                await client.start()
            
            # Start config watcher
            await self.config_watcher.start_watching()
            
            self.running = True
            logger.info("Configuration sync manager started")
            
            # Save initial configuration version
            config = self._load_current_config()
            if config:
                self.config_versioning.save_version(config)
                
        except Exception as e:
            logger.error(f"Error starting config sync manager: {e}")
            raise
    
    async def stop(self):
        """Stop the configuration sync manager."""
        if not self.running:
            return
            
        self.running = False
        
        # Stop components
        await self.config_watcher.stop_watching()
        
        for client in self.sync_clients:
            await client.stop()
        
        if self.sync_server:
            await self.sync_server.stop()
            
        logger.info("Configuration sync manager stopped")
    
    def _load_current_config(self) -> Optional[Dict[str, Any]]:
        """Load current configuration from file."""
        try:
            if not os.path.exists(self.config_path):
                return None
                
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading config: {e}")
            return None
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file."""
        try:
            # Create backup
            backup_path = f"{self.config_path}.backup"
            if os.path.exists(self.config_path):
                os.rename(self.config_path, backup_path)
            
            # Save new config
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Remove backup on success
            if os.path.exists(backup_path):
                os.remove(backup_path)
                
            return True
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            
            # Restore backup if exists
            backup_path = f"{self.config_path}.backup"
            if os.path.exists(backup_path):
                os.rename(backup_path, self.config_path)
                
            return False
    
    async def _on_config_change(self, config: Dict[str, Any]):
        """Handle local configuration change."""
        with self.sync_lock:
            # Avoid sync loops - don't sync if we just received an update
            if time.time() - self.last_sync_time < 2:
                return
            
            logger.info("Local config change detected, syncing to peers")
            
            # Save version
            version_path = self.config_versioning.save_version(config)
            if version_path:
                logger.info(f"Saved config version: {os.path.basename(version_path)}")
            
            # Sync to peers
            for client in self.sync_clients:
                try:
                    await client.send_config_update(config)
                except Exception as e:
                    logger.error(f"Error syncing to peer: {e}")
    
    async def _on_remote_config_update(self, message: SyncMessage):
        """Handle remote configuration update."""
        if message.type != 'config_update' or not message.config_data:
            return
            
        if message.instance_id == self.instance_id:
            # Ignore our own messages
            return
            
        logger.info(f"Received config update from {message.instance_id}")
        
        with self.sync_lock:
            current_config = self._load_current_config()
            
            # Simple conflict resolution: last write wins
            if current_config and message.timestamp > self.last_sync_time:
                # Check if there's a real conflict
                current_hash = hashlib.md5(json.dumps(current_config, sort_keys=True).encode()).hexdigest()
                
                if current_hash != message.config_hash:
                    logger.info("Config conflict detected, applying last-write-wins resolution")
                    
                    # Log security event for config changes
                    log_security_event(
                        event_type="config_sync_update",
                        severity="medium",
                        details={
                            "source_instance": message.instance_id,
                            "timestamp": message.timestamp,
                            "config_hash": message.config_hash,
                            "conflict_resolution": message.conflict_resolution
                        }
                    )
                    
                    # Apply the remote config
                    if self._save_config(message.config_data):
                        self.last_sync_time = time.time()
                        
                        # Save as version
                        version_path = self.config_versioning.save_version(message.config_data)
                        if version_path:
                            logger.info(f"Saved synced config version: {os.path.basename(version_path)}")
                        
                        # Notify callbacks
                        for callback in self.config_update_callbacks:
                            try:
                                await callback(message.config_data)
                            except Exception as e:
                                logger.error(f"Error in config update callback: {e}")
                    else:
                        logger.error("Failed to save synced configuration")
    
    async def force_sync(self):
        """Force synchronization with all peers."""
        config = self._load_current_config()
        if not config:
            logger.warning("No configuration to sync")
            return
            
        logger.info("Forcing configuration sync to all peers")
        
        for client in self.sync_clients:
            try:
                await client.send_config_update(config)
            except Exception as e:
                logger.error(f"Error in force sync: {e}")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status."""
        return {
            'running': self.running,
            'instance_id': self.instance_id,
            'server_enabled': self.enable_server,
            'server_port': self.sync_port if self.enable_server else None,
            'peer_count': len(self.sync_clients),
            'peer_urls': self.peer_urls,
            'last_sync_time': self.last_sync_time,
            'config_versions': len(self.config_versioning.list_versions())
        }

# Factory functions for different deployment scenarios
def create_single_instance_sync(config_path: str, config_base_dir: str) -> ConfigSyncManager:
    """Create sync manager for single instance (no networking)."""
    return ConfigSyncManager(
        config_path=config_path,
        config_base_dir=config_base_dir,
        enable_server=False,
        peer_urls=[]
    )

def create_ha_addon_sync(config_path: str, config_base_dir: str, 
                        addon_options: Dict[str, Any] = None) -> ConfigSyncManager:
    """Create sync manager for Home Assistant addon."""
    options = addon_options or {}
    
    sync_port = options.get('sync_port', 8765)
    peer_urls = options.get('peer_urls', [])
    enable_server = options.get('enable_sync_server', len(peer_urls) > 0)
    
    return ConfigSyncManager(
        config_path=config_path,
        config_base_dir=config_base_dir,
        sync_port=sync_port,
        peer_urls=peer_urls,
        enable_server=enable_server
    )

def create_development_sync(config_path: str, config_base_dir: str) -> ConfigSyncManager:
    """Create sync manager for development environment."""
    return ConfigSyncManager(
        config_path=config_path,
        config_base_dir=config_base_dir,
        sync_port=8765,
        peer_urls=[],
        enable_server=True
    )