# 🎭 AICleaner v3 Multi-Tier System Deployment Guide

## 🚀 Quick Start

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Download Models (Optional - for local processing):**
   ```bash
   mkdir -p /data/models
   # Download LLaVA GGUF models to /data/models/
   ```

3. **Start the System:**
   ```bash
   python3 start_aicleaner.py
   ```

## 🎯 System Architecture

### **Tier 1: Privacy-Preserving Hybrid (Recommended)**
- **Performance**: 5-15 seconds
- **Privacy**: Local preprocessing + cloud inference
- **Use Case**: Balanced privacy and speed

### **Tier 2: Full Local Processing**
- **Performance**: 1-5 minutes
- **Privacy**: Complete local processing
- **Use Case**: Maximum privacy, offline operation

### **Tier 3: Pure Cloud**
- **Performance**: 5-10 seconds  
- **Privacy**: Minimal (direct API calls)
- **Use Case**: Maximum speed

## 🔧 Configuration

Edit `addons/aicleaner_v3/config.yaml` to customize:
- Privacy levels (paranoid/balanced/speed)
- AMD optimization settings
- Cloud provider preferences
- Home Assistant integration

## 🏠 Home Assistant Integration

Add to your `configuration.yaml`:
```yaml
aicleaner_v3:
  enabled: true
  config_path: "/path/to/aicleaner_v3/config.yaml"
```

## 📊 Performance Optimization

### For AMD 8845HS + Radeon 780M:
1. Enable AMD optimization in config
2. Install ROCm drivers for GPU acceleration
3. Download optimized LLaVA models
4. Configure GPU layer allocation

### Privacy Pipeline Optimization:
1. Choose appropriate privacy level
2. Configure preprocessing timeout
3. Enable hardware acceleration

## 🔍 Monitoring

Check logs at `/data/logs/aicleaner.log` for:
- Performance metrics
- Error diagnostics
- Optimization recommendations

## 🆘 Troubleshooting

**Common Issues:**
1. **Missing dependencies**: Run `pip install -r requirements.txt`
2. **GPU acceleration**: Install ROCm drivers for AMD 780M
3. **Model loading**: Ensure models are in `/data/models/`
4. **Performance**: Check GPU layer allocation in config

**Support:**
- Check integration test results
- Review log files for errors
- Validate configuration syntax
