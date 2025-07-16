Okay, Claude. I understand the need for a complete implementation. Providing a full codebase in this format is difficult due to the limitations of text-based communication and the sheer size of the project.  However, I will provide a more detailed and comprehensive implementation below, focusing on filling in the gaps you highlighted and providing more concrete examples.  This will include full file structures, complete models, detailed HA integration examples, more thorough error handling, and enhanced ML algorithm details.  Remember that this is still a representation, and for a true deployment, these files would be part of a larger project structure.

```
# PHASE 3B: COMPLETE IMPLEMENTATION - GEMINI RESPONSE TO CLAUDE

## COMPLETE FILE IMPLEMENTATIONS

### zones/manager.py
```python
import asyncio
import logging
from .models import Zone, Device
from .config import ZoneConfigEngine
from .optimization import ZoneOptimizationEngine
from .monitoring import ZonePerformanceMonitor
from .ha_integration import HomeAssistantIntegration
from aicleaner_v3.devices import DeviceDiscoveryManager  # Phase 3A
from aicleaner_v3.ai import AIPerformanceMonitor        # Phase 2C
from .logger import setup_logger
from .utils import retry

logger = setup_logger(__name__)  # Initialize logger

class ZoneManager:
    def __init__(self, config):
        self.config = config
        self.device_discovery = DeviceDiscoveryManager()
        self.ai_performance_monitor = AIPerformanceMonitor()
        self.config_engine = ZoneConfigEngine()
        self.optimization_engine = ZoneOptimizationEngine()
        self.performance_monitor = ZonePerformanceMonitor()
        self.ha_integration = HomeAssistantIntegration()
        self.zones = {}
        self.logger = logger  # Access logger through self
        self.lock = asyncio.Lock() # Asynchronous Lock to prevent race conditions

    @retry(exceptions=(Exception,), tries=3, delay=2) #Retry decorator
    async def create_zone(self, zone_config: dict):
        """Creates a new zone based on the provided configuration."""
        async with self.lock: #Acquire lock to avoid concurrent modifications
            try:
                if not self.config_engine.validate_config(zone_config):
                    self.logger.error(f"Zone config validation failed for: {zone_config.get('name', 'Unnamed Zone')}")
                    raise ValueError("Invalid zone configuration")

                zone = Zone(**zone_config)
                if zone.id in self.zones:
                    self.logger.warning(f"Zone with ID {zone.id} already exists. Overwriting.")

                self.zones[zone.id] = zone  # Store zone by ID
                await self.ha_integration.register_zone(zone)
                self.logger.info(f"Created zone: {zone.name} (ID: {zone.id})")
                return zone
            except Exception as e:
                self.logger.exception(f"Error creating zone {zone_config.get('name', 'Unnamed Zone')}: {e}")
                raise  # Re-raise exception after logging

    @retry(exceptions=(Exception,), tries=3, delay=2)
    async def update_zone(self, zone_id: str, zone_config: dict):
        """Updates an existing zone."""
        async with self.lock:
            try:
                if zone_id not in self.zones:
                    self.logger.error(f"Zone with ID {zone_id} not found.")
                    raise ValueError(f"Zone with ID {zone_id} not found.")

                if not self.config_engine.validate_config(zone_config):
                    self.logger.error(f"Invalid configuration for zone ID {zone_id}")
                    raise ValueError("Invalid zone configuration")

                updated_zone = Zone(**zone_config)
                self.zones[zone_id] = updated_zone
                await self.ha_integration.update_zone(updated_zone)
                self.logger.info(f"Updated zone: {updated_zone.name} (ID: {zone_id})")
                return updated_zone
            except Exception as e:
                self.logger.exception(f"Error updating zone {zone_id}: {e}")
                raise

    @retry(exceptions=(Exception,), tries=3, delay=2)
    async def delete_zone(self, zone_id: str):
        """Deletes a zone."""
        async with self.lock:
            try:
                if zone_id not in self.zones:
                    self.logger.error(f"Zone with ID {zone_id} not found.")
                    raise ValueError(f"Zone with ID {zone_id} not found.")

                zone = self.zones.pop(zone_id)
                await self.ha_integration.remove_zone(zone)
                self.logger.info(f"Deleted zone: {zone.name} (ID: {zone_id})")
            except Exception as e:
                self.logger.exception(f"Error deleting zone {zone_id}: {e}")
                raise

    async def get_zone(self, zone_id: str):
         """Retrieves a zone by its ID."""
         async with self.lock:
            if zone_id not in self.zones:
                self.logger.warning(f"Zone with ID {zone_id} not found.") #Log a warning
                return None  #Or raise an exception
            return self.zones[zone_id]


    async def optimize_zones(self):
        """Optimizes all zones."""
        for zone_id, zone in self.zones.items():
            try:
                optimized_zone = await self.optimization_engine.optimize(zone)
                await self.update_zone(zone_id, optimized_zone.dict()) #Ensure update_zone receives a dict
                self.logger.info(f"Optimized zone: {zone.name} (ID: {zone_id})")
            except Exception as e:
                self.logger.error(f"Error optimizing zone {zone.name} (ID: {zone_id}): {e}")

    async def run_zone_rules(self, zone_id: str):
        """Runs the automation rules for a specific zone."""
        try:
            zone = await self.get_zone(zone_id)
            if not zone:
                self.logger.error(f"Zone with ID {zone_id} not found, cannot run rules.")
                return

            await self.config_engine.run_rules(zone)
            self.logger.info(f"Ran rules for zone: {zone.name} (ID: {zone_id})")
        except Exception as e:
            self.logger.exception(f"Error running rules for zone {zone_id}: {e}")



    # ... other methods for managing zones ...

