import os
import sys

# Adjust sys.path to allow direct import from the performance directory
# This assumes the script is run from the project root or 'scripts' directory
performance_module_path = "/home/drewcifer/aicleaner_v3/performance"
if performance_module_path not in sys.path:
    sys.path.append(performance_module_path)

try:
    import memory_manager
    import cpu_manager
    import network_manager
    # Add more imports as needed based on actual performance modules
    # e.g., import disk_manager, profiler, resource_manager
except ImportError as e:
    print(f"Error importing performance modules from {performance_module_path}: {e}")
    print("Please ensure the performance modules are correctly located and accessible.")
    sys.exit(1) # Exit if core modules cannot be imported
except Exception as e:
    print(f"An unexpected error occurred during performance module import: {e}")
    sys.exit(1)


def validate_memory_performance():
    """Validates memory performance using memory_manager."""
    print("  - Checking Memory Manager functionality...")
    try:
        if hasattr(memory_manager, 'check_memory_status') and callable(memory_manager.check_memory_status):
            status = memory_manager.check_memory_status()
            if status:
                print("    Memory Manager Check: PASSED")
                return True
            else:
                print("    Memory Manager Check: FAILED (Status issue reported by module)")
                return False
        else:
            print("    Memory Manager Check: SKIPPED (No 'check_memory_status' function found in memory_manager)")
            return True # Not a failure if the function doesn't exist
    except Exception as e:
        print(f"    Error during Memory Manager validation: {e}")
        return False

def validate_cpu_performance():
    """Validates CPU performance using cpu_manager."""
    print("  - Checking CPU Manager functionality...")
    try:
        if hasattr(cpu_manager, 'check_cpu_load') and callable(cpu_manager.check_cpu_load):
            load_ok = cpu_manager.check_cpu_load()
            if load_ok:
                print("    CPU Manager Check: PASSED")
                return True
            else:
                print("    CPU Manager Check: FAILED (High CPU load or other issue)")
                return False
        else:
            print("    CPU Manager Check: SKIPPED (No 'check_cpu_load' function found in cpu_manager)")
            return True
    except Exception as e:
        print(f"    Error during CPU Manager validation: {e}")
        return False

def validate_network_performance():
    """Validates network performance using network_manager."""
    print("  - Checking Network Manager functionality...")
    try:
        if hasattr(network_manager, 'check_network_connectivity') and callable(network_manager.check_network_connectivity):
            connectivity_ok = network_manager.check_network_connectivity()
            if connectivity_ok:
                print("    Network Manager Check: PASSED")
                return True
            else:
                print("    Network Manager Check: FAILED (Connectivity issue)")
                return False
        else:
            print("    Network Manager Check: SKIPPED (No 'check_network_connectivity' function found in network_manager)")
            return True
    except Exception as e:
        print(f"    Error during Network Manager validation: {e}")
        return False

def validate_performance():
    """
    Orchestrates various performance validations using imported modules.
    """
    print("\n--- Running Performance Validation ---")
    all_passed = True

    if not validate_memory_performance():
        all_passed = False

    if not validate_cpu_performance():
        all_passed = False

    if not validate_network_performance():
        all_passed = False

    # Add more performance checks here as needed, e.g.:
    # if not validate_disk_io():
    #     all_passed = False

    if all_passed:
        print("Performance Validation: ALL PASSED")
    else:
        print("Performance Validation: FAILED (One or more checks failed)")
    return all_passed

if __name__ == "__main__":
    if validate_performance():
        sys.exit(0)
    else:
        sys.exit(1)