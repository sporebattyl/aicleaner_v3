#!/bin/bash

# Build Status Monitor Script
# Monitors GitHub Actions build status and generates alerts for failures

set -e

# Configuration
REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-sporebattyl}"
REPO_NAME="${GITHUB_REPOSITORY_NAME:-aicleaner_v3}"
WORKFLOW_NAME="build.yml"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v jq &> /dev/null; then
        log_error "jq is required but not installed"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    if [ -z "$GITHUB_TOKEN" ]; then
        log_warn "GITHUB_TOKEN not set - API rate limits will be restrictive"
    fi
    
    log_success "Dependencies check passed"
}

get_workflow_runs() {
    local limit=${1:-10}
    
    log_info "Fetching last $limit workflow runs..."
    
    local auth_header=""
    if [ -n "$GITHUB_TOKEN" ]; then
        auth_header="-H \"Authorization: token $GITHUB_TOKEN\""
    fi
    
    local api_url="https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/actions/workflows/$WORKFLOW_NAME/runs?per_page=$limit"
    
    local response
    if [ -n "$GITHUB_TOKEN" ]; then
        response=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "$api_url")
    else
        response=$(curl -s "$api_url")
    fi
    
    if [ $? -ne 0 ]; then
        log_error "Failed to fetch workflow runs"
        return 1
    fi
    
    echo "$response"
}

analyze_build_health() {
    local runs_data="$1"
    
    log_info "Analyzing build health..."
    
    local total_runs=$(echo "$runs_data" | jq '.workflow_runs | length')
    local successful_runs=$(echo "$runs_data" | jq '[.workflow_runs[] | select(.conclusion == "success")] | length')
    local failed_runs=$(echo "$runs_data" | jq '[.workflow_runs[] | select(.conclusion == "failure")] | length')
    local cancelled_runs=$(echo "$runs_data" | jq '[.workflow_runs[] | select(.conclusion == "cancelled")] | length')
    
    local success_rate=0
    if [ "$total_runs" -gt 0 ]; then
        success_rate=$(echo "scale=2; $successful_runs * 100 / $total_runs" | bc 2>/dev/null || echo "0")
    fi
    
    echo "=== Build Health Analysis ==="
    echo "Total Runs: $total_runs"
    echo "Successful: $successful_runs"
    echo "Failed: $failed_runs"
    echo "Cancelled: $cancelled_runs"
    echo "Success Rate: ${success_rate}%"
    echo ""
    
    # Health assessment
    if (( $(echo "$success_rate >= 90" | bc -l) )); then
        log_success "Build health: EXCELLENT (${success_rate}%)"
        return 0
    elif (( $(echo "$success_rate >= 75" | bc -l) )); then
        log_info "Build health: GOOD (${success_rate}%)"
        return 0
    elif (( $(echo "$success_rate >= 50" | bc -l) )); then
        log_warn "Build health: FAIR (${success_rate}%) - Investigation recommended"
        return 1
    else
        log_error "Build health: POOR (${success_rate}%) - Immediate attention required"
        return 2
    fi
}

check_recent_failures() {
    local runs_data="$1"
    local failure_threshold="${2:-3}"
    
    log_info "Checking for recent consecutive failures..."
    
    local recent_conclusions=$(echo "$runs_data" | jq -r '.workflow_runs[0:5][] | .conclusion')
    local consecutive_failures=0
    local failure_details=()
    
    while IFS= read -r conclusion; do
        if [ "$conclusion" = "failure" ]; then
            consecutive_failures=$((consecutive_failures + 1))
        else
            break
        fi
    done <<< "$recent_conclusions"
    
    if [ $consecutive_failures -ge $failure_threshold ]; then
        log_error "ALERT: $consecutive_failures consecutive build failures detected!"
        
        # Get failure details
        echo "$runs_data" | jq -r '.workflow_runs[0:'"$consecutive_failures"'][] | 
            "Run #\(.run_number): \(.head_commit.message // "No commit message") (Commit: \(.head_sha[0:7]))"' | 
            while IFS= read -r line; do
                log_error "  $line"
            done
        
        return 1
    else
        log_success "No concerning failure patterns detected"
        return 0
    fi
}