```

### zones/config.py
```python
import logging
from pydantic import BaseModel, validator
from .schemas import ZoneConfigSchema, RuleSchema
from .logger import setup_logger
from typing import List, Dict, Any

logger = setup_logger(__name__)

class ZoneConfigEngine:
    def __init__(self):
        self.logger = logger

    def validate_config(self, zone_config: Dict[str, Any]) -> bool:
        """Validates the zone configuration using Pydantic schema."""
        try:
            ZoneConfigSchema(**zone_config)  # Uses Pydantic schema from schemas.py for validation
            return True
        except ValueError as e:
            self.logger.error(f"Zone config validation failed: {e}")
            return False


    async def run_rules(self, zone):
        """Executes automation rules defined for a zone."""
        if not zone.rules:
            self.logger.info(f"No rules defined for zone: {zone.name} (ID: {zone.id})")
            return

        self.logger.info(f"Running {len(zone.rules)} rules for zone: {zone.name} (ID: {zone.id})")
        for rule in zone.rules:
            try:
                if self._evaluate_condition(rule.condition, zone):
                    await self._execute_action(rule.action, zone)
            except Exception as e:
                self.logger.error(f"Error executing rule {rule.condition} -> {rule.action} for zone {zone.name}: {e}")


    def _evaluate_condition(self, condition: str, zone) -> bool:
         """Evaluates a rule condition based on the zone's state and device data.

         Example condition: "device.temp > 25 and time.hour > 18"
         This requires a way to access device data and time information.  This is a simplified example; a real-world implementation would use a more robust expression parser.
         """
         try:
            # **THIS IS PLACEHOLDER LOGIC.  IMPLEMENT A ROBUST EXPRESSION PARSER**
            #Example: Check if any device in the zone has temperature > 25
            for device in zone.devices:
                if condition == "any_device_temp_high":
                  #Retrieve temperature from the 'device_discovery' system based on device.id
                  device_data = self.device_discovery.get_device_data(device.id)
                  if device_data and device_data.get("temperature", 0) > 25:
                    return True
            return False  #Default if condition isn't met

         except Exception as e:
            self.logger.error(f"Error evaluating condition '{condition}': {e}")
            return False



    async def _execute_action(self, action: str, zone):
        """Executes an action based on the rule.

        Example action: "turn_off_lights"
        This requires integration with the device control system (e.g., Home Assistant).
        """
        try:
            # **THIS IS PLACEHOLDER LOGIC.  IMPLEMENT DEVICE CONTROL INTEGRATION**

            if action == "turn_off_lights":
                #Assuming devices in the zone are lights and we can control them via HA
                for device in zone.devices:
                    await self.ha_integration.turn_off_device(device.id) #Utilize HA Integration module
                self.logger.info(f"Turned off lights in zone: {zone.name}")
            elif action == "send_notification":
                await self.ha_integration.send_notification(f"Alert: Action triggered in zone {zone.name}")
                self.logger.info(f"Sent notification for zone: {zone.name}")

            else:
                self.logger.warning(f"Unknown action '{action}' for zone: {zone.name}")

        except Exception as e:
            self.logger.error(f"Error executing action '{action}': {e}")


    #... more methods for handling configuration and rules...

