import React, { useState, useEffect, useRef } from 'react';
import { Card, Row, Col, Badge, Button, Form, Alert, ProgressBar } from 'react-bootstrap';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import { ApiService } from '../services/ApiService';
import { useAccessibility } from '../utils/AccessibilityManager';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend);

export const AnalyticsManager = () => {
    const { announce } = useAccessibility();
    const [analytics, setAnalytics] = useState({
        metrics: {},
        performance: {},
        usage: {},
        errors: [],
        loading: true
    });
    const [timeRange, setTimeRange] = useState('24h');
    const [refreshInterval, setRefreshInterval] = useState(30);
    const [autoRefresh, setAutoRefresh] = useState(true);
    const refreshTimerRef = useRef(null);

    useEffect(() => {
        loadAnalytics();
        
        if (autoRefresh) {
            refreshTimerRef.current = setInterval(loadAnalytics, refreshInterval * 1000);
        }

        return () => {
            if (refreshTimerRef.current) {
                clearInterval(refreshTimerRef.current);
            }
        };
    }, [timeRange, refreshInterval, autoRefresh]);

    const loadAnalytics = async () => {
        try {
            const data = await ApiService.getAnalytics(timeRange);
            setAnalytics({
                ...data,
                loading: false
            });
            announce('Analytics data updated');
        } catch (error) {
            console.error('Failed to load analytics:', error);
            setAnalytics(prev => ({ ...prev, loading: false }));
            announce('Failed to load analytics data', 'assertive');
        }
    };

    const handleTimeRangeChange = (newRange) => {
        setTimeRange(newRange);
        announce(`Time range changed to ${newRange}`);
    };

    const handleRefreshIntervalChange = (interval) => {
        setRefreshInterval(interval);
        if (refreshTimerRef.current) {
            clearInterval(refreshTimerRef.current);
        }
        if (autoRefresh) {
            refreshTimerRef.current = setInterval(loadAnalytics, interval * 1000);
        }
        announce(`Refresh interval set to ${interval} seconds`);
    };

    const exportAnalytics = async (format) => {
        try {
            const blob = await ApiService.exportAnalytics(format, timeRange);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `analytics_${timeRange}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            announce(`Analytics exported as ${format}`);
        } catch (error) {
            console.error('Export failed:', error);
            announce('Failed to export analytics', 'assertive');
        }
    };

    // Chart configurations
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
            },
            title: {
                display: true,
                text: 'System Performance Metrics'
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleColor: 'white',
                bodyColor: 'white',
                borderColor: '#007bff',
                borderWidth: 1
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                grid: {
                    color: 'rgba(0, 0, 0, 0.1)'
                }
            },
            x: {
                grid: {
                    color: 'rgba(0, 0, 0, 0.1)'
                }
            }
        },
        accessibility: {
            enabled: true,
            description: 'Performance metrics chart showing system utilization over time'
        }
    };

    const performanceData = {
        labels: analytics.performance?.timestamps || [],
        datasets: [
            {
                label: 'CPU Usage (%)',
                data: analytics.performance?.cpu || [],
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                tension: 0.1
            },
            {
                label: 'Memory Usage (%)',
                data: analytics.performance?.memory || [],
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                tension: 0.1
            },
            {
                label: 'Network I/O (MB/s)',
                data: analytics.performance?.network || [],
                borderColor: 'rgb(255, 205, 86)',
                backgroundColor: 'rgba(255, 205, 86, 0.2)',
                tension: 0.1
            }
        ]
    };

    const usageData = {
        labels: ['AI Requests', 'MQTT Messages', 'Device Updates', 'Zone Triggers', 'API Calls'],
        datasets: [
            {
                label: 'Usage Count',
                data: [
                    analytics.usage?.ai_requests || 0,
                    analytics.usage?.mqtt_messages || 0,
                    analytics.usage?.device_updates || 0,
                    analytics.usage?.zone_triggers || 0,
                    analytics.usage?.api_calls || 0
                ],
                backgroundColor: [
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 205, 86, 0.8)',
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(153, 102, 255, 0.8)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 205, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)'
                ],
                borderWidth: 1
            }
        ]
    };

    if (analytics.loading) {
        return (
            <Card>
                <Card.Body className="text-center">
                    <div className="spinner-border" role="status" aria-label="Loading analytics">
                        <span className="visually-hidden">Loading analytics...</span>
                    </div>
                    <p className="mt-2">Loading analytics data...</p>
                </Card.Body>
            </Card>
        );
    }

    return (
        <div>
            {/* Controls */}
            <Card className="mb-4">
                <Card.Header>
                    <Row className="align-items-center">
                        <Col>
                            <h4 className="mb-0">Analytics Dashboard</h4>
                            <small className="text-muted">
                                Real-time monitoring and performance metrics
                            </small>
                        </Col>
                        <Col xs="auto">
                            <Badge 
                                bg={autoRefresh ? 'success' : 'secondary'} 
                                pill
                                aria-label={`Auto refresh ${autoRefresh ? 'enabled' : 'disabled'}`}
                            >
                                {autoRefresh ? 'Live' : 'Paused'}
                            </Badge>
                        </Col>
                    </Row>
                </Card.Header>
                <Card.Body>
                    <Row className="align-items-center mb-3">
                        <Col md={3}>
                            <Form.Group>
                                <Form.Label htmlFor="time-range-select">Time Range</Form.Label>
                                <Form.Select
                                    id="time-range-select"
                                    value={timeRange}
                                    onChange={(e) => handleTimeRangeChange(e.target.value)}
                                    aria-describedby="time-range-help"
                                >
                                    <option value="1h">Last Hour</option>
                                    <option value="24h">Last 24 Hours</option>
                                    <option value="7d">Last 7 Days</option>
                                    <option value="30d">Last 30 Days</option>
                                </Form.Select>
                                <Form.Text id="time-range-help" className="text-muted">
                                    Select the time period for analytics data
                                </Form.Text>
                            </Form.Group>
                        </Col>
                        <Col md={3}>
                            <Form.Group>
                                <Form.Label htmlFor="refresh-interval-select">Refresh Interval</Form.Label>
                                <Form.Select
                                    id="refresh-interval-select"
                                    value={refreshInterval}
                                    onChange={(e) => handleRefreshIntervalChange(parseInt(e.target.value))}
                                    disabled={!autoRefresh}
                                    aria-describedby="refresh-interval-help"
                                >
                                    <option value={10}>10 seconds</option>
                                    <option value={30}>30 seconds</option>
                                    <option value={60}>1 minute</option>
                                    <option value={300}>5 minutes</option>
                                </Form.Select>
                                <Form.Text id="refresh-interval-help" className="text-muted">
                                    How often to update the data
                                </Form.Text>
                            </Form.Group>
                        </Col>
                        <Col md={3}>
                            <Form.Group>
                                <Form.Label>&nbsp;</Form.Label>
                                <div>
                                    <Form.Check
                                        type="switch"
                                        id="auto-refresh-switch"
                                        label="Auto Refresh"
                                        checked={autoRefresh}
                                        onChange={(e) => setAutoRefresh(e.target.checked)}
                                        aria-describedby="auto-refresh-help"
                                    />
                                    <Form.Text id="auto-refresh-help" className="text-muted">
                                        Automatically update dashboard
                                    </Form.Text>
                                </div>
                            </Form.Group>
                        </Col>
                        <Col md={3} className="text-end">
                            <div className="d-flex gap-2 justify-content-end">
                                <Button
                                    variant="outline-primary"
                                    size="sm"
                                    onClick={loadAnalytics}
                                    aria-label="Manually refresh analytics data"
                                >
                                    Refresh
                                </Button>
                                <div className="dropdown">
                                    <Button
                                        variant="outline-secondary"
                                        size="sm"
                                        className="dropdown-toggle"
                                        data-bs-toggle="dropdown"
                                        aria-expanded="false"
                                        aria-label="Export analytics data"
                                    >
                                        Export
                                    </Button>
                                    <ul className="dropdown-menu">
                                        <li>
                                            <button
                                                className="dropdown-item"
                                                onClick={() => exportAnalytics('json')}
                                            >
                                                JSON
                                            </button>
                                        </li>
                                        <li>
                                            <button
                                                className="dropdown-item"
                                                onClick={() => exportAnalytics('csv')}
                                            >
                                                CSV
                                            </button>
                                        </li>
                                        <li>
                                            <button
                                                className="dropdown-item"
                                                onClick={() => exportAnalytics('pdf')}
                                            >
                                                PDF Report
                                            </button>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </Col>
                    </Row>
                </Card.Body>
            </Card>

            {/* Key Metrics */}
            <Row className="mb-4">
                <Col md={3}>
                    <Card className="h-100">
                        <Card.Body className="text-center">
                            <h2 className="text-primary mb-1" aria-label="System uptime percentage">
                                {analytics.metrics?.uptime || '99.9'}%
                            </h2>
                            <p className="text-muted mb-0">System Uptime</p>
                            <ProgressBar
                                now={analytics.metrics?.uptime || 99.9}
                                variant="success"
                                className="mt-2"
                                aria-label={`System uptime: ${analytics.metrics?.uptime || 99.9}%`}
                            />
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={3}>
                    <Card className="h-100">
                        <Card.Body className="text-center">
                            <h2 className="text-info mb-1" aria-label="Average response time">
                                {analytics.metrics?.avg_response_time || '45'}ms
                            </h2>
                            <p className="text-muted mb-0">Avg Response Time</p>
                            <small className="text-success">
                                {analytics.metrics?.response_time_trend || '+5%'} from last period
                            </small>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={3}>
                    <Card className="h-100">
                        <Card.Body className="text-center">
                            <h2 className="text-warning mb-1" aria-label="Active devices count">
                                {analytics.metrics?.active_devices || '12'}
                            </h2>
                            <p className="text-muted mb-0">Active Devices</p>
                            <small className="text-info">
                                {analytics.metrics?.device_trend || '+2'} new this week
                            </small>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={3}>
                    <Card className="h-100">
                        <Card.Body className="text-center">
                            <h2 className="text-danger mb-1" aria-label="Error count">
                                {analytics.metrics?.error_count || '0'}
                            </h2>
                            <p className="text-muted mb-0">Errors (24h)</p>
                            <Badge 
                                bg={analytics.metrics?.error_count === 0 ? 'success' : 'warning'}
                                aria-label={`Error status: ${analytics.metrics?.error_count === 0 ? 'healthy' : 'needs attention'}`}
                            >
                                {analytics.metrics?.error_count === 0 ? 'Healthy' : 'Monitor'}
                            </Badge>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>

            {/* Charts */}
            <Row className="mb-4">
                <Col lg={8}>
                    <Card>
                        <Card.Header>
                            <h5>Performance Metrics</h5>
                            <small className="text-muted">
                                Real-time system resource utilization
                            </small>
                        </Card.Header>
                        <Card.Body>
                            <div style={{ height: '300px' }}>
                                <Line 
                                    data={performanceData} 
                                    options={chartOptions}
                                    aria-label="Performance metrics line chart showing CPU, memory, and network usage over time"
                                />
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
                <Col lg={4}>
                    <Card>
                        <Card.Header>
                            <h5>Usage Statistics</h5>
                            <small className="text-muted">
                                Feature utilization breakdown
                            </small>
                        </Card.Header>
                        <Card.Body>
                            <div style={{ height: '300px' }}>
                                <Bar 
                                    data={usageData} 
                                    options={{
                                        ...chartOptions,
                                        plugins: {
                                            ...chartOptions.plugins,
                                            legend: {
                                                display: false
                                            },
                                            title: {
                                                display: false
                                            }
                                        },
                                        accessibility: {
                                            enabled: true,
                                            description: 'Usage statistics bar chart showing feature utilization counts'
                                        }
                                    }}
                                    aria-label="Usage statistics bar chart showing counts for different system features"
                                />
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>

            {/* Recent Errors */}
            {analytics.errors && analytics.errors.length > 0 && (
                <Card className="mb-4">
                    <Card.Header>
                        <h5 className="mb-0">Recent Errors</h5>
                    </Card.Header>
                    <Card.Body>
                        {analytics.errors.map((error, index) => (
                            <Alert 
                                key={index} 
                                variant="warning" 
                                className="mb-2"
                                role="alert"
                                aria-label={`Error: ${error.message}`}
                            >
                                <div className="d-flex justify-content-between align-items-start">
                                    <div>
                                        <strong>{error.type || 'Error'}</strong>
                                        <p className="mb-1">{error.message}</p>
                                        <small className="text-muted">
                                            {error.timestamp} - Component: {error.component || 'Unknown'}
                                        </small>
                                    </div>
                                    <Badge bg="warning">
                                        {error.severity || 'Medium'}
                                    </Badge>
                                </div>
                            </Alert>
                        ))}
                    </Card.Body>
                </Card>
            )}

            {/* System Health */}
            <Card>
                <Card.Header>
                    <h5>System Health Status</h5>
                </Card.Header>
                <Card.Body>
                    <Row>
                        <Col md={4}>
                            <div className="d-flex align-items-center mb-3">
                                <div 
                                    className="rounded-circle me-3"
                                    style={{
                                        width: '12px',
                                        height: '12px',
                                        backgroundColor: analytics.health?.database ? '#28a745' : '#dc3545'
                                    }}
                                    aria-label={`Database status: ${analytics.health?.database ? 'healthy' : 'unhealthy'}`}
                                ></div>
                                <span>Database Connection</span>
                                <Badge 
                                    bg={analytics.health?.database ? 'success' : 'danger'} 
                                    className="ms-auto"
                                >
                                    {analytics.health?.database ? 'OK' : 'Down'}
                                </Badge>
                            </div>
                        </Col>
                        <Col md={4}>
                            <div className="d-flex align-items-center mb-3">
                                <div 
                                    className="rounded-circle me-3"
                                    style={{
                                        width: '12px',
                                        height: '12px',
                                        backgroundColor: analytics.health?.mqtt ? '#28a745' : '#dc3545'
                                    }}
                                    aria-label={`MQTT broker status: ${analytics.health?.mqtt ? 'connected' : 'disconnected'}`}
                                ></div>
                                <span>MQTT Broker</span>
                                <Badge 
                                    bg={analytics.health?.mqtt ? 'success' : 'danger'} 
                                    className="ms-auto"
                                >
                                    {analytics.health?.mqtt ? 'Connected' : 'Offline'}
                                </Badge>
                            </div>
                        </Col>
                        <Col md={4}>
                            <div className="d-flex align-items-center mb-3">
                                <div 
                                    className="rounded-circle me-3"
                                    style={{
                                        width: '12px',
                                        height: '12px',
                                        backgroundColor: analytics.health?.ai_provider ? '#28a745' : '#dc3545'
                                    }}
                                    aria-label={`AI provider status: ${analytics.health?.ai_provider ? 'available' : 'unavailable'}`}
                                ></div>
                                <span>AI Provider</span>
                                <Badge 
                                    bg={analytics.health?.ai_provider ? 'success' : 'danger'} 
                                    className="ms-auto"
                                >
                                    {analytics.health?.ai_provider ? 'Available' : 'Error'}
                                </Badge>
                            </div>
                        </Col>
                    </Row>
                </Card.Body>
            </Card>
        </div>
    );
};

export default AnalyticsManager;