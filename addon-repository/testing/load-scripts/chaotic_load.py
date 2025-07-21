#!/usr/bin/env python3
"""
AICleaner V3 - Chaotic Load Test
Simulates unpredictable, real-world event patterns with random bursts and quiet periods.
"""

import asyncio
import json
import logging
import random
import time
import websockets
from datetime import datetime, timedelta
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChaoticLoadTester:
    """Simulates chaotic, unpredictable event patterns"""
    
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
            'burst_count': 0,
            'quiet_periods': 0,
            'max_burst_size': 0,
            'max_quiet_duration': 0
        }
        
        # Realistic entity patterns for chaotic simulation
        self.entity_groups = {
            'sensors': [
                'sensor.temperature_{}', 'sensor.humidity_{}', 'sensor.motion_{}',
                'sensor.energy_{}', 'sensor.power_{}', 'sensor.pressure_{}',
                'sensor.air_quality_{}', 'sensor.noise_level_{}'
            ],
            'lights': [
                'light.{}', 'light.{}_main', 'light.{}_accent', 'light.{}_ceiling'
            ],
            'switches': [
                'switch.{}', 'switch.{}_outlet', 'switch.{}_fan'
            ],
            'binary_sensors': [
                'binary_sensor.door_{}', 'binary_sensor.window_{}', 
                'binary_sensor.motion_{}', 'binary_sensor.occupancy_{}'
            ],
            'climate': [
                'climate.{}', 'climate.{}_ac', 'climate.{}_heater'
            ]
        }
        
        self.locations = [
            'living_room', 'bedroom', 'kitchen', 'bathroom', 'office',
            'garage', 'basement', 'attic', 'hallway', 'dining_room',
            'guest_room', 'master_bedroom', 'laundry_room', 'pantry'
        ]
        
        # Chaos patterns
        self.chaos_modes = [
            'normal',      # Regular activity
            'burst',       # Sudden burst of activity
            'quiet',       # Extended quiet period
            'oscillate',   # Rapid on/off changes
            'cascade',     # Sequential device activation
            'storm'        # Complete chaos
        ]
        
        self.current_mode = 'normal'
        self.mode_start_time = datetime.now()
        
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
    
    def select_chaos_mode(self) -> str:
        """Randomly select next chaos mode based on current mode"""
        # Mode transition probabilities
        transitions = {
            'normal': {'normal': 0.7, 'burst': 0.15, 'quiet': 0.1, 'oscillate': 0.03, 'cascade': 0.02},
            'burst': {'normal': 0.5, 'quiet': 0.3, 'storm': 0.1, 'cascade': 0.1},
            'quiet': {'normal': 0.6, 'burst': 0.2, 'oscillate': 0.15, 'cascade': 0.05},
            'oscillate': {'normal': 0.6, 'burst': 0.2, 'quiet': 0.15, 'storm': 0.05},
            'cascade': {'normal': 0.4, 'burst': 0.3, 'oscillate': 0.2, 'quiet': 0.1},
            'storm': {'normal': 0.3, 'quiet': 0.4, 'burst': 0.2, 'cascade': 0.1}
        }
        
        current_probs = transitions.get(self.current_mode, transitions['normal'])
        modes = list(current_probs.keys())
        weights = list(current_probs.values())
        
        return random.choices(modes, weights=weights)[0]
    
    def generate_entity(self, group: str = None) -> str:
        """Generate entity ID from specified group or random"""
        if not group:
            group = random.choice(list(self.entity_groups.keys()))
        
        template = random.choice(self.entity_groups[group])
        location = random.choice(self.locations)
        return template.format(location)
    
    def generate_state_data(self, entity_id: str) -> Dict:
        """Generate realistic state data with chaos factors"""
        domain = entity_id.split('.')[0]
        
        # Add chaos to normal values
        chaos_factor = random.uniform(0.8, 1.2)  # 20% variance
        
        if domain == 'sensor':
            if 'temperature' in entity_id:
                base_temp = 22.0
                value = round(base_temp * chaos_factor, 1)
                return {
                    'state': str(max(15.0, min(30.0, value))),
                    'attributes': {
                        'unit_of_measurement': '°C',
                        'friendly_name': entity_id.replace('_', ' ').title()
                    }
                }
            elif 'humidity' in entity_id:
                base_humidity = 50.0
                value = round(base_humidity * chaos_factor, 1)
                return {
                    'state': str(max(20.0, min(80.0, value))),
                    'attributes': {
                        'unit_of_measurement': '%',
                        'friendly_name': entity_id.replace('_', ' ').title()
                    }
                }
            elif 'power' in entity_id:
                base_power = 100
                value = int(base_power * chaos_factor * random.uniform(0.5, 3.0))
                return {
                    'state': str(max(0, value)),
                    'attributes': {
                        'unit_of_measurement': 'W',
                        'friendly_name': entity_id.replace('_', ' ').title()
                    }
                }
        elif domain == 'light':
            state = random.choice(['on', 'off'])
            attributes = {'friendly_name': entity_id.replace('_', ' ').title()}
            
            if state == 'on':
                # Chaotic brightness changes
                brightness = random.randint(1, 255)
                if self.current_mode == 'oscillate':
                    brightness = random.choice([1, 255])  # Extreme values
                attributes['brightness'] = brightness
                
                # Random color changes in chaos mode
                if self.current_mode == 'storm':
                    attributes['rgb_color'] = [
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255)
                    ]
            
            return {'state': state, 'attributes': attributes}
            
        elif domain == 'switch':
            # More random switching in chaos modes
            if self.current_mode in ['oscillate', 'storm']:
                state = random.choice(['on', 'off'])
            else:
                state = random.choices(['on', 'off'], weights=[0.3, 0.7])[0]
                
            return {
                'state': state,
                'attributes': {'friendly_name': entity_id.replace('_', ' ').title()}
            }
            
        elif domain == 'binary_sensor':
            # Chaotic binary sensor behavior
            if self.current_mode == 'oscillate':
                state = random.choice(['on', 'off'])
            elif self.current_mode == 'storm':
                state = 'on'  # Everything triggered in storm
            else:
                state = random.choices(['on', 'off'], weights=[0.2, 0.8])[0]
                
            return {
                'state': state,
                'attributes': {'friendly_name': entity_id.replace('_', ' ').title()}
            }
        
        # Default fallback
        return {
            'state': random.choice(['on', 'off', 'unknown']),
            'attributes': {'friendly_name': entity_id.replace('_', ' ').title()}
        }
    
    async def send_chaotic_event(self, entity_id: str = None):
        """Send a single chaotic event"""
        try:
            if not entity_id:
                entity_id = self.generate_entity()
            state_data = self.generate_state_data(entity_id)
            
            message = {
                'id': int(time.time() * 1000000) + random.randint(1, 999999),
                'type': 'fire_event',
                'event_type': 'state_changed',
                'event_data': {
                    'entity_id': entity_id,
                    'old_state': {
                        'entity_id': entity_id,
                        'state': 'unknown'
                    },
                    'new_state': {
                        'entity_id': entity_id,
                        'state': state_data['state'],
                        'attributes': state_data['attributes']
                    }
                }
            }
            
            await self.websocket.send(json.dumps(message))
            self.stats['events_sent'] += 1
            
        except Exception as e:
            logger.error(f"Failed to send chaotic event: {e}")
            self.stats['errors'] += 1
    
    async def run_chaos_mode(self):
        """Execute behavior based on current chaos mode"""
        if self.current_mode == 'normal':
            # 1-3 events with random pauses
            event_count = random.randint(1, 3)
            for _ in range(event_count):
                await self.send_chaotic_event()
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
        elif self.current_mode == 'burst':
            # Sudden burst of 5-20 events
            burst_size = random.randint(5, 20)
            logger.info(f"Chaos burst: {burst_size} events")
            
            tasks = []
            for _ in range(burst_size):
                tasks.append(self.send_chaotic_event())
            
            await asyncio.gather(*tasks, return_exceptions=True)
            self.stats['burst_count'] += 1
            self.stats['max_burst_size'] = max(self.stats['max_burst_size'], burst_size)
            
        elif self.current_mode == 'quiet':
            # Extended quiet period (10-60 seconds)
            quiet_duration = random.uniform(10, 60)
            logger.info(f"Quiet period: {quiet_duration:.1f} seconds")
            await asyncio.sleep(quiet_duration)
            self.stats['quiet_periods'] += 1
            self.stats['max_quiet_duration'] = max(self.stats['max_quiet_duration'], quiet_duration)
            
        elif self.current_mode == 'oscillate':
            # Rapid on/off changes for same entities
            entity_id = self.generate_entity()
            for _ in range(random.randint(3, 8)):
                await self.send_chaotic_event(entity_id)
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
        elif self.current_mode == 'cascade':
            # Sequential activation of related entities
            location = random.choice(self.locations)
            cascade_entities = [
                f"light.{location}",
                f"switch.{location}",
                f"sensor.motion_{location}",
                f"binary_sensor.occupancy_{location}"
            ]
            
            logger.info(f"Cascade in {location}")
            for entity in cascade_entities:
                await self.send_chaotic_event(entity)
                await asyncio.sleep(random.uniform(0.2, 1.0))
                
        elif self.current_mode == 'storm':
            # Complete chaos - many random events
            storm_events = random.randint(10, 50)
            logger.info(f"Chaos storm: {storm_events} events")
            
            for _ in range(storm_events):
                await self.send_chaotic_event()
                # Very brief delays in storm mode
                await asyncio.sleep(random.uniform(0.05, 0.2))
    
    async def run_chaotic_load_test(self, duration_minutes: int = 120):
        """Run chaotic load test"""
        logger.info(f"Starting chaotic load test for {duration_minutes} minutes")
        
        if not await self.connect():
            logger.error("Failed to connect to Home Assistant")
            return False
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        end_time = self.stats['start_time'] + timedelta(minutes=duration_minutes)
        
        try:
            while self.running and datetime.now() < end_time:
                # Decide if we should change chaos mode
                mode_duration = (datetime.now() - self.mode_start_time).total_seconds()
                
                # Mode change probability increases with time
                change_probability = min(0.5, mode_duration / 120)  # Up to 50% after 2 minutes
                
                if random.random() < change_probability:
                    new_mode = self.select_chaos_mode()
                    if new_mode != self.current_mode:
                        logger.info(f"Chaos mode change: {self.current_mode} → {new_mode}")
                        self.current_mode = new_mode
                        self.mode_start_time = datetime.now()
                
                # Execute current chaos mode
                await self.run_chaos_mode()
                
                # Random pause between chaos cycles
                pause = random.uniform(1, 10)
                await asyncio.sleep(pause)
                
                # Log progress every 50 events
                if self.stats['events_sent'] % 50 == 0:
                    elapsed = datetime.now() - self.stats['start_time']
                    logger.info(f"Chaotic load running - Mode: {self.current_mode}, "
                               f"Events: {self.stats['events_sent']}, "
                               f"Errors: {self.stats['errors']}, "
                               f"Elapsed: {elapsed}")
                
        except KeyboardInterrupt:
            logger.info("Chaotic load test interrupted by user")
            self.running = False
        except Exception as e:
            logger.error(f"Chaotic load test failed: {e}")
            self.stats['errors'] += 1
        finally:
            if self.websocket:
                await self.websocket.close()
            
            # Report final statistics
            total_time = datetime.now() - self.stats['start_time']
            logger.info("=== Chaotic Load Test Complete ===")
            logger.info(f"Duration: {total_time}")
            logger.info(f"Events Sent: {self.stats['events_sent']}")
            logger.info(f"Errors: {self.stats['errors']}")
            logger.info(f"Bursts: {self.stats['burst_count']}")
            logger.info(f"Quiet Periods: {self.stats['quiet_periods']}")
            logger.info(f"Max Burst Size: {self.stats['max_burst_size']}")
            logger.info(f"Max Quiet Duration: {self.stats['max_quiet_duration']:.1f}s")
            logger.info(f"Average Rate: {self.stats['events_sent'] / max(1, total_time.total_seconds()):.1f} events/sec")
            logger.info(f"Success Rate: {((self.stats['events_sent'] - self.stats['errors']) / max(1, self.stats['events_sent']) * 100):.1f}%")
            
        return True

async def main():
    """Main entry point"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='AICleaner V3 Chaotic Load Test')
    parser.add_argument('--ha-url', default='ws://localhost:8123', help='Home Assistant WebSocket URL')
    parser.add_argument('--ha-token', default=os.getenv('HA_ACCESS_TOKEN'), help='Home Assistant access token')
    parser.add_argument('--duration', type=int, default=120, help='Test duration in minutes')
    
    args = parser.parse_args()
    
    if not args.ha_token:
        logger.error("Home Assistant access token required. Set HA_ACCESS_TOKEN environment variable or use --ha-token")
        return 1
    
    tester = ChaoticLoadTester(args.ha_url, args.ha_token)
    success = await tester.run_chaotic_load_test(args.duration)
    
    return 0 if success else 1

if __name__ == '__main__':
    asyncio.run(main())