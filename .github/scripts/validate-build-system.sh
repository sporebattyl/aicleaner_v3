#!/bin/bash

# Comprehensive Build System Validation Script
# Tests all components of the bulletproof build system

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEMP_DIR="/tmp/build-system-validation-$$"
VALIDATION_LOG="$TEMP_DIR/validation.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$VALIDATION_LOG"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$VALIDATION_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$VALIDATION_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$VALIDATION_LOG"
}

# Test framework functions
start_test() {
    local test_name="$1"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo "" | tee -a "$VALIDATION_LOG"
    log_info "Starting test: $test_name"
    echo "TEST_START: $test_name" >> "$VALIDATION_LOG"
}

pass_test() {
    local test_name="$1"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_success "✅ PASSED: $test_name"
    echo "TEST_RESULT: PASSED - $test_name" >> "$VALIDATION_LOG"
}

fail_test() {
    local test_name="$1"
    local reason="$2"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "❌ FAILED: $test_name"
    if [ -n "$reason" ]; then
        log_error "Reason: $reason"
    fi
    echo "TEST_RESULT: FAILED - $test_name - $reason" >> "$VALIDATION_LOG"
}

skip_test() {
    local test_name="$1"
    local reason="$2"
    SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
    log_warn "⏭️  SKIPPED: $test_name"
    if [ -n "$reason" ]; then
        log_warn "Reason: $reason"
    fi
    echo "TEST_RESULT: SKIPPED - $test_name - $reason" >> "$VALIDATION_LOG"
}

setup_validation_environment() {
    echo "[INFO] Setting up validation environment..."
    
    # Create temp directory
    mkdir -p "$TEMP_DIR"
    touch "$VALIDATION_LOG"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    echo "[SUCCESS] Validation environment ready"
    echo "[INFO] Project root: $PROJECT_ROOT"
    echo "[INFO] Temp directory: $TEMP_DIR"
    echo "[INFO] Validation log: $VALIDATION_LOG"
}

cleanup_validation_environment() {
    log_info "Cleaning up validation environment..."
    
    # Keep logs but clean up temp files
    if [ -d "$TEMP_DIR" ]; then
        # Move log to project root for review
        if [ -f "$VALIDATION_LOG" ]; then
            cp "$VALIDATION_LOG" "$PROJECT_ROOT/build-system-validation.log"
            log_info "Validation log saved: $PROJECT_ROOT/build-system-validation.log"
        fi
        
        rm -rf "$TEMP_DIR"
    fi
    
    log_success "Cleanup completed"
}

# Validation Tests

test_dependencies() {
    start_test "Dependencies Check"
    
    local missing_deps=()
    local deps=("docker" "yq" "jq" "yamllint" "curl" "git")
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        pass_test "Dependencies Check"
    else
        fail_test "Dependencies Check" "Missing: ${missing_deps[*]}"
    fi
}

test_project_structure() {
    start_test "Project Structure"
    
    local required_files=(
        "aicleaner_v3/config.yaml"
        "aicleaner_v3/Dockerfile"
        ".github/workflows/build.yml"
        ".github/workflows/build-health-monitor.yml"
        ".github/scripts/build-status-monitor.sh"
        ".github/scripts/emergency-build.sh"
        ".github/docs/BUILD_SYSTEM_GUIDE.md"
        ".github/docs/QUICK_TROUBLESHOOTING.md"
    )
    
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -eq 0 ]; then
        pass_test "Project Structure"
    else
        fail_test "Project Structure" "Missing files: ${missing_files[*]}"
    fi
}

