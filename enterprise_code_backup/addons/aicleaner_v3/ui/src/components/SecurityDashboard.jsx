import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Alert, 
  Badge, 
  Button, 
  Form, 
  Modal, 
  Spinner,
  ListGroup,
  ProgressBar
} from 'react-bootstrap';
import { 
  FaShieldAlt, 
  FaLock, 
  FaExclamationTriangle, 
  FaCheckCircle, 
  FaTimesCircle,
  FaKey,
  FaWifi,
  FaEye
} from 'react-icons/fa';
import ApiService from '../services/ApiService';

export const SecurityDashboard = () => {
  const [securityStatus, setSecurityStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenInput, setTokenInput] = useState('');
  const [tokenValidation, setTokenValidation] = useState(null);
  const [validatingToken, setValidatingToken] = useState(false);

  useEffect(() => {
    loadSecurityStatus();
    // Refresh security status every 30 seconds
    const interval = setInterval(loadSecurityStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadSecurityStatus = async () => {
    try {
      setLoading(true);
      const response = await ApiService.get('/api/security');
      setSecurityStatus(response);
      setError(null);
    } catch (err) {
      console.error('Failed to load security status:', err);
      setError('Failed to load security status');
    } finally {
      setLoading(false);
    }
  };

  const validateToken = async () => {
    if (!tokenInput.trim()) {
      setTokenValidation({ valid: false, message: 'Token is required' });
      return;
    }

    try {
      setValidatingToken(true);
      const response = await ApiService.post('/api/security/validate-token', {
        token: tokenInput
      });
      setTokenValidation(response);
      
      // Refresh security status after validation
      setTimeout(loadSecurityStatus, 1000);
    } catch (err) {
      console.error('Token validation failed:', err);
      setTokenValidation({ 
        valid: false, 
        message: 'Token validation failed' 
      });
    } finally {
      setValidatingToken(false);
    }
  };

  const getSecurityLevelColor = (level) => {
    switch (level) {
      case 'high': return 'success';
      case 'medium': return 'warning';
      case 'low': return 'danger';
      default: return 'secondary';
    }
  };

  const getSecurityLevelIcon = (level) => {
    switch (level) {
      case 'high': return <FaShieldAlt className="text-success" />;
      case 'medium': return <FaExclamationTriangle className="text-warning" />;
      case 'low': return <FaTimesCircle className="text-danger" />;
      default: return <FaShieldAlt className="text-secondary" />;
    }
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ height: '200px' }}>
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Loading security status...</span>
        </Spinner>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="danger">
        <FaExclamationTriangle className="me-2" />
        {error}
        <Button variant="outline-danger" size="sm" className="ms-2" onClick={loadSecurityStatus}>
          Retry
        </Button>
      </Alert>
    );
  }

  return (
    <div className="security-dashboard">
      <Row className="mb-4">
        <Col>
          <h4>
            <FaShieldAlt className="me-2" />
            Security Dashboard
          </h4>
          <p className="text-muted">
            Monitor and manage AICleaner v3 security status
          </p>
        </Col>
      </Row>

      {/* Security Overview */}
      <Row className="mb-4">
        <Col md={8}>
          <Card>
            <Card.Header>
              <h5 className="mb-0">
                {getSecurityLevelIcon(securityStatus?.security_level)}
                <span className="ms-2">Security Overview</span>
                <Badge 
                  bg={getSecurityLevelColor(securityStatus?.security_level)} 
                  className="ms-2"
                >
                  {securityStatus?.security_level?.toUpperCase() || 'UNKNOWN'}
                </Badge>
              </h5>
            </Card.Header>
            <Card.Body>
              <Row>
                <Col md={6}>
                  <div className="d-flex align-items-center mb-3">
                    {securityStatus?.supervisor_token_valid ? (
                      <FaCheckCircle className="text-success me-2" />
                    ) : (
                      <FaTimesCircle className="text-danger me-2" />
                    )}
                    <span>Supervisor Token</span>
                    <Badge 
                      bg={securityStatus?.supervisor_token_valid ? 'success' : 'danger'} 
                      className="ms-auto"
                    >
                      {securityStatus?.supervisor_token_valid ? 'Valid' : 'Invalid'}
                    </Badge>
                  </div>
                  
                  <div className="d-flex align-items-center mb-3">
                    {securityStatus?.tls_enabled ? (
                      <FaLock className="text-success me-2" />
                    ) : (
                      <FaWifi className="text-warning me-2" />
                    )}
                    <span>MQTT Encryption</span>
                    <Badge 
                      bg={securityStatus?.tls_enabled ? 'success' : 'warning'} 
                      className="ms-auto"
                    >
                      {securityStatus?.tls_enabled ? 'TLS Enabled' : 'Unencrypted'}
                    </Badge>
                  </div>
                  
                  <div className="d-flex align-items-center">
                    {securityStatus?.mqtt_secured ? (
                      <FaCheckCircle className="text-success me-2" />
                    ) : (
                      <FaExclamationTriangle className="text-warning me-2" />
                    )}
                    <span>MQTT Security</span>
                    <Badge 
                      bg={securityStatus?.mqtt_secured ? 'success' : 'warning'} 
                      className="ms-auto"
                    >
                      {securityStatus?.mqtt_secured ? 'Secured' : 'Needs Review'}
                    </Badge>
                  </div>
                </Col>
                
                <Col md={6}>
                  <div className="text-center">
                    <h6>Threats Detected</h6>
                    <div className="display-6 text-primary">
                      {securityStatus?.threats_detected || 0}
                    </div>
                    <small className="text-muted">
                      Last check: {new Date(securityStatus?.last_security_check).toLocaleString()}
                    </small>
                  </div>
                </Col>
              </Row>
            </Card.Body>
          </Card>
        </Col>

        <Col md={4}>
          <Card>
            <Card.Header>
              <h6 className="mb-0">
                <FaKey className="me-2" />
                Security Actions
              </h6>
            </Card.Header>
            <Card.Body>
              <div className="d-grid gap-2">
                <Button 
                  variant="outline-primary" 
                  onClick={() => setShowTokenModal(true)}
                >
                  <FaKey className="me-2" />
                  Validate Token
                </Button>
                
                <Button 
                  variant="outline-secondary" 
                  onClick={loadSecurityStatus}
                >
                  <FaShieldAlt className="me-2" />
                  Refresh Status
                </Button>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Security Events */}
      <Row>
        <Col>
          <Card>
            <Card.Header>
              <h6 className="mb-0">
                <FaEye className="me-2" />
                Recent Security Events
              </h6>
            </Card.Header>
            <Card.Body>
              {securityStatus?.security_events?.length > 0 ? (
                <ListGroup variant="flush">
                  {securityStatus.security_events.slice(0, 10).map((event, index) => (
                    <ListGroup.Item key={index} className="px-0">
                      <div className="d-flex justify-content-between align-items-start">
                        <div>
                          <Badge 
                            bg={event.level === 'error' ? 'danger' : 
                                event.level === 'warning' ? 'warning' : 'info'} 
                            className="me-2"
                          >
                            {event.type}
                          </Badge>
                          <span>{event.message}</span>
                        </div>
                        <small className="text-muted">
                          {new Date(event.timestamp).toLocaleString()}
                        </small>
                      </div>
                    </ListGroup.Item>
                  ))}
                </ListGroup>
              ) : (
                <div className="text-center text-muted py-3">
                  <FaEye className="mb-2" style={{ fontSize: '2rem', opacity: 0.3 }} />
                  <p>No security events recorded</p>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Token Validation Modal */}
      <Modal show={showTokenModal} onHide={() => setShowTokenModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>
            <FaKey className="me-2" />
            Validate Supervisor Token
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Supervisor Token</Form.Label>
              <Form.Control
                type="password"
                placeholder="Enter supervisor token..."
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                isValid={tokenValidation?.valid === true}
                isInvalid={tokenValidation?.valid === false}
              />
              <Form.Text className="text-muted">
                Enter your Home Assistant supervisor token for validation
              </Form.Text>
              {tokenValidation && (
                <div className={`mt-2 ${tokenValidation.valid ? 'text-success' : 'text-danger'}`}>
                  {tokenValidation.valid ? (
                    <FaCheckCircle className="me-1" />
                  ) : (
                    <FaTimesCircle className="me-1" />
                  )}
                  {tokenValidation.message}
                </div>
              )}
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowTokenModal(false)}>
            Cancel
          </Button>
          <Button 
            variant="primary" 
            onClick={validateToken}
            disabled={validatingToken || !tokenInput.trim()}
          >
            {validatingToken ? (
              <>
                <Spinner size="sm" className="me-2" />
                Validating...
              </>
            ) : (
              <>
                <FaKey className="me-2" />
                Validate Token
              </>
            )}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default SecurityDashboard;