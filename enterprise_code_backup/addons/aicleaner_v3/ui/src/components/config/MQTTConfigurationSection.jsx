import React, { useState } from 'react';
import { 
  Row, 
  Col, 
  Form, 
  Card, 
  Button, 
  Alert, 
  Badge, 
  InputGroup,
  Spinner,
  OverlayTrigger,
  Tooltip
} from 'react-bootstrap';
import { 
  FaWifi, 
  FaLock, 
  FaShieldAlt, 
  FaExclamationTriangle, 
  FaCheck,
  FaEye,
  FaEyeSlash,
  FaFileUpload,
  FaTimes,
  FaFlask
} from 'react-icons/fa';
import ApiService from '../../services/ApiService';

export const MQTTConfigurationSection = ({ 
  config, 
  onChange, 
  errors = {}, 
  warnings = {}, 
  canEdit, 
  securityStatus 
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionTestResult, setConnectionTestResult] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState({
    ca_cert: null,
    client_cert: null,
    client_key: null
  });

  // Handle basic configuration changes
  const handleChange = (field, value) => {
    const newConfig = { ...config, [field]: value };
    onChange(newConfig);
  };

  // Handle TLS toggle with security implications
  const handleTLSToggle = (enabled) => {
    const newConfig = {
      ...config,
      use_tls: enabled,
      // Reset TLS-specific fields when disabling
      ...(enabled ? {} : {
        tls_ca_cert: '',
        tls_cert_file: '',
        tls_key_file: '',
        tls_insecure: false
      })
    };
    onChange(newConfig);
  };

  // Handle certificate file selection
  const handleFileSelect = (fileType, event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFiles(prev => ({ ...prev, [fileType]: file }));
      
      // Update config with file path (in real implementation, this would be handled by upload)
      const fieldMap = {
        ca_cert: 'tls_ca_cert',
        client_cert: 'tls_cert_file',
        client_key: 'tls_key_file'
      };
      
      handleChange(fieldMap[fileType], `/certificates/${file.name}`);
    }
  };

  // Clear selected file
  const clearFile = (fileType) => {
    setSelectedFiles(prev => ({ ...prev, [fileType]: null }));
    
    const fieldMap = {
      ca_cert: 'tls_ca_cert',
      client_cert: 'tls_cert_file',
      client_key: 'tls_key_file'
    };
    
    handleChange(fieldMap[fileType], '');
  };

  // Test MQTT connection
  const testConnection = async () => {
    try {
      setTestingConnection(true);
      setConnectionTestResult(null);
      
      const testConfig = { ...config };
      const response = await ApiService.post('/api/mqtt/test-connection', testConfig);
      
      setConnectionTestResult({
        success: true,
        message: response.message || 'Connection successful',
        details: response.details
      });
    } catch (error) {
      setConnectionTestResult({
        success: false,
        message: error.message || 'Connection failed',
        details: error.details
      });
    } finally {
      setTestingConnection(false);
    }
  };

  // Get security level indicator
  const getSecurityLevel = () => {
    let score = 0;
    let level = 'low';
    let color = 'danger';
    
    if (config.use_tls) {
      score += 40;
      level = 'medium';
      color = 'warning';
      
      if (config.tls_ca_cert) score += 20;
      if (config.tls_cert_file && config.tls_key_file) score += 20;
      if (!config.tls_insecure) score += 10;
    }
    
    if (config.username && config.password) score += 10;
    
    if (score >= 80) {
      level = 'high';
      color = 'success';
    } else if (score >= 50) {
      level = 'medium';
      color = 'warning';
    }
    
    return { score, level, color };
  };

  const securityLevel = getSecurityLevel();

  return (
    <div className="mqtt-configuration-section">
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <h5>
                <FaWifi className="me-2" />
                MQTT Discovery Configuration
              </h5>
              <p className="text-muted mb-0">
                Configure MQTT broker connection and discovery settings
              </p>
            </div>
            
            <div className="d-flex align-items-center gap-3">
              {/* Security Level Indicator */}
              <OverlayTrigger
                placement="left"
                overlay={
                  <Tooltip>
                    Security Score: {securityLevel.score}/100
                    <br />
                    Level: {securityLevel.level.toUpperCase()}
                  </Tooltip>
                }
              >
                <Badge bg={securityLevel.color} className="d-flex align-items-center">
                  <FaShieldAlt className="me-1" />
                  {securityLevel.level.toUpperCase()}
                </Badge>
              </OverlayTrigger>
              
              {/* Connection Test Button */}
              <Button
                variant="outline-primary"
                size="sm"
                onClick={testConnection}
                disabled={!canEdit || testingConnection || !config.broker_address}
              >
                {testingConnection ? (
                  <>
                    <Spinner size="sm" className="me-2" />
                    Testing...
                  </>
                ) : (
                  <>
                    <FaTestTube className="me-2" />
                    Test Connection
                  </>
                )}
              </Button>
            </div>
          </div>
        </Col>
      </Row>

      {/* Connection Test Result */}
      {connectionTestResult && (
        <Row className="mb-4">
          <Col>
            <Alert variant={connectionTestResult.success ? 'success' : 'danger'}>
              <div className="d-flex align-items-center">
                {connectionTestResult.success ? (
                  <FaCheck className="me-2" />
                ) : (
                  <FaExclamationTriangle className="me-2" />
                )}
                <div>
                  <strong>Connection Test Result:</strong> {connectionTestResult.message}
                  {connectionTestResult.details && (
                    <div className="small mt-1">{connectionTestResult.details}</div>
                  )}
                </div>
              </div>
            </Alert>
          </Col>
        </Row>
      )}

      {/* Basic Connection Settings */}
      <Card className="mb-4">
        <Card.Header>
          <h6 className="mb-0">Broker Connection</h6>
        </Card.Header>
        <Card.Body>
          <Row>
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Label>Broker Address *</Form.Label>
                <Form.Control
                  type="text"
                  value={config.broker_address || ''}
                  onChange={(e) => handleChange('broker_address', e.target.value)}
                  placeholder="mqtt.example.com or localhost"
                  disabled={!canEdit}
                  isInvalid={!!errors['mqtt.broker_address']}
                />
                <Form.Control.Feedback type="invalid">
                  {errors['mqtt.broker_address']}
                </Form.Control.Feedback>
                <Form.Text className="text-muted">
                  Hostname or IP address of your MQTT broker
                </Form.Text>
              </Form.Group>
            </Col>
            
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Label>Port</Form.Label>
                <Form.Control
                  type="number"
                  value={config.broker_port || 1883}
                  onChange={(e) => handleChange('broker_port', parseInt(e.target.value))}
                  min="1"
                  max="65535"
                  disabled={!canEdit}
                  isInvalid={!!errors['mqtt.broker_port']}
                />
                <Form.Control.Feedback type="invalid">
                  {errors['mqtt.broker_port']}
                </Form.Control.Feedback>
                <Form.Text className="text-muted">
                  Standard: 1883 (plain), 8883 (TLS)
                </Form.Text>
              </Form.Group>
            </Col>
          </Row>
          
          <Row>
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Label>Username</Form.Label>
                <Form.Control
                  type="text"
                  value={config.username || ''}
                  onChange={(e) => handleChange('username', e.target.value)}
                  placeholder="MQTT username (optional)"
                  disabled={!canEdit}
                  isInvalid={!!errors['mqtt.username']}
                />
                <Form.Control.Feedback type="invalid">
                  {errors['mqtt.username']}
                </Form.Control.Feedback>
              </Form.Group>
            </Col>
            
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Label>Password</Form.Label>
                <InputGroup>
                  <Form.Control
                    type={showPassword ? "text" : "password"}
                    value={config.password || ''}
                    onChange={(e) => handleChange('password', e.target.value)}
                    placeholder="MQTT password (optional)"
                    disabled={!canEdit}
                    isInvalid={!!errors['mqtt.password']}
                  />
                  <Button
                    variant="outline-secondary"
                    onClick={() => setShowPassword(!showPassword)}
                    disabled={!canEdit}
                  >
                    {showPassword ? <FaEyeSlash /> : <FaEye />}
                  </Button>
                </InputGroup>
                <Form.Control.Feedback type="invalid">
                  {errors['mqtt.password']}
                </Form.Control.Feedback>
              </Form.Group>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {/* TLS/SSL Configuration */}
      <Card className="mb-4">
        <Card.Header>
          <div className="d-flex justify-content-between align-items-center">
            <h6 className="mb-0">
              <FaLock className="me-2" />
              TLS/SSL Encryption
            </h6>
            <Form.Check
              type="switch"
              label="Enable TLS"
              checked={config.use_tls || false}
              onChange={(e) => handleTLSToggle(e.target.checked)}
              disabled={!canEdit}
            />
          </div>
        </Card.Header>
        <Card.Body>
          {!config.use_tls ? (
            <Alert variant="warning">
              <FaExclamationTriangle className="me-2" />
              TLS encryption is disabled. All MQTT communication will be transmitted in plain text.
              This is not recommended for production environments.
            </Alert>
          ) : (
            <>
              <Alert variant="info" className="mb-3">
                <FaShieldAlt className="me-2" />
                TLS encryption is enabled. Configure certificates below for enhanced security.
              </Alert>
              
              <Row>
                <Col md={12}>
                  <Form.Group className="mb-3">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <Form.Label>CA Certificate</Form.Label>
                      {selectedFiles.ca_cert && (
                        <Button
                          variant="outline-danger"
                          size="sm"
                          onClick={() => clearFile('ca_cert')}
                        >
                          <FaTimes className="me-1" />
                          Clear
                        </Button>
                      )}
                    </div>
                    
                    {selectedFiles.ca_cert ? (
                      <div className="d-flex align-items-center p-2 bg-light rounded">
                        <FaFileUpload className="me-2 text-success" />
                        <span>{selectedFiles.ca_cert.name}</span>
                      </div>
                    ) : (
                      <Form.Control
                        type="file"
                        accept=".crt,.pem,.cer"
                        onChange={(e) => handleFileSelect('ca_cert', e)}
                        disabled={!canEdit}
                      />
                    )}
                    
                    <Form.Text className="text-muted">
                      Certificate Authority file to verify broker certificate
                    </Form.Text>
                  </Form.Group>
                </Col>
              </Row>
              
              <Row>
                <Col md={6}>
                  <Form.Group className="mb-3">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <Form.Label>Client Certificate</Form.Label>
                      {selectedFiles.client_cert && (
                        <Button
                          variant="outline-danger"
                          size="sm"
                          onClick={() => clearFile('client_cert')}
                        >
                          <FaTimes className="me-1" />
                          Clear
                        </Button>
                      )}
                    </div>
                    
                    {selectedFiles.client_cert ? (
                      <div className="d-flex align-items-center p-2 bg-light rounded">
                        <FaFileUpload className="me-2 text-success" />
                        <span>{selectedFiles.client_cert.name}</span>
                      </div>
                    ) : (
                      <Form.Control
                        type="file"
                        accept=".crt,.pem,.cer"
                        onChange={(e) => handleFileSelect('client_cert', e)}
                        disabled={!canEdit}
                      />
                    )}
                    
                    <Form.Text className="text-muted">
                      Client certificate for mutual authentication
                    </Form.Text>
                  </Form.Group>
                </Col>
                
                <Col md={6}>
                  <Form.Group className="mb-3">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <Form.Label>Private Key</Form.Label>
                      {selectedFiles.client_key && (
                        <Button
                          variant="outline-danger"
                          size="sm"
                          onClick={() => clearFile('client_key')}
                        >
                          <FaTimes className="me-1" />
                          Clear
                        </Button>
                      )}
                    </div>
                    
                    {selectedFiles.client_key ? (
                      <div className="d-flex align-items-center p-2 bg-light rounded">
                        <FaFileUpload className="me-2 text-success" />
                        <span>{selectedFiles.client_key.name}</span>
                      </div>
                    ) : (
                      <Form.Control
                        type="file"
                        accept=".key,.pem"
                        onChange={(e) => handleFileSelect('client_key', e)}
                        disabled={!canEdit}
                      />
                    )}
                    
                    <Form.Text className="text-muted">
                      Private key for client certificate
                    </Form.Text>
                  </Form.Group>
                </Col>
              </Row>
              
              <Form.Group className="mb-0">
                <Form.Check
                  type="checkbox"
                  label="Skip certificate verification (insecure - development only)"
                  checked={config.tls_insecure || false}
                  onChange={(e) => handleChange('tls_insecure', e.target.checked)}
                  disabled={!canEdit}
                />
                <Form.Text className="text-muted">
                  Only enable this for testing with self-signed certificates
                </Form.Text>
              </Form.Group>
            </>
          )}
        </Card.Body>
      </Card>

      {/* Discovery Settings */}
      <Card>
        <Card.Header>
          <h6 className="mb-0">Discovery Settings</h6>
        </Card.Header>
        <Card.Body>
          <Row>
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Label>Discovery Prefix</Form.Label>
                <Form.Control
                  type="text"
                  value={config.discovery_prefix || 'homeassistant'}
                  onChange={(e) => handleChange('discovery_prefix', e.target.value)}
                  placeholder="homeassistant"
                  disabled={!canEdit}
                  isInvalid={!!errors['mqtt.discovery_prefix']}
                />
                <Form.Control.Feedback type="invalid">
                  {errors['mqtt.discovery_prefix']}
                </Form.Control.Feedback>
                <Form.Text className="text-muted">
                  MQTT topic prefix for Home Assistant discovery
                </Form.Text>
              </Form.Group>
            </Col>
            
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Label>Quality of Service (QoS)</Form.Label>
                <Form.Select
                  value={config.qos || 1}
                  onChange={(e) => handleChange('qos', parseInt(e.target.value))}
                  disabled={!canEdit}
                  isInvalid={!!errors['mqtt.qos']}
                >
                  <option value={0}>0 - At most once (fire and forget)</option>
                  <option value={1}>1 - At least once (acknowledged delivery)</option>
                  <option value={2}>2 - Exactly once (assured delivery)</option>
                </Form.Select>
                <Form.Control.Feedback type="invalid">
                  {errors['mqtt.qos']}
                </Form.Control.Feedback>
                <Form.Text className="text-muted">
                  Message delivery guarantee level
                </Form.Text>
              </Form.Group>
            </Col>
          </Row>
        </Card.Body>
      </Card>
    </div>
  );
};

export default MQTTConfigurationSection;