#!/bin/bash

# The base name of the addon you are looking for
ADDON_BASENAME="aicleaner_v3"

# --- Internal variables ---
# List of possible slug patterns to check
# 1. The addon slug as defined in config.yaml
# 2. The local addon slug (prefixed with "local_")
# 3. The repository addon slug (prefixed with a hash)
SLUG_PATTERNS=(
    "${ADDON_BASENAME}"
    "local_${ADDON_BASENAME}"
    "*_${ADDON_BASENAME}"
)

# --- Main script ---

# Function to find the addon slug
find_addon_slug() {
    echo "Searching for addon with base name: ${ADDON_BASENAME}"

    # Get the list of installed addons in JSON format
    installed_addons_json=$(ha addons --raw-json)
    if [[ $? -ne 0 ]]; then
        echo "Error: Failed to get the list of installed addons."
        echo "Please ensure you are running this script in the correct environment and have the necessary permissions."
        return 1
    fi

    # Extract the slugs from the JSON output
    installed_slugs=$(echo "${installed_addons_json}" | jq -r '.[].slug')

    # Check each pattern against the list of installed slugs
    for pattern in "${SLUG_PATTERNS[@]}"; do
        for slug in ${installed_slugs}; do
            if [[ "${slug}" == ${pattern} ]]; then
                echo "Found matching addon slug: ${slug}"
                return 0
            fi
        done
    done

    echo "Error: Could not find any addon matching the patterns: ${SLUG_PATTERNS[*]}"
    echo "Please check the addon name and ensure it is installed."
    return 1
}

# --- Execution ---
find_addon_slug