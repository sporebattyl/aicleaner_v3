import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AnalyticsManager } from '../AnalyticsManager';
import ApiService from '../../services/ApiService';
import { useAccessibility } from '../../utils/AccessibilityManager';

// Mock dependencies
jest.mock('../../services/ApiService');
jest.mock('../../utils/AccessibilityManager');
jest.mock('react-csv', () => ({
    CSVLink: ({ children, ...props }) => <a {...props}>{children}</a>
}));
jest.mock('jspdf', () => {
    return jest.fn().mockImplementation(() => ({
        text: jest.fn(),
        addPage: jest.fn(),
        autoTable: jest.fn(),
        save: jest.fn()
    }));
});
jest.mock('chart.js', () => ({
    Chart: {
        register: jest.fn()
    },
    registerables: []
}));

// Mock Chart.js canvas context
HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
    fillRect: jest.fn(),
    clearRect: jest.fn(),
    beginPath: jest.fn(),
    stroke: jest.fn(),
    fill: jest.fn(),
    arc: jest.fn(),
    moveTo: jest.fn(),
    lineTo: jest.fn(),
    scale: jest.fn(),
    rotate: jest.fn(),
    translate: jest.fn(),
    save: jest.fn(),
    restore: jest.fn(),
    measureText: jest.fn(() => ({ width: 0 }))
}));

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn()
    }))
});

