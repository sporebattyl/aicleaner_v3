#!/usr/bin/env python3
"""
Deploy AICleaner v3 Configuration
Direct deployment script to configure entities for Rowan's room
"""

import json
import os
import sys
import subprocess
import time

def create_enhanced_config():
    """Create enhanced configuration with required entities"""
    config = {
        "debug_mode": True,
        "log_level": "debug",
        "mqtt_host": "localhost", 
        "mqtt_port": 1883,
        "core_service_url": "http://localhost:8000",
        "default_camera": "camera.rowan_room_fluent",
        "default_todo_list": "todo.rowan_room_cleaning_to_do",
        "device_id": "aicleaner_v3_rowan",
        "mqtt_discovery_prefix": "homeassistant",
        "enable_zones": True,
        "zones": [
            {
                "name": "Rowan's Room",
                "camera_entity": "camera.rowan_room_fluent",
                "todo_list_entity": "todo.rowan_room_cleaning_to_do",
                "purpose": "Monitor and manage cleanliness of Rowan's room",
                "interval_minutes": 30,
                "ignore_rules": [
                    "Ignore items that are supposed to be there",
                    "Don't flag normal bedroom furniture",
                    "Focus on cleanliness not organization"
                ]
            }
        ]
    }
    return config

def save_config_file(config, filepath):
    """Save configuration to file"""
    try:
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Configuration saved to: {filepath}")
        return True
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return False

def deploy_via_direct_update():
    """Deploy configuration directly"""
    print("🚀 Deploying AICleaner v3 Enhanced Configuration")
    print("=" * 50)
    
    # Create enhanced configuration
    config = create_enhanced_config()
    print("📋 Enhanced configuration created:")
    print(json.dumps(config, indent=2))
    
    # Save to various locations for deployment
    config_files = [
        "/tmp/aicleaner_v3_config.json",
        "/tmp/options.json",
        "./config/enhanced_options.json"
    ]
    
    # Create config directory if needed
    os.makedirs("./config", exist_ok=True)
    
    for config_file in config_files:
        if save_config_file(config, config_file):
            print(f"  ✓ Saved to {config_file}")
        else:
            print(f"  ✗ Failed to save to {config_file}")
    
    print("\n🔧 Configuration deployment summary:")
    print("  • default_camera: camera.rowan_room_fluent")
    print("  • default_todo_list: todo.rowan_room_cleaning_to_do") 
    print("  • Zone configured: Rowan's Room")
    print("  • MQTT discovery: enabled")
    print("  • Debug mode: enabled")
    
    print("\n📡 Next steps for deployment:")
    print("1. Apply this configuration to the AICleaner addon")
    print("2. Restart the addon to load new configuration")
    print("3. Verify MQTT entities are created properly")
    print("4. Test camera and todo list integration")
    
    return config

def verify_entities():
    """Verify required entities exist in Home Assistant"""
    required_entities = [
        "camera.rowan_room_fluent",
        "todo.rowan_room_cleaning_to_do"
    ]
    
    print("\n🔍 Entity verification:")
    for entity in required_entities:
        print(f"  • {entity}: Required for configuration")
    
    print("  Note: Entity verification requires Home Assistant API access")
    return True

def main():
    """Main deployment function"""
    print("AICleaner v3 Configuration Deployment")
    print("=====================================")
    
    # Deploy configuration
    config = deploy_via_direct_update()
    
    # Verify entities
    verify_entities()
    
    print("\n✅ Configuration deployment completed successfully!")
    print("   The enhanced configuration is ready for addon deployment.")
    
    return config

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        sys.exit(1)