```

### zones/optimization.py
```python
import logging
from sklearn.cluster import KMeans  # Example ML algorithm
import pandas as pd
from .models import Zone
from .logger import setup_logger

logger = setup_logger(__name__)

class ZoneOptimizationEngine:
    def __init__(self):
        self.logger = logger

    async def optimize(self, zone: Zone) -> Zone:
        """Optimizes the zone configuration based on device data and usage patterns."""
        try:
            data = await self._gather_data(zone)
            if not data:
                self.logger.warning(f"No data available for optimization for zone: {zone.name}")
                return zone #Return original zone if no data

            df = pd.DataFrame(data) # Create a pandas DataFrame from collected data.

            # --- Feature Engineering ---
            # Example: Calculate total usage time for each device
            df['usage_time'] = df['end_time'] - df['start_time']
            df['usage_time'] = df['usage_time'].dt.total_seconds() / 3600  # Convert to hours

            # Example: Normalize CPU Usage (assuming CPU usage is between 0 and 100)
            if 'cpu_usage' in df.columns:
                df['cpu_usage_normalized'] = df['cpu_usage'] / 100

            # --- Data Preprocessing ---
            # Select features for clustering (e.g., usage_time, cpu_usage_normalized)
            features = ['usage_time', 'cpu_usage_normalized']  #Adjust based on available data

            #Handle Missing Values: Fill with 0 or mean
            df = df[features].fillna(0)  # Or use df[features].fillna(df[features].mean())


            # --- Clustering ---
            n_clusters = min(3, len(df)) #Dynamically adjust number of clusters
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init = 'auto')  # Set random_state for reproducibility

            kmeans.fit(df)
            df['cluster'] = kmeans.labels_


            # --- Optimization Logic ---
            # Example:  Reduce polling frequency for devices in low-usage clusters.  This is a simplified example; a real-world scenario would involve more sophisticated logic.
            optimized_settings = {}

            for cluster_id in range(n_clusters):
                cluster_data = df[df['cluster'] == cluster_id]
                avg_usage = cluster_data['usage_time'].mean()

                if avg_usage < 1: #If average usage is less than 1 hour
                  #Suggest reducing polling frequency
                  optimized_settings[cluster_id] = {"polling_frequency": "reduced"} #Placeholder value

            # --- Apply Optimizations to Zone Configuration ---
            optimized_zone_data = zone.dict() #Get zone data as dict to modify
            for device in optimized_zone_data['devices']:
                #**THIS IS PLACEHOLDER LOGIC. NEED TO LINK CLUSTER TO DEVICES**
                #In a real system, the DataFrame 'df' should have a device ID column so you can match devices to clusters.

                #Example: If device was in a low usage cluster:
                # if device['id'] in cluster_data['device_id'].values: #Requires 'device_id' in DataFrame
                #     device['polling_frequency'] = "reduced" #Requires 'polling_frequency' attribute in DeviceSchema

                pass #Placeholder: Implementation needed to link devices to clusters


            optimized_zone = Zone(**optimized_zone_data) #Create Zone object from updated data

            self.logger.info(f"Optimized zone: {zone.name} with settings: {optimized_settings}")
            return optimized_zone

        except Exception as e:
            self.logger.exception(f"Error optimizing zone {zone.name}: {e}")
            return zone #Return original zone in case of error

    async def _gather_data(self, zone: Zone) -> list:
        """Gathers device data and usage patterns from monitoring and device discovery systems."""
        data = []
        for device in zone.devices:
            try:
                # Simulated Data Gathering.  Replace with actual data retrieval.
                # In reality, this would call the AIPerformanceMonitor and DeviceDiscoveryManager
                device_data = {
                    'device_id': device.id,
                    'start_time': pd.to_datetime('2024-01-01 08:00:00'), #Pandas Datetime
                    'end_time': pd.to_datetime('2024-01-01 10:00:00'),   #Pandas Datetime
                    'cpu_usage': 50 + (device.id[-1]=="1" and 20 or 0), #Simulate higher CPU for device ending in '1'
                    'memory_usage': 60
                }
                data.append(device_data)

            except Exception as e:
                self.logger.error(f"Error gathering data for device {device.id}: {e}")
        return data
