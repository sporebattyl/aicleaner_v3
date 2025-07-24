#!/bin/bash

# AICleaner V3 Addon Testing Script
# Automates the testing workflow for local development

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    print_success "Docker is running"
}

# Function to run static code analysis
run_static_analysis() {
    print_status "Running static code analysis..."
    
    if command -v ruff &> /dev/null; then
        print_status "Running ruff linting..."
        ruff check . || print_warning "Ruff found some issues"
        
        print_status "Running ruff formatting..."
        ruff format . || print_warning "Ruff formatting had issues"
    else
        print_warning "ruff not found. Install with: pip install ruff"
    fi
    
    if [ -d "tests" ]; then
        print_status "Running pytest..."
        python3 -m pytest tests/ || print_warning "Some tests failed"
    else
        print_warning "No tests directory found"
    fi
}

# Function to start the test environment
start_environment() {
    print_status "Starting test environment..."
    docker-compose up -d
    
    print_status "Waiting for Home Assistant to start..."
    sleep 10
    
    # Wait for HA to be ready
    for i in {1..30}; do
        if curl -f http://localhost:8123 &> /dev/null; then
            print_success "Home Assistant is ready at http://localhost:8123"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Home Assistant did not start within 5 minutes"
            exit 1
        fi
        sleep 10
    done
}

# Function to stop the test environment
stop_environment() {
    print_status "Stopping test environment..."
    docker-compose down
    print_success "Test environment stopped"
}

# Function to monitor performance
monitor_performance() {
    print_status "Monitoring performance (Press Ctrl+C to stop)..."
    docker stats
}

# Function to show logs
show_logs() {
    local service=${1:-homeassistant}
    print_status "Showing logs for $service..."
    docker-compose logs -f "$service"
}

# Function to clean environment
clean_environment() {
    print_warning "This will remove all test data. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Cleaning test environment..."
        docker-compose down
        sudo rm -rf testing_env/config/* testing_env/data/* testing_env/mosquitto/data/* testing_env/mosquitto/log/*
        print_success "Test environment cleaned"
    fi
}

# Main script logic
case "${1:-help}" in
    "check")
        check_docker
        run_static_analysis
        ;;
    "start")
        check_docker
        start_environment
        ;;
    "stop")
        stop_environment
        ;;
    "restart")
        stop_environment
        start_environment
        ;;
    "logs")
        show_logs "${2:-homeassistant}"
        ;;
    "monitor")
        monitor_performance
        ;;
    "clean")
        clean_environment
        ;;
    "full-test")
        check_docker
        run_static_analysis
        stop_environment 2>/dev/null || true
        start_environment
        print_success "Full test setup complete. Visit http://localhost:8123"
        ;;
    "help"|*)
        echo "AICleaner V3 Testing Script"
        echo "Usage: $0 {check|start|stop|restart|logs|monitor|clean|full-test|help}"
        echo ""
        echo "Commands:"
        echo "  check       - Run static code analysis and checks"
        echo "  start       - Start the test environment"
        echo "  stop        - Stop the test environment"
        echo "  restart     - Restart the test environment"
        echo "  logs [svc]  - Show logs (default: homeassistant, or mosquitto)"
        echo "  monitor     - Monitor container performance"
        echo "  clean       - Clean all test data (destructive)"
        echo "  full-test   - Run complete test setup"
        echo "  help        - Show this help message"
        ;;
esac