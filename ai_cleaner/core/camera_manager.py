"""
Camera management for AI Cleaner Home Assistant addon.
Handles image fetching from IP cameras via Home Assistant API.
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from io import BytesIO
from PIL import Image
import base64
import json

from .config import get_config, AiCleanerConfig


logger = logging.getLogger(__name__)


class CameraError(Exception):
    """Camera-related exception."""
    pass


class ImageData:
    """Container for camera image data and metadata."""
    
    def __init__(self, data: bytes, entity_id: str, timestamp: Optional[datetime] = None):
        self.data = data
        self.entity_id = entity_id
        self.timestamp = timestamp or datetime.now()
        self._size: Optional[Tuple[int, int]] = None
        self._format: Optional[str] = None
    
    @property
    def size(self) -> Tuple[int, int]:
        """Get image dimensions."""
        if self._size is None:
            try:
                with Image.open(BytesIO(self.data)) as img:
                    self._size = img.size
                    self._format = img.format
            except Exception as e:
                logger.warning(f"Failed to get image size: {e}")
                self._size = (0, 0)
        return self._size
    
    @property
    def format(self) -> Optional[str]:
        """Get image format."""
        if self._format is None:
            _ = self.size  # This will populate both size and format
        return self._format
    
    @property
    def size_bytes(self) -> int:
        """Get image size in bytes."""
        return len(self.data)
    
    def to_base64(self) -> str:
        """Convert image to base64 string."""
        return base64.b64encode(self.data).decode('utf-8')
    
    def save_to_file(self, filepath: str) -> bool:
        """Save image to file."""
        try:
            with open(filepath, 'wb') as f:
                f.write(self.data)
            return True
        except Exception as e:
            logger.error(f"Failed to save image to {filepath}: {e}")
            return False
    
    def resize(self, max_width: int = 1024, max_height: int = 1024, quality: int = 85) -> bytes:
        """Resize image for AI processing."""
        try:
            with Image.open(BytesIO(self.data)) as img:
                # Calculate new size maintaining aspect ratio
                width, height = img.size
                if width <= max_width and height <= max_height:
                    return self.data
                
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                
                # Resize image
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save to bytes
                output = BytesIO()
                format_name = img.format or 'JPEG'
                if format_name.upper() in ['JPEG', 'JPG']:
                    resized_img.save(output, format='JPEG', quality=quality, optimize=True)
                else:
                    resized_img.save(output, format=format_name)
                
                return output.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to resize image: {e}")
            return self.data


class CameraManager:
    """Manages camera image fetching from Home Assistant."""
    
    def __init__(self, config: Optional[AiCleanerConfig] = None):
        """Initialize camera manager."""
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        self._session: Optional[aiohttp.ClientSession] = None
        self._camera_info_cache: Dict[str, Dict] = {}
        self._cache_timeout = timedelta(minutes=5)
        self._last_cache_update: Optional[datetime] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is available."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=self.config.analysis_timeout)
            headers = {
                'User-Agent': 'AI-Cleaner/1.0',
                'Content-Type': 'application/json'
            }
            
            if self.config.ha_token:
                headers['Authorization'] = f'Bearer {self.config.ha_token.get_secret_value()}'
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers
            )
            
            self.logger.debug("HTTP session created")
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.debug("HTTP session closed")
    
    async def get_camera_snapshot(self, entity_id: str, resize_for_ai: bool = True) -> ImageData:
        """
        Get camera snapshot from Home Assistant.
        
        Args:
            entity_id: Camera entity ID (e.g., 'camera.living_room')
            resize_for_ai: Whether to resize image for AI processing
            
        Returns:
            ImageData object containing the image
            
        Raises:
            CameraError: If snapshot cannot be obtained
        """
        await self._ensure_session()
        
        try:
            # Get camera snapshot via HA API
            url = f"{self.config.ha_url}/api/camera_proxy/{entity_id}"
            
            self.logger.debug(f"Fetching snapshot from {entity_id}")
            
            async with self._session.get(url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    
                    if not image_data:
                        raise CameraError(f"Empty image data received from {entity_id}")
                    
                    # Create ImageData object
                    image = ImageData(image_data, entity_id)
                    
                    # Resize if requested
                    if resize_for_ai:
                        resized_data = image.resize()
                        if resized_data != image_data:
                            image = ImageData(resized_data, entity_id, image.timestamp)
                            self.logger.debug(f"Resized image from {len(image_data)} to {len(resized_data)} bytes")
                    
                    self.logger.info(f"Successfully captured snapshot from {entity_id} ({image.size[0]}x{image.size[1]}, {image.size_bytes} bytes)")
                    return image
                
                elif response.status == 404:
                    raise CameraError(f"Camera entity not found: {entity_id}")
                elif response.status == 401:
                    raise CameraError("Unauthorized - check Home Assistant token")
                else:
                    error_text = await response.text()
                    raise CameraError(f"Failed to get snapshot from {entity_id}: HTTP {response.status} - {error_text}")
        
        except aiohttp.ClientError as e:
            raise CameraError(f"Network error getting snapshot from {entity_id}: {e}")
        except Exception as e:
            raise CameraError(f"Unexpected error getting snapshot from {entity_id}: {e}")
    
    async def get_multiple_snapshots(self, entity_ids: List[str], resize_for_ai: bool = True) -> Dict[str, ImageData]:
        """
        Get snapshots from multiple cameras concurrently.
        
        Args:
            entity_ids: List of camera entity IDs
            resize_for_ai: Whether to resize images for AI processing
            
        Returns:
            Dictionary mapping entity IDs to ImageData objects
        """
        if not entity_ids:
            return {}
        
        self.logger.info(f"Fetching snapshots from {len(entity_ids)} cameras")
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.config.max_concurrent_analysis)
        
        async def fetch_single(entity_id: str) -> Tuple[str, Optional[ImageData]]:
            """Fetch single snapshot with semaphore protection."""
            async with semaphore:
                try:
                    image = await self.get_camera_snapshot(entity_id, resize_for_ai)
                    return entity_id, image
                except CameraError as e:
                    self.logger.error(f"Failed to fetch snapshot from {entity_id}: {e}")
                    return entity_id, None
        
        # Execute all requests concurrently
        tasks = [fetch_single(entity_id) for entity_id in entity_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        snapshots = {}
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Snapshot task failed: {result}")
                continue
            
            entity_id, image_data = result
            if image_data:
                snapshots[entity_id] = image_data
        
        self.logger.info(f"Successfully captured {len(snapshots)}/{len(entity_ids)} snapshots")
        return snapshots
    
    async def get_camera_info(self, entity_id: str) -> Dict[str, Any]:
        """
        Get camera information from Home Assistant.
        
        Args:
            entity_id: Camera entity ID
            
        Returns:
            Dictionary with camera information
        """
        # Check cache first
        if (self._last_cache_update and 
            datetime.now() - self._last_cache_update < self._cache_timeout and
            entity_id in self._camera_info_cache):
            return self._camera_info_cache[entity_id]
        
        await self._ensure_session()
        
        try:
            url = f"{self.config.ha_url}/api/states/{entity_id}"
            
            async with self._session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract useful information
                    camera_info = {
                        'entity_id': entity_id,
                        'state': data.get('state'),
                        'friendly_name': data.get('attributes', {}).get('friendly_name', entity_id),
                        'supported_features': data.get('attributes', {}).get('supported_features', 0),
                        'brand': data.get('attributes', {}).get('brand'),
                        'model': data.get('attributes', {}).get('model'),
                        'motion_detection': data.get('attributes', {}).get('motion_detection', False),
                        'last_updated': data.get('last_updated'),
                        'last_changed': data.get('last_changed'),
                    }
                    
                    # Cache the result
                    self._camera_info_cache[entity_id] = camera_info
                    self._last_cache_update = datetime.now()
                    
                    return camera_info
                
                elif response.status == 404:
                    raise CameraError(f"Camera entity not found: {entity_id}")
                else:
                    error_text = await response.text()
                    raise CameraError(f"Failed to get camera info for {entity_id}: HTTP {response.status} - {error_text}")
        
        except aiohttp.ClientError as e:
            raise CameraError(f"Network error getting camera info for {entity_id}: {e}")
        except Exception as e:
            raise CameraError(f"Unexpected error getting camera info for {entity_id}: {e}")
    
    async def list_available_cameras(self) -> List[Dict[str, Any]]:
        """
        List all available camera entities in Home Assistant.
        
        Returns:
            List of camera information dictionaries
        """
        await self._ensure_session()
        
        try:
            url = f"{self.config.ha_url}/api/states"
            
            async with self._session.get(url) as response:
                if response.status == 200:
                    states = await response.json()
                    
                    # Filter for camera entities
                    cameras = []
                    for state in states:
                        entity_id = state.get('entity_id', '')
                        if entity_id.startswith('camera.'):
                            camera_info = {
                                'entity_id': entity_id,
                                'state': state.get('state'),
                                'friendly_name': state.get('attributes', {}).get('friendly_name', entity_id),
                                'supported_features': state.get('attributes', {}).get('supported_features', 0),
                                'brand': state.get('attributes', {}).get('brand'),
                                'model': state.get('attributes', {}).get('model'),
                            }
                            cameras.append(camera_info)
                    
                    self.logger.info(f"Found {len(cameras)} camera entities")
                    return cameras
                
                else:
                    error_text = await response.text()
                    raise CameraError(f"Failed to list cameras: HTTP {response.status} - {error_text}")
        
        except aiohttp.ClientError as e:
            raise CameraError(f"Network error listing cameras: {e}")
        except Exception as e:
            raise CameraError(f"Unexpected error listing cameras: {e}")
    
    async def test_camera_access(self, entity_id: str) -> Dict[str, Any]:
        """
        Test camera access and return diagnostic information.
        
        Args:
            entity_id: Camera entity ID to test
            
        Returns:
            Dictionary with test results
        """
        test_results = {
            'entity_id': entity_id,
            'accessible': False,
            'info_available': False,
            'snapshot_available': False,
            'error': None,
            'response_time_ms': None,
            'image_size': None,
            'image_format': None,
        }
        
        start_time = datetime.now()
        
        try:
            # Test camera info access
            try:
                camera_info = await self.get_camera_info(entity_id)
                test_results['info_available'] = True
                test_results['camera_info'] = camera_info
            except CameraError as e:
                test_results['error'] = f"Info access failed: {e}"
            
            # Test snapshot access
            try:
                image = await self.get_camera_snapshot(entity_id, resize_for_ai=False)
                test_results['snapshot_available'] = True
                test_results['image_size'] = image.size
                test_results['image_format'] = image.format
                test_results['image_bytes'] = image.size_bytes
                test_results['accessible'] = True
            except CameraError as e:
                if not test_results['error']:
                    test_results['error'] = f"Snapshot access failed: {e}"
                else:
                    test_results['error'] += f"; Snapshot access failed: {e}"
        
        except Exception as e:
            test_results['error'] = f"Unexpected error: {e}"
        
        # Calculate response time
        end_time = datetime.now()
        test_results['response_time_ms'] = int((end_time - start_time).total_seconds() * 1000)
        
        return test_results
    
    def get_zone_cameras(self) -> Dict[str, List[str]]:
        """
        Get mapping of zone IDs to camera entity IDs.
        
        Returns:
            Dictionary mapping zone IDs to lists of camera entity IDs
        """
        zone_cameras = {}
        
        if self.config.enable_zones:
            for zone in self.config.zones:
                if zone.enabled and zone.camera_entity:
                    zone_cameras[zone.id] = [zone.camera_entity]
        
        # Add default camera if configured
        if self.config.camera_entity and 'default' not in zone_cameras:
            zone_cameras['default'] = [self.config.camera_entity]
        
        return zone_cameras
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on camera manager.
        
        Returns:
            Dictionary with health check results
        """
        health = {
            'status': 'healthy',
            'session_active': False,
            'cameras_configured': 0,
            'cache_entries': len(self._camera_info_cache),
            'errors': []
        }
        
        try:
            # Check session status
            if self._session and not self._session.closed:
                health['session_active'] = True
            
            # Count configured cameras
            zone_cameras = self.get_zone_cameras()
            all_cameras = set()
            for cameras in zone_cameras.values():
                all_cameras.update(cameras)
            health['cameras_configured'] = len(all_cameras)
            
            # Test default camera if configured
            if self.config.camera_entity:
                try:
                    test_result = await self.test_camera_access(self.config.camera_entity)
                    if not test_result['accessible']:
                        health['status'] = 'degraded'
                        health['errors'].append(f"Default camera not accessible: {test_result.get('error')}")
                except Exception as e:
                    health['status'] = 'degraded'
                    health['errors'].append(f"Default camera test failed: {e}")
        
        except Exception as e:
            health['status'] = 'unhealthy'
            health['errors'].append(f"Health check failed: {e}")
        
        return health