#!/bin/bash
# Validation Script for AICleaner v3 Home Assistant Add-on
# Validates configuration, dependencies, and release readiness

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VALIDATION_RESULTS=()

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

add_result() {
    local status="$1"
    local message="$2"
    VALIDATION_RESULTS+=("$status:$message")
}

validate_project_structure() {
    log_info "Validating project structure..."
    
    # Required files
    local required_files=(
        "config.yaml"
        "Dockerfile"
        "build.yaml"
        "README.md"
        "INSTALL.md"
        "requirements.txt"
        "addons/aicleaner_v3/run.sh"
        "addons/aicleaner_v3/__init__.py"
        "scripts/version_manager.py"
        "scripts/release.sh"
        "scripts/build.sh"
    )
    
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        add_result "ERROR" "Missing required files: ${missing_files[*]}"
        return 1
    fi
    
    # Required directories
    local required_dirs=(
        "addons/aicleaner_v3"
        "addons/aicleaner_v3/ai"
        "addons/aicleaner_v3/core"
        "addons/aicleaner_v3/ha_integration"
        "addons/aicleaner_v3/security"
        "addons/aicleaner_v3/zones"
        "scripts"
    )
    
    local missing_dirs=()
    
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$PROJECT_ROOT/$dir" ]]; then
            missing_dirs+=("$dir")
        fi
    done
    
    if [[ ${#missing_dirs[@]} -gt 0 ]]; then
        add_result "ERROR" "Missing required directories: ${missing_dirs[*]}"
        return 1
    fi
    
    add_result "SUCCESS" "Project structure validation passed"
    return 0
}

validate_config_yaml() {
    log_info "Validating config.yaml..."
    
    local config_file="$PROJECT_ROOT/config.yaml"
    
    # Check if config.yaml is valid YAML
    if ! python3 -c "import yaml; yaml.safe_load(open('$config_file'))" 2>/dev/null; then
        add_result "ERROR" "config.yaml is not valid YAML"
        return 1
    fi
    
    # Check required fields
    local required_fields=(
        "name"
        "version"
        "slug"
        "description"
        "arch"
        "image"
        "schema"
    )
    
    local missing_fields=()
    
    for field in "${required_fields[@]}"; do
        if ! python3 -c "import yaml; config=yaml.safe_load(open('$config_file')); exit(0 if '$field' in config else 1)" 2>/dev/null; then
            missing_fields+=("$field")
        fi
    done
    
    if [[ ${#missing_fields[@]} -gt 0 ]]; then
        add_result "ERROR" "config.yaml missing required fields: ${missing_fields[*]}"
        return 1
    fi
    
    # Validate version format
    local version=$(python3 -c "import yaml; print(yaml.safe_load(open('$config_file'))['version'])")
    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-.*)?$ ]]; then
        add_result "ERROR" "Invalid version format in config.yaml: $version"
        return 1
    fi
    
    # Validate supported architectures
    local architectures=$(python3 -c "import yaml; print(' '.join(yaml.safe_load(open('$config_file'))['arch']))")
    local expected_archs=("aarch64" "amd64" "armv7" "armhf" "i386")
    
    for arch in "${expected_archs[@]}"; do
        if [[ ! " $architectures " =~ " $arch " ]]; then
            add_result "WARNING" "Architecture $arch not supported in config.yaml"
        fi
    done
    
    add_result "SUCCESS" "config.yaml validation passed"
    return 0
}

validate_dockerfile() {
    log_info "Validating Dockerfile..."
    
    local dockerfile="$PROJECT_ROOT/Dockerfile"
    
    # Check if Dockerfile exists and is not empty
    if [[ ! -s "$dockerfile" ]]; then
        add_result "ERROR" "Dockerfile is empty or missing"
        return 1
    fi
    
    # Check for required Dockerfile elements
    local required_elements=(
        "FROM"
        "WORKDIR"
        "COPY"
        "EXPOSE"
        "CMD"
    )
    
    local missing_elements=()
    
    for element in "${required_elements[@]}"; do
        if ! grep -q "^$element " "$dockerfile"; then
            missing_elements+=("$element")
        fi
    done
    
    if [[ ${#missing_elements[@]} -gt 0 ]]; then
        add_result "ERROR" "Dockerfile missing required elements: ${missing_elements[*]}"
        return 1
    fi
    
    # Check for proper labels
    if ! grep -q "io.hass.version" "$dockerfile"; then
        add_result "WARNING" "Dockerfile missing Home Assistant version label"
    fi
    
    # Check for health check
    if ! grep -q "HEALTHCHECK" "$dockerfile"; then
        add_result "WARNING" "Dockerfile missing health check"
    fi
    
    add_result "SUCCESS" "Dockerfile validation passed"
    return 0
}

validate_build_yaml() {
    log_info "Validating build.yaml..."
    
    local build_file="$PROJECT_ROOT/build.yaml"
    
    # Check if build.yaml is valid YAML
    if ! python3 -c "import yaml; yaml.safe_load(open('$build_file'))" 2>/dev/null; then
        add_result "ERROR" "build.yaml is not valid YAML"
        return 1
    fi
    
    # Check for build_from section
    if ! python3 -c "import yaml; config=yaml.safe_load(open('$build_file')); exit(0 if 'build_from' in config else 1)" 2>/dev/null; then
        add_result "ERROR" "build.yaml missing build_from section"
        return 1
    fi
    
    # Check supported architectures
    local supported_archs=$(python3 -c "import yaml; print(' '.join(yaml.safe_load(open('$build_file'))['build_from'].keys()))")
    local expected_archs=("aarch64" "amd64" "armv7" "armhf" "i386")
    
    for arch in "${expected_archs[@]}"; do
        if [[ ! " $supported_archs " =~ " $arch " ]]; then
            add_result "WARNING" "Architecture $arch not supported in build.yaml"
        fi
    done
    
    add_result "SUCCESS" "build.yaml validation passed"
    return 0
}

validate_requirements() {
    log_info "Validating requirements.txt..."
    
    local requirements_file="$PROJECT_ROOT/requirements.txt"
    
    # Check if requirements.txt exists
    if [[ ! -f "$requirements_file" ]]; then
        add_result "ERROR" "requirements.txt not found"
        return 1
    fi
    
    # Check if requirements.txt is not empty
    if [[ ! -s "$requirements_file" ]]; then
        add_result "WARNING" "requirements.txt is empty"
    fi
    
    # Validate requirements format
    local line_number=0
    while IFS= read -r line; do
        ((line_number++))
        
        # Skip empty lines and comments
        if [[ -z "$line" || "$line" =~ ^#.* ]]; then
            continue
        fi
        
        # Check for basic requirement format
        if [[ ! "$line" =~ ^[a-zA-Z0-9_-]+.*$ ]]; then
            add_result "WARNING" "Invalid requirement format at line $line_number: $line"
        fi
    done < "$requirements_file"
    
    add_result "SUCCESS" "requirements.txt validation passed"
    return 0
}

validate_scripts() {
    log_info "Validating scripts..."
    
    local scripts=(
        "version_manager.py"
        "release.sh"
        "build.sh"
        "validate.sh"
    )
    
    local missing_scripts=()
    local non_executable=()
    
    for script in "${scripts[@]}"; do
        local script_path="$PROJECT_ROOT/scripts/$script"
        
        if [[ ! -f "$script_path" ]]; then
            missing_scripts+=("$script")
        elif [[ ! -x "$script_path" ]]; then
            non_executable+=("$script")
        fi
    done
    
    if [[ ${#missing_scripts[@]} -gt 0 ]]; then
        add_result "ERROR" "Missing scripts: ${missing_scripts[*]}"
        return 1
    fi
    
    if [[ ${#non_executable[@]} -gt 0 ]]; then
        add_result "WARNING" "Non-executable scripts: ${non_executable[*]}"
    fi
    
    # Test version manager
    if ! python3 "$PROJECT_ROOT/scripts/version_manager.py" current &>/dev/null; then
        add_result "ERROR" "version_manager.py is not working correctly"
        return 1
    fi
    
    add_result "SUCCESS" "Scripts validation passed"
    return 0
}

validate_documentation() {
    log_info "Validating documentation..."
    
    local docs=(
        "README.md"
        "INSTALL.md"
    )
    
    local missing_docs=()
    local empty_docs=()
    
    for doc in "${docs[@]}"; do
        local doc_path="$PROJECT_ROOT/$doc"
        
        if [[ ! -f "$doc_path" ]]; then
            missing_docs+=("$doc")
        elif [[ ! -s "$doc_path" ]]; then
            empty_docs+=("$doc")
        fi
    done
    
    if [[ ${#missing_docs[@]} -gt 0 ]]; then
        add_result "ERROR" "Missing documentation: ${missing_docs[*]}"
        return 1
    fi
    
    if [[ ${#empty_docs[@]} -gt 0 ]]; then
        add_result "WARNING" "Empty documentation: ${empty_docs[*]}"
    fi
    
    # Check for basic sections in README
    if ! grep -q "## Features" "$PROJECT_ROOT/README.md"; then
        add_result "WARNING" "README.md missing Features section"
    fi
    
    if ! grep -q "## Installation" "$PROJECT_ROOT/README.md"; then
        add_result "WARNING" "README.md missing Installation section"
    fi
    
    add_result "SUCCESS" "Documentation validation passed"
    return 0
}

validate_git_repository() {
    log_info "Validating git repository..."
    
    # Check if we're in a git repository
    if ! git rev-parse --is-inside-work-tree &>/dev/null; then
        add_result "ERROR" "Not in a git repository"
        return 1
    fi
    
    # Check if there are uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        add_result "WARNING" "Working directory has uncommitted changes"
    fi
    
    # Check for .gitignore
    if [[ ! -f "$PROJECT_ROOT/.gitignore" ]]; then
        add_result "WARNING" ".gitignore not found"
    fi
    
    # Check for recent commits
    local last_commit_date=$(git log -1 --format=%ci 2>/dev/null || echo "")
    if [[ -z "$last_commit_date" ]]; then
        add_result "WARNING" "No git commits found"
    fi
    
    add_result "SUCCESS" "Git repository validation passed"
    return 0
}

run_tests() {
    log_info "Running tests..."
    
    local test_dir="$PROJECT_ROOT/addons/aicleaner_v3/tests"
    
    if [[ ! -d "$test_dir" ]]; then
        add_result "WARNING" "Test directory not found"
        return 0
    fi
    
    # Check if pytest is available
    if ! command -v pytest &>/dev/null; then
        add_result "WARNING" "pytest not found, skipping tests"
        return 0
    fi
    
    # Run tests
    cd "$PROJECT_ROOT/addons/aicleaner_v3"
    if pytest tests/ -v --tb=short --quiet &>/dev/null; then
        add_result "SUCCESS" "All tests passed"
    else
        add_result "ERROR" "Some tests failed"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
    return 0
}

generate_validation_report() {
    log_info "Generating validation report..."
    
    local report_file="$PROJECT_ROOT/VALIDATION_REPORT.md"
    local timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
    
    cat > "$report_file" << EOF
# AICleaner v3 Validation Report

**Generated:** $timestamp

## Summary

Total validations: ${#VALIDATION_RESULTS[@]}

EOF
    
    local success_count=0
    local warning_count=0
    local error_count=0
    
    for result in "${VALIDATION_RESULTS[@]}"; do
        local status="${result%%:*}"
        local message="${result#*:}"
        
        case "$status" in
            SUCCESS)
                ((success_count++))
                echo "✅ $message" >> "$report_file"
                ;;
            WARNING)
                ((warning_count++))
                echo "⚠️  $message" >> "$report_file"
                ;;
            ERROR)
                ((error_count++))
                echo "❌ $message" >> "$report_file"
                ;;
        esac
    done
    
    # Add summary statistics
    cat >> "$report_file" << EOF

## Statistics

- ✅ Success: $success_count
- ⚠️  Warnings: $warning_count
- ❌ Errors: $error_count

## Recommendations

EOF
    
    if [[ $error_count -gt 0 ]]; then
        echo "- Fix all errors before proceeding with release" >> "$report_file"
    fi
    
    if [[ $warning_count -gt 0 ]]; then
        echo "- Review and address warnings to improve quality" >> "$report_file"
    fi
    
    if [[ $error_count -eq 0 && $warning_count -eq 0 ]]; then
        echo "- All validations passed! Ready for release." >> "$report_file"
    fi
    
    log_success "Validation report generated: $report_file"
}

# Main script logic
main() {
    cd "$PROJECT_ROOT"
    
    log_info "Starting AICleaner v3 validation..."
    
    # Run all validations
    validate_project_structure
    validate_config_yaml
    validate_dockerfile
    validate_build_yaml
    validate_requirements
    validate_scripts
    validate_documentation
    validate_git_repository
    run_tests
    
    # Generate report
    generate_validation_report
    
    # Show summary
    local success_count=0
    local warning_count=0
    local error_count=0
    
    for result in "${VALIDATION_RESULTS[@]}"; do
        local status="${result%%:*}"
        case "$status" in
            SUCCESS) ((success_count++)) ;;
            WARNING) ((warning_count++)) ;;
            ERROR) ((error_count++)) ;;
        esac
    done
    
    echo
    log_info "Validation Summary:"
    log_success "✅ Success: $success_count"
    if [[ $warning_count -gt 0 ]]; then
        log_warning "⚠️  Warnings: $warning_count"
    fi
    if [[ $error_count -gt 0 ]]; then
        log_error "❌ Errors: $error_count"
    fi
    
    # Exit with appropriate code
    if [[ $error_count -gt 0 ]]; then
        log_error "Validation failed with $error_count errors"
        exit 1
    elif [[ $warning_count -gt 0 ]]; then
        log_warning "Validation completed with $warning_count warnings"
        exit 0
    else
        log_success "All validations passed!"
        exit 0
    fi
}

# Run main function
main "$@"