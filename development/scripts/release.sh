#!/bin/bash
# Release Script for AICleaner v3 Home Assistant Add-on
# Creates production-ready releases with proper versioning and validation

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
VERSION_MANAGER="$SCRIPT_DIR/version_manager.py"
BUILD_SCRIPT="$SCRIPT_DIR/build.sh"

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

show_help() {
    cat << EOF
AICleaner v3 Release Script

Usage: $0 <command> [options]

Commands:
  patch                    - Create patch release (x.x.X)
  minor                    - Create minor release (x.X.0)
  major                    - Create major release (X.0.0)
  custom <version>         - Create custom version release
  validate                 - Validate current release readiness
  build                    - Build Docker images for all architectures
  
Options:
  -m, --message <msg>      - Release message
  -d, --dry-run           - Show what would be done without executing
  -h, --help              - Show this help message
  
Examples:
  $0 patch -m "Fix authentication bug"
  $0 minor -m "Add new zone management features"
  $0 major -m "Complete rewrite with new architecture"
  $0 custom 3.1.0-beta.1 -m "Beta release for testing"
  $0 validate
  $0 build
EOF
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check if we're in a git repository
    if ! git rev-parse --is-inside-work-tree &>/dev/null; then
        log_error "Not in a git repository"
        exit 1
    fi
    
    # Check if Python is available
    if ! command -v python3 &>/dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check if version manager exists
    if [[ ! -f "$VERSION_MANAGER" ]]; then
        log_error "Version manager not found at $VERSION_MANAGER"
        exit 1
    fi
    
    # Check if config.yaml exists
    if [[ ! -f "$PROJECT_ROOT/config.yaml" ]]; then
        log_error "config.yaml not found in project root"
        exit 1
    fi
    
    log_success "All dependencies found"
}

check_git_status() {
    log_info "Checking git status..."
    
    # Check if working directory is clean
    if ! git diff-index --quiet HEAD --; then
        log_error "Working directory is not clean. Please commit or stash changes."
        exit 1
    fi
    
    # Check if we're on main branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [[ "$current_branch" != "main" ]]; then
        log_warning "Not on main branch (current: $current_branch)"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "Git status check passed"
}

