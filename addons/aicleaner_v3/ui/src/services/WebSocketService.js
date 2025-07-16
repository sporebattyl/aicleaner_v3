
"""
WebSocket Service for Real-time Updates
"""

class WebSocketService {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.messageHandlers = [];
        this.statusHandlers = [];
    }

    connect(messageHandler) {
        if (messageHandler) {
            this.messageHandlers.push(messageHandler);
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = () => {
                console.log('WebSocket connected');
                this.connected = true;
                this.reconnectAttempts = 0;
                this.notifyStatusChange('connected');
            };

            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.messageHandlers.forEach(handler => handler(data));
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            this.socket.onclose = () => {
                console.log('WebSocket disconnected');
                this.connected = false;
                this.notifyStatusChange('disconnected');
                this.attemptReconnect();
            };

            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.notifyStatusChange('error');
            };

        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.notifyStatusChange('error');
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
        this.connected = false;
        this.messageHandlers = [];
        this.statusHandlers = [];
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.pow(2, this.reconnectAttempts) * 1000; // Exponential backoff
            
            console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
            
            setTimeout(() => {
                if (!this.connected) {
                    this.connect();
                }
            }, delay);
        } else {
            console.error('Max reconnection attempts reached');
            this.notifyStatusChange('failed');
        }
    }

    onStatusChange(handler) {
        this.statusHandlers.push(handler);
    }

    notifyStatusChange(status) {
        this.statusHandlers.forEach(handler => handler(status));
    }

    send(message) {
        if (this.socket && this.connected) {
            this.socket.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, cannot send message');
        }
    }
}

export const WebSocketService = new WebSocketService();