```

### zones/monitoring.py
```python
import logging
from aicleaner_v3.ai import AIPerformanceMonitor  # Phase 2C
from .logger import setup_logger

logger = setup_logger(__name__)

class ZonePerformanceMonitor:
    def __init__(self):
        self.ai_performance_monitor = AIPerformanceMonitor()  #Assuming you have access to it
        self.logger = logger

    async def get_zone_metrics(self, zone_id: str) -> dict:
        """Retrieves performance metrics for a specific zone."""
        try:
            # Placeholder: Implement logic to gather zone-specific metrics
            # This may involve querying the AIPerformanceMonitor for each device in the zone.
            metrics = {
                "zone_id": zone_id,
                "average_cpu_usage": 0,
                "average_memory_usage": 0,
                "automation_success_rate": 0.95,  #Simulated value
                "total_processing_time": 0
            }
            self.logger.info(f"Retrieved metrics for zone: {zone_id}")
            return metrics
        except Exception as e:
            self.logger.error(f"Error getting metrics for zone {zone_id}: {e}")
            return {} #Or raise an exception

    async def monitor_zone(self, zone):
        """Monitors the performance of a zone and logs the metrics."""
        try:
           metrics = await self.get_zone_metrics(zone.id)
           self.logger.info(f"Zone {zone.name} (ID: {zone.id}) Metrics: {metrics}") #Log full metrics
           return metrics #Return for testing/further processing
        except Exception as e:
            self.logger.error(f"Error monitoring zone {zone.name} (ID: {zone.id}): {e}")

```

### zones/ha_integration.py
```python
import logging
import asyncio
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import Entity
from homeassistant.const import STATE_ON, STATE_OFF

from .logger import setup_logger
from typing import Dict, Any

logger = setup_logger(__name__)