check_build_duration_trends() {
    local runs_data="$1"
    
    log_info "Analyzing build duration trends..."
    
    local avg_duration=$(echo "$runs_data" | jq -r '
        [.workflow_runs[] | select(.conclusion == "success") | 
         ((.updated_at | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime) - 
          (.created_at | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime))] | 
        if length > 0 then (add / length) else 0 end')
    
    if [ "$avg_duration" != "0" ]; then
        local avg_minutes=$(echo "scale=1; $avg_duration / 60" | bc 2>/dev/null || echo "0")
        echo "Average build duration: ${avg_minutes} minutes"
        
        if (( $(echo "$avg_minutes > 30" | bc -l) )); then
            log_warn "Build duration is high (${avg_minutes}min) - Consider optimization"
        else
            log_success "Build duration is acceptable (${avg_minutes}min)"
        fi
    else
        log_warn "Unable to calculate average build duration"
    fi
}

check_architecture_failures() {
    local runs_data="$1"
    
    log_info "Checking for architecture-specific failure patterns..."
    
    # This would require access to job-level data, which needs additional API calls
    # For now, we'll note this as a future enhancement
    log_info "Architecture-specific analysis requires job-level data (future enhancement)"
}

generate_status_report() {
    local runs_data="$1"
    local report_file="${2:-build-status-report.json}"
    
    log_info "Generating status report..."
    
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local latest_run=$(echo "$runs_data" | jq '.workflow_runs[0]')
    
    cat > "$report_file" << EOF
{
  "generated_at": "$timestamp",
  "repository": "$REPO_OWNER/$REPO_NAME",
  "workflow": "$WORKFLOW_NAME",
  "analysis": {
    "total_runs_analyzed": $(echo "$runs_data" | jq '.workflow_runs | length'),
    "success_rate": $(echo "$runs_data" | jq '[.workflow_runs[] | select(.conclusion == "success")] | length / (.workflow_runs | length) * 100'),
    "latest_run": {
      "number": $(echo "$latest_run" | jq '.run_number'),
      "status": "$(echo "$latest_run" | jq -r '.conclusion // "in_progress"')",
      "created_at": "$(echo "$latest_run" | jq -r '.created_at')",
      "head_sha": "$(echo "$latest_run" | jq -r '.head_sha')"
    }
  },
  "health_status": "$(analyze_build_health "$runs_data" >/dev/null 2>&1 && echo "healthy" || echo "unhealthy")",
  "alerts": [
    $(check_recent_failures "$runs_data" >/dev/null 2>&1 || echo '"consecutive_failures_detected"')
  ]
}
EOF
    
    log_success "Status report generated: $report_file"
}

send_notifications() {
    local health_status="$1"
    local consecutive_failures="$2"
    
    # This function would integrate with notification services
    # For now, we'll just log the notification intent
    
    if [ "$health_status" != "0" ] || [ "$consecutive_failures" != "0" ]; then
        log_warn "NOTIFICATION: Build health issues detected"
        log_warn "In a production environment, this would trigger:"
        log_warn "  - Slack/Discord notifications"
        log_warn "  - Email alerts to maintainers"
        log_warn "  - GitHub issue creation"
        log_warn "  - Dashboard status updates"
    fi
}

main() {
    local limit="${1:-20}"
    local report_file="${2:-build-status-report.json}"
    
    echo "=== Build Status Monitor ==="
    echo "Repository: $REPO_OWNER/$REPO_NAME"
    echo "Workflow: $WORKFLOW_NAME"
    echo "Analyzing last $limit runs"
    echo ""
    
    check_dependencies
    
    local runs_data
    runs_data=$(get_workflow_runs "$limit")
    
    if [ $? -ne 0 ]; then
        log_error "Failed to fetch workflow data"
        exit 1
    fi
    
    # Perform analysis
    local health_status=0
    local consecutive_failures=0
    
    analyze_build_health "$runs_data" || health_status=$?
    check_recent_failures "$runs_data" || consecutive_failures=$?
    check_build_duration_trends "$runs_data"
    check_architecture_failures "$runs_data"
    
    # Generate report
    generate_status_report "$runs_data" "$report_file"
    
    # Send notifications if needed
    send_notifications "$health_status" "$consecutive_failures"
    
    echo ""
    echo "=== Monitor Summary ==="
    if [ $health_status -eq 0 ] && [ $consecutive_failures -eq 0 ]; then
        log_success "All checks passed - build system is healthy"
        exit 0
    else
        log_error "Issues detected - review the analysis above"
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--limit)
            LIMIT="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -r|--repo)
            if [[ "$2" == *"/"* ]]; then
                REPO_OWNER="${2%/*}"
                REPO_NAME="${2#*/}"
            fi
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -l, --limit NUM     Number of workflow runs to analyze (default: 20)"
            echo "  -o, --output FILE   Output file for status report (default: build-status-report.json)"
            echo "  -r, --repo OWNER/NAME  Repository to monitor (default: from env)"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  GITHUB_TOKEN        GitHub personal access token (recommended)"
            echo "  GITHUB_REPOSITORY_OWNER  Repository owner"
            echo "  GITHUB_REPOSITORY_NAME   Repository name"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "${LIMIT:-20}" "${OUTPUT_FILE:-build-status-report.json}"