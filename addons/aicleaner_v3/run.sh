#!/usr/bin/with-contenv bashio

# Start AI Cleaner v3
bashio::log.info "Starting AI Cleaner v3..."

# Check for required directories
mkdir -p /data/cache
mkdir -p /data/snapshots

# Start a simple HTTP server for static files in the background
bashio::log.info "Starting static file server for Lovelace cards..."
cd /app/www && python3 -m http.server 8099 --bind 0.0.0.0 &
HTTP_PID=$!

# Give the server a moment to start
sleep 2

# Check if the server is running
if kill -0 $HTTP_PID 2>/dev/null; then
    bashio::log.info "HTTP server is running successfully on port 8099"
else
    bashio::log.warning "HTTP server failed to start"
fi

# Start the main AICleaner application
bashio::log.info "Starting main AICleaner application..."
cd /app && python3 aicleaner.py