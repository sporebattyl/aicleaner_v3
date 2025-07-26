# AICleaner V3 Home Assistant Custom Repository

## 🎯 Custom Addon Repository URL

**Repository URL for Home Assistant:**
```
https://github.com/sporebattyl/aicleaner_v3
```

## 📦 Installation Instructions

### Step 1: Add Custom Repository to Home Assistant

1. **Open Home Assistant**
   - Navigate to http://192.168.88.125:8123
   - Login with credentials: drewcifer / Minds63qq!

2. **Navigate to Add-ons**
   - Go to **Settings** → **Add-ons**
   - Click on **Add-on Store**

3. **Add Custom Repository**
   - Click the **⋮** (three dots) menu in the top-right corner
   - Select **Repositories**
   - Click **Add Repository**
   - Enter: `https://github.com/sporebattyl/aicleaner_v3`
   - Click **Add**

### Step 2: Install AICleaner V3

1. **Find the Addon**
   - After adding the repository, scroll down to find the new repository section
   - Look for **"AICleaner v3"** addon

2. **Install**
   - Click on **AICleaner v3**
   - Click **Install**
   - Wait for installation to complete

3. **Configure**
   - Go to **Configuration** tab
   - Add your Gemini API key: `AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro`
   - Configure zones and camera entities
   - Click **Save**

4. **Start**
   - Go to **Info** tab
   - Click **Start**
   - Monitor logs for successful startup

## 🔧 Repository Structure

The custom repository includes:
- `addon-repository/repository.json` - Repository metadata
- `addon-repository/aicleaner_v3/` - Complete addon files
  - `config.json` - HA addon configuration
  - `Dockerfile` - Container build instructions  
  - `requirements.txt` - Python dependencies
  - `run.sh` - Startup script
  - `src/` - Application source code
  - `core/` - Core functionality
  - `mqtt/` - MQTT integration

## ✅ Verification

After installation, verify:
- [ ] Addon appears in Supervisor → AICleaner v3
- [ ] Configuration interface loads
- [ ] Startup logs show no errors
- [ ] Web interface accessible (if ingress enabled)
- [ ] Integration with HA entities works

## 🚨 Troubleshooting

**If addon doesn't appear:**
1. Check repository URL was added correctly
2. Try refreshing the add-on store page
3. Check GitHub repository is publicly accessible

**If installation fails:**
1. Check addon logs in Supervisor
2. Verify all required files are present
3. Check Docker has sufficient resources

**For configuration issues:**
1. Verify Gemini API key is valid
2. Ensure camera entities exist in HA
3. Check network connectivity for API calls