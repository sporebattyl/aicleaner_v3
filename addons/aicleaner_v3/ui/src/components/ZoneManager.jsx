
import React, { useState, useEffect } from 'react';
import { Card, Button, Form, Badge, Alert, Modal, Row, Col } from 'react-bootstrap';
import ApiService from '../services/ApiService';

export const ZoneManager = () => {
    const [zones, setZones] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [editingZone, setEditingZone] = useState(null);
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        devices: [],
        schedule: {
            enabled: false,
            start_time: '09:00',
            end_time: '17:00',
            days: []
        }
    });

    useEffect(() => {
        loadZones();
    }, []);

    const loadZones = async () => {
        try {
            const data = await ApiService.getZones();
            setZones(data);
        } catch (err) {
            setError('Failed to load zones');
        } finally {
            setLoading(false);
        }
    };

    const openZoneModal = (zone = null) => {
        setEditingZone(zone);
        setFormData(zone || {
            name: '',
            description: '',
            devices: [],
            schedule: {
                enabled: false,
                start_time: '09:00',
                end_time: '17:00',
                days: []
            }
        });
        setShowModal(true);
    };

    const handleSaveZone = async () => {
        try {
            if (editingZone) {
                await ApiService.updateZone(editingZone.id, formData);
            } else {
                await ApiService.createZone(formData);
            }
            setShowModal(false);
            await loadZones();
        } catch (err) {
            setError('Failed to save zone');
        }
    };

    const handleDeleteZone = async (zoneId) => {
        if (window.confirm('Are you sure you want to delete this zone?')) {
            try {
                await ApiService.deleteZone(zoneId);
                await loadZones();
            } catch (err) {
                setError('Failed to delete zone');
            }
        }
    };

    const toggleZone = async (zoneId, active) => {
        try {
            await ApiService.toggleZone(zoneId, active);
            await loadZones();
        } catch (err) {
            setError('Failed to toggle zone');
        }
    };

    return (
        <div>
            <Card>
                <Card.Header className="d-flex justify-content-between align-items-center">
                    <h4>Zone Management</h4>
                    <Button variant="primary" onClick={() => openZoneModal()}>
                        Create Zone
                    </Button>
                </Card.Header>
                <Card.Body>
                    {error && <Alert variant="danger">{error}</Alert>}
                    
                    <Row>
                        {zones.map(zone => (
                            <Col md={6} lg={4} key={zone.id} className="mb-3">
                                <Card>
                                    <Card.Body>
                                        <div className="d-flex justify-content-between align-items-start mb-2">
                                            <h6>{zone.name}</h6>
                                            <Badge bg={zone.active ? 'success' : 'secondary'}>
                                                {zone.active ? 'Active' : 'Inactive'}
                                            </Badge>
                                        </div>
                                        <p className="text-muted small">{zone.description}</p>
                                        <p className="small">
                                            <strong>Devices:</strong> {zone.devices?.length || 0}
                                        </p>
                                        {zone.schedule?.enabled && (
                                            <p className="small">
                                                <strong>Schedule:</strong> {zone.schedule.start_time} - {zone.schedule.end_time}
                                            </p>
                                        )}
                                        <div className="d-flex gap-1">
                                            <Button 
                                                variant={zone.active ? 'outline-danger' : 'outline-success'}
                                                size="sm"
                                                onClick={() => toggleZone(zone.id, !zone.active)}
                                            >
                                                {zone.active ? 'Deactivate' : 'Activate'}
                                            </Button>
                                            <Button 
                                                variant="outline-primary" 
                                                size="sm"
                                                onClick={() => openZoneModal(zone)}
                                            >
                                                Edit
                                            </Button>
                                            <Button 
                                                variant="outline-danger" 
                                                size="sm"
                                                onClick={() => handleDeleteZone(zone.id)}
                                            >
                                                Delete
                                            </Button>
                                        </div>
                                    </Card.Body>
                                </Card>
                            </Col>
                        ))}
                    </Row>
                </Card.Body>
            </Card>

            {/* Zone Edit/Create Modal */}
            <Modal show={showModal} onHide={() => setShowModal(false)} size="lg">
                <Modal.Header closeButton>
                    <Modal.Title>{editingZone ? 'Edit Zone' : 'Create Zone'}</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <Form>
                        <Form.Group className="mb-3">
                            <Form.Label>Zone Name</Form.Label>
                            <Form.Control
                                type="text"
                                value={formData.name}
                                onChange={(e) => setFormData({...formData, name: e.target.value})}
                                placeholder="Enter zone name"
                            />
                        </Form.Group>
                        
                        <Form.Group className="mb-3">
                            <Form.Label>Description</Form.Label>
                            <Form.Control
                                as="textarea"
                                value={formData.description}
                                onChange={(e) => setFormData({...formData, description: e.target.value})}
                                placeholder="Enter zone description"
                            />
                        </Form.Group>
                        
                        <Form.Group className="mb-3">
                            <Form.Check
                                type="checkbox"
                                label="Enable Schedule"
                                checked={formData.schedule?.enabled || false}
                                onChange={(e) => setFormData({
                                    ...formData, 
                                    schedule: {...formData.schedule, enabled: e.target.checked}
                                })}
                            />
                        </Form.Group>
                        
                        {formData.schedule?.enabled && (
                            <Row className="mb-3">
                                <Col md={6}>
                                    <Form.Label>Start Time</Form.Label>
                                    <Form.Control
                                        type="time"
                                        value={formData.schedule.start_time}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            schedule: {...formData.schedule, start_time: e.target.value}
                                        })}
                                    />
                                </Col>
                                <Col md={6}>
                                    <Form.Label>End Time</Form.Label>
                                    <Form.Control
                                        type="time"
                                        value={formData.schedule.end_time}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            schedule: {...formData.schedule, end_time: e.target.value}
                                        })}
                                    />
                                </Col>
                            </Row>
                        )}
                    </Form>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => setShowModal(false)}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={handleSaveZone}>
                        {editingZone ? 'Update Zone' : 'Create Zone'}
                    </Button>
                </Modal.Footer>
            </Modal>
        </div>
    );
};
