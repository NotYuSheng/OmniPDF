#!/bin/bash

# OmniPDF Image Loader - Automates loading external images into CRC registry
# Usage: ./load-images.sh <external-image-url> [external-image-url] ...
#
# Examples:
#   ./load-images.sh ghcr.io/notyusheng/pdf_extraction_service:dev-v0.0.0-6653136
#   ./load-images.sh ghcr.io/notyusheng/pdf_extraction_service:v1.0.0 ghcr.io/notyusheng/embedder_service:v1.1.0

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE=${NAMESPACE:-omnipdf}
CRC_REGISTRY="default-route-openshift-image-registry.apps-crc.testing"

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if running in CRC
    if ! crc status | grep -q "Running"; then
        error "CRC is not running. Please start CRC first with 'crc start'"
    fi
    
    # Check if oc is logged in
    if ! oc whoami &>/dev/null; then
        error "Not logged into OpenShift. Please login first with 'oc login'"
    fi
    
    # Check if docker is available
    if ! command -v docker &>/dev/null; then
        error "Docker is not installed or not in PATH"
    fi
    
    # Check if docker daemon is running
    if ! docker info &>/dev/null; then
        error "Docker daemon is not running"
    fi
    
    success "Prerequisites check passed"
}

setup_registry_access() {
    log "Setting up CRC registry access..."
    
    # Create namespace if it doesn't exist
    if ! oc get namespace "$NAMESPACE" &>/dev/null; then
        log "Creating namespace: $NAMESPACE"
        oc create namespace "$NAMESPACE"
    fi
    
    # Switch to the namespace
    oc project "$NAMESPACE"
    
    # Login to CRC registry
    local token=$(oc whoami --show-token)
    local username=$(oc whoami)
    
    log "Logging into CRC registry: $CRC_REGISTRY"
    if ! echo "$token" | docker login -u "$username" --password-stdin "$CRC_REGISTRY" 2>/dev/null; then
        error "Failed to login to CRC registry"
    fi
    
    success "Registry access configured"
}

extract_image_info() {
    local external_image="$1"
    
    # Parse the external image URL
    # Handle multiple formats:
    # - registry.com/org/image:tag (3 components)
    # - docker.io/org/repo:tag (Docker Hub 3 components)  
    # - docker.io/minio/minio:latest (Docker Hub 4 components)
    
    # Try 4-component format first (docker.io/org/repo:tag)
    if [[ "$external_image" =~ ^([^/]+)/([^/]+)/([^/]+)/([^:@]+)(:(.+)|@(.+))?$ ]]; then
        local registry="${BASH_REMATCH[1]}"
        local org="${BASH_REMATCH[2]}"
        local repo="${BASH_REMATCH[3]}"
        local image="${BASH_REMATCH[4]}"
        local tag_or_sha="${BASH_REMATCH[6]:-${BASH_REMATCH[7]:-latest}}"
        
        # For SHA references, create a simpler tag
        if [[ "$tag_or_sha" =~ ^sha256: ]]; then
            tag_or_sha="$(echo "$tag_or_sha" | cut -c1-12)"
        fi
        
        # Use the last component as the image name for local registry
        echo "$registry|$org/$repo|$image|$tag_or_sha"
    # Try 3-component format (registry.com/org/image:tag)
    elif [[ "$external_image" =~ ^([^/]+)/([^/]+)/([^:@]+)(:(.+)|@(.+))?$ ]]; then
        local registry="${BASH_REMATCH[1]}"
        local org="${BASH_REMATCH[2]}"
        local image="${BASH_REMATCH[3]}"
        local tag_or_sha="${BASH_REMATCH[5]:-${BASH_REMATCH[6]:-latest}}"
        
        # For SHA references, create a simpler tag
        if [[ "$tag_or_sha" =~ ^sha256: ]]; then
            tag_or_sha="$(echo "$tag_or_sha" | cut -c1-12)"
        fi
        
        echo "$registry|$org|$image|$tag_or_sha"
    else
        error "Invalid image format: $external_image. Expected format: registry.com/org/image:tag or registry.com/org/repo/image:tag"
    fi
}