describe('AnalyticsManager', () => {
    const mockAnalytics = {
        metrics: {
            uptime: 99.5,
            avg_response_time: 42,
            active_devices: 15,
            error_count: 2,
            response_time_trend: '+3%',
            device_trend: '+4'
        },
        performance: {
            timestamps: ['2024-01-01T10:00:00Z', '2024-01-01T10:05:00Z'],
            cpu: [25, 30],
            memory: [65, 70],
            network: [12, 15]
        },
        usage: {
            ai_requests: 150,
            mqtt_messages: 3200,
            device_updates: 850,
            zone_triggers: 95,
            api_calls: 1250
        },
        health: {
            database: true,
            mqtt: true,
            ai_provider: false
        },
        errors: [
            {
                timestamp: '2024-01-01T10:00:00Z',
                message: 'Connection timeout',
                source: 'API',
                severity: 'High'
            }
        ]
    };

    const mockAccessibility = {
        announce: jest.fn()
    };

    beforeEach(() => {
        jest.clearAllMocks();
        ApiService.getAnalytics.mockResolvedValue(mockAnalytics);
        useAccessibility.mockReturnValue(mockAccessibility);
    });

    test('renders loading state initially', () => {
        render(<AnalyticsManager />);
        expect(screen.getByText('Loading analytics...')).toBeInTheDocument();
    });

    test('renders analytics dashboard after successful data load', async () => {
        render(<AnalyticsManager />);
        
        await waitFor(() => {
            expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
        });

        // Check key metrics are displayed
        expect(screen.getByText('99.5%')).toBeInTheDocument(); // Uptime
        expect(screen.getByText('42ms')).toBeInTheDocument(); // Response time
        expect(screen.getByText('15')).toBeInTheDocument(); // Active devices
        expect(screen.getByText('2')).toBeInTheDocument(); // Error count
    });

    test('handles API error gracefully', async () => {
        ApiService.getAnalytics.mockRejectedValue(new Error('API Error'));
        
        render(<AnalyticsManager />);
        
        await waitFor(() => {
            expect(screen.getByText('Failed to load analytics data')).toBeInTheDocument();
        });
    });

    test('changes time range and refetches data', async () => {
        const user = userEvent.setup();
        render(<AnalyticsManager />);

        await waitFor(() => {
            expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
        });

        const timeRangeSelect = screen.getByLabelText('Select time range');
        await user.selectOptions(timeRangeSelect, '7d');

        await waitFor(() => {
            expect(ApiService.getAnalytics).toHaveBeenCalledWith('7d');
        });
        
        expect(mockAccessibility.announce).toHaveBeenCalledWith('Time range changed to 7d');
    });

    test('toggles auto refresh', async () => {
        const user = userEvent.setup();
        render(<AnalyticsManager />);

        await waitFor(() => {
            expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
        });

        const autoRefreshSwitch = screen.getByLabelText('Auto Refresh');
        await user.click(autoRefreshSwitch);

        expect(screen.getByText('Paused')).toBeInTheDocument();
    });

    test('exports analytics as JSON', async () => {
        const user = userEvent.setup();
        const mockCreateObjectURL = jest.fn(() => 'blob:test');
        const mockRevokeObjectURL = jest.fn();
        
        global.URL.createObjectURL = mockCreateObjectURL;
        global.URL.revokeObjectURL = mockRevokeObjectURL;

        render(<AnalyticsManager />);

        await waitFor(() => {
            expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
        });

        const exportButton = screen.getByLabelText('Export analytics data');
        await user.click(exportButton);

        const jsonButton = screen.getByText('JSON');
        await user.click(jsonButton);

        expect(mockCreateObjectURL).toHaveBeenCalled();
        expect(mockRevokeObjectURL).toHaveBeenCalled();
        expect(mockAccessibility.announce).toHaveBeenCalledWith('Analytics exported as json');
    });

    test('exports analytics as PDF', async () => {
        const user = userEvent.setup();
        const mockJsPDF = require('jspdf');
        
        render(<AnalyticsManager />);

        await waitFor(() => {
            expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
        });

        const exportButton = screen.getByLabelText('Export analytics data');
        await user.click(exportButton);

        const pdfButton = screen.getByText('PDF Report');
        await user.click(pdfButton);

        expect(mockJsPDF).toHaveBeenCalled();
        expect(mockAccessibility.announce).toHaveBeenCalledWith('Analytics exported as pdf');
    });

    test('displays system health status correctly', async () => {
        render(<AnalyticsManager />);

        await waitFor(() => {
            expect(screen.getByText('System Health Status')).toBeInTheDocument();
        });

        // Check health indicators
        expect(screen.getByText('Database Connection')).toBeInTheDocument();
        expect(screen.getByText('MQTT Broker')).toBeInTheDocument();
        expect(screen.getByText('AI Provider')).toBeInTheDocument();
        
        // Check status badges
        expect(screen.getAllByText('OK')).toHaveLength(2); // Database and MQTT
        expect(screen.getByText('Error')).toBeInTheDocument(); // AI Provider
    });

    test('displays recent errors table', async () => {
        render(<AnalyticsManager />);

        await waitFor(() => {
            expect(screen.getByText('Recent Errors')).toBeInTheDocument();
        });

        expect(screen.getByText('Connection timeout')).toBeInTheDocument();
        expect(screen.getByText('API')).toBeInTheDocument();
        expect(screen.getByText('High')).toBeInTheDocument();
    });

    test('updates refresh interval and announces change', async () => {
        const user = userEvent.setup();
        render(<AnalyticsManager />);

        await waitFor(() => {
            expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
        });

        const refreshIntervalSelect = screen.getByLabelText('Refresh Interval');
        await user.selectOptions(refreshIntervalSelect, '60');

        expect(mockAccessibility.announce).toHaveBeenCalledWith('Refresh interval set to 60 seconds');
    });

    test('manually refreshes data', async () => {
        const user = userEvent.setup();
        render(<AnalyticsManager />);

        await waitFor(() => {
            expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
        });

        // Clear the initial call
        ApiService.getAnalytics.mockClear();

        const refreshButton = screen.getByLabelText('Manually refresh analytics data');
        await user.click(refreshButton);

        await waitFor(() => {
            expect(ApiService.getAnalytics).toHaveBeenCalledWith('24h');
        });
        
        expect(mockAccessibility.announce).toHaveBeenCalledWith('Analytics data updated');
    });

    test('handles CSV export link correctly', async () => {
        render(<AnalyticsManager />);

        await waitFor(() => {
            expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
        });

        const csvLink = screen.getByText('CSV (Errors)');
        expect(csvLink).toBeInTheDocument();
        expect(csvLink).toHaveAttribute('href', '#'); // Mocked CSVLink
    });

    test('accessibility features are properly implemented', async () => {
        render(<AnalyticsManager />);

        await waitFor(() => {
            expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
        });

        // Check ARIA labels
        expect(screen.getByLabelText('System uptime percentage')).toBeInTheDocument();
        expect(screen.getByLabelText('Average response time')).toBeInTheDocument();
        expect(screen.getByLabelText('Active devices count')).toBeInTheDocument();
        expect(screen.getByLabelText('Error count')).toBeInTheDocument();

        // Check chart accessibility
        expect(screen.getByLabelText('Performance metrics chart showing CPU, memory, and network usage over time')).toBeInTheDocument();
        expect(screen.getByLabelText('Usage statistics bar chart showing counts for different system features')).toBeInTheDocument();
    });

    test('renders with custom props', () => {
        render(<AnalyticsManager defaultTimeRange="7d" autoRefreshEnabled={false} />);
        
        // Component should render with custom props
        expect(screen.getByText('Loading analytics...')).toBeInTheDocument();
    });
});