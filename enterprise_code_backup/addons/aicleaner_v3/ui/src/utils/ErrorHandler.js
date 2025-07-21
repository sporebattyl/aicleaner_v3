/**
 * Comprehensive Error Handling and Logging System
 * Provides centralized error management, user-friendly notifications, and detailed logging
 */

class ErrorHandler {
    constructor() {
        this.errorCallbacks = [];
        this.logLevel = this.getLogLevel();
        this.setupGlobalErrorHandling();
    }

    // Log levels
    static LOG_LEVELS = {
        ERROR: 0,
        WARN: 1,
        INFO: 2,
        DEBUG: 3
    };

    getLogLevel() {
        const level = process.env.NODE_ENV === 'development' ? 'DEBUG' : 'INFO';
        return ErrorHandler.LOG_LEVELS[level] || ErrorHandler.LOG_LEVELS.INFO;
    }

    setupGlobalErrorHandling() {
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError(event.reason, 'Unhandled Promise Rejection', {
                promise: event.promise,
                reason: event.reason
            });
            event.preventDefault();
        });

        // Handle JavaScript errors
        window.addEventListener('error', (event) => {
            this.handleError(event.error, 'JavaScript Error', {
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                message: event.message
            });
        });

        // Handle React error boundaries
        window.addEventListener('react-error', (event) => {
            this.handleError(event.detail.error, 'React Error', {
                componentStack: event.detail.componentStack,
                errorBoundary: event.detail.errorBoundary
            });
        });
    }

    /**
     * Handle and categorize errors
     */
    handleError(error, context = 'Unknown', metadata = {}) {
        const errorInfo = this.categorizeError(error, context, metadata);
        
        // Log the error
        this.logError(errorInfo);
        
        // Notify error callbacks
        this.notifyErrorCallbacks(errorInfo);
        
        // Send to monitoring service if available
        this.sendToMonitoring(errorInfo);
        
        return errorInfo;
    }

    /**
     * Categorize errors for better handling
     */
    categorizeError(error, context, metadata) {
        const errorInfo = {
            id: this.generateErrorId(),
            timestamp: new Date().toISOString(),
            context,
            metadata,
            userAgent: navigator.userAgent,
            url: window.location.href,
            userId: this.getCurrentUserId()
        };

        if (error instanceof TypeError) {
            errorInfo.category = 'TYPE_ERROR';
            errorInfo.severity = 'medium';
            errorInfo.userMessage = 'A technical error occurred. Please try again.';
        } else if (error instanceof ReferenceError) {
            errorInfo.category = 'REFERENCE_ERROR';
            errorInfo.severity = 'high';
            errorInfo.userMessage = 'A system error occurred. Please refresh the page.';
        } else if (error?.response) {
            // API/Network errors
            errorInfo.category = 'API_ERROR';
            errorInfo.severity = error.response.status >= 500 ? 'high' : 'medium';
            errorInfo.statusCode = error.response.status;
            errorInfo.userMessage = this.getAPIErrorMessage(error.response.status);
        } else if (error?.name === 'NetworkError' || error?.message?.includes('fetch')) {
            errorInfo.category = 'NETWORK_ERROR';
            errorInfo.severity = 'medium';
            errorInfo.userMessage = 'Network connection issue. Please check your internet connection.';
        } else if (error?.name === 'ValidationError') {
            errorInfo.category = 'VALIDATION_ERROR';
            errorInfo.severity = 'low';
            errorInfo.userMessage = 'Please check your input and try again.';
        } else {
            errorInfo.category = 'UNKNOWN_ERROR';
            errorInfo.severity = 'medium';
            errorInfo.userMessage = 'An unexpected error occurred. Please try again.';
        }

        errorInfo.message = error?.message || String(error);
        errorInfo.stack = error?.stack;
        errorInfo.name = error?.name;

        return errorInfo;
    }

    /**
     * Get user-friendly API error messages
     */
    getAPIErrorMessage(statusCode) {
        const messages = {
            400: 'Invalid request. Please check your input.',
            401: 'Authentication required. Please log in.',
            403: 'Access denied. You do not have permission for this action.',
            404: 'The requested resource was not found.',
            429: 'Too many requests. Please wait and try again.',
            500: 'Server error. Our team has been notified.',
            502: 'Service temporarily unavailable. Please try again later.',
            503: 'Service maintenance in progress. Please try again later.'
        };

        return messages[statusCode] || 'An error occurred while communicating with the server.';
    }

    /**
     * Log errors with appropriate level
     */
    logError(errorInfo) {
        const logData = {
            level: this.getSeverityLogLevel(errorInfo.severity),
            timestamp: errorInfo.timestamp,
            id: errorInfo.id,
            category: errorInfo.category,
            message: errorInfo.message,
            context: errorInfo.context,
            metadata: errorInfo.metadata
        };

        if (this.shouldLog(logData.level)) {
            const logMethod = logData.level === 'error' ? console.error : 
                            logData.level === 'warn' ? console.warn : console.log;
            
            logMethod('AICleaner Error:', logData);
            
            // Store in local storage for debugging
            this.storeErrorLog(errorInfo);
        }
    }

    getSeverityLogLevel(severity) {
        const mapping = {
            low: 'info',
            medium: 'warn',
            high: 'error'
        };
        return mapping[severity] || 'error';
    }

    shouldLog(level) {
        const levelNumbers = {
            error: 0,
            warn: 1,
            info: 2,
            debug: 3
        };
        return levelNumbers[level] <= this.logLevel;
    }

    /**
     * Store error logs locally for debugging
     */
    storeErrorLog(errorInfo) {
        try {
            const logs = JSON.parse(localStorage.getItem('aicleaner_error_logs') || '[]');
            logs.push(errorInfo);
            
            // Keep only last 50 errors
            if (logs.length > 50) {
                logs.splice(0, logs.length - 50);
            }
            
            localStorage.setItem('aicleaner_error_logs', JSON.stringify(logs));
        } catch (e) {
            console.warn('Failed to store error log:', e);
        }
    }

    /**
     * Notify registered error callbacks
     */
    notifyErrorCallbacks(errorInfo) {
        this.errorCallbacks.forEach(callback => {
            try {
                callback(errorInfo);
            } catch (e) {
                console.error('Error in error callback:', e);
            }
        });
    }

    /**
     * Send error to monitoring service
     */
    async sendToMonitoring(errorInfo) {
        if (errorInfo.severity === 'high' || errorInfo.category === 'API_ERROR') {
            try {
                await fetch('/api/errors', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(errorInfo)
                });
            } catch (e) {
                console.warn('Failed to send error to monitoring:', e);
            }
        }
    }

    /**
     * Register error callback
     */
    onError(callback) {
        this.errorCallbacks.push(callback);
        return () => {
            const index = this.errorCallbacks.indexOf(callback);
            if (index > -1) {
                this.errorCallbacks.splice(index, 1);
            }
        };
    }

    /**
     * Utility methods
     */
    generateErrorId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    getCurrentUserId() {
        try {
            const user = JSON.parse(localStorage.getItem('aicleaner_user') || '{}');
            return user.id || 'anonymous';
        } catch {
            return 'anonymous';
        }
    }

    /**
     * Public API methods
     */
    
    // Wrap async functions with error handling
    wrapAsync(fn, context = 'Async Function') {
        return async (...args) => {
            try {
                return await fn(...args);
            } catch (error) {
                throw this.handleError(error, context, { args });
            }
        };
    }

    // Wrap promises with error handling
    wrapPromise(promise, context = 'Promise') {
        return promise.catch(error => {
            this.handleError(error, context);
            throw error;
        });
    }

    // Clear error logs
    clearErrorLogs() {
        localStorage.removeItem('aicleaner_error_logs');
    }

    // Get error logs for debugging
    getErrorLogs() {
        try {
            return JSON.parse(localStorage.getItem('aicleaner_error_logs') || '[]');
        } catch {
            return [];
        }
    }

    // Format error for display
    formatErrorForUser(error) {
        if (typeof error === 'string') return error;
        if (error?.userMessage) return error.userMessage;
        if (error?.message) return error.message;
        return 'An unexpected error occurred';
    }

    // Validate error severity
    isHighSeverity(error) {
        return error?.severity === 'high' || 
               error?.category === 'API_ERROR' ||
               error?.statusCode >= 500;
    }
}