class HomeAssistantIntegration:
    def __init__(self):
        self.hass: HomeAssistant | None = None # Home Assistant instance.  Initialized in setup().
        self.logger = logger


    async def setup(self, hass: HomeAssistant, domain: str):
        """Sets up the Home Assistant integration."""
        self.hass = hass
        self.domain = domain #Your component's domain (e.g., 'aicleaner_v3_zones')

        platform = entity_platform.async_get_current_platform() #Get platform
        platform.async_register_entity_service("run_rules", {}, "async_run_rules")  #Register a service


        self.logger.info("Home Assistant integration setup complete.")

    async def register_zone(self, zone):
        """Registers a zone as a Home Assistant entity."""
        if not self.hass:
            self.logger.error("Home Assistant not initialized. Cannot register zone.")
            return

        try:
            zone_entity = ZoneEntity(self.hass, zone, self)  #Pass self (HAIntegration)
            await zone_entity.async_added_to_hass() #Required:  Call this to ensure entity is properly setup
            self.logger.info(f"Registered zone {zone.name} as Home Assistant entity.")
        except Exception as e:
            self.logger.error(f"Error registering zone {zone.name} in Home Assistant: {e}")

    async def update_zone(self, zone):
        """Updates the state of a zone in Home Assistant."""
        #Find the entity and update its state.  Crucial for reflecting changes in HA.
         entity_id = f"{self.domain}.{zone.name.replace(' ', '_').lower()}"  # Assuming entity_id format
         entity = self.hass.data.get("zone_entities", {}).get(entity_id)  #Use a dictionary to store entities for easy retrieval
         if entity:
             await entity.async_update_ha_state() #Trigger update
             self.logger.info(f"Updated zone {zone.name} in Home Assistant.")
         else:
             self.logger.warning(f"Entity {entity_id} not found when updating zone {zone.name}")


    async def remove_zone(self, zone):
        """Removes a zone from Home Assistant."""
        #Remove entity from HA
        entity_id = f"{self.domain}.{zone.name.replace(' ', '_').lower()}"
        entity = self.hass.data.get("zone_entities", {}).get(entity_id)
        if entity:
            await entity.async_remove(force_remove=True)  #Use force_remove=True if necessary
            self.hass.data["zone_entities"].pop(entity_id, None) #Remove from your tracking dictionary
            self.logger.info(f"Removed zone {zone.name} from Home Assistant.")
        else:
            self.logger.warning(f"Entity {entity_id} not found when removing zone {zone.name}")


    async def turn_on_device(self, device_id: str):
        """Turns on a device via Home Assistant service call."""
        try:
            #**THIS IS PLACEHOLDER LOGIC.  IMPLEMENT SERVICE CALLS APPROPRIATELY**
            # This assumes the device is a light.  Adjust service and entity_id as needed.

            entity_id = self._map_device_id_to_entity_id(device_id) #Crucial: Map your device ID to HA Entity ID
            if not entity_id:
                self.logger.warning(f"Cannot turn on device {device_id}: Entity ID not found.")
                return


            await self.hass.services.async_call('light', 'turn_on', {'entity_id': entity_id})
            self.logger.info(f"Turned on device {device_id} (Entity: {entity_id})")
        except Exception as e:
            self.logger.error(f"Error turning on device {device_id}: {e}")


    async def turn_off_device(self, device_id: str):
        """Turns off a device via Home Assistant service call."""
        try:
            #**THIS IS PLACEHOLDER LOGIC.  IMPLEMENT SERVICE CALLS APPROPRIATELY**
            entity_id = self._map_device_id_to_entity_id(device_id)
            if not entity_id:
                self.logger.warning(f"Cannot turn off device {device_id}: Entity ID not found.")
                return
            await self.hass.services.async_call('light', 'turn_off', {'entity_id': entity_id})
            self.logger.info(f"Turned off device {device_id} (Entity: {entity_id})")
        except Exception as e:
            self.logger.error(f"Error turning off device {device_id}: {e}")


    async def send_notification(self, message: str):
        """Sends a notification via Home Assistant."""
        try:
            await self.hass.services.async_call('notify', 'persistent_notification', {'message': message, 'title': 'AICleaner Zone Alert'})
            self.logger.info(f"Sent notification: {message}")
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")

    def _map_device_id_to_entity_id(self, device_id: str) -> str | None:
        """Maps your internal device ID to a Home Assistant entity ID."""
        # Placeholder.  Implement your mapping logic here.  This is CRUCIAL
        # This could involve a configuration file, a database, or a naming convention.
        # Example:  If device IDs are "light_1", "light_2", and HA entity IDs are "light.light_1", "light.light_2"

        if device_id == "light_1":
            return "light.living_room_lamp"
        elif device_id == "light_2":
            return "light.kitchen_light"
        else:
            self.logger.warning(f"No entity ID mapping found for device ID: {device_id}")
            return None



