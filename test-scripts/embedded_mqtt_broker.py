#!/usr/bin/env python3
"""
Embedded MQTT Broker for AICleaner v3 Testing
Lightweight MQTT broker implementation for testing without Docker
"""

import asyncio
import json
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Set, Any, Optional
import socket
import threading
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MQTTMessage:
    """Simple MQTT message representation"""
    def __init__(self, topic: str, payload: bytes, qos: int = 0, retain: bool = False):
        self.topic = topic
        self.payload = payload
        self.qos = qos
        self.retain = retain
        self.timestamp = datetime.now()

class MQTTClient:
    """Simple MQTT client representation"""
    def __init__(self, client_id: str, socket_conn, broker):
        self.client_id = client_id
        self.socket = socket_conn
        self.broker = broker
        self.subscriptions: Set[str] = set()
        self.connected = True
        self.last_seen = time.time()
    
    def matches_subscription(self, topic: str) -> bool:
        """Check if topic matches any subscriptions (simplified)"""
        for subscription in self.subscriptions:
            if self._topic_matches(topic, subscription):
                return True
        return False
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Simple topic matching with wildcards"""
        if pattern == topic:
            return True
        if pattern.endswith('#'):
            prefix = pattern[:-1]
            return topic.startswith(prefix)
        if '+' in pattern:
            pattern_parts = pattern.split('/')
            topic_parts = topic.split('/')
            if len(pattern_parts) != len(topic_parts):
                return False
            for p, t in zip(pattern_parts, topic_parts):
                if p != '+' and p != t:
                    return False
            return True
        return False

class EmbeddedMQTTBroker:
    """Lightweight MQTT broker for testing"""
    
    def __init__(self, host='127.0.0.1', port=1883):
        self.host = host
        self.port = port
        self.clients: Dict[str, MQTTClient] = {}
        self.retained_messages: Dict[str, MQTTMessage] = {}
        self.running = False
        self.server_socket = None
        self.stats = {
            'clients_connected': 0,
            'messages_published': 0,
            'messages_delivered': 0,
            'subscriptions': 0,
            'start_time': datetime.now()
        }
    
    def start(self):
        """Start the MQTT broker"""
        logger.info(f"Starting embedded MQTT broker on {self.host}:{self.port}")
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logger.info(f"✅ MQTT broker listening on {self.host}:{self.port}")
            
            # Start accepting connections
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    logger.info(f"New connection from {address}")
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        logger.error(f"Error accepting connection: {e}")
        
        except Exception as e:
            logger.error(f"Failed to start MQTT broker: {e}")
            return False
        
        finally:
            if self.server_socket:
                self.server_socket.close()
        
        return True
    
    def handle_client(self, client_socket, address):
        """Handle individual client connection"""
        client_id = f"client_{address[0]}_{address[1]}_{int(time.time())}"
        
        try:
            # Simple MQTT-like protocol simulation
            # In a real implementation, we'd parse actual MQTT packets
            
            # Send connection acknowledgment
            client_socket.send(b"CONNACK\n")
            
            client = MQTTClient(client_id, client_socket, self)
            self.clients[client_id] = client
            self.stats['clients_connected'] += 1
            
            logger.info(f"Client {client_id} connected")
            
            # Handle client messages
            buffer = ""
            while self.running and client.connected:
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    buffer += data
                    lines = buffer.split('\n')
                    buffer = lines[-1]  # Keep incomplete line
                    
                    for line in lines[:-1]:
                        if line.strip():
                            self.process_client_message(client, line.strip())
                
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error handling client {client_id}: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Client connection error: {e}")
        
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
            try:
                client_socket.close()
            except:
                pass
            logger.info(f"Client {client_id} disconnected")
    
    def process_client_message(self, client: MQTTClient, message: str):
        """Process messages from clients (simplified protocol)"""
        try:
            # Simple protocol: COMMAND|data
            if '|' not in message:
                return
            
            command, data = message.split('|', 1)
            
            if command == 'SUBSCRIBE':
                topic = data.strip()
                client.subscriptions.add(topic)
                self.stats['subscriptions'] += 1
                logger.info(f"Client {client.client_id} subscribed to: {topic}")
                
                # Send retained messages for this subscription
                self.send_retained_messages(client, topic)
            
            elif command == 'PUBLISH':
                parts = data.split('|', 2)
                if len(parts) >= 2:
                    topic = parts[0]
                    payload = parts[1].encode('utf-8')
                    retain = len(parts) > 2 and parts[2].lower() == 'true'
                    
                    self.publish_message(topic, payload, retain=retain)
            
            elif command == 'PING':
                client.last_seen = time.time()
                client.socket.send(b"PONG\n")
        
        except Exception as e:
            logger.error(f"Error processing client message: {e}")
    
    def publish_message(self, topic: str, payload: bytes, qos: int = 0, retain: bool = False):
        """Publish message to all matching subscribers"""
        message = MQTTMessage(topic, payload, qos, retain)
        self.stats['messages_published'] += 1
        
        # Store retained message
        if retain:
            self.retained_messages[topic] = message
            logger.info(f"📌 Retained message: {topic}")
        
        # Deliver to subscribers
        delivered_count = 0
        for client in list(self.clients.values()):
            if client.matches_subscription(topic):
                try:
                    # Send message to client
                    msg = f"MESSAGE|{topic}|{payload.decode('utf-8', errors='replace')}\n"
                    client.socket.send(msg.encode('utf-8'))
                    delivered_count += 1
                except Exception as e:
                    logger.error(f"Failed to deliver message to {client.client_id}: {e}")
        
        self.stats['messages_delivered'] += delivered_count
        logger.info(f"📨 Published to {topic}: {payload.decode('utf-8', errors='replace')[:100]}...")
        logger.info(f"   Delivered to {delivered_count} subscribers")
    
    def send_retained_messages(self, client: MQTTClient, subscription: str):
        """Send retained messages matching subscription"""
        for topic, message in self.retained_messages.items():
            if client._topic_matches(topic, subscription):
                try:
                    msg = f"MESSAGE|{topic}|{message.payload.decode('utf-8', errors='replace')}\n"
                    client.socket.send(msg.encode('utf-8'))
                    logger.info(f"📌 Sent retained message to {client.client_id}: {topic}")
                except Exception as e:
                    logger.error(f"Failed to send retained message: {e}")
    
    def stop(self):
        """Stop the broker"""
        logger.info("Stopping MQTT broker...")
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # Close all client connections
        for client in list(self.clients.values()):
            try:
                client.socket.close()
            except:
                pass
        self.clients.clear()
    
    def print_stats(self):
        """Print broker statistics"""
        uptime = datetime.now() - self.stats['start_time']
        
        print("\n" + "=" * 50)
        print("📊 EMBEDDED MQTT BROKER STATS")
        print("=" * 50)
        print(f"⏱️ Uptime: {uptime}")
        print(f"👥 Active Clients: {len(self.clients)}")
        print(f"📊 Total Connections: {self.stats['clients_connected']}")
        print(f"📨 Messages Published: {self.stats['messages_published']}")
        print(f"📦 Messages Delivered: {self.stats['messages_delivered']}")
        print(f"📡 Active Subscriptions: {self.stats['subscriptions']}")
        print(f"📌 Retained Messages: {len(self.retained_messages)}")
        print("=" * 50)
        
        if self.retained_messages:
            print("📌 Retained Messages:")
            for topic, msg in self.retained_messages.items():
                print(f"   {topic}: {msg.payload.decode('utf-8', errors='replace')[:50]}...")

def signal_handler(signum, frame, broker):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    broker.stop()
    sys.exit(0)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Embedded MQTT Broker for Testing")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=1883, help="Port to bind to")
    parser.add_argument("--stats-interval", type=int, default=30, help="Stats interval in seconds")
    
    args = parser.parse_args()
    
    # Create broker
    broker = EmbeddedMQTTBroker(args.host, args.port)
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, broker))
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, broker))
    
    try:
        # Start stats printing in background
        def print_periodic_stats():
            while broker.running:
                time.sleep(args.stats_interval)
                if broker.running:
                    broker.print_stats()
        
        stats_thread = threading.Thread(target=print_periodic_stats, daemon=True)
        stats_thread.start()
        
        # Start broker
        broker.start()
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        broker.stop()

if __name__ == '__main__':
    main()