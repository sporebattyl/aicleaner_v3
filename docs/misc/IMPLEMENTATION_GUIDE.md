# Implementation Guide for aicleaner_v3 Recommendations

This guide provides step-by-step instructions to implement the changes suggested in `GEMINICRITIQUE.md`.

---

## 1. Version Control & Cleanup

Using a version control system like Git is highly recommended over manual `.backup` files.

### Steps:

1.  **Navigate to the project directory:**
    Open a terminal or command prompt and change your directory to the `aicleaner_v3` folder.
    ```bash
    cd X:/aicleaner_v3
    ```

2.  **Initialize a Git repository:**
    This will create a new `.git` subdirectory that contains all the necessary repository files.
    ```bash
    git init
    ```

3.  **Create a `.gitignore` file:**
    To prevent committing unnecessary files (like `__pycache__` or secrets), create a file named `.gitignore` and add the following content:
    ```
    # Python
    __pycache__/
    *.pyc
    *.pyo
    *.pyd
    .Python
    env/
    venv/

    # Secrets
    secrets.yaml
    ```

4.  **Add all files to staging:**
    This command stages all files in the directory for the first commit.
    ```bash
    git add .
    ```

5.  **Commit the initial files:**
    This saves the current state of your project in the Git history.
    ```bash
    git commit -m "Initial commit of aicleaner_v3"
    ```

6.  **Remove the backup files:**
    Now that your project is tracked by Git, you can safely delete the redundant backup files.
    ```bash
    rm aicleaner.py.backup config.yaml.backup Dockerfile.backup run.sh.backup
    ```

7.  **Commit the deletion:**
    ```bash
    git add .
    git commit -m "Remove redundant backup files"
    ```

---

## 2. Project Documentation

Clear documentation is essential for users and future developers.

### Steps:

1.  **Create a `README.md` file:**
    Create a new file named `README.md` in the `X:/aicleaner_v3/` directory. Add a description of the addon, its features, and instructions for installation and configuration.

2.  **Create a `CHANGELOG.md` file:**
    Create a new file named `CHANGELOG.md` in the `X:/aicleaner_v3/` directory. Use this file to log changes for each new version you release. Here is a simple template:
    ```markdown
    # Changelog

    All notable changes to this project will be documented in this file.

    ## [1.0.0] - 2025-07-10
    ### Added
    - Initial release of the AI Cleaner addon.
    ```

3.  **Clarify Directory Purposes:**
    - In the `X:/aicleaner_v3/www/` directory, create a `README.md` file explaining that it contains static files for the addon's frontend/UI.
    - In the `X:/aicleaner_v3/translations/` directory, create a `README.md` file explaining that it holds translation files for different languages.

---

## 3. Updating Addon Configuration Files

These changes ensure your addon is correctly interpreted by the Home Assistant Supervisor.

### Steps:

1.  **Update `build.yaml`:**
    Open `X:/aicleaner_v3/build.yaml` and replace its content with:
    ```yaml
    build_from:
      aarch64: "ghcr.io/home-assistant/aarch64-base-python:3.11"
      amd64: "ghcr.io/home-assistant/amd64-base-python:3.11"
      armv7: "ghcr.io/home-assistant/armv7-base-python:3.11"
    labels:
      org.opencontainers.image.title: "AI Cleaner"
      org.opencontainers.image.description: "An AI-powered cleaner for your smart home."
      org.opencontainers.image.source: "https://github.com/YOUR_USERNAME/YOUR_REPOSITORY"
      org.opencontainers.image.licenses: "Apache-2.0"
    ```
    *Note: Remember to update the `source` URL to your actual GitHub repository.*

2.  **Update `config.yaml`:**
    Open `X:/aicleaner_v3/config.yaml` and replace its content with:
    ```yaml
    # Basic Addon Configuration
    name: "AI Cleaner"
    version: "1.0.0"
    slug: "aicleaner"
    description: "An AI-powered cleaner for your smart home."
    url: "https://github.com/YOUR_USERNAME/YOUR_REPOSITORY"
    arch:
      - aarch64
      - amd64
      - armv7
    init: false
    map:
      - "config:rw"

    # Addon-specific options
    options:
      log_level: "info"
      api_key: ""
    schema:
      log_level: "list(trace|debug|info|notice|warning|error|fatal)"
      api_key: "password"
    ```

3.  **Update `Dockerfile`:**
    Open `X:/aicleaner_v3/Dockerfile` and replace its content with:
    ```dockerfile
    ARG BUILD_FROM
    FROM ${BUILD_FROM}

    # Set shell
    SHELL ["/bin/bash", "-o", "pipefail", "-c"]

    # Copy requirements
    COPY requirements.txt /
    RUN pip install --no-cache-dir -r /requirements.txt

    # Copy root filesystem
    COPY . /

    # Set entrypoint
    CMD [ "python3", "-u", "/aicleaner.py" ]
    ```

