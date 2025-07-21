import React, { useState } from 'react';
import { 
  Row, 
  Col, 
  Form, 
  Card, 
  Button, 
  Alert, 
  Badge, 
  Modal,
  ListGroup,
  Accordion,
  ProgressBar
} from 'react-bootstrap';
import { 
  FaHome, 
  FaPlus, 
  FaEdit, 
  FaTrash, 
  FaClock, 
  FaRobot,
  FaCheckCircle,
  FaTimesCircle,
  FaExclamationTriangle,
  FaCog,
  FaCalendarAlt,
  FaMapMarkerAlt
} from 'react-icons/fa';

export const ZoneConfigurationSection = ({ 
  config, 
  onChange, 
  errors = {}, 
  warnings = {}, 
  canEdit, 
  securityStatus 
}) => {
  const [showZoneModal, setShowZoneModal] = useState(false);
  const [editingZone, setEditingZone] = useState(null);
  const [newZone, setNewZone] = useState({
    name: '',
    description: '',
    area: '',
    automation_enabled: true,
    schedule: {
      enabled: false,
      start_time: '09:00',
      end_time: '17:00',
      days: []
    },
    devices: [],
    ai_optimization: {
      enabled: true,
      learning_mode: 'adaptive',
      priority: 'balanced'
    },
    triggers: []
  });

  // Ensure config is an array
  const zones = Array.isArray(config) ? config : [];

  // Handle zone creation/editing
  const handleZoneSubmit = () => {
    if (editingZone !== null) {
      // Update existing zone
      const updatedZones = [...zones];
      updatedZones[editingZone] = { ...newZone, id: zones[editingZone].id };
      onChange(updatedZones);
    } else {
      // Create new zone
      const zoneWithId = {
        ...newZone,
        id: `zone_${Date.now()}`,
        created_at: new Date().toISOString(),
        status: 'active'
      };
      onChange([...zones, zoneWithId]);
    }
    
    resetModal();
  };

  // Reset modal state
  const resetModal = () => {
    setShowZoneModal(false);
    setEditingZone(null);
    setNewZone({
      name: '',
      description: '',
      area: '',
      automation_enabled: true,
      schedule: {
        enabled: false,
        start_time: '09:00',
        end_time: '17:00',
        days: []
      },
      devices: [],
      ai_optimization: {
        enabled: true,
        learning_mode: 'adaptive',
        priority: 'balanced'
      },
      triggers: []
    });
  };

  // Edit zone
  const editZone = (index) => {
    setEditingZone(index);
    setNewZone({ ...zones[index] });
    setShowZoneModal(true);
  };

  // Delete zone
  const deleteZone = (index) => {
    if (window.confirm('Are you sure you want to delete this zone?')) {
      const updatedZones = zones.filter((_, i) => i !== index);
      onChange(updatedZones);
    }
  };

  // Handle schedule day toggle
  const toggleScheduleDay = (day) => {
    const days = newZone.schedule.days.includes(day)
      ? newZone.schedule.days.filter(d => d !== day)
      : [...newZone.schedule.days, day];
    
    setNewZone({
      ...newZone,
      schedule: { ...newZone.schedule, days }
    });
  };

  // Add trigger
  const addTrigger = () => {
    const triggers = [
      ...newZone.triggers,
      {
        id: `trigger_${Date.now()}`,
        type: 'device_state',
        condition: '',
        action: 'start_cleaning'
      }
    ];
    setNewZone({ ...newZone, triggers });
  };

  // Remove trigger
  const removeTrigger = (triggerId) => {
    const triggers = newZone.triggers.filter(t => t.id !== triggerId);
    setNewZone({ ...newZone, triggers });
  };

  // Get zone status color
  const getZoneStatusColor = (zone) => {
    if (zone.status === 'active') return 'success';
    if (zone.status === 'inactive') return 'secondary';
    if (zone.status === 'error') return 'danger';
    return 'warning';
  };

  // Get zone efficiency score
  const getZoneEfficiency = (zone) => {
    let score = 70; // Base score
    
    if (zone.automation_enabled) score += 10;
    if (zone.schedule?.enabled) score += 10;
    if (zone.ai_optimization?.enabled) score += 10;
    if (zone.devices?.length > 0) score += 5;
    if (zone.triggers?.length > 0) score += 5;
    
    return Math.min(score, 100);
  };

  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  return (
    <div className="zone-configuration-section">
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <h5>
                <FaHome className="me-2" />
                Zone Configuration
              </h5>
              <p className="text-muted mb-0">
                Configure cleaning zones and automation rules
              </p>
            </div>
            
            <Button 
              variant="primary" 
              onClick={() => setShowZoneModal(true)}
              disabled={!canEdit}
            >
              <FaPlus className="me-2" />
              Add Zone
            </Button>
          </div>
        </Col>
      </Row>

      {/* Zone Summary */}
      <Row className="mb-4">
        <Col md={3}>
          <Card className="text-center">
            <Card.Body>
              <h4 className="text-primary">{zones.length}</h4>
              <small className="text-muted">Total Zones</small>
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card className="text-center">
            <Card.Body>
              <h4 className="text-success">{zones.filter(z => z.status === 'active').length}</h4>
              <small className="text-muted">Active Zones</small>
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card className="text-center">
            <Card.Body>
              <h4 className="text-info">{zones.filter(z => z.automation_enabled).length}</h4>
              <small className="text-muted">Automated</small>
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card className="text-center">
            <Card.Body>
              <h4 className="text-warning">{zones.filter(z => z.schedule?.enabled).length}</h4>
              <small className="text-muted">Scheduled</small>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Zones List */}
      {zones.length === 0 ? (
        <Card>
          <Card.Body className="text-center py-5">
            <FaHome className="text-muted mb-3" style={{ fontSize: '3rem', opacity: 0.3 }} />
            <h5 className="text-muted">No zones configured</h5>
            <p className="text-muted mb-3">Create your first zone to start automating your cleaning</p>
            <Button 
              variant="outline-primary" 
              onClick={() => setShowZoneModal(true)}
              disabled={!canEdit}
            >
              <FaPlus className="me-2" />
              Create First Zone
            </Button>
          </Card.Body>
        </Card>
      ) : (
        <Accordion>
          {zones.map((zone, index) => (
            <Accordion.Item key={zone.id || index} eventKey={index.toString()}>
              <Accordion.Header>
                <div className="d-flex justify-content-between align-items-center w-100 me-3">
                  <div className="d-flex align-items-center">
                    <FaMapMarkerAlt className="me-2" />
                    <strong>{zone.name}</strong>
                    <Badge bg={getZoneStatusColor(zone)} className="ms-2">
                      {zone.status || 'active'}
                    </Badge>
                  </div>
                  
                  <div className="d-flex align-items-center gap-2">
                    <small className="text-muted">
                      Efficiency: {getZoneEfficiency(zone)}%
                    </small>
                    <ProgressBar 
                      now={getZoneEfficiency(zone)} 
                      style={{ width: '60px', height: '6px' }}
                      variant={getZoneEfficiency(zone) >= 80 ? 'success' : 
                              getZoneEfficiency(zone) >= 60 ? 'warning' : 'danger'}
                    />
                  </div>
                </div>
              </Accordion.Header>
              <Accordion.Body>
                <Row>
                  <Col md={8}>
                    <div className="mb-3">
                      <strong>Description:</strong> {zone.description || 'No description'}
                    </div>
                    <div className="mb-3">
                      <strong>Area:</strong> {zone.area || 'Not specified'}
                    </div>
                    
                    {/* Zone Settings */}
                    <Row className="mb-3">
                      <Col md={6}>
                        <div className="d-flex align-items-center mb-2">
                          {zone.automation_enabled ? (
                            <FaCheckCircle className="text-success me-2" />
                          ) : (
                            <FaTimesCircle className="text-muted me-2" />
                          )}
                          <span>Automation {zone.automation_enabled ? 'Enabled' : 'Disabled'}</span>
                        </div>
                        
                        <div className="d-flex align-items-center mb-2">
                          {zone.schedule?.enabled ? (
                            <FaCheckCircle className="text-success me-2" />
                          ) : (
                            <FaTimesCircle className="text-muted me-2" />
                          )}
                          <span>Schedule {zone.schedule?.enabled ? 'Active' : 'Inactive'}</span>
                        </div>
                      </Col>
                      
                      <Col md={6}>
                        <div className="d-flex align-items-center mb-2">
                          {zone.ai_optimization?.enabled ? (
                            <FaRobot className="text-info me-2" />
                          ) : (
                            <FaRobot className="text-muted me-2" />
                          )}
                          <span>AI Optimization {zone.ai_optimization?.enabled ? 'On' : 'Off'}</span>
                        </div>
                        
                        <div className="d-flex align-items-center mb-2">
                          <FaCog className="text-secondary me-2" />
                          <span>{zone.devices?.length || 0} Device(s)</span>
                        </div>
                      </Col>
                    </Row>

                    {/* Schedule Info */}
                    {zone.schedule?.enabled && (
                      <Alert variant="info" className="mb-3">
                        <FaCalendarAlt className="me-2" />
                        <strong>Schedule:</strong> {zone.schedule.start_time} - {zone.schedule.end_time}
                        {zone.schedule.days?.length > 0 && (
                          <span> on {zone.schedule.days.join(', ')}</span>
                        )}
                      </Alert>
                    )}

                    {/* Triggers */}
                    {zone.triggers?.length > 0 && (
                      <div className="mb-3">
                        <strong>Triggers:</strong>
                        <ListGroup variant="flush" className="mt-2">
                          {zone.triggers.map((trigger, triggerIndex) => (
                            <ListGroup.Item key={trigger.id || triggerIndex} className="px-0 py-2">
                              <Badge bg="secondary" className="me-2">{trigger.type}</Badge>
                              {trigger.condition} → {trigger.action}
                            </ListGroup.Item>
                          ))}
                        </ListGroup>
                      </div>
                    )}
                  </Col>
                  
                  <Col md={4}>
                    <div className="d-grid gap-2">
                      <Button
                        variant="outline-primary"
                        size="sm"
                        onClick={() => editZone(index)}
                        disabled={!canEdit}
                      >
                        <FaEdit className="me-2" />
                        Edit Zone
                      </Button>
                      
                      <Button
                        variant="outline-danger"
                        size="sm"
                        onClick={() => deleteZone(index)}
                        disabled={!canEdit}
                      >
                        <FaTrash className="me-2" />
                        Delete Zone
                      </Button>
                    </div>
                  </Col>
                </Row>
              </Accordion.Body>
            </Accordion.Item>
          ))}
        </Accordion>
      )}

      {/* Zone Modal */}
      <Modal show={showZoneModal} onHide={resetModal} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>
            <FaHome className="me-2" />
            {editingZone !== null ? 'Edit Zone' : 'Create New Zone'}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            {/* Basic Info */}
            <Row className="mb-3">
              <Col md={6}>
                <Form.Group>
                  <Form.Label>Zone Name *</Form.Label>
                  <Form.Control
                    type="text"
                    value={newZone.name}
                    onChange={(e) => setNewZone({ ...newZone, name: e.target.value })}
                    placeholder="e.g., Living Room"
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group>
                  <Form.Label>Area</Form.Label>
                  <Form.Control
                    type="text"
                    value={newZone.area}
                    onChange={(e) => setNewZone({ ...newZone, area: e.target.value })}
                    placeholder="e.g., Ground Floor"
                  />
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-3">
              <Form.Label>Description</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={newZone.description}
                onChange={(e) => setNewZone({ ...newZone, description: e.target.value })}
                placeholder="Describe this zone and its cleaning requirements"
              />
            </Form.Group>

            {/* Automation Settings */}
            <Card className="mb-3">
              <Card.Header>
                <h6 className="mb-0">Automation Settings</h6>
              </Card.Header>
              <Card.Body>
                <Form.Check
                  type="switch"
                  label="Enable Automation"
                  checked={newZone.automation_enabled}
                  onChange={(e) => setNewZone({ ...newZone, automation_enabled: e.target.checked })}
                  className="mb-3"
                />

                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Learning Mode</Form.Label>
                      <Form.Select
                        value={newZone.ai_optimization?.learning_mode || 'adaptive'}
                        onChange={(e) => setNewZone({
                          ...newZone,
                          ai_optimization: {
                            ...newZone.ai_optimization,
                            learning_mode: e.target.value
                          }
                        })}
                      >
                        <option value="adaptive">Adaptive Learning</option>
                        <option value="manual">Manual Control</option>
                        <option value="scheduled">Scheduled Only</option>
                      </Form.Select>
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Priority</Form.Label>
                      <Form.Select
                        value={newZone.ai_optimization?.priority || 'balanced'}
                        onChange={(e) => setNewZone({
                          ...newZone,
                          ai_optimization: {
                            ...newZone.ai_optimization,
                            priority: e.target.value
                          }
                        })}
                      >
                        <option value="high">High Priority</option>
                        <option value="balanced">Balanced</option>
                        <option value="low">Low Priority</option>
                      </Form.Select>
                    </Form.Group>
                  </Col>
                </Row>
              </Card.Body>
            </Card>

            {/* Schedule Settings */}
            <Card className="mb-3">
              <Card.Header>
                <div className="d-flex justify-content-between align-items-center">
                  <h6 className="mb-0">Schedule Settings</h6>
                  <Form.Check
                    type="switch"
                    label="Enable Schedule"
                    checked={newZone.schedule?.enabled}
                    onChange={(e) => setNewZone({
                      ...newZone,
                      schedule: { ...newZone.schedule, enabled: e.target.checked }
                    })}
                  />
                </div>
              </Card.Header>
              {newZone.schedule?.enabled && (
                <Card.Body>
                  <Row className="mb-3">
                    <Col md={6}>
                      <Form.Group>
                        <Form.Label>Start Time</Form.Label>
                        <Form.Control
                          type="time"
                          value={newZone.schedule?.start_time || '09:00'}
                          onChange={(e) => setNewZone({
                            ...newZone,
                            schedule: { ...newZone.schedule, start_time: e.target.value }
                          })}
                        />
                      </Form.Group>
                    </Col>
                    <Col md={6}>
                      <Form.Group>
                        <Form.Label>End Time</Form.Label>
                        <Form.Control
                          type="time"
                          value={newZone.schedule?.end_time || '17:00'}
                          onChange={(e) => setNewZone({
                            ...newZone,
                            schedule: { ...newZone.schedule, end_time: e.target.value }
                          })}
                        />
                      </Form.Group>
                    </Col>
                  </Row>

                  <Form.Group>
                    <Form.Label>Active Days</Form.Label>
                    <div className="d-flex flex-wrap gap-2 mt-2">
                      {daysOfWeek.map(day => (
                        <Form.Check
                          key={day}
                          type="checkbox"
                          label={day.substring(0, 3)}
                          checked={newZone.schedule?.days?.includes(day) || false}
                          onChange={() => toggleScheduleDay(day)}
                          className="me-2"
                        />
                      ))}
                    </div>
                  </Form.Group>
                </Card.Body>
              )}
            </Card>

            {/* Triggers */}
            <Card>
              <Card.Header>
                <div className="d-flex justify-content-between align-items-center">
                  <h6 className="mb-0">Automation Triggers</h6>
                  <Button variant="outline-primary" size="sm" onClick={addTrigger}>
                    <FaPlus className="me-1" />
                    Add Trigger
                  </Button>
                </div>
              </Card.Header>
              <Card.Body>
                {newZone.triggers?.length === 0 ? (
                  <p className="text-muted text-center">No triggers configured</p>
                ) : (
                  <ListGroup variant="flush">
                    {newZone.triggers?.map((trigger, index) => (
                      <ListGroup.Item key={trigger.id} className="d-flex justify-content-between align-items-center px-0">
                        <div>
                          <Badge bg="secondary" className="me-2">{trigger.type}</Badge>
                          {trigger.condition} → {trigger.action}
                        </div>
                        <Button
                          variant="outline-danger"
                          size="sm"
                          onClick={() => removeTrigger(trigger.id)}
                        >
                          <FaTrash />
                        </Button>
                      </ListGroup.Item>
                    ))}
                  </ListGroup>
                )}
              </Card.Body>
            </Card>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={resetModal}>
            Cancel
          </Button>
          <Button 
            variant="primary" 
            onClick={handleZoneSubmit}
            disabled={!newZone.name.trim()}
          >
            {editingZone !== null ? 'Update Zone' : 'Create Zone'}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default ZoneConfigurationSection;