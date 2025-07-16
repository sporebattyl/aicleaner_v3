import React from 'react';
import { Toast, ToastContainer, Alert, Button } from 'react-bootstrap';
import { useErrorHandler } from '../utils/ErrorHandler';

export const ErrorNotification = () => {
    const { errors, clearErrors, formatError, isHighSeverity } = useErrorHandler();
    const [dismissedErrors, setDismissedErrors] = React.useState(new Set());

    const dismissError = (errorId) => {
        setDismissedErrors(prev => new Set([...prev, errorId]));
    };

    const clearAllErrors = () => {
        clearErrors();
        setDismissedErrors(new Set());
    };

    const visibleErrors = errors.filter(error => !dismissedErrors.has(error.id));

    if (visibleErrors.length === 0) return null;

    return (
        <ToastContainer position="top-end" className="p-3">
            {visibleErrors.map(error => (
                <Toast
                    key={error.id}
                    onClose={() => dismissError(error.id)}
                    delay={isHighSeverity(error) ? 10000 : 5000}
                    autohide={!isHighSeverity(error)}
                    className={`text-white ${isHighSeverity(error) ? 'bg-danger' : 'bg-warning'}`}
                >
                    <Toast.Header closeButton={true}>
                        <strong className="me-auto">
                            {isHighSeverity(error) ? '⚠️ Critical Error' : '⚠️ Warning'}
                        </strong>
                        <small>{new Date(error.timestamp).toLocaleTimeString()}</small>
                    </Toast.Header>
                    <Toast.Body>
                        <div>{formatError(error)}</div>
                        {error.category && (
                            <small className="text-muted d-block mt-1">
                                Type: {error.category}
                            </small>
                        )}
                        {process.env.NODE_ENV === 'development' && error.id && (
                            <small className="text-muted d-block">
                                Error ID: {error.id}
                            </small>
                        )}
                    </Toast.Body>
                </Toast>
            ))}
            
            {visibleErrors.length > 1 && (
                <div className="position-fixed bottom-0 end-0 m-3">
                    <Button 
                        variant="outline-light" 
                        size="sm" 
                        onClick={clearAllErrors}
                        className="bg-dark text-white"
                    >
                        Clear All ({visibleErrors.length})
                    </Button>
                </div>
            )}
        </ToastContainer>
    );
};

export const ErrorAlert = ({ error, onDismiss, variant = 'danger' }) => {
    if (!error) return null;

    return (
        <Alert 
            variant={variant} 
            dismissible={!!onDismiss}
            onClose={onDismiss}
            className="mb-3"
        >
            <Alert.Heading>
                {variant === 'danger' ? 'Error' : 'Warning'}
            </Alert.Heading>
            <p className="mb-0">{typeof error === 'string' ? error : error.message}</p>
            {error.details && (
                <hr />
                <p className="mb-0 small text-muted">{error.details}</p>
            )}
        </Alert>
    );
};

export default ErrorNotification;