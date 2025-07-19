import os
import sys
import yaml # Assuming PyYAML is installed for YAML parsing
import json # For JSON parsing

def validate_ai_providers():
    """
    Validates the configuration for AI providers.
    Checks for the existence and basic structure of AI provider configurations
    in common project configuration files.
    """
    print("\n--- Running AI Providers Validation ---")
    all_passed = True

    # Common paths for project configuration files
    # Ordered by typical precedence or likelihood of containing AI config
    config_files_to_check = [
        "/home/drewcifer/aicleaner_v3/config.yaml",
        "/home/drewcifer/aicleaner_v3/addons/aicleaner_v3/config.yaml",
        "/home/drewcifer/aicleaner_v3/addons/aicleaner_v3/config.json"
    ]

    found_ai_config_section = False

    for path in config_files_to_check:
        print(f"Checking for AI provider configuration in: {path}")
        if not os.path.exists(path):
            print(f"  File not found: {path} (Skipping)")
            continue

        try:
            config = None
            if path.endswith('.yaml'):
                with open(path, 'r') as f:
                    config = yaml.safe_load(f)
            elif path.endswith('.json'):
                with open(path, 'r') as f:
                    config = json.load(f)
            else:
                print(f"  Skipping unsupported config file type: {path}")
                continue

            if config is None:
                print(f"  Config file {path} is empty or malformed.")
                all_passed = False
                continue

            # Check for common AI-related keys
            # This assumes 'gemini_api_key' is under 'options' for config.json
            # and potentially directly under the root for config.yaml
            if 'gemini_api_key' in config.get('options', {}):
                api_key = config['options']['gemini_api_key']
                if api_key and api_key != "AIzaSyExampleKeyReplaceMeWithYourKey":
                    print(f"  'gemini_api_key' found and appears configured in {path}.")
                    found_ai_config_section = True
                else:
                    print(f"  Warning: 'gemini_api_key' found in {path} but is empty or still a placeholder.")
                    # This might not fail validation, but indicates a potential issue
            elif 'ai_providers' in config:
                print(f"  'ai_providers' section found in {path}. (Further detailed validation needed)")
                found_ai_config_section = True
                # Here, you would add more specific checks for each AI provider listed
                # e.g., iterating through config['ai_providers'] and checking for required keys
            else:
                print(f"  No explicit 'gemini_api_key' or 'ai_providers' section found in {path}.")

        except (yaml.YAMLError, json.JSONDecodeError) as e:
            print(f"  Error parsing config file {path}: {e}")
            all_passed = False
        except Exception as e:
            print(f"  An unexpected error occurred while reading {path}: {e}")
            all_passed = False

    if not found_ai_config_section:
        print("\nWarning: No explicit AI provider configuration sections found in any checked files.")
        print("Please ensure your AI services are properly configured for production.")
        # Decide if this should fail the validation. For now, it's a warning.
        # all_passed = False # Uncomment to make this a hard failure

    if all_passed:
        print("AI Providers Validation: ALL PASSED (Basic configuration checks)")
    else:
        print("AI Providers Validation: FAILED (One or more checks failed or critical config missing)")
    return all_passed

if __name__ == "__main__":
    if validate_ai_providers():
        sys.exit(0)
    else:
        sys.exit(1)