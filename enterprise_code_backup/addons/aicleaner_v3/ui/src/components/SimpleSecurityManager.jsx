import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Button, Alert, Badge, ListGroup, ProgressBar } from 'react-bootstrap';
import { Shield, ShieldCheck, ShieldX, Zap, BarChart, ShieldLock } from 'react-bootstrap-icons';
import ApiService from '../services/ApiService';

const SimpleSecurityManager = () => {
    const [securityStatus, setSecurityStatus] = useState(null);
    const [presets, setPresets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [applying, setApplying] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadSecurityData();
    }, []);

    const loadSecurityData = async () => {
        try {
            setLoading(true);
            const [status, presetList] = await Promise.all([
                ApiService.request('/security/status'),
                ApiService.request('/security/presets')
            ]);
            
            setSecurityStatus(status);
            setPresets(presetList);
            setError(null);
        } catch (err) {
            setError('Failed to load security data');
            console.error('Security data error:', err);
        } finally {
            setLoading(false);
        }
    };

    const applyPreset = async (level) => {
        try {
            setApplying(level);
            await ApiService.request(`/security/preset/${level}`, { method: 'POST' });
            await loadSecurityData(); // Reload to get updated status
        } catch (err) {
            setError(`Failed to apply ${level} preset`);
            console.error('Apply preset error:', err);
        } finally {
            setApplying(null);
        }
    };

    const getPresetIcon = (level) => {
        switch (level) {
            case 'speed':
                return <Zap className="text-primary" size={24} />;
            case 'balanced':
                return <BarChart className="text-success" size={24} />;
            case 'paranoid':
                return <ShieldLock className="text-warning" size={24} />;
            default:
                return <Shield className="text-muted" size={24} />;
        }
    };

    const getSecurityScoreColor = (score) => {
        if (score >= 80) return 'success';
        if (score >= 60) return 'warning';
        return 'danger';
    };

    if (loading) {
        return (
            <Card>
                <Card.Body className="text-center">
                    <div className="spinner-border" role="status">
                        <span className="visually-hidden">Loading...</span>
                    </div>
                    <p className="mt-2">Loading security settings...</p>
                </Card.Body>
            </Card>
        );
    }

    return (
        <div>
            {error && <Alert variant="danger" className="mb-3">{error}</Alert>}

            {/* Current Security Status */}
            {securityStatus && (
                <Card className="mb-4">
                    <Card.Header>
                        <div className="d-flex justify-content-between align-items-center">
                            <h5 className="mb-0">
                                <Shield className="me-2" />
                                Security Status
                            </h5>
                            {securityStatus.status === 'configured' && (
                                <Badge bg={getSecurityScoreColor(securityStatus.security_score)} className="fs-6">
                                    {securityStatus.security_score}% Secure
                                </Badge>
                            )}
                        </div>
                    </Card.Header>
                    <Card.Body>
                        {securityStatus.status === 'configured' ? (
                            <div>
                                <Row>
                                    <Col md={8}>
                                        <div className="d-flex align-items-center mb-3">
                                            {getPresetIcon(securityStatus.preset.level)}
                                            <div className="ms-3">
                                                <h6 className="mb-0">{securityStatus.preset.name} Security</h6>
                                                <small className="text-muted">{securityStatus.preset.description}</small>
                                            </div>
                                        </div>

                                        <div className="mb-3">
                                            <h6>Security Features</h6>
                                            <Row>
                                                {Object.entries(securityStatus.features_enabled).map(([feature, enabled]) => (
                                                    <Col sm={6} key={feature} className="mb-1">
                                                        <div className="d-flex align-items-center">
                                                            {enabled ? 
                                                                <ShieldCheck className="text-success me-2" size={16} /> : 
                                                                <ShieldX className="text-muted me-2" size={16} />
                                                            }
                                                            <small className={enabled ? 'text-success' : 'text-muted'}>
                                                                {feature.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                                            </small>
                                                        </div>
                                                    </Col>
                                                ))}
                                            </Row>
                                        </div>
                                    </Col>
                                    <Col md={4}>
                                        <div className="text-center">
                                            <h6>Security Score</h6>
                                            <ProgressBar 
                                                now={securityStatus.security_score} 
                                                variant={getSecurityScoreColor(securityStatus.security_score)}
                                                className="mb-2"
                                                style={{ height: '20px' }}
                                            />
                                            <small className="text-muted">
                                                {securityStatus.performance_impact.expected_impact}
                                            </small>
                                        </div>
                                    </Col>
                                </Row>

                                {securityStatus.recommendations && securityStatus.recommendations.length > 0 && (
                                    <div className="mt-3">
                                        <h6>Current Configuration</h6>
                                        <ListGroup variant="flush">
                                            {securityStatus.recommendations.slice(0, 3).map((rec, index) => (
                                                <ListGroup.Item key={index} className="px-0 py-1">
                                                    <small>{rec}</small>
                                                </ListGroup.Item>
                                            ))}
                                        </ListGroup>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <Alert variant="warning">
                                <strong>Security not configured</strong><br />
                                Choose a security preset below to configure system security.
                            </Alert>
                        )}
                    </Card.Body>
                </Card>
            )}

            {/* Security Presets */}
            <Card>
                <Card.Header>
                    <h5 className="mb-0">Security Presets</h5>
                    <small className="text-muted">Choose your security level - you can change this anytime</small>
                </Card.Header>
                <Card.Body>
                    <Row>
                        {presets.map((preset) => {
                            const isActive = securityStatus?.preset?.level === preset.level;
                            const isApplying = applying === preset.level;
                            
                            return (
                                <Col md={4} key={preset.level} className="mb-3">
                                    <Card className={`h-100 ${isActive ? 'border-primary' : ''}`}>
                                        <Card.Body className="text-center">
                                            <div className="mb-3">
                                                {getPresetIcon(preset.level)}
                                            </div>
                                            
                                            <h6 className="mb-2">
                                                {preset.name}
                                                {isActive && <Badge bg="primary" className="ms-2">Active</Badge>}
                                            </h6>
                                            
                                            <p className="small text-muted mb-3">
                                                {preset.description}
                                            </p>

                                            <div className="mb-3">
                                                <small className="text-muted d-block mb-1">Key Features:</small>
                                                <div className="d-flex flex-wrap justify-content-center">
                                                    {preset.encrypt_configs && <Badge bg="secondary" className="me-1 mb-1">Encryption</Badge>}
                                                    {preset.require_tls && <Badge bg="secondary" className="me-1 mb-1">TLS</Badge>}
                                                    {preset.use_strong_auth && <Badge bg="secondary" className="me-1 mb-1">Strong Auth</Badge>}
                                                    {preset.enable_audit_log && <Badge bg="secondary" className="me-1 mb-1">Audit Log</Badge>}
                                                    {preset.anonymize_data && <Badge bg="secondary" className="me-1 mb-1">Privacy</Badge>}
                                                </div>
                                            </div>

                                            <div className="mb-3">
                                                <small className="text-muted d-block">Performance Impact:</small>
                                                <small className={`fw-bold ${
                                                    preset.level === 'speed' ? 'text-success' :
                                                    preset.level === 'balanced' ? 'text-warning' : 'text-danger'
                                                }`}>
                                                    {preset.level === 'speed' ? 'Minimal' :
                                                     preset.level === 'balanced' ? 'Low' : 'Moderate'}
                                                </small>
                                            </div>

                                            <Button
                                                variant={isActive ? 'outline-primary' : 'primary'}
                                                size="sm"
                                                onClick={() => applyPreset(preset.level)}
                                                disabled={isActive || isApplying}
                                                className="w-100"
                                            >
                                                {isApplying ? (
                                                    <>
                                                        <span className="spinner-border spinner-border-sm me-2" />
                                                        Applying...
                                                    </>
                                                ) : isActive ? (
                                                    'Currently Active'
                                                ) : (
                                                    `Apply ${preset.name}`
                                                )}
                                            </Button>
                                        </Card.Body>
                                    </Card>
                                </Col>
                            );
                        })}
                    </Row>

                    {/* Preset Comparison */}
                    <div className="mt-4">
                        <h6>Which preset should I choose?</h6>
                        <Row>
                            <Col md={4}>
                                <div className="d-flex align-items-start">
                                    <Zap className="text-primary mt-1 me-2" size={16} />
                                    <div>
                                        <strong className="small">Speed</strong>
                                        <div className="small text-muted">
                                            Perfect for development, testing, or local-only setups where performance matters most.
                                        </div>
                                    </div>
                                </div>
                            </Col>
                            <Col md={4}>
                                <div className="d-flex align-items-start">
                                    <BarChart className="text-success mt-1 me-2" size={16} />
                                    <div>
                                        <strong className="small">Balanced</strong>
                                        <div className="small text-muted">
                                            Recommended for most users. Good security without sacrificing performance.
                                        </div>
                                    </div>
                                </div>
                            </Col>
                            <Col md={4}>
                                <div className="d-flex align-items-start">
                                    <ShieldLock className="text-warning mt-1 me-2" size={16} />
                                    <div>
                                        <strong className="small">Paranoid</strong>
                                        <div className="small text-muted">
                                            Maximum security for sensitive environments or internet-facing systems.
                                        </div>
                                    </div>
                                </div>
                            </Col>
                        </Row>
                    </div>
                </Card.Body>
            </Card>
        </div>
    );
};

export default SimpleSecurityManager;