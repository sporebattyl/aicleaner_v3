# 🔧 AICleaner v3 Troubleshooting Guide

Common issues and solutions for AICleaner v3 with Ollama integration.

## 🚨 Quick Diagnostics

### Health Check Commands
```bash
# Check all services
docker-compose ps

# Check container health
docker inspect aicleaner-app-basic --format='{{.State.Health.Status}}'
docker inspect aicleaner-ollama-basic --format='{{.State.Health.Status}}'

# Test connectivity
curl http://localhost:8099/health
curl http://localhost:11434/api/tags
```

### Log Analysis
```bash
# View all logs
docker-compose logs

# Follow specific service logs
docker-compose logs -f aicleaner
docker-compose logs -f ollama

# Search for errors
docker-compose logs | grep -i error
docker-compose logs | grep -i failed
```

## 🐳 Docker Issues

### Container Won't Start

**Symptoms:**
- Container exits immediately
- "Exited (1)" status
- Port binding errors

**Solutions:**

1. **Check port conflicts:**
```bash
# Check if ports are in use
netstat -tulpn | grep :8099
netstat -tulpn | grep :11434

# Kill conflicting processes
sudo lsof -ti:8099 | xargs kill -9
sudo lsof -ti:11434 | xargs kill -9
```

2. **Fix permission issues:**
```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/
chmod -R 755 data/
chmod +x scripts/*.sh
```

3. **Check Docker resources:**
```bash
# Increase Docker memory (Docker Desktop)
# Settings → Resources → Memory: 4GB+

# Check available space
df -h
docker system df
```

### Container Keeps Restarting

**Symptoms:**
- Container status shows "Restarting"
- Frequent restarts in logs

**Solutions:**

1. **Check resource limits:**
```bash
# Monitor resource usage
docker stats

# Reduce resource limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2G  # Reduce from 4G
      cpus: '1.0'  # Reduce from 2.0
```

2. **Check health check failures:**
```bash
# Disable health checks temporarily
# Comment out healthcheck section in docker-compose.yml
```

3. **Review startup logs:**
```bash
# Check initialization errors
docker-compose logs aicleaner | head -50
```

## 🤖 Ollama Issues

### Models Not Downloading

**Symptoms:**
- Empty model list
- "No models available" errors
- Slow or failed downloads

**Solutions:**

1. **Manual model download:**
```bash
# Download models manually
docker exec aicleaner-ollama-basic ollama pull llava:13b
docker exec aicleaner-ollama-basic ollama pull mistral:7b
docker exec aicleaner-ollama-basic ollama pull llama2:7b

# Check download progress
docker exec aicleaner-ollama-basic ollama list
```

2. **Check network connectivity:**
```bash
# Test internet connection from container
docker exec aicleaner-ollama-basic curl -I https://ollama.ai

# Check DNS resolution
docker exec aicleaner-ollama-basic nslookup ollama.ai
```

3. **Increase timeout:**
```bash
# Set longer timeout in environment
OLLAMA_DOWNLOAD_TIMEOUT=600  # 10 minutes
```

4. **Use smaller models:**
```yaml
# In config.yaml, use smaller models
preferred_models:
  vision: "llava:7b"  # Instead of llava:13b
  text: "mistral:7b"
```

### Ollama API Not Responding

**Symptoms:**
- Connection refused errors
- Timeout errors
- 404 responses

**Solutions:**

1. **Check Ollama service:**
```bash
# Check if Ollama is running
docker exec aicleaner-ollama-basic ps aux | grep ollama

# Restart Ollama service
docker-compose restart ollama
```

2. **Verify network connectivity:**
```bash
# Test from AICleaner container
docker exec aicleaner-app-basic curl http://ollama:11434/api/tags

# Check network configuration
docker network ls
docker network inspect aicleaner_aicleaner_network
```

3. **Check firewall/security:**
```bash
# Disable firewall temporarily (Linux)
sudo ufw disable

# Check SELinux (RHEL/CentOS)
getenforce
sudo setenforce 0
```

### Model Inference Errors

**Symptoms:**
- "Model not found" errors
- Slow inference
- Memory errors

**Solutions:**

1. **Verify model availability:**
```bash
# List available models
docker exec aicleaner-ollama-basic ollama list

# Test model inference
docker exec aicleaner-ollama-basic ollama run mistral:7b "Hello"
```

2. **Increase memory limits:**
```yaml
# In docker-compose.yml
deploy:
  resources:
    limits:
      memory: 6G  # Increase for larger models
```

3. **Use quantized models:**
```bash
# Pull quantized versions
docker exec aicleaner-ollama-basic ollama pull mistral:7b-q4_0
docker exec aicleaner-ollama-basic ollama pull llava:13b-q4_0
```

## 🏠 Home Assistant Integration Issues

### Connection Refused

**Symptoms:**
- "Cannot connect to Home Assistant" errors
- Authentication failures
- Timeout errors

**Solutions:**

