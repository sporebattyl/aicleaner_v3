// Global variables to store fetched entities
let availableCameraEntities = [];
let availableTodoListEntities = [];
let zoneConfig = []; // This will hold the current configuration

document.addEventListener('DOMContentLoaded', async () => {
    // IMPORTANT: HASSIO_TOKEN should be securely provided by the addon's backend
    // and NOT hardcoded here. For example, it could be injected into the HTML
    // or fetched from a secure endpoint exposed by the addon's backend.
    const HASSIO_TOKEN = 'YOUR_HASSIO_TOKEN'; // Placeholder

    // Fetch entities when the page loads
    const { cameraEntities, todoListEntities } = await fetchHomeAssistantEntities(HASSIO_TOKEN);
    availableCameraEntities = cameraEntities;
    availableTodoListEntities = todoListEntities;

    // Load existing configuration
    zoneConfig = await loadExistingConfig(); // This function needs to be implemented in the addon's backend

    if (zoneConfig.length === 0) {
        addZoneEntry(); // Add one empty zone entry if no config exists
    } else {
        zoneConfig.forEach(zone => addZoneEntry(zone));
    }

    document.getElementById('add-zone-button').addEventListener('click', () => addZoneEntry());
    document.getElementById('save-config-button').addEventListener('click', saveZoneConfiguration);
});

/**
 * Fetches camera and todo list entities from the Home Assistant API.
 * @param {string} token The Home Assistant Supervisor token.
 * @returns {Promise<{cameraEntities: Array, todoListEntities: Array}>}
 */
async function fetchHomeAssistantEntities(token) {
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };

    try {
        // Assuming the addon can directly access the Home Assistant Core API via the supervisor
        const response = await fetch('http://supervisor/core/api/states', { headers: headers });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const entities = await response.json();

        const cameraEntities = entities.filter(entity => entity.entity_id.startsWith('camera.'));
        const todoListEntities = entities.filter(entity => entity.entity_id.startsWith('todo.'));

        return { cameraEntities, todoListEntities };
    } catch (error) {
        console.error("Error fetching Home Assistant entities:", error);
        return { cameraEntities: [], todoListEntities: [] };
    }
}

/**
 * Creates a dropdown (select) element populated with Home Assistant entities.
 * @param {Array} entities An array of Home Assistant entity objects.
 * @param {string} selectedEntityId The entity_id to pre-select in the dropdown.
 * @returns {HTMLSelectElement} The created select element.
 */
function createDropdown(entities, selectedEntityId = '') {
    const select = document.createElement('select');
    select.className = 'entity-dropdown';
    let defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Select an entity';
    select.appendChild(defaultOption);

    entities.forEach(entity => {
        const option = document.createElement('option');
        option.value = entity.entity_id;
        option.textContent = `${entity.attributes.friendly_name || entity.entity_id} (${entity.entity_id})`;
        if (entity.entity_id === selectedEntityId) {
            option.selected = true;
        }
        select.appendChild(option);
    });
    return select;
}

/**
 * Adds a new zone entry to the form, optionally pre-filling with existing data.
 * @param {Object} zone An optional zone object to pre-fill the form fields.
 */
function addZoneEntry(zone = {}) {
    const zonesContainer = document.getElementById('zones-container');
    const zoneDiv = document.createElement('div');
    zoneDiv.className = 'zone-entry';
    zoneDiv.style.border = '1px solid var(--divider-color)';
    zoneDiv.style.borderRadius = '8px';
    zoneDiv.style.padding = '16px';
    zoneDiv.style.margin = '16px 0';
    zoneDiv.style.backgroundColor = 'var(--card-background-color)';

    const zoneIndex = zonesContainer.children.length; // Simple index for now

    zoneDiv.innerHTML = `
        <h3>Zone ${zoneIndex + 1}</h3>
        <div class="form-row">
            <label for="zone-name-${zoneIndex}">Name:</label>
            <input type="text" id="zone-name-${zoneIndex}" class="zone-name" value="${zone.name || ''}" placeholder="e.g., Living Room">
        </div>
        <div class="form-row">
            <label for="camera-entity-${zoneIndex}">Camera Entity:</label>
            <div id="camera-dropdown-container-${zoneIndex}" class="dropdown-container"></div>
        </div>
        <div class="form-row">
            <label for="todo-list-entity-${zoneIndex}">Todo List Entity:</label>
            <div id="todo-list-dropdown-container-${zoneIndex}" class="dropdown-container"></div>
        </div>
        <div class="form-row">
            <label for="zone-purpose-${zoneIndex}">Purpose:</label>
            <textarea id="zone-purpose-${zoneIndex}" class="zone-purpose" rows="3" placeholder="e.g., Living room for relaxation and entertainment">${zone.purpose || ''}</textarea>
        </div>
        <div class="form-row">
            <label for="zone-interval-${zoneIndex}">Interval Minutes:</label>
            <input type="number" id="zone-interval-${zoneIndex}" class="zone-interval" value="${zone.interval_minutes || 60}" min="1">
        </div>
        <div class="form-row">
            <label for="zone-ignore-rules-${zoneIndex}">Ignore Rules (one per line):</label>
            <textarea id="zone-ignore-rules-${zoneIndex}" class="zone-ignore-rules" rows="4" placeholder="e.g., Ignore items on the coffee table\nDon't worry about books on the bookshelf">${(zone.ignore_rules || []).join('\n')}</textarea>
        </div>
        <button class="remove-zone-button">Remove Zone</button>
    `;

    const cameraDropdownContainer = zoneDiv.querySelector(`#camera-dropdown-container-${zoneIndex}`);
    cameraDropdownContainer.appendChild(createDropdown(availableCameraEntities, zone.camera_entity));

    const todoListDropdownContainer = zoneDiv.querySelector(`#todo-list-dropdown-container-${zoneIndex}`);
    todoListDropdownContainer.appendChild(createDropdown(availableTodoListEntities, zone.todo_list_entity));

    zoneDiv.querySelector('.remove-zone-button').addEventListener('click', () => {
        zonesContainer.removeChild(zoneDiv);
        // Note: If you need to maintain a strict `zoneConfig` array in sync with the DOM,
        // you'd re-build it or remove the corresponding item here.
        // For simplicity, `saveZoneConfiguration` re-reads the DOM.
    });

    zonesContainer.appendChild(zoneDiv);
}

