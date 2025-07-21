#!/usr/bin/env python3
"""
AICleaner V3 - Storm Load Test
Simulates high-volume event activity to test addon responsiveness under pressure.
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

class StormLoadTester:
    """Simulates high-volume event storm conditions"""
    
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
            'peak_events_per_second': 0,
            'current_events_per_second': 0
        }
        
        # Large number of simulated entities for storm testing
        self.entity_templates = [
            'sensor.temperature_{}',
            'sensor.humidity_{}',
            'sensor.motion_{}',
            'light.{}',
            'switch.{}',
            'binary_sensor.door_{}',
            'binary_sensor.window_{}',
            'sensor.energy_{}',
            'sensor.power_{}',
            'climate.{}',
            'cover.blinds_{}',
            'fan.{}',
            'media_player.{}',
            'camera.{}',
            'alarm_control_panel.{}'
        ]
        
        self.room_names = [
            'living_room', 'bedroom', 'kitchen', 'bathroom', 'hallway',
            'dining_room', 'office', 'basement', 'garage', 'attic',
            'guest_room', 'master_bedroom', 'family_room', 'study',
            'laundry_room', 'mudroom', 'pantry', 'closet', 'porch'
        ]
        
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
    
    def generate_random_entity(self) -> str:
        """Generate a random entity ID"""
        template = random.choice(self.entity_templates)
        room = random.choice(self.room_names)
        return template.format(room)
    
    def generate_random_state_data(self, entity_id: str) -> Dict:
        """Generate realistic state data for entity"""
        domain = entity_id.split('.')[0]
        
        if domain == 'sensor':
            if 'temperature' in entity_id:
                return {
                    'state': str(round(random.uniform(18.0, 26.0), 1)),
                    'attributes': {
                        'unit_of_measurement': '°C',
                        'friendly_name': entity_id.replace('_', ' ').title()
                    }
                }
            elif 'humidity' in entity_id:
                return {
                    'state': str(round(random.uniform(30.0, 70.0), 1)),
                    'attributes': {
                        'unit_of_measurement': '%',
                        'friendly_name': entity_id.replace('_', ' ').title()
                    }
                }
            elif 'energy' in entity_id:
                return {
                    'state': str(round(random.uniform(0.5, 5.0), 2)),
                    'attributes': {
                        'unit_of_measurement': 'kWh',
                        'friendly_name': entity_id.replace('_', ' ').title()
                    }
                }
            elif 'power' in entity_id:
                return {
                    'state': str(random.randint(50, 2000)),
                    'attributes': {
                        'unit_of_measurement': 'W',
                        'friendly_name': entity_id.replace('_', ' ').title()
                    }
                }
        elif domain in ['light', 'switch', 'fan']:
            state = random.choice(['on', 'off'])
            attributes = {'friendly_name': entity_id.replace('_', ' ').title()}
            
            if domain == 'light' and state == 'on':
                attributes['brightness'] = random.randint(1, 255)
                attributes['color_temp'] = random.randint(153, 500)
            
            return {'state': state, 'attributes': attributes}
            
        elif domain == 'binary_sensor':
            return {
                'state': random.choice(['on', 'off']),
                'attributes': {'friendly_name': entity_id.replace('_', ' ').title()}
            }
        elif domain == 'climate':
            return {
                'state': random.choice(['heat', 'cool', 'auto', 'off']),
                'attributes': {
                    'temperature': random.randint(18, 26),
                    'target_temp_high': 24,
                    'target_temp_low': 20,
                    'friendly_name': entity_id.replace('_', ' ').title()
                }
            }
        elif domain == 'cover':
            return {
                'state': random.choice(['open', 'closed', 'opening', 'closing']),
                'attributes': {
                    'current_position': random.randint(0, 100),
                    'friendly_name': entity_id.replace('_', ' ').title()
                }
            }
        
        # Default fallback
        return {
            'state': random.choice(['on', 'off', 'unknown']),
            'attributes': {'friendly_name': entity_id.replace('_', ' ').title()}
        }
    
    async def send_storm_event(self):
        """Send a single storm event"""
        try:
            entity_id = self.generate_random_entity()
            state_data = self.generate_random_state_data(entity_id)
            
            message = {
                'id': int(time.time() * 1000000) + random.randint(1, 999),  # Unique ID
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
            logger.error(f"Failed to send storm event: {e}")
            self.stats['errors'] += 1
    
    async def run_storm_burst(self, events_per_second: int, duration_seconds: int):
        """Run a burst of storm events at specified rate"""
        logger.info(f"Starting storm burst: {events_per_second} events/sec for {duration_seconds} seconds")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        events_in_burst = 0
        
        while time.time() < end_time and self.running:
            burst_start = time.time()
            
            # Send events for this second
            tasks = []
            for _ in range(events_per_second):
                tasks.append(self.send_storm_event())
            
            await asyncio.gather(*tasks, return_exceptions=True)
            events_in_burst += events_per_second
            
            # Calculate sleep time to maintain rate
            elapsed = time.time() - burst_start
            sleep_time = max(0, 1.0 - elapsed)
            
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            
            # Update current rate statistics
            actual_elapsed = time.time() - burst_start
            self.stats['current_events_per_second'] = events_per_second / max(actual_elapsed, 0.1)
            
            if self.stats['current_events_per_second'] > self.stats['peak_events_per_second']:
                self.stats['peak_events_per_second'] = self.stats['current_events_per_second']
        
        logger.info(f"Storm burst complete: {events_in_burst} events sent")
    
    async def run_storm_load_test(self, duration_minutes: int = 60):
        """Run complete storm load test with varying intensity"""
        logger.info(f"Starting storm load test for {duration_minutes} minutes")
        
        if not await self.connect():
            logger.error("Failed to connect to Home Assistant")
            return False
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        try:
            # Storm test phases with increasing intensity
            phases = [
                {'name': 'Ramp Up', 'rate': 10, 'duration': 300},      # 5 min at 10 events/sec
                {'name': 'Medium Load', 'rate': 25, 'duration': 600},   # 10 min at 25 events/sec
                {'name': 'High Load', 'rate': 50, 'duration': 900},     # 15 min at 50 events/sec
                {'name': 'Peak Storm', 'rate': 100, 'duration': 600},   # 10 min at 100 events/sec
                {'name': 'Extreme Peak', 'rate': 200, 'duration': 300}, # 5 min at 200 events/sec
                {'name': 'Cool Down', 'rate': 25, 'duration': 900}      # 15 min at 25 events/sec
            ]
            
            # Adjust phases based on requested duration
            total_planned = sum(p['duration'] for p in phases)
            if duration_minutes * 60 != total_planned:
                scale_factor = (duration_minutes * 60) / total_planned
                for phase in phases:
                    phase['duration'] = int(phase['duration'] * scale_factor)
            
            for phase in phases:
                if not self.running:
                    break
                    
                logger.info(f"Starting phase: {phase['name']} "
                           f"({phase['rate']} events/sec for {phase['duration']} seconds)")
                
                await self.run_storm_burst(phase['rate'], phase['duration'])
                
                # Brief pause between phases
                await asyncio.sleep(5)
                
                # Log intermediate statistics
                elapsed = datetime.now() - self.stats['start_time']
                logger.info(f"Phase '{phase['name']}' complete - "
                           f"Total events: {self.stats['events_sent']}, "
                           f"Errors: {self.stats['errors']}, "
                           f"Elapsed: {elapsed}")
                
        except KeyboardInterrupt:
            logger.info("Storm load test interrupted by user")
            self.running = False
        except Exception as e:
            logger.error(f"Storm load test failed: {e}")
            self.stats['errors'] += 1
        finally:
            if self.websocket:
                await self.websocket.close()
            
            # Report final statistics
            total_time = datetime.now() - self.stats['start_time']
            logger.info("=== Storm Load Test Complete ===")
            logger.info(f"Duration: {total_time}")
            logger.info(f"Events Sent: {self.stats['events_sent']}")
            logger.info(f"Errors: {self.stats['errors']}")
            logger.info(f"Peak Rate: {self.stats['peak_events_per_second']:.1f} events/sec")
            logger.info(f"Average Rate: {self.stats['events_sent'] / max(1, total_time.total_seconds()):.1f} events/sec")
            logger.info(f"Success Rate: {((self.stats['events_sent'] - self.stats['errors']) / max(1, self.stats['events_sent']) * 100):.1f}%")
            
        return True

async def main():
    """Main entry point"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='AICleaner V3 Storm Load Test')
    parser.add_argument('--ha-url', default='ws://localhost:8123', help='Home Assistant WebSocket URL')
    parser.add_argument('--ha-token', default=os.getenv('HA_ACCESS_TOKEN'), help='Home Assistant access token')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in minutes')
    
    args = parser.parse_args()
    
    if not args.ha_token:
        logger.error("Home Assistant access token required. Set HA_ACCESS_TOKEN environment variable or use --ha-token")
        return 1
    
    tester = StormLoadTester(args.ha_url, args.ha_token)
    success = await tester.run_storm_load_test(args.duration)
    
    return 0 if success else 1

if __name__ == '__main__':
    asyncio.run(main())