4.  **Update `run.sh`:**
    The `Dockerfile` now calls the Python script directly, which is a more modern approach. You can delete the `run.sh` file.
    ```bash
    rm X:/aicleaner_v3/run.sh
    ```

5.  **Update `services.yaml`:**
    Open `X:/aicleaner_v3/services.yaml` and add content to define the services your addon offers.
    ```yaml
    clean_room:
      name: "Clean Room"
      description: "Starts a cleaning cycle for a specific room."
      fields:
        entity_id:
          name: "Entity"
          description: "The vacuum entity to use for cleaning."
          required: true
          selector:
            entity:
              domain: vacuum
        room:
          name: "Room"
          description: "The name of the room to clean."
          required: true
          example: "living_room"
          selector:
            text:
    ```

---

## 4. Python Code Improvements

Refactor the Python code for better robustness and maintainability.

### Steps:

1.  **Error Handling:**
    Wrap code that makes external calls (e.g., Home Assistant API, web requests) in `try...except` blocks to handle potential failures gracefully.
    *Example in `aicleaner.py`*:
    ```python
    import logging

    _LOGGER = logging.getLogger(__name__)

    try:
        # Code that might fail
        response = requests.get("http://homeassistant.local:8123/api/", timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        _LOGGER.error("Could not connect to Home Assistant API: %s", e)
        # Handle the error, maybe exit or retry
    ```

2.  **Logging:**
    Use the standard Python `logging` module to provide insight into the addon's execution. The Home Assistant base images are configured to route this to the addon logs.
    *Example in `aicleaner.py`*:
    ```python
    import logging

    # At the top of your file
    logging.basicConfig(level=logging.INFO)
    _LOGGER = logging.getLogger(__name__)

    # In your functions
    _LOGGER.info("Starting the AI Cleaner main loop.")
    _LOGGER.debug("Received data: %s", some_variable)
    _LOGGER.warning("Configuration option 'xyz' is deprecated.")
    ```

3.  **Modularity:**
    Break down large functions in `aicleaner.py` and other files into smaller, single-purpose functions. This makes the code easier to read, test, and maintain.
    *Example*: Instead of one giant `main()` function, create separate functions for `setup_mqtt()`, `load_configuration()`, `run_analysis()`, etc., and call them from `main()`.

---

## 5. Security

A security audit is a specialized task.

### Recommendation:

-   Once the addon is functional and stable, consider asking for a peer review from other developers in the Home Assistant community. You can do this on the official forums or the Discord server.
-   Pay special attention to how you handle secrets (like the `api_key`). Ensure they are never logged or exposed in error messages. The `password` schema type in `config.yaml` helps mask this in the UI.

---

## 6. Frontend Critique & Implementation Guide

This section covers the addon's Configuration UI (defined in `config.yaml`) and the Lovelace Dashboard UI (the custom card in the `www` directory).

### 6.1. Addon Configuration UI (`config.yaml`)

The `schema` in your `config.yaml` defines the user interface for configuring the addon itself under **Settings > Add-ons > AICleaner > Configuration**.

#### Critique:

*   **Good:** The schema correctly uses a mix of types like `str`, `bool`, `port`, and `password`, which provides a good user experience.
*   **Good:** The `zones` list of objects is a powerful way to allow users to configure multiple areas.
*   **Improvement:** The `update_frequency` is an integer string `"int(1,24)"`. While functional, using a `range` selector would be more user-friendly.
*   **Improvement:** The notification settings are extensive. They could be grouped under a collapsible section to make the main configuration less cluttered.
*   **Missing:** There are no help texts or labels to guide the user. For example, what is the `gemini_api_key` for? What format does `notification_service` expect?

#### Implementation Steps:

1.  **Improve `update_frequency`:**
    Change the schema for `update_frequency` to use a slider.
    ```yaml
    # In the zones list
    update_frequency: "range(1, 24)" # Creates a slider from 1 to 24
    ```

2.  **Group Notification Settings (Advanced):**
    Home Assistant's addon configuration does not directly support collapsible sections. The best practice is to keep the most important options visible and potentially move less-used options to a separate, optional configuration file that the addon can read. For now, the current flat structure is acceptable, but consider simplifying if possible.

