#!/bin/bash

# Simple Unit Test Runner using Docker Compose
# Starts all services and runs tests in their containers

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}🧪 OmniPDF Unit Test Runner${NC}"
echo "=========================================="

# Services with unit tests
SERVICES=(
    "chat_service"
    "pdf_extraction_service" 
    "docling_translation_service"
    "pdf_renderer_service"
    "embedder_service"
    "pdf_processor_service"
    "image_captioner_service"
)

# Check if specific service requested
if [ ! -z "$1" ]; then
    if [[ " ${SERVICES[@]} " =~ " $1 " ]]; then
        SINGLE_SERVICE="$1"
        echo -e "${YELLOW}Testing specific service: $1${NC}"
    else
        echo -e "${RED}❌ Unknown service: $1${NC}"
        echo "Available services: ${SERVICES[*]}"
        exit 1
    fi
fi

# Start services
echo -e "${YELLOW}🚀 Starting services with docker-compose...${NC}"
if ! docker compose up -d --build; then
    echo -e "${RED}❌ Failed to start services${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Services started${NC}"
echo ""

# Test results tracking  
declare -A test_results
total_services=0
passed_services=0

# Function to run tests for a service
run_service_tests() {
    local service=$1
    
    echo -e "${BLUE}📦 Testing $service${NC}"
    echo "----------------------------------------"
    
    # Install pytest and run tests in the service container
    if docker compose exec -T "$service" sh -c "python -m pytest ${service}/tests/ -v --tb=short"; then
        echo -e "${GREEN}✅ $service tests PASSED${NC}"
        test_results[$service]="PASS"
        ((passed_services++))
    else
        echo -e "${RED}❌ $service tests FAILED${NC}"
        test_results[$service]="FAIL"
    fi
    
    ((total_services++))
    echo ""
}

# Run tests
if [ ! -z "$SINGLE_SERVICE" ]; then
    run_service_tests "$SINGLE_SERVICE"
else
    for service in "${SERVICES[@]}"; do
        run_service_tests "$service"
    done
fi

# Summary
echo "=========================================="
echo -e "${BLUE}📊 UNIT TEST SUMMARY${NC}"
echo "=========================================="

if [ ! -z "$SINGLE_SERVICE" ]; then
    SERVICES=("$SINGLE_SERVICE")
fi

for service in "${SERVICES[@]}"; do
    result=${test_results[$service]}
    case $result in
        "PASS")
            echo -e "$service: ${GREEN}✅ PASSED${NC}"
            ;;
        "FAIL") 
            echo -e "$service: ${RED}❌ FAILED${NC}"
            ;;
    esac
done

echo ""
echo -e "${BLUE}Results: $passed_services/$total_services services passed${NC}"

# Cleanup
echo ""
echo -e "${YELLOW}🧹 Stopping services...${NC}"
docker compose down

if [ $passed_services -eq $total_services ]; then
    echo -e "${GREEN}🎉 All unit tests passed!${NC}"
    exit 0
else
    failed=$((total_services - passed_services))
    echo -e "${RED}🚨 $failed service(s) failed unit tests${NC}"
    exit 1
fi