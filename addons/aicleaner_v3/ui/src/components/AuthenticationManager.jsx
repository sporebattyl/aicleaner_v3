import React, { useState, useEffect, useContext, createContext } from 'react';
import { Card, Form, Button, Alert, Modal, Badge } from 'react-bootstrap';
import ApiService from '../services/ApiService';

// Authentication Context
const AuthContext = createContext();

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        checkAuthStatus();
    }, []);

    const checkAuthStatus = async () => {
        try {
            const token = localStorage.getItem('aicleaner_token');
            if (token) {
                const userData = await ApiService.validateToken(token);
                setUser(userData);
            }
        } catch (err) {
            localStorage.removeItem('aicleaner_token');
            setError('Session expired');
        } finally {
            setLoading(false);
        }
    };

    const login = async (username, password) => {
        try {
            setError(null);
            const response = await ApiService.login(username, password);
            localStorage.setItem('aicleaner_token', response.token);
            setUser(response.user);
            return { success: true };
        } catch (err) {
            setError(err.message || 'Login failed');
            return { success: false, error: err.message };
        }
    };

    const logout = async () => {
        try {
            await ApiService.logout();
        } catch (err) {
            console.error('Logout error:', err);
        } finally {
            localStorage.removeItem('aicleaner_token');
            setUser(null);
        }
    };

    const value = {
        user,
        login,
        logout,
        loading,
        error,
        isAuthenticated: !!user
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

export const LoginForm = () => {
    const [credentials, setCredentials] = useState({ username: '', password: '' });
    const [loading, setLoading] = useState(false);
    const [showHelp, setShowHelp] = useState(false);
    const { login, error } = useAuth();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        
        try {
            const result = await login(credentials.username, credentials.password);
            if (!result.success) {
                console.error('Login failed:', result.error);
            }
        } finally {
            setLoading(false);
        }
    };

    const handleInputChange = (field, value) => {
        setCredentials(prev => ({ ...prev, [field]: value }));
    };

    return (
        <div className="d-flex justify-content-center align-items-center min-vh-100">
            <Card style={{ width: '400px' }}>
                <Card.Header className="text-center">
                    <h4 className="mb-0">AICleaner v3 Login</h4>
                </Card.Header>
                <Card.Body>
                    {error && (
                        <Alert variant="danger" className="mb-3">
                            {error}
                        </Alert>
                    )}
                    
                    <Form onSubmit={handleSubmit}>
                        <Form.Group className="mb-3">
                            <Form.Label>Username</Form.Label>
                            <Form.Control
                                type="text"
                                value={credentials.username}
                                onChange={(e) => handleInputChange('username', e.target.value)}
                                placeholder="Enter username"
                                required
                                autoComplete="username"
                                aria-label="Username"
                            />
                        </Form.Group>
                        
                        <Form.Group className="mb-3">
                            <Form.Label>Password</Form.Label>
                            <Form.Control
                                type="password"
                                value={credentials.password}
                                onChange={(e) => handleInputChange('password', e.target.value)}
                                placeholder="Enter password"
                                required
                                autoComplete="current-password"
                                aria-label="Password"
                            />
                        </Form.Group>
                        
                        <div className="d-grid mb-3">
                            <Button 
                                type="submit" 
                                variant="primary"
                                disabled={loading || !credentials.username || !credentials.password}
                                aria-label="Login to AICleaner v3"
                            >
                                {loading ? 'Logging in...' : 'Login'}
                            </Button>
                        </div>
                        
                        <div className="text-center">
                            <Button 
                                variant="link" 
                                size="sm"
                                onClick={() => setShowHelp(true)}
                                aria-label="Get login help"
                            >
                                Need help?
                            </Button>
                        </div>
                    </Form>
                </Card.Body>
            </Card>

            {/* Help Modal */}
            <Modal show={showHelp} onHide={() => setShowHelp(false)}>
                <Modal.Header closeButton>
                    <Modal.Title>Login Help</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <h6>Default Credentials</h6>
                    <p>Username: <code>admin</code></p>
                    <p>Password: <code>aicleaner</code></p>
                    
                    <h6>First Time Setup</h6>
                    <p>If this is your first time accessing AICleaner v3, use the default credentials above. You'll be prompted to change the password after login.</p>
                    
                    <h6>Password Reset</h6>
                    <p>If you've forgotten your password, access the Home Assistant addon configuration to reset credentials.</p>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => setShowHelp(false)}>
                        Close
                    </Button>
                </Modal.Footer>
            </Modal>
        </div>
    );
};

export const UserProfile = () => {
    const { user, logout } = useAuth();
    const [showProfile, setShowProfile] = useState(false);

    if (!user) return null;

    return (
        <>
            <div className="d-flex align-items-center">
                <Badge bg="success" className="me-2">
                    {user.role || 'User'}
                </Badge>
                <span className="me-2">{user.username}</span>
                <Button 
                    variant="outline-secondary" 
                    size="sm"
                    onClick={() => setShowProfile(true)}
                    aria-label="View user profile"
                >
                    Profile
                </Button>
                <Button 
                    variant="outline-danger" 
                    size="sm" 
                    className="ms-2"
                    onClick={logout}
                    aria-label="Logout from AICleaner v3"
                >
                    Logout
                </Button>
            </div>

            {/* Profile Modal */}
            <Modal show={showProfile} onHide={() => setShowProfile(false)}>
                <Modal.Header closeButton>
                    <Modal.Title>User Profile</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <div className="mb-3">
                        <strong>Username:</strong> {user.username}
                    </div>
                    <div className="mb-3">
                        <strong>Role:</strong> {user.role || 'User'}
                    </div>
                    <div className="mb-3">
                        <strong>Last Login:</strong> {user.lastLogin ? new Date(user.lastLogin).toLocaleString() : 'N/A'}
                    </div>
                    <div className="mb-3">
                        <strong>Permissions:</strong>
                        <ul className="mt-2">
                            {user.permissions?.map(permission => (
                                <li key={permission}>{permission}</li>
                            )) || <li>Standard user permissions</li>}
                        </ul>
                    </div>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => setShowProfile(false)}>
                        Close
                    </Button>
                </Modal.Footer>
            </Modal>
        </>
    );
};

// Protected Route Component
export const ProtectedRoute = ({ children }) => {
    const { isAuthenticated, loading } = useAuth();

    if (loading) {
        return (
            <div className="d-flex justify-content-center align-items-center min-vh-100">
                <div className="text-center">
                    <div className="spinner-border" role="status" aria-hidden="true"></div>
                    <p className="mt-2">Loading...</p>
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return <LoginForm />;
    }

    return children;
};