import React, { useState, useEffect, useCallback } from 'react';
import { 
  Card, 
  Tabs, 
  Tab, 
  Button, 
  Alert, 
  Spinner, 
  Toast, 
  ToastContainer,
  Badge,
  Form,
  Row,
  Col
} from 'react-bootstrap';
import { 
  FaCog, 
  FaSave, 
  FaCheck, 
  FaExclamationTriangle, 
  FaSync,
  FaShieldAlt,
  FaWifi,
  FaHome
} from 'react-icons/fa';
import { debounce } from 'lodash';
import ApiService from '../services/ApiService';
import { MQTTConfigurationSection } from './config/MQTTConfigurationSection';
import { SecurityConfigurationSection } from './config/SecurityConfigurationSection';
import { ZoneConfigurationSection } from './config/ZoneConfigurationSection';

export const UnifiedConfigurationPanel = ({ securityStatus }) => {
  // Core state management
  const [config, setConfig] = useState(null);
  const [originalConfig, setOriginalConfig] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});
  const [validationWarnings, setValidationWarnings] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [canEdit, setCanEdit] = useState(false);
  const [activeTab, setActiveTab] = useState('mqtt');
  
  // UI state
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastVariant, setToastVariant] = useState('success');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Initialize component and load data
  useEffect(() => {
    loadConfiguration();
    checkPermissions();
    setupWebSocketConnection();
  }, []);

  // Check for unsaved changes
  useEffect(() => {
    if (config && originalConfig) {
      const hasChanges = JSON.stringify(config) !== JSON.stringify(originalConfig);
      setHasUnsavedChanges(hasChanges);
    }
  }, [config, originalConfig]);

  // Load initial configuration
  const loadConfiguration = async () => {
    try {
      setIsLoading(true);
      const response = await ApiService.get('/api/config');
      setConfig(response);
      setOriginalConfig(JSON.parse(JSON.stringify(response)));
    } catch (error) {
      console.error('Failed to load configuration:', error);
      showNotification('Failed to load configuration', 'danger');
    } finally {
      setIsLoading(false);
    }
  };

  // Check user permissions
  const checkPermissions = async () => {
    try {
      // Use security status to determine permissions
      const canEditConfig = securityStatus?.security_level !== 'low';
      setCanEdit(canEditConfig);
      
      if (!canEditConfig) {
        showNotification('Configuration editing restricted due to security level', 'warning');
      }
    } catch (error) {
      console.error('Failed to check permissions:', error);
      setCanEdit(false);
    }
  };

  // Setup WebSocket for real-time configuration sync
  const setupWebSocketConnection = () => {
    // Note: This would be implemented with actual WebSocket service
    // For now, we'll use polling as fallback
    const interval = setInterval(() => {
      if (!hasUnsavedChanges) {
        checkForConfigurationUpdates();
      }
    }, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  };

  // Check for external configuration updates
  const checkForConfigurationUpdates = async () => {
    try {
      const response = await ApiService.get('/api/config');
      const serverConfig = JSON.stringify(response);
      const currentOriginal = JSON.stringify(originalConfig);
      
      if (serverConfig !== currentOriginal) {
        showNotification('Configuration updated externally', 'info');
        setOriginalConfig(response);
        if (!hasUnsavedChanges) {
          setConfig(response);
        }
      }
    } catch (error) {
      console.error('Failed to check for configuration updates:', error);
    }
  };

  // Debounced server-side validation
  const debouncedValidate = useCallback(
    debounce(async (configToValidate) => {
      if (!canEdit || !configToValidate) return;
      
      try {
        setIsValidating(true);
        const response = await ApiService.post('/api/config/validate', configToValidate);
        
        setValidationErrors(response.errors || {});
        setValidationWarnings(response.warnings || {});
        
        if (response.security_impact?.level === 'high') {
          showNotification('Configuration changes have high security impact', 'warning');
        }
      } catch (error) {
        console.error('Configuration validation failed:', error);
        setValidationErrors({ general: 'Validation service unavailable' });
      } finally {
        setIsValidating(false);
      }
    }, 750),
    [canEdit]
  );

  // Handle configuration changes from child components
  const handleConfigChange = (section, newSectionConfig) => {
    const newConfig = {
      ...config,
      [section]: newSectionConfig
    };
    
    setConfig(newConfig);
    debouncedValidate(newConfig);
  };

  // Save configuration
  const handleSave = async () => {
    if (!canEdit || Object.keys(validationErrors).length > 0) return;
    
    try {
      setIsSaving(true);
      const response = await ApiService.post('/api/config', config);
      
      if (response.status === 'success') {
        setOriginalConfig(JSON.parse(JSON.stringify(config)));
        setHasUnsavedChanges(false);
        showNotification('Configuration saved successfully', 'success');
      } else {
        throw new Error(response.message || 'Failed to save configuration');
      }
    } catch (error) {
      console.error('Failed to save configuration:', error);
      showNotification('Failed to save configuration: ' + error.message, 'danger');
    } finally {
      setIsSaving(false);
    }
  };

  // Reset configuration to last saved state
  const handleReset = () => {
    setConfig(JSON.parse(JSON.stringify(originalConfig)));
    setValidationErrors({});
    setValidationWarnings({});
    setHasUnsavedChanges(false);
    showNotification('Configuration reset to last saved state', 'info');
  };

  // Show notification toast
  const showNotification = (message, variant = 'success') => {
    setToastMessage(message);
    setToastVariant(variant);
    setShowToast(true);
  };

  // Get validation status for tab
  const getTabValidationStatus = (tabKey) => {
    const sectionErrors = Object.keys(validationErrors).filter(key => key.startsWith(tabKey));
    const sectionWarnings = Object.keys(validationWarnings).filter(key => key.startsWith(tabKey));
    
    if (sectionErrors.length > 0) return 'error';
    if (sectionWarnings.length > 0) return 'warning';
    return 'valid';
  };

  // Get tab icon based on section
  const getTabIcon = (tabKey) => {
    switch (tabKey) {
      case 'mqtt': return <FaWifi className="me-2" />;
      case 'security': return <FaShieldAlt className="me-2" />;
      case 'zones': return <FaHome className="me-2" />;
      default: return <FaCog className="me-2" />;
    }
  };

  // Get tab title with validation indicator
  const getTabTitle = (tabKey, title) => {
    const status = getTabValidationStatus(tabKey);
    return (
      <span>
        {getTabIcon(tabKey)}
        {title}
        {status === 'error' && <Badge bg="danger" className="ms-2">!</Badge>}
        {status === 'warning' && <Badge bg="warning" className="ms-2">⚠</Badge>}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ height: '400px' }}>
        <div className="text-center">
          <Spinner animation="border" role="status" className="mb-3" />
          <div>Loading configuration...</div>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <Alert variant="danger">
        <FaExclamationTriangle className="me-2" />
        Failed to load configuration. Please refresh the page.
        <Button variant="outline-danger" size="sm" className="ms-2" onClick={loadConfiguration}>
          Retry
        </Button>
      </Alert>
    );
  }

  return (
    <div className="unified-configuration-panel">
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <h4>
                <FaCog className="me-2" />
                Unified Configuration
              </h4>
              <p className="text-muted mb-0">
                Configure all AICleaner v3 settings from a single interface
              </p>
            </div>
            
            <div className="d-flex gap-2">
              {isValidating && (
                <Button variant="outline-secondary" disabled>
                  <Spinner size="sm" className="me-2" />
                  Validating...
                </Button>
              )}
              
              {hasUnsavedChanges && (
                <Button 
                  variant="outline-warning" 
                  onClick={handleReset}
                  disabled={!canEdit}
                >
                  <FaSync className="me-2" />
                  Reset
                </Button>
              )}
              
              <Button 
                variant="primary" 
                onClick={handleSave}
                disabled={
                  !canEdit || 
                  isSaving || 
                  !hasUnsavedChanges ||
                  Object.keys(validationErrors).length > 0
                }
              >
                {isSaving ? (
                  <>
                    <Spinner size="sm" className="me-2" />
                    Saving...
                  </>
                ) : (
                  <>
                    <FaSave className="me-2" />
                    Save Configuration
                  </>
                )}
              </Button>
            </div>
          </div>
        </Col>
      </Row>

      {/* Security Warning */}
      {!canEdit && (
        <Alert variant="warning" className="mb-4">
          <FaShieldAlt className="me-2" />
          Configuration editing is restricted due to current security level. 
          Please resolve security issues in the Security Dashboard before making changes.
        </Alert>
      )}

      {/* Validation Summary */}
      {Object.keys(validationErrors).length > 0 && (
        <Alert variant="danger" className="mb-4">
          <FaExclamationTriangle className="me-2" />
          <strong>Configuration Errors:</strong>
          <ul className="mb-0 mt-2">
            {Object.entries(validationErrors).map(([key, error]) => (
              <li key={key}>{error}</li>
            ))}
          </ul>
        </Alert>
      )}

      {/* Configuration Tabs */}
      <Card>
        <Card.Body>
          <Tabs 
            activeKey={activeTab} 
            onSelect={setActiveTab}
            className="mb-4"
          >
            <Tab 
              eventKey="mqtt" 
              title={getTabTitle('mqtt', 'MQTT Discovery')}
            >
              <MQTTConfigurationSection
                config={config.mqtt || {}}
                onChange={(mqttConfig) => handleConfigChange('mqtt', mqttConfig)}
                errors={validationErrors}
                warnings={validationWarnings}
                canEdit={canEdit}
                securityStatus={securityStatus}
              />
            </Tab>
            
            <Tab 
              eventKey="security" 
              title={getTabTitle('security', 'Security')}
            >
              <SecurityConfigurationSection
                config={config.security || {}}
                onChange={(securityConfig) => handleConfigChange('security', securityConfig)}
                errors={validationErrors}
                warnings={validationWarnings}
                canEdit={canEdit}
                securityStatus={securityStatus}
              />
            </Tab>
            
            <Tab 
              eventKey="zones" 
              title={getTabTitle('zones', 'Zones')}
            >
              <ZoneConfigurationSection
                config={config.zones || []}
                onChange={(zoneConfig) => handleConfigChange('zones', zoneConfig)}
                errors={validationErrors}
                warnings={validationWarnings}
                canEdit={canEdit}
                securityStatus={securityStatus}
              />
            </Tab>
          </Tabs>
        </Card.Body>
      </Card>

      {/* Unsaved Changes Warning */}
      {hasUnsavedChanges && (
        <Alert variant="info" className="mt-3">
          <FaExclamationTriangle className="me-2" />
          You have unsaved changes. Don't forget to save your configuration.
        </Alert>
      )}

      {/* Toast Notifications */}
      <ToastContainer position="top-end" className="p-3">
        <Toast 
          show={showToast} 
          onClose={() => setShowToast(false)}
          delay={5000}
          autohide
          bg={toastVariant}
        >
          <Toast.Header>
            <FaCheck className="me-2" />
            <strong className="me-auto">Configuration</strong>
          </Toast.Header>
          <Toast.Body className="text-white">
            {toastMessage}
          </Toast.Body>
        </Toast>
      </ToastContainer>
    </div>
  );
};

export default UnifiedConfigurationPanel;