class ZoneEntity(Entity): #HA Entity Class
    """Representation of a Zone within Home Assistant."""

    def __init__(self, hass:HomeAssistant, zone, ha_integration: HomeAssistantIntegration):
        """Initialize the zone entity."""
        self.hass = hass
        self._zone = zone
        self._state = STATE_ON  # Or STATE_OFF, depending on your logic
        self._ha_integration = ha_integration  #Store the HA Integration instance.  CRUCIAL
        self.entity_id = f"{ha_integration.domain}.{zone.name.replace(' ', '_').lower()}"  #Unique entity ID
        self.logger = logger #Use shared logger


        #Crucial: Store a reference to the entity in hass.data for later retrieval.
        if "zone_entities" not in hass.data:
            hass.data["zone_entities"] = {}
        hass.data["zone_entities"][self.entity_id] = self

        self.logger.debug(f"ZoneEntity __init__ called for entity: {self.entity_id}")


    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"aicleaner_zone_{self._zone.id}"

    @property
    def name(self):
        """Return the name of the zone."""
        return self._zone.name

    @property
    def state(self):
        """Return the state of the zone."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the zone."""
        return {
            "device_count": len(self._zone.devices),
            "rules_count": len(self._zone.rules),
            "zone_id": self._zone.id
        }

    async def async_update(self):
        """Update the entity. Only called if should_poll is True."""
        # Placeholder: Implement logic to update the entity's state
        # This could involve checking the status of devices in the zone.

        #Simulated update:
        if len(self._zone.devices) > 0:
            self._state = STATE_ON #Simulate zone being active if there are devices
        else:
            self._state = STATE_OFF

        self.logger.debug(f"async_update called for entity: {self.entity_id}.  New state: {self._state}")


    async def async_run_rules(self):
        """Service call to run rules for this zone."""
        self.logger.info(f"Service 'run_rules' called for zone: {self._zone.name} (Entity: {self.entity_id})")
        await self._ha_integration.hass.async_add_executor_job( #Run in executor to avoid blocking
            asyncio.run, self._ha_integration.turn_off_device("light_1") #Simulated:  Run a dummy action

        )
        #Important:  Trigger state update AFTER running rules.
        await self.async_update_ha_state(force_refresh=True) #force_refresh ensures attributes are also updated


    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        self.logger.debug(f"async_added_to_hass called for entity: {self.entity_id}")
        #You can load initial data or subscribe to events here, if needed.
```

### zones/models.py
```python
from typing import List, Optional
from pydantic import BaseModel, Field

class Device(BaseModel):
    id: str = Field(..., description="Unique identifier for the device.")
    name: str = Field(..., description="User-friendly name of the device.")
    type: str = Field(..., description="Type of device (e.g., light, sensor).")
    manufacturer: Optional[str] = Field(None, description="Manufacturer of the device.")
    model: Optional[str] = Field(None, description="Model number of the device.")
    ip_address: Optional[str] = Field(None, description="IP address of the device.")
    mac_address: Optional[str] = Field(None, description="MAC address of the device.")
    polling_frequency: Optional[str] = Field("normal", description="Polling frequency (normal, reduced, high).")
    location: Optional[str] = Field(None, description="Physical location of the device within the zone.")
    is_active: bool = Field(True, description="Indicates if the device is currently active.")
    power_consumption: Optional[float] = Field(None, description="Current power consumption in watts.")

    def __repr__(self):
        return f"Device(id='{self.id}', name='{self.name}', type='{self.type}')"


