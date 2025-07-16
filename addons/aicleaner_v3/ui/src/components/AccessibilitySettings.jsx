import React, { useState, useEffect } from 'react';
import { Card, Form, Button, Badge, Alert } from 'react-bootstrap';
import { useAccessibility } from '../utils/AccessibilityManager';

export const AccessibilitySettings = () => {
    const { highContrast, toggleHighContrast, announce } = useAccessibility();
    const [settings, setSettings] = useState({
        highContrast: false,
        reducedMotion: false,
        fontSize: 'medium',
        screenReader: false,
        keyboardOnly: false
    });

    useEffect(() => {
        // Load saved accessibility settings
        const savedSettings = localStorage.getItem('aicleaner_accessibility_settings');
        if (savedSettings) {
            try {
                const parsed = JSON.parse(savedSettings);
                setSettings(prev => ({ ...prev, ...parsed }));
            } catch (e) {
                console.warn('Failed to parse accessibility settings:', e);
            }
        }

        // Detect system preferences
        const mediaQueries = {
            reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)'),
            highContrast: window.matchMedia('(prefers-contrast: high)'),
            largeFonts: window.matchMedia('(min-resolution: 192dpi)')
        };

        setSettings(prev => ({
            ...prev,
            highContrast: highContrast || mediaQueries.highContrast.matches,
            reducedMotion: mediaQueries.reducedMotion.matches
        }));

        // Listen for system preference changes
        Object.entries(mediaQueries).forEach(([key, mq]) => {
            mq.addEventListener('change', (e) => {
                setSettings(prev => ({ ...prev, [key]: e.matches }));
            });
        });

        return () => {
            Object.values(mediaQueries).forEach(mq => {
                mq.removeEventListener('change', () => {});
            });
        };
    }, [highContrast]);

    const updateSetting = (key, value) => {
        const newSettings = { ...settings, [key]: value };
        setSettings(newSettings);
        
        // Save to localStorage
        localStorage.setItem('aicleaner_accessibility_settings', JSON.stringify(newSettings));
        
        // Apply settings
        applySetting(key, value);
        
        // Announce change
        announce(`${key} ${value ? 'enabled' : 'disabled'}`);
    };

    const applySetting = (key, value) => {
        switch (key) {
            case 'highContrast':
                if (value !== highContrast) {
                    toggleHighContrast();
                }
                break;
            case 'reducedMotion':
                document.body.classList.toggle('reduced-motion', value);
                break;
            case 'fontSize':
                document.documentElement.className = document.documentElement.className
                    .replace(/font-size-\w+/g, '');
                document.documentElement.classList.add(`font-size-${value}`);
                break;
            case 'screenReader':
                document.body.classList.toggle('screen-reader-mode', value);
                break;
            case 'keyboardOnly':
                document.body.classList.toggle('keyboard-only-mode', value);
                break;
        }
    };

    const resetToDefaults = () => {
        const defaultSettings = {
            highContrast: false,
            reducedMotion: false,
            fontSize: 'medium',
            screenReader: false,
            keyboardOnly: false
        };
        
        setSettings(defaultSettings);
        localStorage.removeItem('aicleaner_accessibility_settings');
        
        // Apply default settings
        Object.entries(defaultSettings).forEach(([key, value]) => {
            applySetting(key, value);
        });
        
        announce('Accessibility settings reset to defaults');
    };

    const runAccessibilityTest = () => {
        announce('Running accessibility test');
        
        // Simple accessibility audit
        const issues = [];
        
        // Check for images without alt text
        const imagesWithoutAlt = document.querySelectorAll('img:not([alt])');
        if (imagesWithoutAlt.length > 0) {
            issues.push(`${imagesWithoutAlt.length} images missing alt text`);
        }
        
        // Check for buttons without labels
        const buttonsWithoutLabels = document.querySelectorAll('button:not([aria-label]):not([aria-labelledby])');
        if (buttonsWithoutLabels.length > 0) {
            issues.push(`${buttonsWithoutLabels.length} buttons missing labels`);
        }
        
        // Check for form inputs without labels
        const inputsWithoutLabels = document.querySelectorAll('input:not([aria-label]):not([aria-labelledby])');
        if (inputsWithoutLabels.length > 0) {
            issues.push(`${inputsWithoutLabels.length} form inputs missing labels`);
        }
        
        if (issues.length === 0) {
            announce('No accessibility issues found');
        } else {
            announce(`Found ${issues.length} accessibility issues: ${issues.join(', ')}`);
        }
    };

    return (
        <Card>
            <Card.Header>
                <h4>Accessibility Settings</h4>
                <p className="text-muted mb-0">
                    Customize the interface to meet your accessibility needs
                </p>
            </Card.Header>
            <Card.Body>
                <Alert variant="info" className="mb-3">
                    <strong>Tip:</strong> These settings are automatically detected from your system preferences 
                    and can be customized here.
                </Alert>

                {/* Visual Accessibility */}
                <Card className="mb-3">
                    <Card.Header>
                        <h6>Visual Accessibility</h6>
                    </Card.Header>
                    <Card.Body>
                        <Form.Group className="mb-3">
                            <Form.Check
                                type="switch"
                                id="high-contrast-switch"
                                label="High Contrast Mode"
                                checked={settings.highContrast}
                                onChange={(e) => updateSetting('highContrast', e.target.checked)}
                                aria-describedby="high-contrast-help"
                            />
                            <Form.Text id="high-contrast-help" className="text-muted">
                                Increases contrast between text and background for better visibility
                            </Form.Text>
                        </Form.Group>

                        <Form.Group className="mb-3">
                            <Form.Label htmlFor="font-size-select">
                                Font Size
                            </Form.Label>
                            <Form.Select
                                id="font-size-select"
                                value={settings.fontSize}
                                onChange={(e) => updateSetting('fontSize', e.target.value)}
                                aria-describedby="font-size-help"
                            >
                                <option value="small">Small</option>
                                <option value="medium">Medium (Default)</option>
                                <option value="large">Large</option>
                                <option value="xl">Extra Large</option>
                            </Form.Select>
                            <Form.Text id="font-size-help" className="text-muted">
                                Adjust text size throughout the interface
                            </Form.Text>
                        </Form.Group>
                    </Card.Body>
                </Card>

                {/* Motor Accessibility */}
                <Card className="mb-3">
                    <Card.Header>
                        <h6>Motor Accessibility</h6>
                    </Card.Header>
                    <Card.Body>
                        <Form.Group className="mb-3">
                            <Form.Check
                                type="switch"
                                id="reduced-motion-switch"
                                label="Reduce Motion"
                                checked={settings.reducedMotion}
                                onChange={(e) => updateSetting('reducedMotion', e.target.checked)}
                                aria-describedby="reduced-motion-help"
                            />
                            <Form.Text id="reduced-motion-help" className="text-muted">
                                Minimizes animations and transitions that may cause discomfort
                            </Form.Text>
                        </Form.Group>

                        <Form.Group className="mb-3">
                            <Form.Check
                                type="switch"
                                id="keyboard-only-switch"
                                label="Keyboard-Only Navigation"
                                checked={settings.keyboardOnly}
                                onChange={(e) => updateSetting('keyboardOnly', e.target.checked)}
                                aria-describedby="keyboard-only-help"
                            />
                            <Form.Text id="keyboard-only-help" className="text-muted">
                                Optimizes interface for keyboard-only navigation
                            </Form.Text>
                        </Form.Group>
                    </Card.Body>
                </Card>

                {/* Screen Reader */}
                <Card className="mb-3">
                    <Card.Header>
                        <h6>Screen Reader Support</h6>
                    </Card.Header>
                    <Card.Body>
                        <Form.Group className="mb-3">
                            <Form.Check
                                type="switch"
                                id="screen-reader-switch"
                                label="Screen Reader Mode"
                                checked={settings.screenReader}
                                onChange={(e) => updateSetting('screenReader', e.target.checked)}
                                aria-describedby="screen-reader-help"
                            />
                            <Form.Text id="screen-reader-help" className="text-muted">
                                Provides additional context and descriptions for screen readers
                            </Form.Text>
                        </Form.Group>

                        <Alert variant="info" className="mb-0">
                            <strong>Screen Reader Detected:</strong> 
                            {navigator.userAgent.includes('NVDA') ? ' NVDA' :
                             navigator.userAgent.includes('JAWS') ? ' JAWS' :
                             navigator.userAgent.includes('VoiceOver') ? ' VoiceOver' :
                             ' No specific screen reader detected'}
                        </Alert>
                    </Card.Body>
                </Card>

                {/* Current Status */}
                <Card className="mb-3">
                    <Card.Header>
                        <h6>Current Status</h6>
                    </Card.Header>
                    <Card.Body>
                        <div className="d-flex flex-wrap gap-2 mb-3">
                            <Badge bg={settings.highContrast ? 'success' : 'secondary'}>
                                High Contrast: {settings.highContrast ? 'On' : 'Off'}
                            </Badge>
                            <Badge bg={settings.reducedMotion ? 'success' : 'secondary'}>
                                Reduced Motion: {settings.reducedMotion ? 'On' : 'Off'}
                            </Badge>
                            <Badge bg={settings.fontSize !== 'medium' ? 'info' : 'secondary'}>
                                Font Size: {settings.fontSize}
                            </Badge>
                            <Badge bg={settings.screenReader ? 'success' : 'secondary'}>
                                Screen Reader: {settings.screenReader ? 'On' : 'Off'}
                            </Badge>
                            <Badge bg={settings.keyboardOnly ? 'success' : 'secondary'}>
                                Keyboard Only: {settings.keyboardOnly ? 'On' : 'Off'}
                            </Badge>
                        </div>
                    </Card.Body>
                </Card>

                {/* Actions */}
                <div className="d-flex gap-2 flex-wrap">
                    <Button
                        variant="primary"
                        onClick={runAccessibilityTest}
                        aria-describedby="test-help"
                    >
                        Test Accessibility
                    </Button>
                    <Button
                        variant="outline-secondary"
                        onClick={resetToDefaults}
                        aria-describedby="reset-help"
                    >
                        Reset to Defaults
                    </Button>
                    <Button
                        variant="outline-info"
                        onClick={() => announce('Accessibility settings configured')}
                        aria-describedby="announce-help"
                    >
                        Test Screen Reader
                    </Button>
                </div>

                <div className="mt-2">
                    <Form.Text id="test-help" className="text-muted d-block">
                        Test: Runs a basic accessibility audit of the current page
                    </Form.Text>
                    <Form.Text id="reset-help" className="text-muted d-block">
                        Reset: Restores all settings to their default values
                    </Form.Text>
                    <Form.Text id="announce-help" className="text-muted d-block">
                        Test: Sends a test message to screen readers
                    </Form.Text>
                </div>
            </Card.Body>
        </Card>
    );
};

export default AccessibilitySettings;