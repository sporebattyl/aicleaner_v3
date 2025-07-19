"""
Home Assistant WebSocket and REST API Client
Phase 4A: Enhanced Home Assistant Integration

Handles all communication with Home Assistant's WebSocket API and REST API.
"""

import asyncio
import json
import logging
import aiohttp
import websockets
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
import os
from pathlib import Path

from .models import (
    HAAuthMessage,
    HASubscribeMessage, 
    HACallServiceMessage,
    HAGetStatesMessage,
    HAWebSocketResponse,
    HAConnectionStatus,
    HAEntityState
)
from .config_schema import HAIntegrationConfig

logger = logging.getLogger(__name__)

class HAClient:
    """
    Home Assistant WebSocket and REST API client
    
    Manages authenticated connections to Home Assistant and provides
    methods for entity registration, state updates, and service calls.
    """
    
    def __init__(self, config: HAIntegrationConfig):
        self.config = config
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.message_id = 0
        self.event_handlers: Dict[str, Callable] = {}
        self.pending_requests: Dict[int, asyncio.Future] = {}
        self.connection_status = HAConnectionStatus()
        self.reconnect_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
    async def start(self) -> bool:
        """
        Start the HA client and establish connections
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Starting Home Assistant client...")
            
            # Load authentication token
            if not await self._load_auth_token():
                logger.error("Failed to load authentication token")
                return False
            
            # Create HTTP session
            connector = aiohttp.TCPConnector(
                verify_ssl=self.config.verify_ssl,
                limit=10,
                limit_per_host=5
            )
            timeout = aiohttp.ClientTimeout(total=self.config.connection_timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )
            
            # Test REST API connection
            if not await self._test_rest_api():
                logger.error("Failed to connect to Home Assistant REST API")
                return False
            
            # Connect WebSocket
            if not await self._connect_websocket():
                logger.error("Failed to connect to Home Assistant WebSocket")
                return False
            
            logger.info("Home Assistant client started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start HA client: {e}")
            return False
    
    async def stop(self):
        """Stop the HA client and cleanup connections"""
        logger.info("Stopping Home Assistant client...")
        self._shutdown = True
        
        # Cancel background tasks
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
        
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
        
        # Close WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
        
        # Close HTTP session
        if self.session:
            try:
                await self.session.close()
            except Exception as e:
                logger.warning(f"Error closing HTTP session: {e}")
        
        logger.info("Home Assistant client stopped")
    
    async def _load_auth_token(self) -> bool:
        """Load authentication token from supervisor"""
        try:
            token_path = Path(self.config.token_path)
            if not token_path.exists():
                logger.error(f"Token file not found: {token_path}")
                return False
            
            self.auth_token = token_path.read_text().strip()
            if not self.auth_token:
                logger.error("Empty authentication token")
                return False
            
            logger.debug("Authentication token loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load auth token: {e}")
            return False
    
    async def _test_rest_api(self) -> bool:
        """Test REST API connectivity"""
        try:
            url = f"{self.config.rest_api_url}/config"
            async with self.session.get(url) as response:
                if response.status == 200:
                    logger.debug("REST API connection test successful")
                    return True
                else:
                    logger.error(f"REST API test failed with status: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"REST API test failed: {e}")
            return False
    
    async def _connect_websocket(self) -> bool:
        """Establish WebSocket connection and authenticate"""
        try:
            logger.debug(f"Connecting to WebSocket: {self.config.websocket_url}")
            
            # Connect to WebSocket
            self.websocket = await websockets.connect(
                self.config.websocket_url,
                compression="deflate" if self.config.websocket_compression else None,
                ping_interval=self.config.heartbeat_interval,
                close_timeout=10
            )
            
            # Wait for auth_required message
            auth_required = await self.websocket.recv()
            auth_data = json.loads(auth_required)
            
            if auth_data.get("type") != "auth_required":
                logger.error(f"Expected auth_required, got: {auth_data}")
                return False
            
            # Send authentication
            auth_msg = HAAuthMessage(access_token=self.auth_token)
            await self.websocket.send(auth_msg.json())
            
            # Wait for auth response
            auth_response = await self.websocket.recv()
            auth_result = json.loads(auth_response)
            
            if auth_result.get("type") != "auth_ok":
                logger.error(f"Authentication failed: {auth_result}")
                return False
            
            logger.info("WebSocket connection and authentication successful")
            
            # Update connection status
            self.connection_status.connected = True
            self.connection_status.websocket_connected = True
            self.connection_status.authenticated = True
            self.connection_status.last_connection = datetime.now()
            self.connection_status.reconnect_attempts = 0
            
            # Start message handling task
            asyncio.create_task(self._handle_websocket_messages())
            
            # Start heartbeat task
            if self.heartbeat_task is None or self.heartbeat_task.done():
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.connection_status.last_error = str(e)
            return False
    
    async def _handle_websocket_messages(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._process_websocket_message(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to decode WebSocket message: {e}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.connection_status.websocket_connected = False
            if not self._shutdown:
                await self._schedule_reconnect()
        except Exception as e:
            logger.error(f"WebSocket message handling error: {e}")
            self.connection_status.last_error = str(e)
            if not self._shutdown:
                await self._schedule_reconnect()
    
    async def _process_websocket_message(self, data: Dict[str, Any]):
        """Process individual WebSocket message"""
        msg_type = data.get("type")
        msg_id = data.get("id")
        
        # Handle responses to pending requests
        if msg_id is not None and msg_id in self.pending_requests:
            future = self.pending_requests.pop(msg_id)
            if not future.done():
                future.set_result(data)
            return
        
        # Handle events
        if msg_type == "event":
            event_data = data.get("event", {})
            event_type = event_data.get("event_type")
            
            if event_type in self.event_handlers:
                try:
                    await self.event_handlers[event_type](event_data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")
        
        # Handle other message types
        elif msg_type == "pong":
            logger.debug("Received WebSocket pong")
        else:
            logger.debug(f"Unhandled WebSocket message type: {msg_type}")
    
    async def _schedule_reconnect(self):
        """Schedule WebSocket reconnection"""
        if self.reconnect_task and not self.reconnect_task.done():
            return
        
        self.reconnect_task = asyncio.create_task(self._reconnect_loop())
    
    async def _reconnect_loop(self):
        """Reconnection loop with exponential backoff"""
        attempts = 0
        while (attempts < self.config.max_reconnect_attempts and 
               not self._shutdown and 
               not self.connection_status.websocket_connected):
            
            attempts += 1
            wait_time = min(self.config.reconnect_interval * (2 ** (attempts - 1)), 300)
            
            logger.info(f"Reconnecting to WebSocket (attempt {attempts}/{self.config.max_reconnect_attempts})...")
            
            try:
                await asyncio.sleep(wait_time)
                if await self._connect_websocket():
                    logger.info("WebSocket reconnection successful")
                    return
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempts} failed: {e}")
        
        if attempts >= self.config.max_reconnect_attempts:
            logger.error("Maximum reconnection attempts reached")
            self.connection_status.last_error = "Maximum reconnection attempts reached"
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages"""
        while not self._shutdown and self.connection_status.websocket_connected:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                if self.websocket and not self.websocket.closed:
                    await self.websocket.ping()
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
                break
    
    async def call_service(self, domain: str, service: str, 
                          service_data: Optional[Dict[str, Any]] = None,
                          target: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Call a Home Assistant service
        
        Args:
            domain: Service domain
            service: Service name
            service_data: Service data payload
            target: Service target
            
        Returns:
            Service call result
        """
        if not self.connection_status.websocket_connected:
            raise RuntimeError("WebSocket not connected")
        
        msg_id = self._get_message_id()
        message = HACallServiceMessage(
            id=msg_id,
            domain=domain,
            service=service,
            service_data=service_data or {},
            target=target
        )
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[msg_id] = future
        
        try:
            await self.websocket.send(message.json())
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=30.0)
            
            if not response.get("success", False):
                error = response.get("error", {})
                raise RuntimeError(f"Service call failed: {error}")
            
            return response.get("result", {})
            
        except asyncio.TimeoutError:
            self.pending_requests.pop(msg_id, None)
            raise RuntimeError("Service call timeout")
        except Exception as e:
            self.pending_requests.pop(msg_id, None)
            raise RuntimeError(f"Service call failed: {e}")
    
    async def get_states(self, entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get entity states from Home Assistant
        
        Args:
            entity_id: Specific entity ID (optional)
            
        Returns:
            List of entity states
        """
        if not self.connection_status.websocket_connected:
            raise RuntimeError("WebSocket not connected")
        
        msg_id = self._get_message_id()
        message = HAGetStatesMessage(id=msg_id)
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[msg_id] = future
        
        try:
            await self.websocket.send(message.json())
            
            # Wait for response
            response = await asyncio.wait_for(future, timeout=10.0)
            
            if not response.get("success", False):
                error = response.get("error", {})
                raise RuntimeError(f"Get states failed: {error}")
            
            states = response.get("result", [])
            
            # Filter by entity_id if specified
            if entity_id:
                states = [state for state in states if state.get("entity_id") == entity_id]
            
            return states
            
        except asyncio.TimeoutError:
            self.pending_requests.pop(msg_id, None)
            raise RuntimeError("Get states timeout")
        except Exception as e:
            self.pending_requests.pop(msg_id, None)
            raise RuntimeError(f"Get states failed: {e}")
    
    async def subscribe_events(self, event_type: Optional[str] = None, 
                             handler: Optional[Callable] = None) -> bool:
        """
        Subscribe to Home Assistant events
        
        Args:
            event_type: Specific event type to subscribe to
            handler: Event handler callback
            
        Returns:
            True if successful
        """
        if not self.connection_status.websocket_connected:
            raise RuntimeError("WebSocket not connected")
        
        msg_id = self._get_message_id()
        message = HASubscribeMessage(id=msg_id, event_type=event_type)
        
        # Register event handler
        if handler and event_type:
            self.event_handlers[event_type] = handler
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[msg_id] = future
        
        try:
            await self.websocket.send(message.json())
            
            # Wait for response
            response = await asyncio.wait_for(future, timeout=10.0)
            
            if not response.get("success", False):
                error = response.get("error", {})
                raise RuntimeError(f"Event subscription failed: {error}")
            
            logger.debug(f"Subscribed to events: {event_type or 'all'}")
            return True
            
        except asyncio.TimeoutError:
            self.pending_requests.pop(msg_id, None)
            raise RuntimeError("Event subscription timeout")
        except Exception as e:
            self.pending_requests.pop(msg_id, None)
            raise RuntimeError(f"Event subscription failed: {e}")
    
    async def register_entity(self, entity_config: Dict[str, Any]) -> bool:
        """
        Register entity with Home Assistant via REST API
        
        Args:
            entity_config: Entity configuration
            
        Returns:
            True if successful
        """
        try:
            url = f"{self.config.rest_api_url}/config/entity_registry"
            
            async with self.session.post(url, json=entity_config) as response:
                if response.status in [200, 201]:
                    logger.debug(f"Entity registered successfully: {entity_config.get('unique_id')}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Entity registration failed: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Entity registration error: {e}")
            return False
    
    async def update_entity_state(self, entity_id: str, state: Any, 
                                attributes: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update entity state in Home Assistant
        
        Args:
            entity_id: Full entity ID
            state: Entity state value
            attributes: Entity attributes
            
        Returns:
            True if successful
        """
        try:
            url = f"{self.config.rest_api_url}/states/{entity_id}"
            
            payload = {
                "state": state,
                "attributes": attributes or {}
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status in [200, 201]:
                    logger.debug(f"Entity state updated: {entity_id} = {state}")
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(f"State update failed: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"State update error: {e}")
            return False
    
    def _get_message_id(self) -> int:
        """Get next message ID for WebSocket messages"""
        self.message_id += 1
        return self.message_id
    
    def get_connection_status(self) -> HAConnectionStatus:
        """Get current connection status"""
        return self.connection_status
    
    def is_connected(self) -> bool:
        """Check if client is fully connected and authenticated"""
        return (self.connection_status.connected and 
                self.connection_status.websocket_connected and 
                self.connection_status.authenticated)