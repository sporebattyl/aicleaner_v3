
import React, { useState, useEffect, Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Container, Navbar, Nav, Tab, Tabs, Alert, Badge, Spinner } from 'react-bootstrap';
import { FaShieldAlt, FaExclamationTriangle, FaCog, FaWifi } from 'react-icons/fa';
import ApiService from './services/ApiService';
import { getIngressBasePath, isIngressMode } from './utils/ingress';

// Lazy load components for better performance
const TieredConfigurationPanel = lazy(() => import('./components/TieredConfigurationPanel'));
const SimpleHealthDashboard = lazy(() => import('./components/SimpleHealthDashboard'));
const DeviceController = lazy(() => import('./components/DeviceController').then(module => ({ default: module.DeviceController })));
const ZoneManager = lazy(() => import('./components/ZoneManager').then(module => ({ default: module.ZoneManager })));
const SimpleSecurityManager = lazy(() => import('./components/SimpleSecurityManager'));
const UnifiedConfigurationPanel = lazy(() => import('./components/UnifiedConfigurationPanel').then(module => ({ default: module.UnifiedConfigurationPanel })));

function AppContent() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [securityStatus, setSecurityStatus] = useState(null);
  const [mqttStatus, setMqttStatus] = useState(null);

  // Load security and MQTT status for enhanced navigation
  useEffect(() => {
    loadSystemStatus();
    const interval = setInterval(loadSystemStatus, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const loadSystemStatus = async () => {
    try {
      const [securityResponse, mqttResponse] = await Promise.all([
        ApiService.get('/api/security').catch(() => null),
        ApiService.get('/api/mqtt/status').catch(() => null)
      ]);
      
      setSecurityStatus(securityResponse);
      setMqttStatus(mqttResponse);
    } catch (error) {
      console.error('Failed to load system status:', error);
    }
  };

  // Get security level indicator for tabs
  const getSecurityBadge = () => {
    if (!securityStatus) return null;
    
    const level = securityStatus.security_level;
    if (level === 'low') {
      return <Badge bg="danger" className="ms-1">!</Badge>;
    } else if (level === 'medium') {
      return <Badge bg="warning" className="ms-1">⚠</Badge>;
    }
    return null;
  };

  // Get MQTT connection badge
  const getMqttBadge = () => {
    if (!mqttStatus) return null;
    
    if (!mqttStatus.connected) {
      return <Badge bg="warning" className="ms-1">!</Badge>;
    }
    return null;
  };

  // Loading component for lazy-loaded routes
  const LoadingSpinner = () => (
    <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '200px' }}>
      <Spinner animation="border" role="status" variant="primary">
        <span className="visually-hidden">Loading...</span>
      </Spinner>
    </div>
  );

  return (
    <div className="App">
      <Navbar bg="light" expand="lg" className="mb-4">
        <Container fluid>
          <Navbar.Brand href="#home">
            <strong>AICleaner v3</strong>
            {securityStatus?.security_level === 'low' && (
              <Badge bg="danger" className="ms-2">
                <FaExclamationTriangle className="me-1" />
                Security Issue
              </Badge>
            )}
          </Navbar.Brand>
          <Navbar.Toggle aria-controls="basic-navbar-nav" />
        </Container>
      </Navbar>

      <Container fluid>
        {/* Security Alert Banner */}
        {securityStatus?.security_level === 'low' && (
          <Alert variant="danger" className="mb-4">
            <FaShieldAlt className="me-2" />
            <strong>Security Alert:</strong> Your system security level is LOW. 
            Please review the Security Dashboard to resolve critical security issues.
          </Alert>
        )}

        <Tabs
          activeKey={activeTab}
          onSelect={(k) => setActiveTab(k)}
          className="mb-4"
        >
          <Tab eventKey="dashboard" title="Dashboard">
            <Suspense fallback={<LoadingSpinner />}>
              <SimpleHealthDashboard />
            </Suspense>
          </Tab>
          
          <Tab eventKey="devices" title="Devices">
            <Suspense fallback={<LoadingSpinner />}>
              <DeviceController />
            </Suspense>
          </Tab>
          
          <Tab eventKey="zones" title="Zones">
            <Suspense fallback={<LoadingSpinner />}>
              <ZoneManager />
            </Suspense>
          </Tab>
          
          <Tab 
            eventKey="security" 
            title={
              <span>
                <FaShieldAlt className="me-1" />
                Security
                {getSecurityBadge()}
              </span>
            }
          >
            <Suspense fallback={<LoadingSpinner />}>
              <SimpleSecurityManager />
            </Suspense>
          </Tab>
          
          <Tab 
            eventKey="unified-config" 
            title={
              <span>
                <FaCog className="me-1" />
                Configuration
                {getMqttBadge()}
              </span>
            }
          >
            <Suspense fallback={<LoadingSpinner />}>
              <UnifiedConfigurationPanel securityStatus={securityStatus} />
            </Suspense>
          </Tab>
          
          <Tab eventKey="legacy-config" title="Legacy Config">
            <Suspense fallback={<LoadingSpinner />}>
              <TieredConfigurationPanel />
            </Suspense>
          </Tab>
        </Tabs>
      </Container>
    </div>
  );
}

// Main App component with ingress-aware routing
function App() {
  const basename = getIngressBasePath();
  
  // Add ingress status to console for debugging
  useEffect(() => {
    if (isIngressMode()) {
      console.log('AICleaner running in Home Assistant Ingress mode');
      console.log('Ingress base path:', basename);
    } else {
      console.log('AICleaner running in direct access mode');
    }
  }, [basename]);

  return (
    <BrowserRouter basename={basename}>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
