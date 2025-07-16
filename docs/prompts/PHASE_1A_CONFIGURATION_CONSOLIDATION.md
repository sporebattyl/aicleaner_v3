
# Phase 1A: Configuration Schema Consolidation

## 1. Objective
Merge the three separate configuration files (`config.yaml`, `addons/aicleaner_v3/config.yaml`, and `addons/aicleaner_v3/config.json`) into a single, authoritative `config.yaml` file located in the addon's root directory (`addons/aicleaner_v3`). This will eliminate redundancy, simplify configuration management, and reduce the risk of inconsistencies.

## 2. Prerequisites
- A complete backup of the entire `aicleaner_v3` directory.
- A thorough understanding of the purpose and contents of each of the three configuration files.

## 3. Implementation Steps
1.  **Analyze Existing Configurations:**
    -   Identify all unique keys and their purposes in each of the three configuration files.
    -   Create a mapping of all configuration options, noting any overlaps or conflicts.
2.  **Design the Consolidated Schema:**
    -   Define a clear and logical structure for the new, unified `config.yaml`.
    -   Prioritize the settings in `addons/aicleaner_v3/config.yaml` as the primary source of truth, as it is the most comprehensive.
    -   Incorporate the necessary Home Assistant addon metadata from the root `config.yaml`.
    -   Migrate any essential and non-conflicting settings from `addons/aicleaner_v3/config.json`.
3.  **Implement the Consolidated `config.yaml`:**
    -   Create the new `config.yaml` file in the `addons/aicleaner_v3` directory.
    -   Carefully populate the new file with the consolidated configuration settings.
4.  **Update the Addon Code:**
    -   Refactor the addon's Python code to read all configuration values from the new, single `config.yaml`.
    -   Remove all code that reads from the old configuration files.
5.  **Create a Migration Script (Optional but Recommended):**
    -   Develop a Python script to automatically migrate a user's existing configuration to the new format.
    -   This script should be included in the addon's `scripts` directory.
6.  **Remove Old Configuration Files:**
    -   Once the new configuration is fully implemented and tested, delete the old `config.yaml` (from the root directory) and `config.json`.

## 4. Technical Specifications
- The final `config.yaml` must be located at `X:/aicleaner_v3/addons/aicleaner_v3/config.yaml`.
- The schema should be validated using a library like `voluptuous` to ensure data integrity.
- The addon must be able to handle the absence of the old configuration files gracefully.

## 5. Success Criteria
- The addon starts and runs without errors using only the new `config.yaml`.
- All existing functionality of the addon is preserved.
- All 14 existing tests pass without modification.
- The new `config.yaml` is the single source of truth for all configuration settings.

## 6. Risk Mitigation
- **Risk:** Data loss or corruption during migration.
-   **Mitigation:** Create a complete backup of the project before starting.
- **Risk:** Incompatibilities or conflicts between the old configuration files.
-   **Mitigation:** Thoroughly analyze and map all configuration options before merging.
- **Risk:** The addon fails to start or function correctly with the new configuration.
-   **Mitigation:** Test the addon thoroughly in a development environment before deploying to production.

## 7. Validation Procedures
1.  **Unit Tests:** Run the existing test suite to ensure that all tests pass.
2.  **Integration Tests:** Manually test the addon in a Home Assistant environment to verify that all features are working as expected.
3.  **Configuration Validation:** Test the addon with various valid and invalid configuration settings to ensure that the schema validation is working correctly.

## 8. Rollback Procedures
- Restore the project from the backup created in the prerequisites.
- Revert the changes to the addon's code to use the old configuration files.

## 9. Tools/Resources
- A text editor or IDE for editing the configuration files and Python code.
- A Python environment with the necessary dependencies installed.
- A Home Assistant development environment for testing the addon.

## 10. Time Estimates
- **Analysis and Design:** 4-6 hours
- **Implementation:** 8-12 hours
- **Testing and Validation:** 6-8 hours
- **Total:** 18-26 hours
