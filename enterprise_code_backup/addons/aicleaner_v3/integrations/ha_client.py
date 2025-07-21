"""
Home Assistant client for AI Cleaner addon.
Handles communication with Home Assistant API.
"""
import os
import logging
import aiohttp
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

class HAClient:
    """
    Home Assistant client.
    
    Features:
    - Camera snapshot capture
    - Todo list management
    - Notification sending
    - State updates
    """
    
    def __init__(self, config):
        """
        Initialize the Home Assistant client.
        
        Args:
            config: Configuration
        """
        self.config = config
        self.logger = logging.getLogger("ha_client")
        
        # Home Assistant API URL
        self.api_url = "http://supervisor/core/api"
        
        # Home Assistant API token
        self.api_token = os.environ.get("SUPERVISOR_TOKEN")
        
        # HTTP session
        self.session = None
        
        # Image directory
        self.image_dir = "/data/images"
        
    async def initialize(self):
        """Initialize the Home Assistant client."""
        self.logger.info("Initializing Home Assistant client")
        
        # Create HTTP session
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
        )
        
        # Create image directory
        os.makedirs(self.image_dir, exist_ok=True)
        
    async def close(self):
        """Close the Home Assistant client."""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def capture_image(self, camera_entity: str) -> Optional[str]:
        """
        Capture image from camera.
        
        Args:
            camera_entity: Camera entity ID
            
        Returns:
            Image path
        """
        try:
            # Generate image path
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            image_path = os.path.join(self.image_dir, f"{camera_entity.replace('.', '_')}_{timestamp}.jpg")
            
            # Call camera/snapshot service
            response = await self.call_service(
                "camera", "snapshot",
                {
                    "entity_id": camera_entity,
                    "filename": image_path
                }
            )
            
            # Check if image exists
            if os.path.exists(image_path):
                self.logger.info(f"Captured image from {camera_entity}: {image_path}")
                return image_path
            else:
                self.logger.error(f"Image not found after capture: {image_path}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error capturing image from {camera_entity}: {e}")
            return None
            
    async def add_todo_item(self, todo_list_entity: str, item: str) -> Optional[str]:
        """
        Add todo item.
        
        Args:
            todo_list_entity: Todo list entity ID
            item: Todo item
            
        Returns:
            Todo item ID
        """
        try:
            # Call todo/add_item service
            response = await self.call_service(
                "todo", "add_item",
                {
                    "entity_id": todo_list_entity,
                    "item": item
                }
            )
            
            # Get item ID from response
            if response and "item" in response:
                item_id = response["item"].get("uid")
                self.logger.info(f"Added todo item to {todo_list_entity}: {item} (ID: {item_id})")
                return item_id
            else:
                self.logger.warning(f"No item ID returned for todo item: {item}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error adding todo item to {todo_list_entity}: {e}")
            return None

    async def update_todo_item(self, entity_id: str, item: str, status: str) -> bool:
        """
        Update todo item status.

        Args:
            entity_id: Todo list entity ID
            item: Todo item description
            status: New status ('completed', 'needs_action', etc.)

        Returns:
            Success
        """
        try:
            # Call todo/update_item service
            response = await self.call_service(
                "todo", "update_item",
                {
                    "entity_id": entity_id,
                    "item": item,
                    "status": status
                }
            )

            self.logger.info(f"Updated todo item in {entity_id}: {item} -> {status}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating todo item in {entity_id}: {e}")
            return False

    async def get_todo_list_items(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get all items from a todo list.

        Args:
            entity_id: Todo list entity ID

        Returns:
            List of todo items
        """
        try:
            # Get entity state
            state_data = await self.get_state(entity_id)

            if not state_data:
                self.logger.warning(f"Could not get state for todo list {entity_id}")
                return []

            # Extract items from attributes
            items = state_data.get("attributes", {}).get("items", [])

            self.logger.debug(f"Retrieved {len(items)} items from todo list {entity_id}")
            return items

        except Exception as e:
            self.logger.error(f"Error getting todo list items from {entity_id}: {e}")
            return []

    async def send_notification(self, service: str, message: str, data: Dict[str, Any] = None) -> bool:
        """
        Send notification.
        
        Args:
            service: Notification service
            message: Message
            data: Additional data
            
        Returns:
            Success
        """
        try:
            # Split service into domain and service
            domain, service_name = service.split(".", 1)
            
            # Prepare service data
            service_data = {
                "message": message
            }
            
            # Add additional data
            if data:
                service_data.update(data)
                
            # Call service
            await self.call_service(domain, service_name, service_data)
            
            self.logger.info(f"Sent notification via {service}: {message}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending notification via {service}: {e}")
            return False
            
    async def call_service(self, domain: str, service: str, service_data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Call Home Assistant service.
        
        Args:
            domain: Service domain
            service: Service name
            service_data: Service data
            
        Returns:
            Response data
        """
        if not self.session:
            self.logger.error("HTTP session not initialized")
            return None
            
        try:
            # Prepare URL
            url = f"{self.api_url}/services/{domain}/{service}"
            
            # Call service
            async with self.session.post(url, json=service_data or {}) as response:
                # Check response
                if response.status == 200:
                    # Parse response
                    return await response.json()
                else:
                    # Log error
                    error_text = await response.text()
                    self.logger.error(f"Error calling service {domain}.{service}: {response.status} {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error calling service {domain}.{service}: {e}")
            return None
            
    async def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get entity state.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity state
        """
        if not self.session:
            self.logger.error("HTTP session not initialized")
            return None
            
        try:
            # Prepare URL
            url = f"{self.api_url}/states/{entity_id}"
            
            # Get state
            async with self.session.get(url) as response:
                # Check response
                if response.status == 200:
                    # Parse response
                    return await response.json()
                else:
                    # Log error
                    error_text = await response.text()
                    self.logger.error(f"Error getting state for {entity_id}: {response.status} {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error getting state for {entity_id}: {e}")
            return None
            
    async def set_state(self, entity_id: str, state: str, attributes: Dict[str, Any] = None) -> bool:
        """
        Set entity state.
        
        Args:
            entity_id: Entity ID
            state: State
            attributes: Attributes
            
        Returns:
            Success
        """
        if not self.session:
            self.logger.error("HTTP session not initialized")
            return False
            
        try:
            # Prepare URL
            url = f"{self.api_url}/states/{entity_id}"
            
            # Prepare data
            data = {
                "state": state
            }
            
            # Add attributes
            if attributes:
                data["attributes"] = attributes
                
            # Set state
            async with self.session.post(url, json=data) as response:
                # Check response
                if response.status == 200 or response.status == 201:
                    self.logger.info(f"Set state for {entity_id}: {state}")
                    return True
                else:
                    # Log error
                    error_text = await response.text()
                    self.logger.error(f"Error setting state for {entity_id}: {response.status} {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error setting state for {entity_id}: {e}")
            return False