3.  **Add Descriptions and Labels (Most Important):**
    This is not a feature of the addon `config.yaml`. Instead, you must document these options clearly in the addon's `DOCS.md` or `README.md`. Create a **Configuration** section in your main `README.md` file and explain each option in detail.

    *Example for `README.md`:*
    ```markdown
    ## Configuration

    -   **`gemini_api_key`**: (Required) Your API key for the Google Gemini model, used for AI-powered image analysis.
    -   **`display_name`**: A friendly name for your household, used in notifications.
    -   **`enable_mqtt`**: Set to `true` to enable MQTT integration for real-time updates.
    -   **`zones`**: A list of areas to monitor.
        -   **`name`**: A unique, lowercase name for the zone (e.g., `living_room`).
        -   **`camera_entity`**: The `entity_id` of the camera for this zone.
        -   **`update_frequency`**: How often (in hours) to analyze the zone.
    ```

### 6.2. Lovelace Dashboard UI (`aicleaner-card.js` & `aicleaner-card-editor.js`)

This is the custom card that users add to their Lovelace dashboards. It's the primary way they will interact with the addon daily.

#### Critique:

*   **`aicleaner-card.js` (The Card Itself):**
    *   **Excellent:** The card is incredibly feature-rich, with multiple views (dashboard, zone detail, setup wizard), mobile-aware gestures (swipe, pull-to-refresh), and a robust data validation system. The graceful degradation for missing entities is a standout feature.
    *   **Excellent:** The dynamic rendering based on state (loading, error, empty, normal) provides a polished user experience.
    *   **Improvement:** The code is very long (over 6000 lines). It should be broken down into smaller, more manageable modules (e.g., `styles.js`, `views/dashboard.js`, `views/zone-detail.js`, `utils/validation.js`). This is a significant refactoring effort but would drastically improve maintainability.
    *   **Improvement:** The CSS is embedded directly in the JavaScript. While common for web components, moving it to a separate template literal or file would clean up the main class.
    *   **Minor Bug:** The `console.log` statements should be removed for production releases. They are helpful for debugging but add noise for end-users.

*   **`aicleaner-card-editor.js` (The Card Editor):**
    *   **Good:** It provides a simple and effective UI for configuring the card's appearance and behavior.
    *   **Improvement:** The editor UI is functional but could be more visually appealing. It uses basic HTML elements. Leveraging Home Assistant's own UI components (like `ha-textfield`, `ha-switch`, `ha-select`) would make it look and feel more native.
    *   **Improvement:** The help text is good but could be more descriptive. For example, what are the implications of turning off the "Analytics Tab"?

#### Implementation Steps:

1.  **Refactor `aicleaner-card.js` (Long-Term Goal):**
    This is a large task. The first step would be to separate the different parts of the card into their own files.

    *   **Create a `lit-element` base:** Modern Home Assistant cards use `lit-element`. Refactoring to this structure is the standard.
    *   **Separate Views:** Create a directory `X:/aicleaner_v3/www/views/`.
        -   `dashboard-view.js`: Contains the `renderDashboard()` method and its helpers.
        -   `zone-detail-view.js`: Contains the `renderZoneDetail()` method.
        -   `setup-wizard-view.js`: Contains all `renderSetup...()` methods.
    *   **Separate Styles:** Create `X:/aicleaner_v3/www/styles.js` and export the CSS as a `css` template literal from `lit-element`.
    *   **Main Card File:** The main `aicleaner-card.js` would then import these modules and orchestrate which view to render.

2.  **Clean Up `console.log`:**
    Before releasing, search for and remove all `console.log` statements from `aicleaner-card.js`.

3.  **Improve the Card Editor UI:**
    Modify `aicleaner-card-editor.js` to use Home Assistant's built-in components. This requires that your card has access to the `hass` object, which it does.

    *Example of changing a text input:*
    ```javascript
    // Before (in render method):
    <input 
        type="text" 
        id="title" 
        .value="${this._config.title || 'AICleaner'}"
        @input="${this._valueChanged}"
    />

    // After (using ha-textfield):
    <ha-textfield
        label="Card Title"
        .value="${this._config.title || 'AICleaner'}"
        .configValue="${'title'}"
        @input="${this._valueChanged}"
    ></ha-textfield>
    ```

    *Example of changing a checkbox:*
    ```javascript
    // Before:
    <input 
        type="checkbox" 
        id="show_analytics" 
        ?checked="${this._config.show_analytics !== false}"
        @change="${this._valueChanged}"
    />
    <label for="show_analytics">Show Analytics Tab</label>

    // After (using ha-switch):
    <ha-switch
        .checked="${this._config.show_analytics !== false}"
        .configValue="${'show_analytics'}"
        @change="${this._valueChanged}"
    >
    </ha-switch>
    <label>Show Analytics Tab</label>
    ```
    *Note: You will need to adjust the `_valueChanged` function to get the value from `ev.target.configValue` and `ev.target.checked`.*