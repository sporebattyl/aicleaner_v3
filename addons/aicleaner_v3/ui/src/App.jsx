
import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Container, Navbar, Nav, Tab, Tabs } from 'react-bootstrap';
import { ConfigurationManager } from './components/ConfigurationManager';
import { MonitoringDashboard } from './components/MonitoringDashboard';
import { DeviceController } from './components/DeviceController';
import { ZoneManager } from './components/ZoneManager';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="App">
      <Navbar bg="light" expand="lg" className="mb-4">
        <Container fluid>
          <Navbar.Brand href="#home">
            <strong>AICleaner v3</strong>
          </Navbar.Brand>
          <Navbar.Toggle aria-controls="basic-navbar-nav" />
        </Container>
      </Navbar>

      <Container fluid>
        <Tabs
          activeKey={activeTab}
          onSelect={(k) => setActiveTab(k)}
          className="mb-4"
        >
          <Tab eventKey="dashboard" title="Dashboard">
            <MonitoringDashboard />
          </Tab>
          <Tab eventKey="devices" title="Devices">
            <DeviceController />
          </Tab>
          <Tab eventKey="zones" title="Zones">
            <ZoneManager />
          </Tab>
          <Tab eventKey="config" title="Configuration">
            <ConfigurationManager />
          </Tab>
        </Tabs>
      </Container>
    </div>
  );
}

export default App;