1. **Verify HA token:**
```bash
# Test token manually
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://your-ha-ip:8123/api/states

# Check token in .env file
grep HA_TOKEN .env
```

2. **Check network connectivity:**
```bash
# Test from AICleaner container
docker exec aicleaner-app-basic curl http://homeassistant:8123

# Check if HA is accessible
ping your-home-assistant-ip
telnet your-home-assistant-ip 8123
```

3. **Update HA URL:**
```bash
# In .env file, try different formats
HA_URL=http://192.168.1.100:8123  # IP address
HA_URL=http://homeassistant.local:8123  # mDNS
HA_URL=http://homeassistant:8123  # Docker network
```

### Camera Entity Not Found

**Symptoms:**
- "Camera entity not available" errors
- No image analysis
- Entity state errors

**Solutions:**

1. **Verify camera entities:**
```bash
# List all camera entities
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://your-ha-ip:8123/api/states | grep camera
```

2. **Check entity names in config:**
```yaml
# In config.yaml, verify exact entity names
zones:
  - name: "Living Room"
    camera_entity: "camera.living_room"  # Must match exactly
```

3. **Test camera access:**
```bash
# Get camera snapshot URL
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://your-ha-ip:8123/api/camera_proxy/camera.living_room
```

## 📊 Performance Issues

### Slow Analysis

**Symptoms:**
- Long response times
- Timeout errors
- High CPU/memory usage

**Solutions:**

1. **Optimize model settings:**
```yaml
# In config.yaml
local_llm:
  performance_tuning:
    timeout_seconds: 180  # Increase timeout
    max_concurrent_requests: 1  # Reduce concurrency
    quantization_level: 8  # Use higher quantization
```

2. **Use faster models:**
```yaml
preferred_models:
  vision: "llava:7b"  # Smaller, faster model
  text: "mistral:7b"
```

3. **Increase resources:**
```yaml
# In docker-compose.yml
deploy:
  resources:
    limits:
      memory: 8G
      cpus: '4.0'
```

### High Memory Usage

**Symptoms:**
- Out of memory errors
- Container killed by OOM killer
- System slowdown

**Solutions:**

1. **Monitor memory usage:**
```bash
# Check container memory usage
docker stats

# Check system memory
free -h
```

2. **Reduce model size:**
```bash
# Use smaller quantized models
docker exec aicleaner-ollama-basic ollama pull mistral:7b-q8_0
```

3. **Limit concurrent operations:**
```yaml
# In config.yaml
performance:
  max_concurrent_requests: 1
  batch_processing: false
```

## 🔒 Security Issues

### Permission Denied

**Symptoms:**
- File access errors
- Directory creation failures
- Script execution errors

**Solutions:**

1. **Fix file permissions:**
```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/
chmod -R 755 data/

# Fix script permissions
chmod +x scripts/*.sh
```

2. **Check SELinux/AppArmor:**
```bash
# Check SELinux status
getenforce

# Check AppArmor status
sudo apparmor_status
```

3. **Run with proper user:**
```yaml
# In docker-compose.yml
user: "${UID}:${GID}"
```

## 🌐 Network Issues

### DNS Resolution Problems

**Symptoms:**
- "Name resolution failed" errors
- Cannot reach external services
- Container communication issues

**Solutions:**

1. **Check DNS configuration:**
```bash
# Test DNS from container
docker exec aicleaner-app-basic nslookup google.com

# Check Docker DNS settings
docker exec aicleaner-app-basic cat /etc/resolv.conf
```

2. **Use custom DNS:**
```yaml
# In docker-compose.yml
dns:
  - 8.8.8.8
  - 1.1.1.1
```

3. **Check network configuration:**
```bash
# Inspect Docker network
docker network inspect aicleaner_aicleaner_network
```

## 🔄 Recovery Procedures

### Complete Reset

```bash
# Stop all services
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Clean up Docker resources
docker system prune -f

# Restart from scratch
docker-compose up -d
```

### Backup and Restore

```bash
# Backup configuration and data
tar -czf aicleaner-backup.tar.gz data/ config.yaml .env

# Restore from backup
tar -xzf aicleaner-backup.tar.gz
```

### Update to Latest Version

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d
```

## 📞 Getting Help

### Collect Diagnostic Information

```bash
# Create diagnostic report
./scripts/collect-diagnostics.sh > diagnostics.txt
```

### Support Channels

- **GitHub Issues**: Report bugs with diagnostic info
- **Community Forum**: Ask questions and share solutions
- **Documentation**: Check latest guides and references

### Before Asking for Help

1. ✅ Check this troubleshooting guide
2. ✅ Review logs for error messages
3. ✅ Test with basic configuration
4. ✅ Verify system requirements
5. ✅ Include diagnostic information in your report

---

**💡 Pro Tip**: Most issues are resolved by checking logs, verifying configuration, and ensuring proper resource allocation. Start with the basics before diving into complex solutions!
