# AICleaner V3 Manual Installation Guide

## Issue Identified
The AICleaner addon appears in the sidebar but **is not properly installed** in the Home Assistant supervisor system. The configuration dropdowns are missing because the addon doesn't exist in the supervisor.

## Evidence
- Error message: "Error fetching addon info: Addon aicleaner_v3 does not exist"
- Config.yaml has correct entity selector syntax
- Entities exist but addon backend is not running

## Manual Installation Steps

### Step 1: Access Home Assistant Supervisor
1. Navigate to: `http://192.168.88.125:8123`
2. Login with: `drewcifer / Minds63qq!`
3. Go to **Settings** → **Add-ons**

### Step 2: Add Repository
1. Click **Add-on Store** (bottom right)
2. Click the **⋮** menu (top right)
3. Select **Repositories**
4. Click **Add Repository**
5. Enter: `https://github.com/sporebattyl/aicleaner_v3`
6. Click **Add**

### Step 3: Install AICleaner V3
1. Go back to **Add-on Store**
2. Refresh the page or wait for new addons to load
3. Look for **AICleaner V3** in the addon list
4. Click on **AICleaner V3**
5. Click **Install**
6. Wait for installation to complete (may take several minutes)

### Step 4: Configure with Dropdowns
1. After installation, click **Configuration** tab
2. You should now see:
   - **Default Camera Entity**: Dropdown selector (not text field)
   - **Default To-Do List Entity**: Dropdown selector (not text field)
3. Select:
   - Camera: `camera.rowan_room_fluent`
   - Todo List: `todo.rowan_room_cleaning_to_do`
4. Click **Save**

### Step 5: Start the Addon
1. Go to **Info** tab
2. Toggle **Start on boot**: ON
3. Click **Start**
4. Check **Logs** tab for any errors

## Expected Result
- Dropdown entity selectors instead of text fields
- Addon properly running with status indicators
- Configuration saved and functional

## Current Config.yaml Status
✅ **CORRECT** - The config.yaml already has proper entity selector syntax:
```yaml
schema:
  default_camera:
    name: "Default Camera Entity"
    description: "Select the default camera entity for cleaning area monitoring"
    selector:
      entity:
        domain: camera
  default_todo_list:
    name: "Default To-Do List Entity"
    description: "Select the to-do list entity for automated task management"
    selector:
      entity:
        domain: todo
```

## Troubleshooting
If AICleaner doesn't appear in addon store after adding repository:
1. Wait 5 minutes for repository refresh
2. Refresh browser page
3. Check Settings → Add-ons → Repositories to confirm repository was added
4. Look in **Community Add-ons** section

The dropdowns will work once the addon is properly installed through the supervisor system.