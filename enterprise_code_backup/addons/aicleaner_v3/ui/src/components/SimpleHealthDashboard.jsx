import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Alert, Badge, Button, Spinner, ProgressBar, ListGroup } from 'react-bootstrap';
import { CheckCircle, ExclamationTriangle, XCircle, Clock, RefreshCw, Activity } from 'react-bootstrap-icons';
import ApiService from '../services/ApiService';

const SimpleHealthDashboard = () => {
    const [healthData, setHealthData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [lastUpdate, setLastUpdate] = useState(null);
    const [autoRefresh, setAutoRefresh] = useState(true);

    useEffect(() => {
        loadHealthData();
        
        if (autoRefresh) {
            const interval = setInterval(loadHealthData, 30000); // Refresh every 30 seconds
            return () => clearInterval(interval);
        }
    }, [autoRefresh]);

    const loadHealthData = async () => {
        try {
            if (!loading) setRefreshing(true);
            
            const data = await ApiService.request('/health/system');
            setHealthData(data);
            setLastUpdate(new Date().toLocaleTimeString());
        } catch (error) {
            console.error('Failed to load health data:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'healthy':
                return <CheckCircle className="text-success" size={20} />;
            case 'warning':
                return <ExclamationTriangle className="text-warning" size={20} />;
            case 'critical':
                return <XCircle className="text-danger" size={20} />;
            default:
                return <Clock className="text-muted" size={20} />;
        }
    };

    const getStatusVariant = (status) => {
        switch (status) {
            case 'healthy':
                return 'success';
            case 'warning':
                return 'warning';
            case 'critical':
                return 'danger';
            default:
                return 'secondary';
        }
    };

    const getProgressVariant = (value, warningThreshold = 70, criticalThreshold = 90) => {
        if (value >= criticalThreshold) return 'danger';
        if (value >= warningThreshold) return 'warning';
        return 'success';
    };

    const parseResourceValue = (value) => {
        if (!value) return 0;
        return parseFloat(value.replace('%', ''));
    };

    if (loading) {
        return (
            <Card>
                <Card.Body className="text-center">
                    <Spinner animation="border" />
                    <p className="mt-2">Loading system health...</p>
                </Card.Body>
            </Card>
        );
    }

    if (!healthData) {
        return (
            <Card>
                <Card.Body>
                    <Alert variant="warning">
                        Unable to load health data. Check system status.
                    </Alert>
                </Card.Body>
            </Card>
        );
    }

    const { overall_status, indicators, recommendations, uptime_seconds } = healthData;
    const uptimeHours = Math.floor(uptime_seconds / 3600);
    const uptimeDays = Math.floor(uptimeHours / 24);

    // Separate indicators by category
    const resourceIndicators = indicators.filter(i => 
        ['CPU Usage', 'Memory Usage', 'Disk Usage'].includes(i.name)
    );
    const serviceIndicators = indicators.filter(i => 
        i.name.includes('Service')
    );
    const integrationIndicators = indicators.filter(i => 
        ['Home Assistant', 'MQTT Broker'].includes(i.name)
    );
    const configIndicators = indicators.filter(i => 
        ['API Keys', 'Zone Configuration', 'MQTT Settings'].includes(i.name)
    );

    return (
        <div>
            {/* Overall Status Card */}
            <Card className="mb-4">
                <Card.Header className="d-flex justify-content-between align-items-center">
                    <div className="d-flex align-items-center">
                        {getStatusIcon(overall_status)}
                        <h5 className="mb-0 ms-2">System Health</h5>
                    </div>
                    <div className="d-flex align-items-center">
                        <small className="text-muted me-2">
                            Last updated: {lastUpdate}
                        </small>
                        <Button 
                            variant="outline-secondary" 
                            size="sm" 
                            onClick={loadHealthData}
                            disabled={refreshing}
                        >
                            <RefreshCw className={refreshing ? 'spin' : ''} size={14} />
                        </Button>
                    </div>
                </Card.Header>
                <Card.Body>
                    <Row>
                        <Col md={8}>
                            <Alert variant={getStatusVariant(overall_status)} className="mb-3">
                                <div className="d-flex align-items-center">
                                    {getStatusIcon(overall_status)}
                                    <div className="ms-2">
                                        <strong>
                                            {overall_status === 'healthy' && 'All Systems Operational'}
                                            {overall_status === 'warning' && 'Minor Issues Detected'}
                                            {overall_status === 'critical' && 'Critical Issues Require Attention'}
                                            {overall_status === 'unknown' && 'System Status Unknown'}
                                        </strong>
                                        <div className="small">
                                            {indicators.filter(i => i.status === 'critical').length > 0 && (
                                                <span className="text-danger">
                                                    {indicators.filter(i => i.status === 'critical').length} critical issue(s)
                                                </span>
                                            )}
                                            {indicators.filter(i => i.status === 'warning').length > 0 && (
                                                <span className="text-warning">
                                                    {indicators.filter(i => i.status === 'warning').length} warning(s)
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </Alert>
                        </Col>
                        <Col md={4}>
                            <div className="text-center">
                                <div className="d-flex align-items-center justify-content-center mb-1">
                                    <Activity size={16} className="me-1" />
                                    <strong>Uptime</strong>
                                </div>
                                <div>
                                    {uptimeDays > 0 ? `${uptimeDays}d ` : ''}
                                    {uptimeHours % 24}h
                                </div>
                            </div>
                        </Col>
                    </Row>
                </Card.Body>
            </Card>

            {/* Resource Usage */}
            <Row className="mb-4">
                <Col md={12}>
                    <Card>
                        <Card.Header>
                            <h6 className="mb-0">Resource Usage</h6>
                        </Card.Header>
                        <Card.Body>
                            <Row>
                                {resourceIndicators.map((indicator, index) => {
                                    const value = parseResourceValue(indicator.value);
                                    return (
                                        <Col md={4} key={index} className="mb-3">
                                            <div className="d-flex justify-content-between align-items-center mb-1">
                                                <span className="small fw-bold">{indicator.name}</span>
                                                <Badge bg={getStatusVariant(indicator.status)}>
                                                    {indicator.value}
                                                </Badge>
                                            </div>
                                            <ProgressBar 
                                                now={value}
                                                variant={getProgressVariant(value)}
                                                className="mb-1"
                                                style={{ height: '8px' }}
                                            />
                                            {indicator.action_needed && (
                                                <small className="text-muted">
                                                    {indicator.action_needed}
                                                </small>
                                            )}
                                        </Col>
                                    );
                                })}
                            </Row>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>

            {/* Services and Integrations */}
            <Row className="mb-4">
                <Col md={6}>
                    <Card>
                        <Card.Header>
                            <h6 className="mb-0">Core Services</h6>
                        </Card.Header>
                        <Card.Body>
                            <ListGroup variant="flush">
                                {serviceIndicators.map((indicator, index) => (
                                    <ListGroup.Item 
                                        key={index} 
                                        className="d-flex justify-content-between align-items-center px-0"
                                    >
                                        <div className="d-flex align-items-center">
                                            {getStatusIcon(indicator.status)}
                                            <div className="ms-2">
                                                <div className="fw-bold small">{indicator.name}</div>
                                                <small className="text-muted">{indicator.message}</small>
                                            </div>
                                        </div>
                                        {indicator.value && (
                                            <Badge bg="light" text="dark">
                                                {indicator.value}
                                            </Badge>
                                        )}
                                    </ListGroup.Item>
                                ))}
                            </ListGroup>
                        </Card.Body>
                    </Card>
                </Col>

                <Col md={6}>
                    <Card>
                        <Card.Header>
                            <h6 className="mb-0">Integrations</h6>
                        </Card.Header>
                        <Card.Body>
                            <ListGroup variant="flush">
                                {integrationIndicators.map((indicator, index) => (
                                    <ListGroup.Item 
                                        key={index} 
                                        className="d-flex justify-content-between align-items-center px-0"
                                    >
                                        <div className="d-flex align-items-center">
                                            {getStatusIcon(indicator.status)}
                                            <div className="ms-2">
                                                <div className="fw-bold small">{indicator.name}</div>
                                                <small className="text-muted">{indicator.message}</small>
                                            </div>
                                        </div>
                                        <Badge bg={getStatusVariant(indicator.status)}>
                                            {indicator.status}
                                        </Badge>
                                    </ListGroup.Item>
                                ))}
                            </ListGroup>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>

            {/* Configuration Status */}
            <Row className="mb-4">
                <Col md={12}>
                    <Card>
                        <Card.Header>
                            <h6 className="mb-0">Configuration Health</h6>
                        </Card.Header>
                        <Card.Body>
                            <Row>
                                {configIndicators.map((indicator, index) => (
                                    <Col md={4} key={index} className="mb-2">
                                        <div className="d-flex align-items-center">
                                            {getStatusIcon(indicator.status)}
                                            <div className="ms-2">
                                                <div className="small fw-bold">{indicator.name}</div>
                                                <small className="text-muted">{indicator.message}</small>
                                            </div>
                                        </div>
                                    </Col>
                                ))}
                            </Row>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>

            {/* Recommendations */}
            {recommendations && recommendations.length > 0 && (
                <Card>
                    <Card.Header>
                        <h6 className="mb-0">Recommendations</h6>
                    </Card.Header>
                    <Card.Body>
                        <ListGroup variant="flush">
                            {recommendations.map((recommendation, index) => (
                                <ListGroup.Item key={index} className="px-0">
                                    <div className="small">
                                        {recommendation}
                                    </div>
                                </ListGroup.Item>
                            ))}
                        </ListGroup>
                    </Card.Body>
                </Card>
            )}

            {/* Auto-refresh toggle */}
            <div className="text-center mt-3">
                <small className="text-muted">
                    <input 
                        type="checkbox" 
                        checked={autoRefresh} 
                        onChange={(e) => setAutoRefresh(e.target.checked)}
                        className="me-1"
                    />
                    Auto-refresh every 30 seconds
                </small>
            </div>
        </div>
    );
};

export default SimpleHealthDashboard;