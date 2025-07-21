#!/usr/bin/env python3
"""
AICleaner V3 - Baseline Load Test
Simulates normal, quiet home automation activity for 24-hour soak testing.
"""

import asyncio
import json
import logging
import random
import time
import websockets
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BaselineLoadTester:
    """Simulates normal home automation activity"""
    
    def __init__(self, ha_url: str = "ws://localhost:8123", ha_token: str = None):
        self.ha_url = ha_url.replace("http://", "ws://").replace("https://", "wss://")
        self.ha_token = ha_token
        self.websocket = None
        self.running = False
        self.stats = {
            'events_sent': 0,
            'responses_received': 0,
            'errors': 0,
            'start_time': None,
            'last_activity': None
        }
        
        # Realistic device states for simulation
        self.device_states = {
            'sensor.temperature_living_room': {'value': 21.5, 'unit': '°C', 'drift': 0.1},
            'sensor.humidity_living_room': {'value': 45.0, 'unit': '%', 'drift': 0.5},
            'sensor.motion_living_room': {'value': 'off', 'unit': None, 'drift': 0.0},
            'light.living_room_main': {'value': 'off', 'brightness': 0, 'drift': 0.0},
            'switch.coffee_maker': {'value': 'off', 'unit': None, 'drift': 0.0},
            'sensor.door_front': {'value': 'closed', 'unit': None, 'drift': 0.0},
            'sensor.window_living_room': {'value': 'closed', 'unit': None, 'drift': 0.0}
        }
        
    async def connect(self):
        """Connect to Home Assistant WebSocket API"""
        try:
            headers = {}
            if self.ha_token:
                headers['Authorization'] = f'Bearer {self.ha_token}'
                
            self.websocket = await websockets.connect(
                f"{self.ha_url}/api/websocket",
                extra_headers=headers
            )
            
            # Authenticate
            auth_msg = await self.websocket.recv()
            auth_data = json.loads(auth_msg)
            
            if auth_data['type'] == 'auth_required':
                await self.websocket.send(json.dumps({
                    'type': 'auth',
                    'access_token': self.ha_token
                }))
                
                auth_result = await self.websocket.recv()
                result_data = json.loads(auth_result)
                
                if result_data['type'] == 'auth_ok':
                    logger.info("Connected to Home Assistant WebSocket API")
                    return True
                else:
                    logger.error(f"Authentication failed: {result_data}")
                    return False
                    
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def send_state_change(self, entity_id: str, new_state: str, attributes: Dict = None):
        """Send a state change event"""
        try:
            message = {
                'id': int(time.time() * 1000),
                'type': 'fire_event',
                'event_type': 'state_changed',
                'event_data': {
                    'entity_id': entity_id,
                    'old_state': {
                        'entity_id': entity_id,
                        'state': self.device_states.get(entity_id, {}).get('value', 'unknown')
                    },
                    'new_state': {
                        'entity_id': entity_id,
                        'state': new_state,
                        'attributes': attributes or {}
                    }
                }
            }
            
            await self.websocket.send(json.dumps(message))
            self.stats['events_sent'] += 1
            self.stats['last_activity'] = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to send state change: {e}")
            self.stats['errors'] += 1
    
    async def simulate_temperature_drift(self):
        """Simulate gradual temperature changes throughout the day"""
        temp_sensors = [k for k in self.device_states.keys() if 'temperature' in k]
        
        for sensor in temp_sensors:
            current_temp = self.device_states[sensor]['value']
            # Small random drift ±0.1°C
            drift = random.uniform(-0.1, 0.1)
            new_temp = round(current_temp + drift, 1)
            
            # Keep temperature in realistic range (18-26°C)
            new_temp = max(18.0, min(26.0, new_temp))
            
            self.device_states[sensor]['value'] = new_temp
            
            await self.send_state_change(sensor, str(new_temp), {
                'unit_of_measurement': '°C',
                'friendly_name': 'Living Room Temperature'
            })
    
    async def simulate_humidity_drift(self):
        """Simulate gradual humidity changes"""
        humidity_sensors = [k for k in self.device_states.keys() if 'humidity' in k]
        
        for sensor in humidity_sensors:
            current_humidity = self.device_states[sensor]['value']
            # Small random drift ±0.5%
            drift = random.uniform(-0.5, 0.5)
            new_humidity = round(current_humidity + drift, 1)
            
            # Keep humidity in realistic range (30-70%)
            new_humidity = max(30.0, min(70.0, new_humidity))
            
            self.device_states[sensor]['value'] = new_humidity
            
            await self.send_state_change(sensor, str(new_humidity), {
                'unit_of_measurement': '%',
                'friendly_name': 'Living Room Humidity'
            })
    
    async def simulate_motion_activity(self):
        """Simulate realistic motion detection patterns"""
        motion_sensors = [k for k in self.device_states.keys() if 'motion' in k]
        
        # Motion is more likely during certain hours
        current_hour = datetime.now().hour
        motion_probability = 0.1  # Base 10% chance per minute
        
        # Higher activity during wake hours
        if 7 <= current_hour <= 23:
            motion_probability = 0.3
        elif 23 <= current_hour or current_hour <= 6:
            motion_probability = 0.05  # Lower activity during sleep hours
        
        for sensor in motion_sensors:
            if random.random() < motion_probability:
                # Motion detected
                await self.send_state_change(sensor, 'on', {
                    'friendly_name': 'Living Room Motion'
                })
                self.device_states[sensor]['value'] = 'on'
                
                # Motion clears after 30-120 seconds
                await asyncio.sleep(random.uniform(30, 120))
                
                await self.send_state_change(sensor, 'off', {
                    'friendly_name': 'Living Room Motion'
                })
                self.device_states[sensor]['value'] = 'off'
    
    async def simulate_light_usage(self):
        """Simulate realistic light switching patterns"""
        lights = [k for k in self.device_states.keys() if 'light.' in k]
        current_hour = datetime.now().hour
        
        # Light usage patterns based on time of day
        if 6 <= current_hour <= 8 or 18 <= current_hour <= 23:
            light_probability = 0.2  # Higher during morning/evening
        else:
            light_probability = 0.05
        
        for light in lights:
            if random.random() < light_probability:
                current_state = self.device_states[light]['value']
                
                if current_state == 'off':
                    # Turn on light
                    brightness = random.randint(50, 255)
                    await self.send_state_change(light, 'on', {
                        'brightness': brightness,
                        'friendly_name': 'Living Room Light'
                    })
                    self.device_states[light]['value'] = 'on'
                    self.device_states[light]['brightness'] = brightness
                    
                elif random.random() < 0.3:  # 30% chance to turn off when on
                    await self.send_state_change(light, 'off', {
                        'brightness': 0,
                        'friendly_name': 'Living Room Light'
                    })
                    self.device_states[light]['value'] = 'off'
                    self.device_states[light]['brightness'] = 0
    
    async def simulate_appliance_usage(self):
        """Simulate appliance on/off patterns"""
        appliances = [k for k in self.device_states.keys() if 'switch.' in k]
        
        for appliance in appliances:
            # Very low probability for random appliance activity
            if random.random() < 0.02:  # 2% chance per minute
                current_state = self.device_states[appliance]['value']
                new_state = 'on' if current_state == 'off' else 'off'
                
                await self.send_state_change(appliance, new_state, {
                    'friendly_name': appliance.replace('switch.', '').replace('_', ' ').title()
                })
                self.device_states[appliance]['value'] = new_state
    
    async def run_baseline_load(self, duration_hours: int = 24):
        """Run baseline load test for specified duration"""
        logger.info(f"Starting baseline load test for {duration_hours} hours")
        
        if not await self.connect():
            logger.error("Failed to connect to Home Assistant")
            return False
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        end_time = self.stats['start_time'] + timedelta(hours=duration_hours)
        
        try:
            while self.running and datetime.now() < end_time:
                # Run all simulation tasks
                await asyncio.gather(
                    self.simulate_temperature_drift(),
                    self.simulate_humidity_drift(),
                    self.simulate_motion_activity(),
                    self.simulate_light_usage(),
                    self.simulate_appliance_usage()
                )
                
                # Log progress every 5 minutes
                if self.stats['events_sent'] % 25 == 0:
                    elapsed = datetime.now() - self.stats['start_time']
                    logger.info(f"Baseline load running - Events: {self.stats['events_sent']}, "
                               f"Errors: {self.stats['errors']}, Elapsed: {elapsed}")
                
                # Wait 60 seconds between simulation cycles (1 minute intervals)
                await asyncio.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("Baseline load test interrupted by user")
            self.running = False
        except Exception as e:
            logger.error(f"Baseline load test failed: {e}")
            self.stats['errors'] += 1
        finally:
            if self.websocket:
                await self.websocket.close()
            
            # Report final statistics
            total_time = datetime.now() - self.stats['start_time']
            logger.info("=== Baseline Load Test Complete ===")
            logger.info(f"Duration: {total_time}")
            logger.info(f"Events Sent: {self.stats['events_sent']}")
            logger.info(f"Errors: {self.stats['errors']}")
            logger.info(f"Success Rate: {((self.stats['events_sent'] - self.stats['errors']) / max(1, self.stats['events_sent']) * 100):.1f}%")
            
        return True

async def main():
    """Main entry point"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='AICleaner V3 Baseline Load Test')
    parser.add_argument('--ha-url', default='ws://localhost:8123', help='Home Assistant WebSocket URL')
    parser.add_argument('--ha-token', default=os.getenv('HA_ACCESS_TOKEN'), help='Home Assistant access token')
    parser.add_argument('--duration', type=int, default=24, help='Test duration in hours')
    
    args = parser.parse_args()
    
    if not args.ha_token:
        logger.error("Home Assistant access token required. Set HA_ACCESS_TOKEN environment variable or use --ha-token")
        return 1
    
    tester = BaselineLoadTester(args.ha_url, args.ha_token)
    success = await tester.run_baseline_load(args.duration)
    
    return 0 if success else 1

if __name__ == '__main__':
    asyncio.run(main())