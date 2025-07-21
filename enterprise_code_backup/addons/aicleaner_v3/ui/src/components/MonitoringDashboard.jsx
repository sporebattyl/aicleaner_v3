
import React, { useState, useEffect, lazy, Suspense } from 'react';
import { Card, Row, Col, ProgressBar, Badge, Alert, Spinner } from 'react-bootstrap';
import WebSocketService from '../services/WebSocketService';
import { LazyAnalyticsManager } from './LazyChartComponents';

// Lazy load the Line chart component
const LazyLineChart = lazy(() => import('react-chartjs-2').then(module => ({ default: module.Line })));

export const MonitoringDashboard = () => {
    const [metrics, setMetrics] = useState({});
    const [devices, setDevices] = useState([]);
    const [zones, setZones] = useState([]);
    const [connectionStatus, setConnectionStatus] = useState('disconnected');
    const [performanceData, setPerformanceData] = useState({
        cpu: [],
        memory: [],
        timestamps: []
    });

    useEffect(() => {
        // Initialize WebSocket connection
        WebSocketService.connect((data) => {
            handleRealtimeUpdate(data);
        });

        WebSocketService.onStatusChange((status) => {
            setConnectionStatus(status);
        });

        return () => {
            WebSocketService.disconnect();
        };
    }, []);

    const handleRealtimeUpdate = (data) => {
        switch (data.type) {
            case 'metrics':
                setMetrics(data.payload);
                updatePerformanceData(data.payload);
                break;
            case 'devices':
                setDevices(data.payload);
                break;
            case 'zones':
                setZones(data.payload);
                break;
        }
    };

    const updatePerformanceData = (newMetrics) => {
        setPerformanceData(prev => ({
            cpu: [...prev.cpu.slice(-19), newMetrics.cpu_usage || 0],
            memory: [...prev.memory.slice(-19), newMetrics.memory_usage || 0],
            timestamps: [...prev.timestamps.slice(-19), new Date().toLocaleTimeString()]
        }));
    };

    const chartData = {
        labels: performanceData.timestamps,
        datasets: [
            {
                label: 'CPU Usage (%)',
                data: performanceData.cpu,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.1
            },
            {
                label: 'Memory Usage (%)',
                data: performanceData.memory,
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                tension: 0.1
            }
        ]
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                max: 100
            }
        }
    };

    return (
        <div>
            {/* Connection Status */}
            <Alert variant={connectionStatus === 'connected' ? 'success' : 'warning'} className="mb-3">
                <strong>Status:</strong> {connectionStatus === 'connected' ? 'Connected' : 'Disconnected'}
                {connectionStatus === 'connected' && (
                    <Badge bg="success" className="ms-2">Live</Badge>
                )}
            </Alert>

            {/* System Metrics Overview */}
            <Row className="mb-4">
                <Col md={3}>
                    <Card>
                        <Card.Body>
                            <h6>CPU Usage</h6>
                            <ProgressBar 
                                now={metrics.cpu_usage || 0} 
                                label={`${metrics.cpu_usage || 0}%`}
                                variant={metrics.cpu_usage > 80 ? 'danger' : metrics.cpu_usage > 60 ? 'warning' : 'success'}
                            />
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={3}>
                    <Card>
                        <Card.Body>
                            <h6>Memory Usage</h6>
                            <ProgressBar 
                                now={metrics.memory_usage || 0} 
                                label={`${metrics.memory_usage || 0}%`}
                                variant={metrics.memory_usage > 80 ? 'danger' : metrics.memory_usage > 60 ? 'warning' : 'success'}
                            />
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={3}>
                    <Card>
                        <Card.Body>
                            <h6>Active Zones</h6>
                            <h3 className="text-primary">{zones.filter(z => z.active).length}</h3>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={3}>
                    <Card>
                        <Card.Body>
                            <h6>Connected Devices</h6>
                            <h3 className="text-success">{devices.filter(d => d.online).length}</h3>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>

            {/* Performance Chart */}
            <Card className="mb-4">
                <Card.Header>Performance Metrics</Card.Header>
                <Card.Body style={{ height: '300px' }}>
                    <Line data={chartData} options={chartOptions} />
                </Card.Body>
            </Card>

            {/* Device Status */}
            <Row>
                <Col md={6}>
                    <Card>
                        <Card.Header>Device Status</Card.Header>
                        <Card.Body>
                            {devices.map(device => (
                                <div key={device.id} className="d-flex justify-content-between align-items-center mb-2">
                                    <span>{device.name}</span>
                                    <Badge bg={device.online ? 'success' : 'secondary'}>
                                        {device.online ? 'Online' : 'Offline'}
                                    </Badge>
                                </div>
                            ))}
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={6}>
                    <Card>
                        <Card.Header>Zone Status</Card.Header>
                        <Card.Body>
                            {zones.map(zone => (
                                <div key={zone.id} className="d-flex justify-content-between align-items-center mb-2">
                                    <span>{zone.name}</span>
                                    <Badge bg={zone.active ? 'primary' : 'secondary'}>
                                        {zone.active ? 'Active' : 'Inactive'}
                                    </Badge>
                                </div>
                            ))}
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        </div>
    );
};