// Create singleton instance
const errorHandler = new ErrorHandler();

// React hook for error handling
export const useErrorHandler = () => {
    const [errors, setErrors] = React.useState([]);

    React.useEffect(() => {
        const unsubscribe = errorHandler.onError((errorInfo) => {
            setErrors(prev => [...prev, errorInfo].slice(-5)); // Keep last 5 errors
        });

        return unsubscribe;
    }, []);

    const clearErrors = () => setErrors([]);
    
    const handleError = (error, context) => errorHandler.handleError(error, context);

    return {
        errors,
        clearErrors,
        handleError,
        formatError: errorHandler.formatErrorForUser.bind(errorHandler),
        isHighSeverity: errorHandler.isHighSeverity.bind(errorHandler)
    };
};

// Error Boundary Component
export class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        this.setState({ error, errorInfo });
        
        // Send error to error handler
        errorHandler.handleError(error, 'React Error Boundary', {
            componentStack: errorInfo.componentStack,
            errorBoundary: this.constructor.name
        });

        // Dispatch custom event for global handling
        window.dispatchEvent(new CustomEvent('react-error', {
            detail: { error, componentStack: errorInfo.componentStack, errorBoundary: this.constructor.name }
        }));
    }

    render() {
        if (this.state.hasError) {
            return this.props.fallback || (
                <div className="alert alert-danger" role="alert">
                    <h4>Something went wrong</h4>
                    <p>We apologize for the inconvenience. The application has encountered an error.</p>
                    <button 
                        className="btn btn-primary"
                        onClick={() => window.location.reload()}
                    >
                        Refresh Page
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}

export default errorHandler;