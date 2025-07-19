
import React, { useState, useEffect } from 'react';
import { Card, Button, Form, Badge, Alert, Modal } from 'react-bootstrap';
import ApiService from '../services/ApiService';

export const DeviceController = () => {
    const [devices, setDevices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [selectedDevice, setSelectedDevice] = useState(null);

    useEffect(() => {
        loadDevices();
    }, []);

    const loadDevices = async () => {
        try {
            const data = await ApiService.getDevices();
            setDevices(data);
        } catch (err) {
            setError('Failed to load devices');
        } finally {
            setLoading(false);
        }
    };

    const handleDeviceAction = async (deviceId, action) => {
        try {
            await ApiService.controlDevice(deviceId, action);
            await loadDevices(); // Refresh device list
        } catch (err) {
            setError(`Failed to ${action} device`);
        }
    };

    const openDeviceModal = (device) => {
        setSelectedDevice(device);
        setShowModal(true);
    };

    return (
        <div>
            <Card>
                <Card.Header>
                    <h4>Device Control Panel</h4>
                </Card.Header>
                <Card.Body>
                    {error && <Alert variant="danger">{error}</Alert>}
                    
                    {devices.map(device => (
                        <Card key={device.id} className="mb-3">
                            <Card.Body>
                                <div className="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h5>{device.name}</h5>
                                        <p className="text-muted">{device.type}</p>
                                        <Badge bg={device.online ? 'success' : 'secondary'}>
                                            {device.online ? 'Online' : 'Offline'}
                                        </Badge>
                                    </div>
                                    <div>
                                        <Button 
                                            variant="outline-primary" 
                                            size="sm" 
                                            className="me-2"
                                            onClick={() => openDeviceModal(device)}
                                        >
                                            Details
                                        </Button>
                                        {device.controllable && (
                                            <>
                                                <Button 
                                                    variant="success" 
                                                    size="sm" 
                                                    className="me-2"
                                                    onClick={() => handleDeviceAction(device.id, 'start')}
                                                    disabled={!device.online}
                                                >
                                                    Start
                                                </Button>
                                                <Button 
                                                    variant="danger" 
                                                    size="sm"
                                                    onClick={() => handleDeviceAction(device.id, 'stop')}
                                                    disabled={!device.online}
                                                >
                                                    Stop
                                                </Button>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </Card.Body>
                        </Card>
                    ))}
                </Card.Body>
            </Card>

            {/* Device Details Modal */}
            <Modal show={showModal} onHide={() => setShowModal(false)} size="lg">
                <Modal.Header closeButton>
                    <Modal.Title>{selectedDevice?.name} Details</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    {selectedDevice && (
                        <div>
                            <p><strong>Type:</strong> {selectedDevice.type}</p>
                            <p><strong>Status:</strong> {selectedDevice.online ? 'Online' : 'Offline'}</p>
                            <p><strong>Last Seen:</strong> {selectedDevice.last_seen}</p>
                            <p><strong>Capabilities:</strong> {selectedDevice.capabilities?.join(', ')}</p>
                            {selectedDevice.properties && (
                                <div>
                                    <h6>Properties:</h6>
                                    <pre>{JSON.stringify(selectedDevice.properties, null, 2)}</pre>
                                </div>
                            )}
                        </div>
                    )}
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => setShowModal(false)}>
                        Close
                    </Button>
                </Modal.Footer>
            </Modal>
        </div>
    );
};
