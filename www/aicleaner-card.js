/**
 * DebugManager for conditional console logging in production
 * Supports multiple debug sources: localhost, URL params, localStorage, and HA entity
 */
class DebugManager {
  constructor(options = {}) {
    this.hassCheckInterval = options.hassCheckInterval || 5000;
    this.baseCheckInterval = options.baseCheckInterval || 30000;
    this.debugEnabled = this.calculateDebugState();
    this.lastHassCheck = 0;
    this.lastBaseCheck = 0;
  }
  
  calculateDebugState() {
    return (window.location.hostname === 'localhost' || 
            window.location.search.includes('debug=true') ||
            localStorage.getItem('aicleaner_debug') === 'true');
  }
  
  updateDebugState(hass) {
    const now = Date.now();
    
    // Periodically re-check base debug state (localStorage, URL params)
    if (now - this.lastBaseCheck > this.baseCheckInterval) {
      const baseState = this.calculateDebugState();
      if (baseState !== this.debugEnabled) {
        this.debugEnabled = baseState;
        this.log('info', `Debug mode ${baseState ? 'enabled' : 'disabled'} via base detection`);
      }
      this.lastBaseCheck = now;
    }
    
    // Check HA entity state (with error handling)
    if (hass && (now - this.lastHassCheck > this.hassCheckInterval)) {
      try {
        const debugEntity = hass.states?.['input_boolean.aicleaner_debug_mode'];
        if (debugEntity && debugEntity.state) {
          const hassDebugState = debugEntity.state === 'on';
          if (hassDebugState !== this.debugEnabled) {
            this.debugEnabled = hassDebugState;
            this.log('info', `Debug mode ${hassDebugState ? 'enabled' : 'disabled'} via HA entity`);
          }
        }
      } catch (error) {
        // Silently handle HA state access errors
        this.log('warn', 'Failed to check HA debug entity:', error.message);
      }
      this.lastHassCheck = now;
    }
  }
  
  log(level, ...args) {
    // Always show errors and warnings, only show info/debug when enabled
    if (this.debugEnabled || ['warn', 'error'].includes(level)) {
      console[level]('[AICleaner]', ...args);
    }
  }
}

// Initialize debug manager singleton
const debugManager = new DebugManager({
  hassCheckInterval: 5000,    // Check HA every 5s
  baseCheckInterval: 30000    // Check localStorage/URL every 30s
});

class AICleanerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    this._hass = hass;
    debugManager.updateDebugState(hass);
    
    if (!this.content) {
      this.content = document.createElement('div');
      this.content.className = 'card-content';
      this.shadowRoot.appendChild(this.content);
      
      const style = document.createElement('style');
      style.textContent = `
        .card-content {
          padding: 16px;
        }
        .zone {
          margin-bottom: 16px;
          padding: 16px;
          border-radius: 8px;
          background-color: var(--card-background-color, #fff);
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          position: relative;
        }
        .zone.error {
          border: 2px solid var(--error-color, #f44336);
          background-color: rgba(244, 67, 54, 0.1);
        }
        .error-message {
          color: var(--error-color, #f44336);
          font-weight: bold;
          margin-top: 8px;
          margin-bottom: 12px;
          padding: 8px;
          background-color: rgba(244, 67, 54, 0.15);
          border-radius: 4px;
        }
        .troubleshoot-button {
          background-color: var(--warning-color, #ff9800);
          margin-left: 8px;
        }
        .troubleshoot-button:hover {
          background-color: #e68900;
        }
        .error-icon {
          position: absolute;
          top: 16px;
          right: 16px;
          color: var(--error-color, #f44336);
          font-size: 20px;
        }
        .zone-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        .zone-name {
          font-size: 18px;
          font-weight: bold;
        }
        .scores {
          display: flex;
          gap: 16px;
          margin-bottom: 8px;
        }
        .score {
          text-align: center;
        }
        .score-value {
          font-size: 24px;
          font-weight: bold;
        }
        .score-label {
          font-size: 12px;
          color: var(--secondary-text-color);
        }
        .tasks {
          margin-top: 16px;
        }
        .task-count {
          font-size: 14px;
          margin-bottom: 8px;
        }
        .task-list {
          max-height: 200px;
          overflow-y: auto;
        }
        .task {
          padding: 8px;
          border-radius: 4px;
          margin-bottom: 4px;
          background-color: var(--secondary-background-color);
        }
        .button {
          background-color: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          padding: 8px 16px;
          cursor: pointer;
        }
        .last-updated {
          font-size: 12px;
          color: var(--secondary-text-color);
          margin-top: 8px;
          text-align: right;
        }
      `;
      this.shadowRoot.appendChild(style);
    }
    
    this._updateContent();
  }
  
  _updateContent() {
    if (!this._hass || !this.config) {
      return;
    }
    
    // Clear content
    this.content.innerHTML = '';
    
    // Find all AI Cleaner sensors
    const aiCleanerSensors = Object.keys(this._hass.states)
      .filter(entityId => entityId.startsWith('sensor.aicleaner_'))
      .map(entityId => this._hass.states[entityId]);
    
    if (aiCleanerSensors.length === 0) {
      this.content.innerHTML = '<div>No AI Cleaner zones found</div>';
      return;
    }
    
    // Create zone cards
    aiCleanerSensors.forEach(sensor => {
      const zone = document.createElement('div');
      zone.className = 'zone';
      
      const zoneName = sensor.attributes.zone_name || 'Unknown Zone';
      const cleanlinessScore = sensor.attributes.cleanliness_score || 0;
      const organizationScore = sensor.attributes.organization_score || 0;
      const activeTasks = sensor.attributes.active_tasks || 0;
      const completedTasks = sensor.attributes.completed_tasks || 0;
      const lastUpdated = sensor.attributes.last_updated || '';
      
      // Format last updated time
      let lastUpdatedText = '';
      if (lastUpdated) {
        const lastUpdatedDate = new Date(lastUpdated);
        lastUpdatedText = `Last updated: ${lastUpdatedDate.toLocaleString()}`;
      }
      
      zone.innerHTML = `
        <div class="zone-header">
          <div class="zone-name">${zoneName}</div>
          <button class="button analyze-button" data-zone="${zoneName}">Analyze Now</button>
        </div>
        
        <div class="scores">
          <div class="score">
            <div class="score-value">${cleanlinessScore}</div>
            <div class="score-label">Cleanliness</div>
          </div>
          <div class="score">
            <div class="score-value">${organizationScore}</div>
            <div class="score-label">Organization</div>
          </div>
        </div>
        
        <div class="tasks">
          <div class="task-count">
            ${activeTasks} active tasks, ${completedTasks} completed
          </div>
        </div>
        
        <div class="last-updated">${lastUpdatedText}</div>
      `;
      
      // Add event listener to analyze button
      const analyzeButton = zone.querySelector('.analyze-button');
      if (analyzeButton) {
        analyzeButton.addEventListener('click', () => {
          const zoneName = analyzeButton.getAttribute('data-zone');
          this._callService(zoneName);
        });
      }
      
      this.content.appendChild(zone);
    });
  }
  
  _callService(zoneName) {
    this._hass.callService('aicleaner', 'analyze_zone', {
      zone_name: zoneName
    });
  }
  
  setConfig(config) {
    this.config = config;
  }
  
  getCardSize() {
    // Dynamic card size based on configuration and zone count
    const zones = this.config?.zones || [];
    const baseSize = 3; // Minimum card height
    const zoneSize = Math.ceil(zones.length / 2); // 2 zones per row
    return Math.max(baseSize, zoneSize + 2);
  }

  // Initialize charts for analytics view
  initializeCharts() {
    // Check if Chart.js is available
    if (typeof Chart === 'undefined') {
      debugManager.log('warn', 'Chart.js not loaded. Analytics charts will not be available.');
      // Display fallback message
      const analyticsContainer = this.shadowRoot.querySelector('.analytics-view');
      if (analyticsContainer) {
        analyticsContainer.innerHTML = `
          <div class="chart-fallback">
            <p>📊 Analytics charts require Chart.js</p>
            <p>Add Chart.js script before loading this card:</p>
            <code>&lt;script src="https://cdn.jsdelivr.net/npm/chart.js"&gt;&lt;/script&gt;</code>
          </div>
        `;
      }
      return;
    }

    // Clear existing charts
    if (this.charts) {
      Object.values(this.charts).forEach(chart => chart.destroy());
    }
    this.charts = {};

    // Create chart containers if they don't exist
    this.createChartContainers();
    
    // Initialize basic charts
    this.createTaskStatusChart();
    this.createZonePerformanceChart();
    this.createActivityTrendChart();
  }

  createChartContainers() {
    const analyticsContainer = this.shadowRoot.querySelector('.analytics-view');
    if (!analyticsContainer) return;

    analyticsContainer.innerHTML = `
      <div class="charts-grid">
        <div class="chart-card">
          <h3>Task Status</h3>
          <canvas id="taskStatusChart"></canvas>
        </div>
        <div class="chart-card">
          <h3>Zone Performance</h3>
          <canvas id="zonePerformanceChart"></canvas>
        </div>
        <div class="chart-card">
          <h3>Activity Trend</h3>
          <canvas id="activityTrendChart"></canvas>
        </div>
      </div>
    `;

    // Add chart styles
    const style = document.createElement('style');
    style.textContent = `
      .charts-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 16px;
        padding: 16px;
      }
      .chart-card {
        background: var(--card-background-color);
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      }
      .chart-card h3 {
        margin: 0 0 16px 0;
        color: var(--primary-text-color);
      }
      .chart-fallback {
        padding: 32px;
        text-align: center;
        color: var(--secondary-text-color);
      }
      .chart-fallback code {
        background: var(--secondary-background-color);
        padding: 8px;
        border-radius: 4px;
        font-family: monospace;
      }
    `;
    this.shadowRoot.appendChild(style);
  }

  createTaskStatusChart() {
    const canvas = this.shadowRoot.getElementById('taskStatusChart');
    if (!canvas) return;

    // Get data from Home Assistant states
    const taskData = this.getTaskStatusData();
    
    this.charts.taskStatus = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: ['Completed', 'Active', 'Pending', 'Error'],
        datasets: [{
          data: [taskData.completed, taskData.active, taskData.pending, taskData.error],
          backgroundColor: ['#4caf50', '#2196f3', '#ff9800', '#f44336'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom'
          }
        }
      }
    });
  }

  createZonePerformanceChart() {
    const canvas = this.shadowRoot.getElementById('zonePerformanceChart');
    if (!canvas) return;

    const performanceData = this.getZonePerformanceData();
    
    this.charts.zonePerformance = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: performanceData.labels,
        datasets: [{
          label: 'Completion Rate (%)',
          data: performanceData.completionRates,
          backgroundColor: '#2196f3',
          borderColor: '#1976d2',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            max: 100
          }
        }
      }
    });
  }

  createActivityTrendChart() {
    const canvas = this.shadowRoot.getElementById('activityTrendChart');
    if (!canvas) return;

    const trendData = this.getActivityTrendData();
    
    this.charts.activityTrend = new Chart(canvas, {
      type: 'line',
      data: {
        labels: trendData.labels,
        datasets: [{
          label: 'Tasks Completed',
          data: trendData.completed,
          borderColor: '#4caf50',
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          tension: 0.4
        }, {
          label: 'Tasks Created',
          data: trendData.created,
          borderColor: '#2196f3',
          backgroundColor: 'rgba(33, 150, 243, 0.1)',
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false
        }
      }
    });
  }

  // Data extraction methods
  getTaskStatusData() {
    if (!this._hass) return { completed: 0, active: 0, pending: 0, error: 0 };
    
    const aiCleanerSensors = Object.keys(this._hass.states)
      .filter(entityId => entityId.startsWith('sensor.aicleaner_'))
      .map(entityId => this._hass.states[entityId]);

    let completed = 0, active = 0, pending = 0, error = 0;
    
    aiCleanerSensors.forEach(sensor => {
      const attributes = sensor.attributes || {};
      completed += parseInt(attributes.completed_tasks || 0);
      active += parseInt(attributes.active_tasks || 0);
      pending += parseInt(attributes.pending_tasks || 0);
      error += parseInt(attributes.error_tasks || 0);
    });

    return { completed, active, pending, error };
  }

  getZonePerformanceData() {
    if (!this._hass) return { labels: [], completionRates: [] };
    
    const aiCleanerSensors = Object.keys(this._hass.states)
      .filter(entityId => entityId.startsWith('sensor.aicleaner_') && entityId.includes('_tasks'))
      .map(entityId => this._hass.states[entityId]);

    const labels = [];
    const completionRates = [];
    
    aiCleanerSensors.forEach(sensor => {
      const attributes = sensor.attributes || {};
      const zoneName = attributes.zone_name || 'Unknown';
      const completed = parseInt(attributes.completed_tasks || 0);
      const total = completed + parseInt(attributes.active_tasks || 0) + parseInt(attributes.pending_tasks || 0);
      const rate = total > 0 ? Math.round((completed / total) * 100) : 0;
      
      labels.push(zoneName);
      completionRates.push(rate);
    });

    return { labels, completionRates };
  }

  getActivityTrendData() {
    // For now, return mock trend data
    // In a full implementation, this would fetch from HA history API
    const labels = [];
    const completed = [];
    const created = [];
    
    // Generate last 7 days
    for (let i = 6; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
      
      // Mock data - replace with actual HA history data
      completed.push(Math.floor(Math.random() * 50) + 10);
      created.push(Math.floor(Math.random() * 60) + 15);
    }

    return { labels, completed, created };
  }
}
</augment_code_snippet>