validate_release() {
    log_info "Validating release readiness..."
    
    # Check if required files exist
    required_files=(
        "config.yaml"
        "Dockerfile"
        "README.md"
        "INSTALL.md"
        "build.yaml"
        "requirements.txt"
        "addons/aicleaner_v3/run.sh"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            log_error "Required file missing: $file"
            exit 1
        fi
    done
    
    # Validate configuration
    if ! python3 -c "import yaml; yaml.safe_load(open('$PROJECT_ROOT/config.yaml'))" 2>/dev/null; then
        log_error "Invalid config.yaml format"
        exit 1
    fi
    
    # Check if tests pass (if test directory exists)
    if [[ -d "$PROJECT_ROOT/addons/aicleaner_v3/tests" ]]; then
        log_info "Running tests..."
        cd "$PROJECT_ROOT/addons/aicleaner_v3"
        if command -v pytest &>/dev/null; then
            if ! pytest tests/ -v --tb=short; then
                log_error "Tests failed"
                exit 1
            fi
        else
            log_warning "pytest not found, skipping tests"
        fi
        cd "$PROJECT_ROOT"
    fi
    
    log_success "Release validation passed"
}

create_release() {
    local release_type="$1"
    local version="$2"
    local message="$3"
    local dry_run="$4"
    
    log_info "Creating $release_type release..."
    
    # Get current version
    current_version=$(python3 "$VERSION_MANAGER" current | cut -d' ' -f3)
    log_info "Current version: $current_version"
    
    # Calculate new version
    if [[ "$release_type" == "custom" ]]; then
        new_version="$version"
    else
        new_version=$(python3 "$VERSION_MANAGER" bump "$release_type" --dry-run 2>/dev/null | grep "to" | cut -d' ' -f4)
    fi
    
    if [[ -z "$new_version" ]]; then
        log_error "Failed to calculate new version"
        exit 1
    fi
    
    log_info "New version: $new_version"
    
    if [[ "$dry_run" == "true" ]]; then
        log_info "DRY RUN: Would update version to $new_version"
        log_info "DRY RUN: Would create git tag v$new_version"
        log_info "DRY RUN: Would update changelog"
        return 0
    fi
    
    # Update version in all files
    if [[ "$release_type" == "custom" ]]; then
        if ! python3 "$VERSION_MANAGER" set "$new_version" "$message"; then
            log_error "Failed to update version"
            exit 1
        fi
    else
        if ! python3 "$VERSION_MANAGER" bump "$release_type" "$message"; then
            log_error "Failed to bump version"
            exit 1
        fi
    fi
    
    # Update git hash in version file
    git_hash=$(git rev-parse HEAD)
    version_file="$PROJECT_ROOT/addons/aicleaner_v3/core/version.py"
    if [[ -f "$version_file" ]]; then
        sed -i.bak "s/__git_hash__ = \"unknown\"/__git_hash__ = \"$git_hash\"/" "$version_file"
        rm "$version_file.bak"
    fi
    
    # Commit changes
    git add -A
    git commit -m "Release v$new_version: $message"
    
    # Create and push tag
    git tag -a "v$new_version" -m "Release v$new_version: $message"
    
    log_success "Created release v$new_version"
    log_info "To publish: git push origin main --tags"
}

build_docker_images() {
    log_info "Building Docker images for all architectures..."
    
    # Get current version
    current_version=$(python3 "$VERSION_MANAGER" current | cut -d' ' -f3)
    
    # Build for each architecture
    architectures=("aarch64" "amd64" "armv7" "armhf" "i386")
    
    for arch in "${architectures[@]}"; do
        log_info "Building for $arch..."
        
        # Build image
        if ! docker buildx build \
            --platform "linux/$arch" \
            --build-arg "BUILD_ARCH=$arch" \
            --build-arg "BUILD_VERSION=$current_version" \
            -t "aicleaner_v3:$current_version-$arch" \
            -f Dockerfile \
            . ; then
            log_error "Failed to build for $arch"
            exit 1
        fi
        
        log_success "Built image for $arch"
    done
    
    log_success "All Docker images built successfully"
}

generate_release_notes() {
    local version="$1"
    
    log_info "Generating release notes for v$version..."
    
    # Get changelog entry for this version
    changelog_entry=$(sed -n "/## \[$version\]/,/## \[/p" "$PROJECT_ROOT/CHANGELOG.md" | head -n -1)
    
    if [[ -z "$changelog_entry" ]]; then
        log_warning "No changelog entry found for v$version"
        return 1
    fi
    
    # Create release notes file
    cat > "$PROJECT_ROOT/RELEASE_NOTES.md" << EOF
# AICleaner v3 Release Notes - v$version

$changelog_entry

## Installation

1. Add repository to Home Assistant:
   \`\`\`
   https://github.com/drewcifer/aicleaner_v3
   \`\`\`

2. Install AICleaner v3 from Add-on Store

3. Configure and start the add-on

## Docker Images

Multi-architecture Docker images are available:
- \`ghcr.io/drewcifer/aicleaner_v3-aarch64:$version\`
- \`ghcr.io/drewcifer/aicleaner_v3-amd64:$version\`
- \`ghcr.io/drewcifer/aicleaner_v3-armv7:$version\`
- \`ghcr.io/drewcifer/aicleaner_v3-armhf:$version\`
- \`ghcr.io/drewcifer/aicleaner_v3-i386:$version\`

## Support

- [Documentation](https://github.com/drewcifer/aicleaner_v3/blob/main/README.md)
- [Installation Guide](https://github.com/drewcifer/aicleaner_v3/blob/main/INSTALL.md)
- [Issue Tracker](https://github.com/drewcifer/aicleaner_v3/issues)
EOF
    
    log_success "Release notes generated at RELEASE_NOTES.md"
}

# Main script logic
main() {
    cd "$PROJECT_ROOT"
    
    # Parse command line arguments
    command=""
    message=""
    dry_run="false"
    custom_version=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            patch|minor|major|validate|build)
                command="$1"
                shift
                ;;
            custom)
                command="custom"
                custom_version="$2"
                shift 2
                ;;
            -m|--message)
                message="$2"
                shift 2
                ;;
            -d|--dry-run)
                dry_run="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Check if command is provided
    if [[ -z "$command" ]]; then
        log_error "No command specified"
        show_help
        exit 1
    fi
    
    # Check dependencies
    check_dependencies
    
    # Execute command
    case "$command" in
        patch|minor|major)
            if [[ -z "$message" ]]; then
                log_error "Release message is required for $command releases"
                exit 1
            fi
            
            check_git_status
            validate_release
            create_release "$command" "" "$message" "$dry_run"
            
            if [[ "$dry_run" != "true" ]]; then
                current_version=$(python3 "$VERSION_MANAGER" current | cut -d' ' -f3)
                generate_release_notes "$current_version"
            fi
            ;;
        custom)
            if [[ -z "$custom_version" ]]; then
                log_error "Custom version is required"
                exit 1
            fi
            
            if [[ -z "$message" ]]; then
                log_error "Release message is required for custom releases"
                exit 1
            fi
            
            check_git_status
            validate_release
            create_release "custom" "$custom_version" "$message" "$dry_run"
            
            if [[ "$dry_run" != "true" ]]; then
                generate_release_notes "$custom_version"
            fi
            ;;
        validate)
            validate_release
            log_success "Release validation completed successfully"
            ;;
        build)
            build_docker_images
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"