/**
 * Collects data from the form and sends it to the addon's backend for saving.
 */
async function saveZoneConfiguration() {
    const zonesContainer = document.getElementById('zones-container');
    const zoneEntries = zonesContainer.querySelectorAll('.zone-entry');
    const newZoneConfig = [];
    let isValid = true;

    zoneEntries.forEach(zoneDiv => {
        const name = zoneDiv.querySelector('.zone-name').value.trim();
        const camera_entity = zoneDiv.querySelector('.dropdown-container select.entity-dropdown').value;
        const todo_list_entity = zoneDiv.querySelector('.dropdown-container select.entity-dropdown:nth-of-type(2)').value; // Assuming order
        const purpose = zoneDiv.querySelector('.zone-purpose').value.trim();
        const interval_minutes = parseInt(zoneDiv.querySelector('.zone-interval').value, 10);
        const ignore_rules = zoneDiv.querySelector('.zone-ignore-rules').value
                                .split('\n')
                                .map(rule => rule.trim())
                                .filter(rule => rule !== '');

        if (!name || !camera_entity || !todo_list_entity) {
            isValid = false;
            alert('Please fill in all required fields (Name, Camera, Todo List) for each zone.');
            return; // Exit forEach early if validation fails
        }

        newZoneConfig.push({
            name,
            camera_entity,
            todo_list_entity,
            purpose,
            interval_minutes,
            ignore_rules
        });
    });

    if (!isValid) {
        return; // Stop if any validation failed
    }

    console.log("Attempting to save configuration:", newZoneConfig);

    try {
        // This endpoint needs to be implemented in your addon's backend (e.g., Python Flask/FastAPI)
        // It should receive the JSON, validate it, and write it to your config.yaml.
        const response = await fetch('/api/aicleaner/config/zones', { // Example endpoint
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // If your addon's backend requires authentication for its own endpoints,
                // you might need to pass a token here, but typically not the HASSIO_TOKEN itself.
            },
            body: JSON.stringify({ zones: newZoneConfig }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }

        const result = await response.json();
        console.log("Configuration saved successfully:", result);
        alert("Configuration saved successfully!");
        // Optionally, reload the config after saving to reflect any backend processing
        zoneConfig = await loadExistingConfig();
        document.getElementById('zones-container').innerHTML = ''; // Clear existing
        zoneConfig.forEach(zone => addZoneEntry(zone)); // Re-render
    } catch (error) {
        console.error("Error saving configuration:", error);
        alert("Failed to save configuration. Check console for details.");
    }
}

/**
 * Placeholder for loading existing configuration from the addon's backend.
 * This function needs to be implemented in the addon's backend.
 * @returns {Promise<Array>} A promise that resolves to an array of zone objects.
 */
async function loadExistingConfig() {
    try {
        // This endpoint needs to be implemented in your addon's backend
        const response = await fetch('/api/aicleaner/config/zones'); // Example endpoint
        if (!response.ok) {
            // If config doesn't exist or error, return empty array
            if (response.status === 404) {
                console.warn("No existing zone configuration found.");
                return [];
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data.zones || []; // Assuming the response has a 'zones' key
    } catch (error) {
        console.error("Error loading existing configuration:", error);
        return [];
    }
}