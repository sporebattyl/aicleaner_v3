import React, { useState, useEffect } from 'react';
import { Card, Form, Button, Alert, Spinner, Nav, Tab, Badge, Collapse } from 'react-bootstrap';
import { ChevronRight, ChevronDown, Settings, Code, Terminal } from 'react-bootstrap-icons';
import ApiService from '../services/ApiService';

const TieredConfigurationPanel = () => {
    const [activeTab, setActiveTab] = useState('ui_basic');
    const [configs, setConfigs] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);
    const [showAdvanced, setShowAdvanced] = useState({});

    const tiers = {
        ui_basic: {
            title: 'Basic Settings',
            icon: <Settings size={16} />,
            description: 'Essential settings for getting started',
            badge: 'Recommended',
            badgeVariant: 'success'
        },
        yaml_advanced: {
            title: 'Advanced YAML',
            icon: <Code size={16} />,
            description: 'Full configuration flexibility',
            badge: 'Power User',
            badgeVariant: 'warning'
        },
        api_programmatic: {
            title: 'API Access',
            icon: <Terminal size={16} />,
            description: 'Script and automation interface',
            badge: 'Developer',
            badgeVariant: 'info'
        }
    };

    useEffect(() => {
        loadConfigurations();
    }, []);

    const loadConfigurations = async () => {
        try {
            setLoading(true);
            const data = await Promise.all([
                ApiService.getTieredConfig('ui_basic'),
                ApiService.getTieredConfig('yaml_advanced'),
                ApiService.getTieredConfig('api_programmatic')
            ]);
            
            setConfigs({
                ui_basic: data[0],
                yaml_advanced: data[1],
                api_programmatic: data[2]
            });
            setError(null);
        } catch (err) {
            setError('Failed to load configurations');
        } finally {
            setLoading(false);
        }
    };

    const saveConfiguration = async (tier) => {
        try {
            setSaving(true);
            await ApiService.updateTieredConfig(tier, configs[tier]);
            setSuccess(true);
            setTimeout(() => setSuccess(false), 3000);
            // Reload to get updated merged config
            await loadConfigurations();
        } catch (err) {
            setError(`Failed to save ${tier} configuration`);
        } finally {
            setSaving(false);
        }
    };

    const handleInputChange = (tier, section, key, value) => {
        setConfigs(prev => ({
            ...prev,
            [tier]: {
                ...prev[tier],
                [section]: {
                    ...prev[tier]?.[section],
                    [key]: value
                }
            }
        }));
    };

    const toggleAdvanced = (section) => {
        setShowAdvanced(prev => ({
            ...prev,
            [section]: !prev[section]
        }));
    };

    const renderBasicConfig = () => {
        const config = configs.ui_basic || {};
        
        return (
            <div>
                {/* AI Provider Settings */}
                <Card className="mb-3">
                    <Card.Header className="d-flex justify-content-between align-items-center">
                        <span>AI Provider</span>
                        <Badge bg="primary">Required</Badge>
                    </Card.Header>
                    <Card.Body>
                        <Form.Group className="mb-3">
                            <Form.Label>Primary Provider</Form.Label>
                            <Form.Select 
                                value={config.ai?.primary_provider || ''}
                                onChange={(e) => handleInputChange('ui_basic', 'ai', 'primary_provider', e.target.value)}
                            >
                                <option value="">Select Provider</option>
                                <option value="openai">OpenAI (GPT-4o)</option>
                                <option value="anthropic">Anthropic (Claude)</option>
                                <option value="google">Google (Gemini)</option>
                                <option value="ollama">Ollama (Local)</option>
                            </Form.Select>
                            <Form.Text className="text-muted">
                                Choose your primary AI provider for cleaning analysis
                            </Form.Text>
                        </Form.Group>
                        
                        <Form.Group className="mb-3">
                            <Form.Label>API Key</Form.Label>
                            <Form.Control
                                type="password"
                                value={config.ai?.api_key || ''}
                                onChange={(e) => handleInputChange('ui_basic', 'ai', 'api_key', e.target.value)}
                                placeholder="Enter your API key"
                            />
                            <Form.Text className="text-muted">
                                Get your API key from your provider's dashboard
                            </Form.Text>
                        </Form.Group>

                        <Button 
                            variant="outline-secondary" 
                            size="sm" 
                            onClick={() => toggleAdvanced('ai')}
                            className="d-flex align-items-center"
                        >
                            {showAdvanced.ai ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                            <span className="ms-1">Advanced AI Settings</span>
                        </Button>
                        
                        <Collapse in={showAdvanced.ai}>
                            <div className="mt-3">
                                <Form.Group className="mb-3">
                                    <Form.Label>Model Selection</Form.Label>
                                    <Form.Select 
                                        value={config.ai?.model || ''}
                                        onChange={(e) => handleInputChange('ui_basic', 'ai', 'model', e.target.value)}
                                    >
                                        <option value="gpt-4o">GPT-4o (Recommended)</option>
                                        <option value="gpt-4">GPT-4</option>
                                        <option value="claude-3.5-sonnet">Claude 3.5 Sonnet</option>
                                        <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                                    </Form.Select>
                                </Form.Group>
                                
                                <Form.Group className="mb-3">
                                    <Form.Label>Timeout (seconds)</Form.Label>
                                    <Form.Control
                                        type="number"
                                        value={config.ai?.timeout || 30}
                                        onChange={(e) => handleInputChange('ui_basic', 'ai', 'timeout', parseInt(e.target.value))}
                                        min="10"
                                        max="120"
                                    />
                                </Form.Group>
                            </div>
                        </Collapse>
                    </Card.Body>
                </Card>

                {/* MQTT Settings */}
                <Card className="mb-3">
                    <Card.Header className="d-flex justify-content-between align-items-center">
                        <span>MQTT Connection</span>
                        <Badge bg="secondary">Optional</Badge>
                    </Card.Header>
                    <Card.Body>
                        <Form.Group className="mb-3">
                            <Form.Label>Broker Host</Form.Label>
                            <Form.Control
                                type="text"
                                value={config.mqtt?.broker_host || ''}
                                onChange={(e) => handleInputChange('ui_basic', 'mqtt', 'broker_host', e.target.value)}
                                placeholder="localhost or IP address"
                            />
                        </Form.Group>
                        
                        <Form.Group className="mb-3">
                            <Form.Label>Broker Port</Form.Label>
                            <Form.Control
                                type="number"
                                value={config.mqtt?.broker_port || 1883}
                                onChange={(e) => handleInputChange('ui_basic', 'mqtt', 'broker_port', parseInt(e.target.value))}
                                min="1"
                                max="65535"
                            />
                        </Form.Group>
                        
                        <Form.Check
                            type="checkbox"
                            label="Use TLS Encryption"
                            checked={config.mqtt?.use_tls || false}
                            onChange={(e) => handleInputChange('ui_basic', 'mqtt', 'use_tls', e.target.checked)}
                        />
                    </Card.Body>
                </Card>

                {/* Notifications */}
                <Card className="mb-3">
                    <Card.Header>Notifications</Card.Header>
                    <Card.Body>
                        <Form.Check
                            type="checkbox"
                            label="Enable Notifications"
                            checked={config.notifications?.enabled || false}
                            onChange={(e) => handleInputChange('ui_basic', 'notifications', 'enabled', e.target.checked)}
                            className="mb-3"
                        />
                        
                        {config.notifications?.enabled && (
                            <Form.Group className="mb-3">
                                <Form.Label>Notification Service</Form.Label>
                                <Form.Control
                                    type="text"
                                    value={config.notifications?.service || ''}
                                    onChange={(e) => handleInputChange('ui_basic', 'notifications', 'service', e.target.value)}
                                    placeholder="notify.mobile_app"
                                />
                                <Form.Text className="text-muted">
                                    Home Assistant notification service entity
                                </Form.Text>
                            </Form.Group>
                        )}
                    </Card.Body>
                </Card>
            </div>
        );
    };

    const renderAdvancedConfig = () => {
        const config = configs.yaml_advanced || {};
        
        return (
            <div>
                <Alert variant="info" className="mb-3">
                    <strong>Advanced Configuration</strong><br/>
                    Full YAML editing with complete control over all AICleaner settings.
                    Changes here override basic settings.
                </Alert>
                
                {/* Security Settings */}
                <Card className="mb-3">
                    <Card.Header>Security & Privacy</Card.Header>
                    <Card.Body>
                        <Form.Group className="mb-3">
                            <Form.Label>Privacy Level</Form.Label>
                            <Form.Select 
                                value={config.security?.privacy_level || 'balanced'}
                                onChange={(e) => handleInputChange('yaml_advanced', 'security', 'privacy_level', e.target.value)}
                            >
                                <option value="speed">Speed (Minimal privacy, faster processing)</option>
                                <option value="balanced">Balanced (Good privacy with performance)</option>
                                <option value="paranoid">Paranoid (Maximum privacy, slower processing)</option>
                            </Form.Select>
                        </Form.Group>
                        
                        <Form.Group className="mb-3">
                            <Form.Label>Data Retention (days)</Form.Label>
                            <Form.Control
                                type="number"
                                value={config.security?.data_retention_days || 90}
                                onChange={(e) => handleInputChange('yaml_advanced', 'security', 'data_retention_days', parseInt(e.target.value))}
                                min="1"
                                max="365"
                            />
                        </Form.Group>
                        
                        <Form.Check
                            type="checkbox"
                            label="Encrypt Configuration Files"
                            checked={config.security?.encrypt_config || false}
                            onChange={(e) => handleInputChange('yaml_advanced', 'security', 'encrypt_config', e.target.checked)}
                        />
                    </Card.Body>
                </Card>

                {/* Performance Settings */}
                <Card className="mb-3">
                    <Card.Header>Performance Tuning</Card.Header>
                    <Card.Body>
                        <Form.Group className="mb-3">
                            <Form.Label>Max Concurrent Tasks</Form.Label>
                            <Form.Control
                                type="number"
                                value={config.performance?.max_concurrent_tasks || 5}
                                onChange={(e) => handleInputChange('yaml_advanced', 'performance', 'max_concurrent_tasks', parseInt(e.target.value))}
                                min="1"
                                max="20"
                            />
                            <Form.Text className="text-muted">
                                Higher values increase throughput but use more resources
                            </Form.Text>
                        </Form.Group>
                        
                        <Form.Group className="mb-3">
                            <Form.Label>Cache Duration (seconds)</Form.Label>
                            <Form.Control
                                type="number"
                                value={config.performance?.cache_duration || 300}
                                onChange={(e) => handleInputChange('yaml_advanced', 'performance', 'cache_duration', parseInt(e.target.value))}
                                min="60"
                                max="3600"
                            />
                        </Form.Group>
                        
                        <Form.Check
                            type="checkbox"
                            label="Enable Performance Profiling"
                            checked={config.performance?.enable_profiling || false}
                            onChange={(e) => handleInputChange('yaml_advanced', 'performance', 'enable_profiling', e.target.checked)}
                        />
                    </Card.Body>
                </Card>

                {/* Raw YAML Editor */}
                <Card className="mb-3">
                    <Card.Header>
                        <div className="d-flex justify-content-between align-items-center">
                            <span>Raw YAML Configuration</span>
                            <Badge bg="warning">Expert Mode</Badge>
                        </div>
                    </Card.Header>
                    <Card.Body>
                        <Form.Group>
                            <Form.Control
                                as="textarea"
                                rows={10}
                                value={JSON.stringify(config, null, 2)}
                                onChange={(e) => {
                                    try {
                                        const parsed = JSON.parse(e.target.value);
                                        setConfigs(prev => ({ ...prev, yaml_advanced: parsed }));
                                    } catch (err) {
                                        // Handle JSON parse errors gracefully
                                    }
                                }}
                                style={{ fontFamily: 'monospace', fontSize: '12px' }}
                            />
                            <Form.Text className="text-muted">
                                Direct YAML editing. Use with caution - invalid YAML will prevent startup.
                            </Form.Text>
                        </Form.Group>
                    </Card.Body>
                </Card>
            </div>
        );
    };

    const renderApiConfig = () => {
        const config = configs.api_programmatic || {};
        
        return (
            <div>
                <Alert variant="warning" className="mb-3">
                    <strong>Developer Mode</strong><br/>
                    API access for automation and scripting. Requires technical knowledge.
                </Alert>
                
                {/* API Settings */}
                <Card className="mb-3">
                    <Card.Header>REST API Configuration</Card.Header>
                    <Card.Body>
                        <Form.Check
                            type="checkbox"
                            label="Enable REST API"
                            checked={config.api?.enabled || false}
                            onChange={(e) => handleInputChange('api_programmatic', 'api', 'enabled', e.target.checked)}
                            className="mb-3"
                        />
                        
                        {config.api?.enabled && (
                            <>
                                <Form.Group className="mb-3">
                                    <Form.Label>Rate Limit (requests/minute)</Form.Label>
                                    <Form.Control
                                        type="number"
                                        value={config.api?.rate_limit || 100}
                                        onChange={(e) => handleInputChange('api_programmatic', 'api', 'rate_limit', parseInt(e.target.value))}
                                        min="1"
                                        max="1000"
                                    />
                                </Form.Group>
                                
                                <Form.Check
                                    type="checkbox"
                                    label="Require Authentication"
                                    checked={config.api?.require_auth || true}
                                    onChange={(e) => handleInputChange('api_programmatic', 'api', 'require_auth', e.target.checked)}
                                />
                            </>
                        )}
                    </Card.Body>
                </Card>

                {/* API Examples */}
                <Card className="mb-3">
                    <Card.Header>API Examples</Card.Header>
                    <Card.Body>
                        <h6>Get System Status:</h6>
                        <pre style={{ backgroundColor: '#f8f9fa', padding: '10px', fontSize: '12px' }}>
{`curl -X GET http://localhost:8080/api/status \\
  -H "Authorization: Bearer YOUR_TOKEN"`}
                        </pre>
                        
                        <h6 className="mt-3">Start Zone Cleaning:</h6>
                        <pre style={{ backgroundColor: '#f8f9fa', padding: '10px', fontSize: '12px' }}>
{`curl -X POST http://localhost:8080/api/zones/zone_1/clean \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"mode": "normal", "duration": 30}'`}
                        </pre>
                        
                        <h6 className="mt-3">Bulk Configuration Update:</h6>
                        <pre style={{ backgroundColor: '#f8f9fa', padding: '10px', fontSize: '12px' }}>
{`curl -X PUT http://localhost:8080/api/config \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d @config.json`}
                        </pre>
                    </Card.Body>
                </Card>
            </div>
        );
    };

    if (loading) {
        return (
            <Card>
                <Card.Body className="text-center">
                    <Spinner animation="border" />
                    <p>Loading tiered configuration...</p>
                </Card.Body>
            </Card>
        );
    }

    return (
        <Card>
            <Card.Header>
                <h4>AICleaner v3 Configuration</h4>
                <p className="mb-0 text-muted">
                    Progressive configuration system: choose your complexity level
                </p>
            </Card.Header>
            <Card.Body>
                {error && <Alert variant="danger">{error}</Alert>}
                {success && <Alert variant="success">Configuration saved successfully!</Alert>}
                
                <Tab.Container activeKey={activeTab} onSelect={setActiveTab}>
                    <Nav variant="pills" className="mb-4">
                        {Object.entries(tiers).map(([key, tier]) => (
                            <Nav.Item key={key}>
                                <Nav.Link eventKey={key} className="d-flex align-items-center">
                                    {tier.icon}
                                    <span className="ms-2">{tier.title}</span>
                                    <Badge bg={tier.badgeVariant} className="ms-2">
                                        {tier.badge}
                                    </Badge>
                                </Nav.Link>
                            </Nav.Item>
                        ))}
                    </Nav>
                    
                    <Tab.Content>
                        <Tab.Pane eventKey="ui_basic">
                            <div className="mb-3">
                                <h5>Basic Settings</h5>
                                <p className="text-muted">
                                    Essential settings for getting started. Perfect for first-time setup.
                                </p>
                            </div>
                            {renderBasicConfig()}
                        </Tab.Pane>
                        
                        <Tab.Pane eventKey="yaml_advanced">
                            <div className="mb-3">
                                <h5>Advanced YAML Configuration</h5>
                                <p className="text-muted">
                                    Full configuration flexibility with performance tuning and security options.
                                </p>
                            </div>
                            {renderAdvancedConfig()}
                        </Tab.Pane>
                        
                        <Tab.Pane eventKey="api_programmatic">
                            <div className="mb-3">
                                <h5>API & Automation</h5>
                                <p className="text-muted">
                                    Script and automation interface for bulk operations and integration.
                                </p>
                            </div>
                            {renderApiConfig()}
                        </Tab.Pane>
                    </Tab.Content>
                </Tab.Container>

                <div className="d-grid">
                    <Button 
                        variant="primary" 
                        onClick={() => saveConfiguration(activeTab)}
                        disabled={saving}
                        size="lg"
                    >
                        {saving ? (
                            <>
                                <Spinner as="span" animation="border" size="sm" className="me-2" />
                                Saving {tiers[activeTab].title}...
                            </>
                        ) : (
                            `Save ${tiers[activeTab].title}`
                        )}
                    </Button>
                </div>
            </Card.Body>
        </Card>
    );
};

export default TieredConfigurationPanel;