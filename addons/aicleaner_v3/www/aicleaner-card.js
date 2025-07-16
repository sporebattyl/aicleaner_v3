class AICleanerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    this._hass = hass;
    
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
  
  getCardSize()
</augment_code_snippet>