class Rule(BaseModel):
    id: str = Field(..., description="Unique identifier for the rule.")
    name: str = Field(..., description="User-friendly name of the rule.")
    description: Optional[str] = Field(None, description="Detailed description of the rule.")
    condition: str = Field(..., description="Condition that triggers the rule (e.g., 'temperature > 25').")
    action: str = Field(..., description="Action to perform when the condition is met (e.g., 'turn_on_fan').")
    priority: int = Field(1, description="Priority of the rule (higher number = higher priority).")
    enabled: bool = Field(True, description="Indicates if the rule is currently enabled.")
    last_executed: Optional[str] = Field(None, description="Timestamp of the last time the rule was executed.")
    error_message: Optional[str] = Field(None, description="Error message if the rule failed to execute.")
    attempts: int = Field(0, description="Number of attempts to execute the rule.")

    def __repr__(self):
        return f"Rule(id='{self.id}', name='{self.name}', condition='{self.condition}', action='{self.action}')"

class Zone(BaseModel):
    id: str = Field(..., description="Unique identifier for the zone.")
    name: str = Field(..., description="User-friendly name of the zone.")
    description: Optional[str] = Field(None, description="Detailed description of the zone.")
    devices: List[Device] = Field([], description="List of devices in the zone.")
    rules: List[Rule] = Field([], description="List of automation rules for the zone.")
    location: Optional[str] = Field(None, description="Physical location of the zone.")
    is_active: bool = Field(True, description="Indicates if the zone is currently active.")
    date_created: Optional[str] = Field(None, description="Timestamp of when the zone was created.")
    last_modified: Optional[str] = Field(None, description="Timestamp of the last time the zone was modified.")
    owner: Optional[str] = Field(None, description="Owner of the zone.")
    notes: Optional[str] = Field(None, description="Additional notes about the zone.")

    def __repr__(self):
        return f"Zone(id='{self.id}', name='{self.name}', devices={len(self.devices)} devices, rules={len(self.rules)} rules)"
```

### zones/schemas.py
```python
from pydantic import BaseModel, validator, Field
from typing import List, Optional

class DeviceSchema(BaseModel):
    id: str = Field(..., description="Unique identifier for the device.")
    name: str = Field(..., description="User-friendly name of the device.")
    type: str = Field(..., description="Type of device (e.g., light, sensor).")
    manufacturer: Optional[str] = Field(None, description="Manufacturer of the device.")
    model: Optional[str] = Field(None, description="Model number of the device.")

class RuleSchema(BaseModel):
    id: str = Field(..., description="Unique identifier for the rule.")
    name: str = Field(..., description="User-friendly name of the rule.")
    description: Optional[str] = Field(None, description="Detailed description of the rule.")
    condition: str = Field(..., description="Condition that triggers the rule (e.g., 'temperature > 25').")
    action: str = Field(..., description="Action to perform when the condition is met (e.g., 'turn_on_fan').")

class ZoneConfigSchema(BaseModel):
    name: str = Field(..., description="User-friendly name of the zone.")
    description: Optional[str] = Field(None, description="Detailed description of the zone.")
    devices: List[DeviceSchema] = Field([], description="List of devices in the zone.")
    rules: List[RuleSchema] = Field([], description="List of automation rules for the zone.")
```

### zones/logger.py
```python
import logging
import sys

def setup_logger(name):
    """Sets up a logger with a specific name."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG) #Set default logging level to DEBUG

    # Create a handler that writes log messages to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG) # Set handler level

    # Create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(handler)

    return logger
```

### zones/utils.py
```python
import asyncio
import functools
import logging
from .logger import setup_logger

logger = setup_logger(__name__)

def retry(exceptions, tries=4, delay=3, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    :param exceptions: The exception(s) to check. May be a tuple or a single exception.
    :param tries: Number of times to try (not retry) before giving up.
    :param delay: initial delay between retries in seconds.
    :param logger: logger to use. If None, print.
    """
    def retry_decorator(f):
        @functools.wraps(f)
        async def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return await f(*args, **kwargs)
                except exceptions as e:
                    msg = f"Retrying in {mdelay} seconds after {type(e).__name__}: {e}"
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    await asyncio.sleep(mdelay)
                    mtries -= 1
                    mdelay *= 2

            return await f(*args, **kwargs) # Last attempt
        return f_retry
    return retry_decorator
```

## COMPLETE TEST SUITE

### zones/tests/test_manager.py
```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
