#!/bin/bash

# Unified Helm deployment script for OmniPDF
# Supports both single service and all services deployment
# Usage: 
#   ./scripts/deploy-helm-charts.sh --service chat-service --env staging
#   ./scripts/deploy-helm-charts.sh --all --env production
#   ./scripts/deploy-helm-charts.sh --help

set -e

# Default values
NAMESPACE="omnipdf"
ENV="staging"
MODE=""
SERVICE=""
ACTION="install"
DRY_RUN=false
SHARED_VALUES_DIR="helm/shared-values"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Usage function
show_help() {
    cat << EOF
🚀 OmniPDF Helm Deployment Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -s, --service SERVICE    Deploy specific service (e.g., chat-service)
    -a, --all               Deploy all services
    -e, --env ENV           Environment (staging|production|prestaging) [default: staging]
    -n, --namespace NS      Kubernetes namespace [default: omnipdf]
    --action ACTION         Helm action (install|upgrade|uninstall) [default: install]
    --dry-run              Show what would be deployed without executing
    -h, --help             Show this help message

EXAMPLES:
    # Deploy single service to staging
    $0 --service chat-service --env staging

    # Deploy all services to production
    $0 --all --env production

    # Upgrade specific service
    $0 --service pdf-processor-service --action upgrade

    # Dry run deployment
    $0 --all --env staging --dry-run

    # Uninstall service
    $0 --service chat-service --action uninstall

SUPPORTED SERVICES:
    rbac, chat-service, pdf-processor-service, pdf-extraction-service,
    docling-translation-service, pdf-renderer-service, embedder-service,
    image-captioner-service, metadata-service, cleaner, frontend,
    nginx, redis, chromadb, minio

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--service)
            SERVICE="$2"
            MODE="single"
            shift 2
            ;;
        -a|--all)
            MODE="all"
            shift
            ;;
        -e|--env)
            ENV="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --action)
            ACTION="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate inputs
if [[ -z "$MODE" ]]; then
    print_error "Must specify either --service or --all"
    show_help
    exit 1
fi

if [[ "$MODE" == "single" && -z "$SERVICE" ]]; then
    print_error "Service name required when using --service"
    show_help
    exit 1
fi

# Build values files in correct precedence order
build_values_files() {
    local service=$1
    local values_files=""
    
    # 1. Shared base values (most general)
    local shared_base="$SHARED_VALUES_DIR/common-base.yaml"
    if [[ -f "$shared_base" ]]; then
        values_files="-f $shared_base"
    fi
    
    # 2. Shared environment values
    local shared_env="$SHARED_VALUES_DIR/common-$ENV.yaml"
    if [[ -f "$shared_env" ]]; then
        values_files="$values_files -f $shared_env"
    fi
    
    # 3. Service environment values (environment-specific deployment)
    local service_env="helm/$service/values-$ENV.yaml"
    if [[ -f "$service_env" ]]; then
        values_files="$values_files -f $service_env"
    else
        # Special case for rbac which uses base values.yaml
        local service_base="helm/$service/values.yaml"
        if [[ -f "$service_base" ]]; then
            values_files="$values_files -f $service_base"
        else
            print_error "No values file found for $service (expected: $service_env or $service_base)"
            return 1
        fi
    fi
    
    echo "$values_files"
}

# Deploy single service
deploy_service() {
    local service=$1
    local chart_dir="helm/$service"
    
    if [[ ! -d "$chart_dir" ]]; then
        print_error "Chart directory not found: $chart_dir"
        return 1
    fi
    
    local values_files
    values_files=$(build_values_files "$service")
    
    local helm_cmd="helm $ACTION $service $chart_dir --namespace $NAMESPACE --create-namespace $values_files"
    
    print_info "Deploying $service to $ENV environment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "DRY RUN - Command that would be executed:"
        echo "  $helm_cmd --dry-run"
        helm $ACTION $service $chart_dir --namespace $NAMESPACE --create-namespace $values_files --dry-run
    else
        print_info "Executing: $helm_cmd"
        if helm $ACTION $service $chart_dir --namespace $NAMESPACE --create-namespace $values_files; then
            print_success "Successfully deployed $service"
        else
            print_error "Failed to deploy $service"
            return 1
        fi
    fi
}

# Deploy all services
deploy_all_services() {
    print_info "Deploying all services to $ENV environment..."
    
    local services=(
        "rbac"
        "redis"
        "chromadb" 
        "minio"
        "pdf-processor-service"
        "pdf-extraction-service"
        "docling-translation-service"
        "pdf-renderer-service"
        "embedder-service"
        "chat-service"
        "image-captioner-service"
        "metadata-service"
        "cleaner"
        "frontend"
        "nginx"
    )
    
    local failed_services=()
    local successful_services=()
    
    for service in "${services[@]}"; do
        if deploy_service "$service"; then
            successful_services+=("$service")
        else
            failed_services+=("$service")
        fi
    done
    
    # Summary
    echo
    print_info "=== DEPLOYMENT SUMMARY ==="
    if [[ ${#successful_services[@]} -gt 0 ]]; then
        print_success "Successfully deployed (${#successful_services[@]}):"
        printf '  %s\n' "${successful_services[@]}"
    fi
    
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        print_error "Failed deployments (${#failed_services[@]}):"
        printf '  %s\n' "${failed_services[@]}"
        return 1
    fi
    
    print_success "All services deployed successfully!"
}

# Main execution
main() {
    print_info "OmniPDF Helm Deployment Script"
    print_info "Mode: $MODE | Environment: $ENV | Namespace: $NAMESPACE | Action: $ACTION"
    
    if [[ "$MODE" == "single" ]]; then
        deploy_service "$SERVICE"
    elif [[ "$MODE" == "all" ]]; then
        deploy_all_services
    fi
}

# Execute main function
main "$@"