
📋 AICleaner V3 Installation Guide for Real Home Assistant
==========================================================

🔧 INSTALLATION STEPS:

1. **Copy Addon to HA Server:**
   ```bash
   # On your HA server, navigate to:
   cd /usr/share/hassio/addons/local/
   
   # Create directory and copy files:
   sudo mkdir -p aicleaner_v3
   sudo cp -r /path/to/your/addons/aicleaner_v3/* aicleaner_v3/
   ```

2. **Set Permissions:**
   ```bash
   sudo chown -R root:root aicleaner_v3/
   sudo chmod +x aicleaner_v3/run.sh
   ```

3. **Restart Home Assistant:**
   ```bash
   # Via UI: Configuration > Server Controls > Restart
   # Or via command:
   ha core restart
   ```

4. **Install Addon:**
   - Go to Supervisor > Add-on Store
   - Scroll to "Local add-ons" section
   - Find "AI Cleaner v3"
   - Click Install

5. **Configure Addon:**
   - Add your Gemini API key
   - Configure camera entities
   - Set up zones and rules
   - Click "Save" and "Start"

🚨 REQUIREMENTS:
- Home Assistant OS or Supervised installation
- Local add-ons support enabled
- Gemini API key required
- Camera entities must exist

📱 TESTING CHECKLIST:
□ Addon appears in local add-ons
□ Installation completes without errors
□ Configuration interface loads
□ Addon starts successfully
□ Web interface accessible (if ingress enabled)
□ Logs show proper initialization
