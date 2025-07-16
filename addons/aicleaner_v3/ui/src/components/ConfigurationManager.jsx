
import React, { useState, useEffect } from 'react';
import { Card, Form, Button, Alert, Spinner } from 'react-bootstrap';
import { ApiService } from '../services/ApiService';

export const ConfigurationManager = () => {
    const [config, setConfig] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);

    useEffect(() => {
        loadConfiguration();
    }, []);

    const loadConfiguration = async () => {
        try {
            setLoading(true);
            const data = await ApiService.getConfiguration();
            setConfig(data);
            setError(null);
        } catch (err) {
            setError('Failed to load configuration');
        } finally {
            setLoading(false);
        }
    };

    const saveConfiguration = async () => {
        try {
            setSaving(true);
            await ApiService.updateConfiguration(config);
            setSuccess(true);
            setTimeout(() => setSuccess(false), 3000);
        } catch (err) {
            setError('Failed to save configuration');
        } finally {
            setSaving(false);
        }
    };

    const handleInputChange = (section, key, value) => {
        setConfig(prev => ({
            ...prev,
            [section]: {
                ...prev[section],
                [key]: value
            }
        }));
    };

    if (loading) {
        return (
            <Card>
                <Card.Body className="text-center">
                    <Spinner animation="border" />
                    <p>Loading configuration...</p>
                </Card.Body>
            </Card>
        );
    }

    return (
        <Card>
            <Card.Header>
                <h4>AICleaner v3 Configuration</h4>
            </Card.Header>
            <Card.Body>
                {error && <Alert variant="danger">{error}</Alert>}
                {success && <Alert variant="success">Configuration saved successfully!</Alert>}
                
                <Form>
                    {/* AI Provider Configuration */}
                    <Card className="mb-3">
                        <Card.Header>AI Provider Settings</Card.Header>
                        <Card.Body>
                            <Form.Group className="mb-3">
                                <Form.Label>Primary Provider</Form.Label>
                                <Form.Select 
                                    value={config.ai?.primary_provider || ''}
                                    onChange={(e) => handleInputChange('ai', 'primary_provider', e.target.value)}
                                >
                                    <option value="openai">OpenAI</option>
                                    <option value="anthropic">Anthropic</option>
                                    <option value="google">Google</option>
                                    <option value="ollama">Ollama</option>
                                </Form.Select>
                            </Form.Group>
                            
                            <Form.Group className="mb-3">
                                <Form.Label>API Key</Form.Label>
                                <Form.Control
                                    type="password"
                                    value={config.ai?.api_key || ''}
                                    onChange={(e) => handleInputChange('ai', 'api_key', e.target.value)}
                                    placeholder="Enter API key"
                                />
                            </Form.Group>
                        </Card.Body>
                    </Card>

                    {/* MQTT Configuration */}
                    <Card className="mb-3">
                        <Card.Header>MQTT Settings</Card.Header>
                        <Card.Body>
                            <Form.Group className="mb-3">
                                <Form.Label>Broker Host</Form.Label>
                                <Form.Control
                                    type="text"
                                    value={config.mqtt?.broker_host || ''}
                                    onChange={(e) => handleInputChange('mqtt', 'broker_host', e.target.value)}
                                    placeholder="localhost"
                                />
                            </Form.Group>
                            
                            <Form.Group className="mb-3">
                                <Form.Label>Broker Port</Form.Label>
                                <Form.Control
                                    type="number"
                                    value={config.mqtt?.broker_port || 1883}
                                    onChange={(e) => handleInputChange('mqtt', 'broker_port', parseInt(e.target.value))}
                                />
                            </Form.Group>
                            
                            <Form.Check
                                type="checkbox"
                                label="Use TLS Encryption"
                                checked={config.mqtt?.use_tls || false}
                                onChange={(e) => handleInputChange('mqtt', 'use_tls', e.target.checked)}
                            />
                        </Card.Body>
                    </Card>

                    <div className="d-grid">
                        <Button 
                            variant="primary" 
                            onClick={saveConfiguration}
                            disabled={saving}
                        >
                            {saving ? (
                                <>
                                    <Spinner as="span" animation="border" size="sm" className="me-2" />
                                    Saving...
                                </>
                            ) : (
                                'Save Configuration'
                            )}
                        </Button>
                    </div>
                </Form>
            </Card.Body>
        </Card>
    );
};
