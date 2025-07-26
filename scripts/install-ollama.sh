#!/bin/bash
# Automatic Ollama installation script for AICleaner v3
# Supports multiple platforms and installation methods

set -e

# Configuration
OLLAMA_VERSION="latest"
INSTALL_DIR="/usr/local/bin"
SERVICE_USER="ollama"
DATA_DIR="/var/lib/ollama"
LOG_FILE="/var/log/ollama-install.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Detect operating system and architecture
detect_platform() {
    local os arch
    
    os=$(uname -s | tr '[:upper:]' '[:lower:]')
    arch=$(uname -m)
    
    case "$arch" in
        x86_64|amd64)
            arch="amd64"
            ;;
        aarch64|arm64)
            arch="arm64"
            ;;
        armv7l)
            arch="arm"
            ;;
        *)
            log_error "Unsupported architecture: $arch"
            return 1
            ;;
    esac
    
    case "$os" in
        linux)
            PLATFORM="linux-$arch"
            ;;
        darwin)
            PLATFORM="darwin-$arch"
            ;;
        *)
            log_error "Unsupported operating system: $os"
            return 1
            ;;
    esac
    
    log_info "Detected platform: $PLATFORM"
    return 0
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check if running as root or with sudo
    if [[ $EUID -ne 0 ]] && ! command -v sudo >/dev/null 2>&1; then
        log_error "This script requires root privileges or sudo access"
        return 1
    fi
    
    # Check available disk space (minimum 10GB)
    local available_space
    available_space=$(df / | tail -1 | awk '{print $4}')
    if [[ $available_space -lt 10485760 ]]; then  # 10GB in KB
        log_warning "Low disk space detected. Ollama models require significant storage."
    fi
    
    # Check available memory (minimum 4GB recommended)
    local available_memory
    available_memory=$(free -m | grep '^Mem:' | awk '{print $2}')
    if [[ $available_memory -lt 4096 ]]; then
        log_warning "Limited memory detected ($available_memory MB). 4GB+ recommended for optimal performance."
    fi
    
    log_success "System requirements check completed"
    return 0
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    
    if command -v apt-get >/dev/null 2>&1; then
        # Debian/Ubuntu
        sudo apt-get update
        sudo apt-get install -y curl wget ca-certificates gnupg lsb-release
    elif command -v yum >/dev/null 2>&1; then
        # RHEL/CentOS/Fedora
        sudo yum install -y curl wget ca-certificates gnupg
    elif command -v apk >/dev/null 2>&1; then
        # Alpine
        sudo apk add --no-cache curl wget ca-certificates gnupg
    elif command -v brew >/dev/null 2>&1; then
        # macOS with Homebrew
        brew install curl wget
    else
        log_warning "Package manager not detected. Please ensure curl and wget are installed."
    fi
    
    log_success "Dependencies installed"
}

# Download and install Ollama
install_ollama() {
    log_info "Downloading and installing Ollama..."
    
    # Create installation directory
    sudo mkdir -p "$INSTALL_DIR"
    
    # Download Ollama binary
    local download_url="https://ollama.ai/download/ollama-$PLATFORM"
    local temp_file="/tmp/ollama"
    
    log_info "Downloading from: $download_url"
    
    if curl -fsSL "$download_url" -o "$temp_file"; then
        log_success "Ollama downloaded successfully"
    else
        log_error "Failed to download Ollama"
        return 1
    fi
    
    # Install binary
    sudo mv "$temp_file" "$INSTALL_DIR/ollama"
    sudo chmod +x "$INSTALL_DIR/ollama"
    
    # Create symlink if not in PATH
    if ! command -v ollama >/dev/null 2>&1; then
        sudo ln -sf "$INSTALL_DIR/ollama" /usr/local/bin/ollama
    fi
    
    log_success "Ollama installed to $INSTALL_DIR/ollama"
}

