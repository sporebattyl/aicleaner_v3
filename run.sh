#!/usr/bin/with-contenv bashio

bashio::log.info "Starting AICleaner v2.1+ ..."

# Start a simple HTTP server for static files in the background
bashio::log.info "Starting static file server for Lovelace cards..."
bashio::log.info "Checking /app/www directory..."
ls -la /app/www/ || bashio::log.error "Failed to list /app/www directory"

bashio::log.info "Starting HTTP server on port 8099..."
cd /app/www && python3 -m http.server 8099 --bind 0.0.0.0 > /tmp/http_server.log 2>&1 &
HTTP_PID=$!
bashio::log.info "HTTP server started with PID: $HTTP_PID"

# Give the server a moment to start
sleep 2

# Check if the server is running
if kill -0 $HTTP_PID 2>/dev/null; then
    bashio::log.info "HTTP server is running successfully"
else
    bashio::log.error "HTTP server failed to start"
    cat /tmp/http_server.log
fi

# Start the main AICleaner application
bashio::log.info "Starting main AICleaner application..."
cd /app && python3 aicleaner.py
