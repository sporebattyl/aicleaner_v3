# AICleaner V3

AI-powered cleaning task management with intelligent zone monitoring and automatic dashboard integration.

## Installation

1. Add this repository to your Home Assistant Add-on Store
2. Find "AICleaner V3" in the add-on store
3. Click Install
4. Configure the add-on (see Configuration section)
5. Click Start

## Configuration

### Basic Configuration

**Default Camera**: Enter the entity ID of your camera (e.g., `camera.rowan_room_fluent`)
- Find your camera entity IDs in Home Assistant under Settings → Devices & Services → Entities

**Default Todo List**: Enter the entity ID of your todo list (e.g., `todo.rowan_room_cleaning_to_do`)
- Create todo lists in Home Assistant and find their entity IDs in the same location

### Advanced Options

- **Debug Mode**: Enable detailed logging for troubleshooting
- **Enable Zones**: Advanced zone-based monitoring (requires additional configuration)
- **Auto Dashboard**: Automatically create Home Assistant dashboard cards

## Usage

1. Configure your camera and todo list entities
2. Start the add-on
3. The addon will monitor your specified camera for cleaning tasks
4. Tasks will be automatically added to your specified todo list
5. View progress through the AICleaner interface in your Home Assistant sidebar

## Support

For issues and feature requests, visit: https://github.com/sporebattyl/aicleaner_v3