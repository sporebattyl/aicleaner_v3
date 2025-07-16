import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigurationManager } from '../ConfigurationManager';
import { ApiService } from '../../services/ApiService';

// Mock ApiService
jest.mock('../../services/ApiService');

describe('ConfigurationManager', () => {
  const mockConfig = {
    ai: {
      primary_provider: 'openai',
      api_key: 'test-key'
    },
    mqtt: {
      broker_host: 'localhost',
      broker_port: 1883,
      use_tls: false
    }
  };

  beforeEach(() => {
    ApiService.getConfiguration.mockResolvedValue(mockConfig);
    ApiService.updateConfiguration.mockResolvedValue({ status: 'success' });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('renders configuration form', async () => {
    render(<ConfigurationManager />);
    
    expect(screen.getByText('Loading configuration...')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByText('AICleaner v3 Configuration')).toBeInTheDocument();
    });

    expect(screen.getByText('AI Provider Settings')).toBeInTheDocument();
    expect(screen.getByText('MQTT Settings')).toBeInTheDocument();
  });

  test('loads and displays configuration data', async () => {
    render(<ConfigurationManager />);

    await waitFor(() => {
      expect(ApiService.getConfiguration).toHaveBeenCalled();
    });

    expect(screen.getByDisplayValue('openai')).toBeInTheDocument();
    expect(screen.getByDisplayValue('localhost')).toBeInTheDocument();
    expect(screen.getByDisplayValue('1883')).toBeInTheDocument();
  });

  test('updates AI provider configuration', async () => {
    const user = userEvent.setup();
    render(<ConfigurationManager />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('openai')).toBeInTheDocument();
    });

    const providerSelect = screen.getByDisplayValue('openai');
    await user.selectOptions(providerSelect, 'anthropic');

    const saveButton = screen.getByText('Save Configuration');
    await user.click(saveButton);

    await waitFor(() => {
      expect(ApiService.updateConfiguration).toHaveBeenCalledWith(
        expect.objectContaining({
          ai: expect.objectContaining({
            primary_provider: 'anthropic'
          })
        })
      );
    });
  });

  test('updates MQTT configuration', async () => {
    const user = userEvent.setup();
    render(<ConfigurationManager />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('localhost')).toBeInTheDocument();
    });

    const hostInput = screen.getByDisplayValue('localhost');
    await user.clear(hostInput);
    await user.type(hostInput, '192.168.1.100');

    const tlsCheckbox = screen.getByRole('checkbox', { name: /use tls encryption/i });
    await user.click(tlsCheckbox);

    const saveButton = screen.getByText('Save Configuration');
    await user.click(saveButton);

    await waitFor(() => {
      expect(ApiService.updateConfiguration).toHaveBeenCalledWith(
        expect.objectContaining({
          mqtt: expect.objectContaining({
            broker_host: '192.168.1.100',
            use_tls: true
          })
        })
      );
    });
  });

  test('shows success message after saving', async () => {
    const user = userEvent.setup();
    render(<ConfigurationManager />);

    await waitFor(() => {
      expect(screen.getByText('Save Configuration')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save Configuration');
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Configuration saved successfully!')).toBeInTheDocument();
    });
  });

  test('handles API errors gracefully', async () => {
    ApiService.getConfiguration.mockRejectedValue(new Error('API Error'));
    
    render(<ConfigurationManager />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load configuration')).toBeInTheDocument();
    });
  });

  test('disables save button while saving', async () => {
    const user = userEvent.setup();
    ApiService.updateConfiguration.mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 1000))
    );

    render(<ConfigurationManager />);

    await waitFor(() => {
      expect(screen.getByText('Save Configuration')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save Configuration');
    await user.click(saveButton);

    expect(screen.getByText('Saving...')).toBeInTheDocument();
    expect(saveButton).toBeDisabled();
  });

  test('validates required fields', async () => {
    const user = userEvent.setup();
    render(<ConfigurationManager />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('localhost')).toBeInTheDocument();
    });

    const hostInput = screen.getByDisplayValue('localhost');
    await user.clear(hostInput);

    const saveButton = screen.getByText('Save Configuration');
    await user.click(saveButton);

    // Should not call API with empty required field
    expect(ApiService.updateConfiguration).not.toHaveBeenCalled();
  });

  test('is accessible with keyboard navigation', async () => {
    render(<ConfigurationManager />);

    await waitFor(() => {
      expect(screen.getByText('AICleaner v3 Configuration')).toBeInTheDocument();
    });

    // Test tab navigation through form elements
    const providerSelect = screen.getByDisplayValue('openai');
    providerSelect.focus();
    expect(providerSelect).toHaveFocus();

    fireEvent.keyDown(providerSelect, { key: 'Tab' });
    const apiKeyInput = screen.getByPlaceholderText('Enter API key');
    expect(apiKeyInput).toHaveFocus();
  });
});