load_image() {
    local external_image="$1"
    log "Processing image: $external_image"
    
    # Extract image components
    local image_info
    image_info=$(extract_image_info "$external_image")
    IFS='|' read -r registry org image tag <<< "$image_info"
    
    # Generate local image name
    local local_image="$CRC_REGISTRY/$NAMESPACE/${image}:${tag}"
    
    log "  External: $external_image"
    log "  Local:    $local_image"
    
    # Pull external image
    log "  Pulling external image..."
    if ! docker pull "$external_image"; then
        error "Failed to pull external image: $external_image"
    fi
    
    # Tag for local registry
    log "  Tagging for local registry..."
    docker tag "$external_image" "$local_image"
    
    # Push to local registry
    log "  Pushing to CRC registry..."
    if ! docker push "$local_image"; then
        error "Failed to push to CRC registry: $local_image"
    fi
    
    success "  Image loaded: $image:$tag"
    echo "  Use in values-{ENV}.yaml:"
    echo "    image:"
    echo "      repository: $CRC_REGISTRY/$NAMESPACE/$image"
    echo "      tag: \"$tag\""
    echo "      pullPolicy: IfNotPresent"
    echo ""
}

cleanup_local_images() {
    log "Cleaning up local Docker images..."
    # Remove dangling images to save space
    docker image prune -f >/dev/null 2>&1 || true
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] <external-image-url> [external-image-url] ...
       $0 [OPTIONS] -f <file>

Load external container images into CRC's internal registry for use with Helm charts.

Options:
  -f, --file FILE    Load image URLs from a file (one URL per line)
  -h, --help         Show this help message

Examples:
  $0 ghcr.io/notyusheng/pdf_extraction_service:dev-v0.0.0-6653136
  $0 ghcr.io/notyusheng/pdf_extraction_service:v1.0.0 ghcr.io/notyusheng/embedder_service:v1.1.0
  $0 -f images.txt

File format (images.txt):
  ghcr.io/notyusheng/pdf_extraction_service:dev-v0.0.0-6653136
  ghcr.io/notyusheng/embedder_service:dev-v0.0.0-6255367
  ghcr.io/notyusheng/pdf_processor_service:latest
  # Comments and empty lines are ignored

The script will:
1. Pull images from external registries
2. Tag them for CRC's internal registry
3. Push them to CRC registry
4. Show how to configure Helm environment values files

Environment Variables:
  NAMESPACE    Target namespace (default: omnipdf)

Prerequisites:
- CRC must be running
- Must be logged into OpenShift (oc login)
- Docker must be available and running
EOF
}

read_images_from_file() {
    local file="$1"
    local images=()
    
    if [[ ! -f "$file" ]]; then
        error "File not found: $file"
    fi
    
    log "Reading images from file: $file" >&2
    
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip empty lines and comments
        if [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi
        
        # Trim whitespace
        line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        if [[ -n "$line" ]]; then
            images+=("$line")
        fi
    done < "$file"
    
    if [[ ${#images[@]} -eq 0 ]]; then
        error "No valid image URLs found in file: $file"
    fi
    
    log "Found ${#images[@]} images in file" >&2
    printf '%s\n' "${images[@]}"
}

main() {
    local file_mode=false
    local input_file=""
    local images=()
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -f|--file)
                file_mode=true
                input_file="$2"
                shift 2
                ;;
            -*)
                error "Unknown option: $1"
                ;;
            *)
                if [[ "$file_mode" == true ]]; then
                    error "Cannot specify both file mode (-f) and individual image URLs"
                fi
                images+=("$1")
                shift
                ;;
        esac
    done
    
    # Check for help flag or no arguments
    if [[ "$file_mode" == false ]] && [[ ${#images[@]} -eq 0 ]]; then
        show_usage
        exit 0
    fi
    
    log "OmniPDF Image Loader - Starting..."
    log "Target namespace: $NAMESPACE"
    
    check_prerequisites
    setup_registry_access
    
    # Get list of images to process
    if [[ "$file_mode" == true ]]; then
        readarray -t images < <(read_images_from_file "$input_file")
    fi
    
    # Process each image
    local success_count=0
    local total_count=${#images[@]}
    
    for external_image in "${images[@]}"; do
        if load_image "$external_image"; then
            ((success_count++))
        else
            warn "Failed to process: $external_image"
        fi
    done
    
    cleanup_local_images
    
    echo ""
    success "Processed $success_count/$total_count images successfully"
    
    if [[ $success_count -gt 0 ]]; then
        echo ""
        log "Next steps:"
        echo "1. Update your Helm values-{ENV}.yaml files with the local registry URLs shown above"
        echo "2. Deploy with: make install CHART_NAME=<service> ENV=<env>"
        echo "3. Verify with: oc get pods -n $NAMESPACE"
    fi
}

main "$@"