# Create service user
create_service_user() {
    log_info "Creating service user..."
    
    if ! id "$SERVICE_USER" >/dev/null 2>&1; then
        sudo useradd -r -s /bin/false -d "$DATA_DIR" "$SERVICE_USER"
        log_success "Created user: $SERVICE_USER"
    else
        log_info "User $SERVICE_USER already exists"
    fi
    
    # Create data directory
    sudo mkdir -p "$DATA_DIR"
    sudo chown "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR"
    sudo chmod 755 "$DATA_DIR"
    
    log_success "Data directory created: $DATA_DIR"
}

# Create systemd service
create_systemd_service() {
    log_info "Creating systemd service..."
    
    local service_file="/etc/systemd/system/ollama.service"
    
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=$INSTALL_DIR/ollama serve
User=$SERVICE_USER
Group=$SERVICE_USER
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=$DATA_DIR/models"

[Install]
WantedBy=default.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable ollama
    
    log_success "Systemd service created and enabled"
}

# Start Ollama service
start_ollama() {
    log_info "Starting Ollama service..."
    
    sudo systemctl start ollama
    
    # Wait for service to be ready
    local retries=0
    local max_retries=30
    
    while [[ $retries -lt $max_retries ]]; do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            log_success "Ollama service is running and ready"
            return 0
        fi
        
        retries=$((retries + 1))
        log_info "Waiting for Ollama to start... ($retries/$max_retries)"
        sleep 2
    done
    
    log_error "Ollama service failed to start within expected time"
    return 1
}

# Verify installation
verify_installation() {
    log_info "Verifying Ollama installation..."
    
    # Check if binary exists and is executable
    if [[ ! -x "$INSTALL_DIR/ollama" ]]; then
        log_error "Ollama binary not found or not executable"
        return 1
    fi
    
    # Check version
    local version
    version=$("$INSTALL_DIR/ollama" --version 2>/dev/null || echo "unknown")
    log_info "Ollama version: $version"
    
    # Check if service is running
    if systemctl is-active --quiet ollama; then
        log_success "Ollama service is active"
    else
        log_error "Ollama service is not running"
        return 1
    fi
    
    # Test API endpoint
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        log_success "Ollama API is responding"
    else
        log_error "Ollama API is not responding"
        return 1
    fi
    
    log_success "Ollama installation verified successfully"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f /tmp/ollama
}

# Main installation function
main() {
    log_info "Starting Ollama installation for AICleaner v3..."
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Check if Ollama is already installed
    if command -v ollama >/dev/null 2>&1 && systemctl is-active --quiet ollama 2>/dev/null; then
        log_info "Ollama is already installed and running"
        if verify_installation; then
            log_success "Existing Ollama installation is working correctly"
            exit 0
        fi
    fi
    
    # Run installation steps
    detect_platform || exit 1
    check_requirements || exit 1
    install_dependencies || exit 1
    install_ollama || exit 1
    create_service_user || exit 1
    create_systemd_service || exit 1
    start_ollama || exit 1
    verify_installation || exit 1
    
    log_success "Ollama installation completed successfully!"
    log_info "You can now run 'ollama pull <model>' to download models"
    log_info "Service status: systemctl status ollama"
    log_info "Service logs: journalctl -u ollama -f"
}

# Handle command line arguments
case "${1:-install}" in
    "install")
        main
        ;;
    "verify")
        verify_installation
        ;;
    "uninstall")
        log_info "Uninstalling Ollama..."
        sudo systemctl stop ollama 2>/dev/null || true
        sudo systemctl disable ollama 2>/dev/null || true
        sudo rm -f /etc/systemd/system/ollama.service
        sudo rm -f "$INSTALL_DIR/ollama"
        sudo rm -f /usr/local/bin/ollama
        sudo userdel "$SERVICE_USER" 2>/dev/null || true
        sudo rm -rf "$DATA_DIR"
        log_success "Ollama uninstalled"
        ;;
    *)
        echo "Usage: $0 {install|verify|uninstall}"
        echo "  install   - Install Ollama (default)"
        echo "  verify    - Verify existing installation"
        echo "  uninstall - Remove Ollama completely"
        exit 1
        ;;
esac
