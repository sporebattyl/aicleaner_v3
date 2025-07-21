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
  Modal,
  ListGroup
} from 'react-bootstrap';
import { 
  FaShieldAlt, 
  FaKey, 
  FaLock, 
  FaExclamationTriangle, 
  FaCheck,
  FaEye,
  FaEyeSlash,
  FaUsers,
  FaClipboardCheck
} from 'react-icons/fa';

export const SecurityConfigurationSection = ({ 
  config, 
  onChange, 
  errors = {}, 
  warnings = {}, 
  canEdit, 
  securityStatus 
}) => {
  const [showToken, setShowToken] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);

  // Handle configuration changes
  const handleChange = (field, value) => {
    const newConfig = { ...config, [field]: value };
    onChange(newConfig);
  };

  // Handle role permissions changes
  const handleRoleChange = (role, permission, enabled) => {
    const roles = { ...config.roles };
    if (!roles[role]) roles[role] = {};
    roles[role][permission] = enabled;
    handleChange('roles', roles);
  };

  // Get security compliance score
  const getComplianceScore = () => {
    let score = 0;
    let total = 0;

    // Supervisor token validation
    total += 20;
    if (config.supervisor_token_valid) score += 20;

    // Authentication enabled
    total += 15;
    if (config.authentication_enabled) score += 15;

    // Session timeout configured
    total += 10;
    if (config.session_timeout && config.session_timeout > 0) score += 10;

    // Audit logging enabled
    total += 15;
    if (config.audit_logging) score += 15;

    // SSL/TLS required
    total += 20;
    if (config.ssl_required) score += 20;

    // Role-based access control
    total += 10;
    if (config.roles && Object.keys(config.roles).length > 0) score += 10;

    // Threat detection enabled
    total += 10;
    if (config.threat_detection_enabled) score += 10;

    return { score, total, percentage: Math.round((score / total) * 100) };
  };

  const compliance = getComplianceScore();

  const getComplianceColor = (percentage) => {
    if (percentage >= 80) return 'success';
    if (percentage >= 60) return 'warning';
    return 'danger';
  };

  return (
    <div className="security-configuration-section">
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <h5>
                <FaShieldAlt className="me-2" />
                Security Configuration
              </h5>
              <p className="text-muted mb-0">
                Configure authentication, authorization, and security monitoring
              </p>
            </div>
            
            <div className="d-flex align-items-center gap-3">
              {/* Compliance Score */}
              <div className="text-center">
                <Badge bg={getComplianceColor(compliance.percentage)} className="mb-1">
                  {compliance.percentage}% Compliant
                </Badge>
                <div className="small text-muted">
                  Security Score: {compliance.score}/{compliance.total}
                </div>
              </div>
              
              <Button
                variant="outline-info"
                size="sm"
                onClick={() => setShowValidationModal(true)}
              >
                <FaClipboardCheck className="me-2" />
                View Compliance
              </Button>
            </div>
          </div>
        </Col>
      </Row>

      {/* Authentication Settings */}
      <Card className="mb-4">
        <Card.Header>
          <h6 className="mb-0">Authentication & Access Control</h6>
        </Card.Header>
        <Card.Body>
          <Row>
            <Col md={6}>
              <Form.Group className="mb-3">
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <Form.Label>Supervisor Token</Form.Label>
                  <Badge bg={config.supervisor_token_valid ? 'success' : 'danger'}>
                    {config.supervisor_token_valid ? 'Valid' : 'Invalid'}
                  </Badge>
                </div>
                <InputGroup>
                  <Form.Control
                    type={showToken ? "text" : "password"}
                    value={config.supervisor_token || ''}
                    onChange={(e) => handleChange('supervisor_token', e.target.value)}
                    placeholder="Enter Home Assistant supervisor token"
                    disabled={!canEdit}
                    isInvalid={!!errors['security.supervisor_token']}
                  />
                  <Button
                    variant="outline-secondary"
                    onClick={() => setShowToken(!showToken)}
                    disabled={!canEdit}
                  >
                    {showToken ? <FaEyeSlash /> : <FaEye />}
                  </Button>
                </InputGroup>
                <Form.Control.Feedback type="invalid">
                  {errors['security.supervisor_token']}
                </Form.Control.Feedback>
                <Form.Text className="text-muted">
                  Token for authenticating with Home Assistant Supervisor API
                </Form.Text>
              </Form.Group>
            </Col>
            
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Label>Session Timeout (minutes)</Form.Label>
                <Form.Control
                  type="number"
                  value={config.session_timeout || 30}
                  onChange={(e) => handleChange('session_timeout', parseInt(e.target.value))}
                  min="5"
                  max="1440"
                  disabled={!canEdit}
                  isInvalid={!!errors['security.session_timeout']}
                />
                <Form.Control.Feedback type="invalid">
                  {errors['security.session_timeout']}
                </Form.Control.Feedback>
                <Form.Text className="text-muted">
                  Automatic logout after inactivity (5-1440 minutes)
                </Form.Text>
              </Form.Group>
            </Col>
          </Row>

          <Row>
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Check
                  type="switch"
                  label="Require Authentication"
                  checked={config.authentication_enabled || false}
                  onChange={(e) => handleChange('authentication_enabled', e.target.checked)}
                  disabled={!canEdit}
                />
                <Form.Text className="text-muted">
                  Require valid supervisor token for all operations
                </Form.Text>
              </Form.Group>
            </Col>
            
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Check
                  type="switch"
                  label="Require SSL/TLS"
                  checked={config.ssl_required || false}
                  onChange={(e) => handleChange('ssl_required', e.target.checked)}
                  disabled={!canEdit}
                />
                <Form.Text className="text-muted">
                  Force HTTPS connections for web interface
                </Form.Text>
              </Form.Group>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {/* Role-Based Access Control */}
      <Card className="mb-4">
        <Card.Header>
          <h6 className="mb-0">
            <FaUsers className="me-2" />
            Role-Based Access Control
          </h6>
        </Card.Header>
        <Card.Body>
          <Row>
            <Col md={4}>
              <h6>Administrator</h6>
              <Form.Check
                label="Configuration Management"
                checked={config.roles?.admin?.config_management || false}
                onChange={(e) => handleRoleChange('admin', 'config_management', e.target.checked)}
                disabled={!canEdit}
                className="mb-2"
              />
              <Form.Check
                label="Security Management"
                checked={config.roles?.admin?.security_management || false}
                onChange={(e) => handleRoleChange('admin', 'security_management', e.target.checked)}
                disabled={!canEdit}
                className="mb-2"
              />
              <Form.Check
                label="System Control"
                checked={config.roles?.admin?.system_control || false}
                onChange={(e) => handleRoleChange('admin', 'system_control', e.target.checked)}
                disabled={!canEdit}
                className="mb-2"
              />
            </Col>
            
            <Col md={4}>
              <h6>Operator</h6>
              <Form.Check
                label="Device Control"
                checked={config.roles?.operator?.device_control || false}
                onChange={(e) => handleRoleChange('operator', 'device_control', e.target.checked)}
                disabled={!canEdit}
                className="mb-2"
              />
              <Form.Check
                label="Zone Management"
                checked={config.roles?.operator?.zone_management || false}
                onChange={(e) => handleRoleChange('operator', 'zone_management', e.target.checked)}
                disabled={!canEdit}
                className="mb-2"
              />
              <Form.Check
                label="View Configuration"
                checked={config.roles?.operator?.view_config || false}
                onChange={(e) => handleRoleChange('operator', 'view_config', e.target.checked)}
                disabled={!canEdit}
                className="mb-2"
              />
            </Col>
            
            <Col md={4}>
              <h6>Viewer</h6>
              <Form.Check
                label="Read-Only Access"
                checked={config.roles?.viewer?.read_only || false}
                onChange={(e) => handleRoleChange('viewer', 'read_only', e.target.checked)}
                disabled={!canEdit}
                className="mb-2"
              />
              <Form.Check
                label="View Dashboards"
                checked={config.roles?.viewer?.view_dashboards || false}
                onChange={(e) => handleRoleChange('viewer', 'view_dashboards', e.target.checked)}
                disabled={!canEdit}
                className="mb-2"
              />
              <Form.Check
                label="View Devices"
                checked={config.roles?.viewer?.view_devices || false}
                onChange={(e) => handleRoleChange('viewer', 'view_devices', e.target.checked)}
                disabled={!canEdit}
                className="mb-2"
              />
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {/* Security Monitoring */}
      <Card>
        <Card.Header>
          <h6 className="mb-0">Security Monitoring & Logging</h6>
        </Card.Header>
        <Card.Body>
          <Row>
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Check
                  type="switch"
                  label="Enable Audit Logging"
                  checked={config.audit_logging || false}
                  onChange={(e) => handleChange('audit_logging', e.target.checked)}
                  disabled={!canEdit}
                />
                <Form.Text className="text-muted">
                  Log all configuration changes and security events
                </Form.Text>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Check
                  type="switch"
                  label="Enable Threat Detection"
                  checked={config.threat_detection_enabled || false}
                  onChange={(e) => handleChange('threat_detection_enabled', e.target.checked)}
                  disabled={!canEdit}
                />
                <Form.Text className="text-muted">
                  Real-time monitoring for suspicious activities
                </Form.Text>
              </Form.Group>
            </Col>
            
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Label>Log Retention (days)</Form.Label>
                <Form.Control
                  type="number"
                  value={config.log_retention_days || 30}
                  onChange={(e) => handleChange('log_retention_days', parseInt(e.target.value))}
                  min="1"
                  max="365"
                  disabled={!canEdit}
                  isInvalid={!!errors['security.log_retention_days']}
                />
                <Form.Control.Feedback type="invalid">
                  {errors['security.log_retention_days']}
                </Form.Control.Feedback>
                <Form.Text className="text-muted">
                  Number of days to retain security logs
                </Form.Text>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label>Alert Threshold</Form.Label>
                <Form.Select
                  value={config.alert_threshold || 'medium'}
                  onChange={(e) => handleChange('alert_threshold', e.target.value)}
                  disabled={!canEdit}
                  isInvalid={!!errors['security.alert_threshold']}
                >
                  <option value="low">Low - All security events</option>
                  <option value="medium">Medium - Moderate and high severity</option>
                  <option value="high">High - High severity only</option>
                  <option value="critical">Critical - Critical severity only</option>
                </Form.Select>
                <Form.Control.Feedback type="invalid">
                  {errors['security.alert_threshold']}
                </Form.Control.Feedback>
                <Form.Text className="text-muted">
                  Minimum severity level for security alerts
                </Form.Text>
              </Form.Group>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {/* Security Compliance Modal */}
      <Modal show={showValidationModal} onHide={() => setShowValidationModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>
            <FaClipboardCheck className="me-2" />
            Security Compliance Report
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="mb-3">
            <h6>Overall Compliance Score</h6>
            <div className="progress mb-3" style={{ height: '25px' }}>
              <div 
                className={`progress-bar bg-${getComplianceColor(compliance.percentage)}`}
                style={{ width: `${compliance.percentage}%` }}
              >
                {compliance.percentage}% ({compliance.score}/{compliance.total})
              </div>
            </div>
          </div>

          <ListGroup variant="flush">
            <ListGroup.Item className="d-flex justify-content-between align-items-center">
              <span>Supervisor Token Validation</span>
              {config.supervisor_token_valid ? (
                <Badge bg="success"><FaCheck /> Valid</Badge>
              ) : (
                <Badge bg="danger"><FaExclamationTriangle /> Invalid</Badge>
              )}
            </ListGroup.Item>
            
            <ListGroup.Item className="d-flex justify-content-between align-items-center">
              <span>Authentication Required</span>
              {config.authentication_enabled ? (
                <Badge bg="success"><FaCheck /> Enabled</Badge>
              ) : (
                <Badge bg="danger"><FaExclamationTriangle /> Disabled</Badge>
              )}
            </ListGroup.Item>
            
            <ListGroup.Item className="d-flex justify-content-between align-items-center">
              <span>Session Timeout Configured</span>
              {config.session_timeout > 0 ? (
                <Badge bg="success"><FaCheck /> {config.session_timeout} minutes</Badge>
              ) : (
                <Badge bg="danger"><FaExclamationTriangle /> Not configured</Badge>
              )}
            </ListGroup.Item>
            
            <ListGroup.Item className="d-flex justify-content-between align-items-center">
              <span>Audit Logging</span>
              {config.audit_logging ? (
                <Badge bg="success"><FaCheck /> Enabled</Badge>
              ) : (
                <Badge bg="warning"><FaExclamationTriangle /> Disabled</Badge>
              )}
            </ListGroup.Item>
            
            <ListGroup.Item className="d-flex justify-content-between align-items-center">
              <span>SSL/TLS Required</span>
              {config.ssl_required ? (
                <Badge bg="success"><FaCheck /> Required</Badge>
              ) : (
                <Badge bg="warning"><FaExclamationTriangle /> Optional</Badge>
              )}
            </ListGroup.Item>
            
            <ListGroup.Item className="d-flex justify-content-between align-items-center">
              <span>Role-Based Access Control</span>
              {config.roles && Object.keys(config.roles).length > 0 ? (
                <Badge bg="success"><FaCheck /> Configured</Badge>
              ) : (
                <Badge bg="warning"><FaExclamationTriangle /> Not configured</Badge>
              )}
            </ListGroup.Item>
            
            <ListGroup.Item className="d-flex justify-content-between align-items-center">
              <span>Threat Detection</span>
              {config.threat_detection_enabled ? (
                <Badge bg="success"><FaCheck /> Enabled</Badge>
              ) : (
                <Badge bg="warning"><FaExclamationTriangle /> Disabled</Badge>
              )}
            </ListGroup.Item>
          </ListGroup>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowValidationModal(false)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default SecurityConfigurationSection;