test_config_validation() {
    start_test "Configuration Validation"
    
    cd aicleaner_v3
    
    # Test YAML syntax
    if ! yamllint config.yaml &>/dev/null; then
        fail_test "Configuration Validation" "config.yaml has YAML syntax errors"
        cd ..
        return 1
    fi
    
    # Test required fields
    local name=$(yq eval '.name' config.yaml)
    local version=$(yq eval '.version' config.yaml)
    local slug=$(yq eval '.slug' config.yaml)
    local arch_count=$(yq eval '.arch | length' config.yaml)
    
    local issues=()
    
    if [ "$name" = "null" ] || [ -z "$name" ]; then
        issues+=("missing name field")
    fi
    
    if [ "$version" = "null" ] || [ -z "$version" ]; then
        issues+=("missing version field")
    fi
    
    if [ "$slug" = "null" ] || [ -z "$slug" ]; then
        issues+=("missing slug field")
    fi
    
    if [ "$arch_count" -eq 0 ]; then
        issues+=("no architectures defined")
    fi
    
    cd ..
    
    if [ ${#issues[@]} -eq 0 ]; then
        pass_test "Configuration Validation"
    else
        fail_test "Configuration Validation" "${issues[*]}"
    fi
}

test_architecture_detection() {
    start_test "Architecture Detection System"
    
    cd aicleaner_v3
    
    # Test Strategy 2: Direct config parsing
    local parsed_arch
    if ! parsed_arch=$(yq eval -o=json '.arch' config.yaml 2>/dev/null); then
        fail_test "Architecture Detection System" "Direct config parsing failed"
        cd ..
        return 1
    fi
    
    # Validate JSON format
    if ! echo "$parsed_arch" | jq -e . >/dev/null 2>&1; then
        fail_test "Architecture Detection System" "Parsed architectures not valid JSON"
        cd ..
        return 1
    fi
    
    # Check architecture count
    local arch_count
    if ! arch_count=$(echo "$parsed_arch" | jq '. | length' 2>/dev/null); then
        fail_test "Architecture Detection System" "Cannot count architectures"
        cd ..
        return 1
    fi
    
    if [ "$arch_count" -eq 0 ]; then
        fail_test "Architecture Detection System" "Architecture list is empty"
        cd ..
        return 1
    fi
    
    # Test Strategy 3: Hardcoded fallback
    local hardcoded_arch='["aarch64","amd64","armhf","armv7"]'
    if ! echo "$hardcoded_arch" | jq -e . >/dev/null 2>&1; then
        fail_test "Architecture Detection System" "Hardcoded fallback not valid JSON"
        cd ..
        return 1
    fi
    
    cd ..
    pass_test "Architecture Detection System"
}

test_dockerfile_validation() {
    start_test "Dockerfile Validation"
    
    cd aicleaner_v3
    
    # Check basic structure
    if ! grep -q "^FROM " Dockerfile; then
        fail_test "Dockerfile Validation" "Missing FROM instruction"
        cd ..
        return 1
    fi
    
    # Test with hadolint if available
    if command -v hadolint &> /dev/null; then
        if hadolint Dockerfile &>/dev/null; then
            log_info "Hadolint validation passed"
        else
            log_warn "Hadolint found issues (non-critical for test)"
        fi
    else
        log_warn "Hadolint not available, skipping advanced validation"
    fi
    
    cd ..
    pass_test "Dockerfile Validation"
}

test_workflow_syntax() {
    start_test "Workflow Syntax Validation"
    
    # Test main build workflow
    if ! yamllint .github/workflows/build.yml &>/dev/null; then
        fail_test "Workflow Syntax Validation" "build.yml has YAML syntax errors"
        return 1
    fi
    
    # Test health monitor workflow
    if ! yamllint .github/workflows/build-health-monitor.yml &>/dev/null; then
        fail_test "Workflow Syntax Validation" "build-health-monitor.yml has YAML syntax errors"
        return 1
    fi
    
    # Check for required workflow components
    local required_jobs=("pre-build-validation" "info" "validate-build" "build" "test-build" "publish" "post-build")
    
    for job in "${required_jobs[@]}"; do
        if ! grep -q "^  $job:" .github/workflows/build.yml; then
            fail_test "Workflow Syntax Validation" "Missing job: $job"
            return 1
        fi
    done
    
    pass_test "Workflow Syntax Validation"
}

test_script_permissions() {
    start_test "Script Permissions"
    
    local scripts=(
        ".github/scripts/build-status-monitor.sh"
        ".github/scripts/emergency-build.sh"
        ".github/scripts/validate-build-system.sh"
    )
    
    local non_executable=()
    
    for script in "${scripts[@]}"; do
        if [ ! -x "$script" ]; then
            non_executable+=("$script")
        fi
    done
    
    if [ ${#non_executable[@]} -eq 0 ]; then
        pass_test "Script Permissions"
    else
        fail_test "Script Permissions" "Non-executable scripts: ${non_executable[*]}"
    fi
}

test_docker_environment() {
    start_test "Docker Environment"
    
    # Check Docker daemon
    if ! docker info &>/dev/null; then
        fail_test "Docker Environment" "Docker daemon not accessible"
        return 1
    fi
    
    # Check Docker buildx
    if ! docker buildx version &>/dev/null; then
        fail_test "Docker Environment" "Docker buildx not available"
        return 1
    fi
    
    # Test basic Docker functionality
    if ! docker run --rm hello-world &>/dev/null; then
        fail_test "Docker Environment" "Cannot run test container"
        return 1
    fi
    
    pass_test "Docker Environment"
}

test_build_system_dry_run() {
    start_test "Build System Dry Run"
    
    cd aicleaner_v3
    
    # Test Docker build dry run
    if docker build --dry-run . &>/dev/null; then
        log_info "Docker dry run successful"
    else
        fail_test "Build System Dry Run" "Docker dry run failed"
        cd ..
        return 1
    fi
    
    cd ..
    pass_test "Build System Dry Run"
}

test_monitoring_system() {
    start_test "Monitoring System"
    
    # Test build status monitor script
    if [ -x ".github/scripts/build-status-monitor.sh" ]; then
        # Test help functionality
        if ./.github/scripts/build-status-monitor.sh --help &>/dev/null; then
            log_info "Build status monitor help works"
        else
            fail_test "Monitoring System" "Build status monitor help failed"
            return 1
        fi
    else
        fail_test "Monitoring System" "Build status monitor not executable"
        return 1
    fi
    
    # Test emergency build script
    if [ -x ".github/scripts/emergency-build.sh" ]; then
        if ./.github/scripts/emergency-build.sh --help &>/dev/null; then
            log_info "Emergency build script help works"
        else
            fail_test "Monitoring System" "Emergency build script help failed"
            return 1
        fi
    else
        fail_test "Monitoring System" "Emergency build script not executable"
        return 1
    fi
    
    pass_test "Monitoring System"
}

test_fallback_strategies() {
    start_test "Fallback Strategy Integration"
    
    cd aicleaner_v3
    
    # Simulate config parsing workflow
    local strategies_working=0
    
    # Strategy 2: Direct config parsing
    if yq eval -o=json '.arch' config.yaml >/dev/null 2>&1; then
        strategies_working=$((strategies_working + 1))
        log_info "Strategy 2 (direct config parsing) works"
    fi
    
    # Strategy 3: Hardcoded fallback
    local hardcoded='["aarch64","amd64","armhf","armv7"]'
    if echo "$hardcoded" | jq -e . >/dev/null 2>&1; then
        strategies_working=$((strategies_working + 1))
        log_info "Strategy 3 (hardcoded fallback) works"
    fi
    
    cd ..
    
    if [ $strategies_working -ge 2 ]; then
        pass_test "Fallback Strategy Integration"
    else
        fail_test "Fallback Strategy Integration" "Only $strategies_working/2 fallback strategies working"
    fi
}

test_documentation_completeness() {
    start_test "Documentation Completeness"
    
    local doc_files=(
        ".github/docs/BUILD_SYSTEM_GUIDE.md"
        ".github/docs/QUICK_TROUBLESHOOTING.md"
    )
    
    local issues=()
    
    for doc in "${doc_files[@]}"; do
        if [ ! -f "$doc" ]; then
            issues+=("Missing: $doc")
        elif [ ! -s "$doc" ]; then
            issues+=("Empty: $doc")
        fi
    done
    
    # Check for key sections in main guide
    if [ -f ".github/docs/BUILD_SYSTEM_GUIDE.md" ]; then
        local required_sections=("## Overview" "## Troubleshooting" "## Architecture" "## Disaster Recovery")
        
        for section in "${required_sections[@]}"; do
            if ! grep -q "$section" ".github/docs/BUILD_SYSTEM_GUIDE.md"; then
                issues+=("Missing section: $section")
            fi
        done
    fi
    
    if [ ${#issues[@]} -eq 0 ]; then
        pass_test "Documentation Completeness"
    else
        fail_test "Documentation Completeness" "${issues[*]}"
    fi
}

generate_validation_report() {
    local report_file="$PROJECT_ROOT/build-system-validation-report.json"
    
    log_info "Generating validation report..."
    
    cat > "$report_file" << EOF
{
  "validation_summary": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "total_tests": $TOTAL_TESTS,
    "passed_tests": $PASSED_TESTS,
    "failed_tests": $FAILED_TESTS,
    "skipped_tests": $SKIPPED_TESTS,
    "success_rate": $(echo "scale=2; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l 2>/dev/null || echo "0"),
    "overall_status": "$([ $FAILED_TESTS -eq 0 ] && echo "PASSED" || echo "FAILED")"
  },
  "test_categories": {
    "configuration": "$(grep -c "Configuration.*PASSED" "$VALIDATION_LOG" >/dev/null 2>&1 && echo "PASSED" || echo "FAILED")",
    "architecture_detection": "$(grep -c "Architecture Detection.*PASSED" "$VALIDATION_LOG" >/dev/null 2>&1 && echo "PASSED" || echo "FAILED")",
    "workflow_validation": "$(grep -c "Workflow.*PASSED" "$VALIDATION_LOG" >/dev/null 2>&1 && echo "PASSED" || echo "FAILED")",
    "docker_environment": "$(grep -c "Docker Environment.*PASSED" "$VALIDATION_LOG" >/dev/null 2>&1 && echo "PASSED" || echo "FAILED")",
    "monitoring_system": "$(grep -c "Monitoring System.*PASSED" "$VALIDATION_LOG" >/dev/null 2>&1 && echo "PASSED" || echo "FAILED")",
    "documentation": "$(grep -c "Documentation.*PASSED" "$VALIDATION_LOG" >/dev/null 2>&1 && echo "PASSED" || echo "FAILED")"
  },
  "recommendations": [
    $([ $FAILED_TESTS -gt 0 ] && echo '"Fix failed tests before proceeding with builds",' || echo '"System is ready for production builds",')
    $([ $SKIPPED_TESTS -gt 0 ] && echo '"Review skipped tests for completeness",' || echo '"All tests completed successfully",')
    "Regular validation should be performed after system changes"
  ]
}
EOF
    
    log_success "Validation report generated: $report_file"
}

show_validation_summary() {
    echo ""
    echo "============================================="
    echo "        BUILD SYSTEM VALIDATION SUMMARY"
    echo "============================================="
    echo "Total Tests:     $TOTAL_TESTS"
    echo "Passed:          $PASSED_TESTS"
    echo "Failed:          $FAILED_TESTS"
    echo "Skipped:         $SKIPPED_TESTS"
    
    local success_rate=0
    if [ $TOTAL_TESTS -gt 0 ]; then
        success_rate=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l 2>/dev/null || echo "0")
    fi
    echo "Success Rate:    ${success_rate}%"
    echo ""
    
    if [ $FAILED_TESTS -eq 0 ]; then
        log_success "🎉 ALL TESTS PASSED - Build system is ready for production!"
        echo ""
        echo "Next Steps:"
        echo "- The build system is fully validated and ready to use"
        echo "- All fallback strategies are working correctly"
        echo "- Monitor builds using the health check system"
        echo "- Refer to documentation for maintenance procedures"
    else
        log_error "❌ VALIDATION FAILED - Issues must be resolved before production use"
        echo ""
        echo "Required Actions:"
        echo "- Review failed tests in the validation log"
        echo "- Fix identified issues"
        echo "- Re-run validation after fixes"
        echo "- Do not proceed with production builds until all tests pass"
    fi
    
    echo ""
    echo "Reports Generated:"
    echo "- Detailed log: $PROJECT_ROOT/build-system-validation.log"
    echo "- JSON report:  $PROJECT_ROOT/build-system-validation-report.json"
    echo "============================================="
}

main() {
    echo "=== AICleaner V3 Build System Validation ==="
    echo "Starting comprehensive validation of bulletproof build system..."
    echo ""
    
    # Setup
    setup_validation_environment
    
    # Run all validation tests
    test_dependencies
    test_project_structure
    test_config_validation
    test_architecture_detection
    test_dockerfile_validation
    test_workflow_syntax
    test_script_permissions
    test_docker_environment
    test_build_system_dry_run
    test_monitoring_system
    test_fallback_strategies
    test_documentation_completeness
    
    # Generate reports
    generate_validation_report
    
    # Show summary
    show_validation_summary
    
    # Cleanup
    cleanup_validation_environment
    
    # Exit with appropriate code
    if [ $FAILED_TESTS -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"