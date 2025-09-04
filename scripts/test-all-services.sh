#!/bin/bash

# Quick test runner for all OmniPDF services
# Runs each service test individually to avoid timeout issues

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="/home/ubuntu/Desktop/OmniPDF"
cd "$PROJECT_ROOT"

echo -e "${BLUE}🧪 OmniPDF Complete Unit Test Suite${NC}"
echo "================================================="

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

# Test results tracking  
declare -A test_results
declare -A test_details
total_services=0
passed_services=0

# Function to run tests for a service
run_service_tests() {
    local service=$1
    
    echo -e "\n${BLUE}📦 Testing $service${NC}"
    echo "----------------------------------------"
    
    # Clean up any existing containers first
    docker compose down > /dev/null 2>&1
    
    # Run the test via the unit test script 
    if ./scripts/test-single-service.sh "$service" > "/tmp/${service}_test.log" 2>&1; then
        echo -e "${GREEN}✅ $service tests PASSED${NC}"
        test_results[$service]="PASS"
        # Get test count from log
        test_count=$(grep -o "[0-9]\+ passed" "/tmp/${service}_test.log" | head -1 | grep -o "[0-9]\+")
        test_details[$service]="$test_count tests passed"
        ((passed_services++))
    else
        echo -e "${RED}❌ $service tests FAILED${NC}"
        test_results[$service]="FAIL"
        # Get failure details
        failed_count=$(grep -o "[0-9]\+ failed" "/tmp/${service}_test.log" | head -1 | grep -o "[0-9]\+" || echo "?")
        passed_count=$(grep -o "[0-9]\+ passed" "/tmp/${service}_test.log" | head -1 | grep -o "[0-9]\+" || echo "0")
        test_details[$service]="$failed_count failed, $passed_count passed"
    fi
    
    ((total_services++))
}

# Run tests for all services
for service in "${SERVICES[@]}"; do
    run_service_tests "$service"
done

# Summary
echo ""
echo "================================================="
echo -e "${BLUE}📊 COMPLETE UNIT TEST SUMMARY${NC}"
echo "================================================="

for service in "${SERVICES[@]}"; do
    result=${test_results[$service]}
    details=${test_details[$service]}
    case $result in
        "PASS")
            echo -e "$service: ${GREEN}✅ PASSED${NC} ($details)"
            ;;
        "FAIL") 
            echo -e "$service: ${RED}❌ FAILED${NC} ($details)"
            ;;
    esac
done

echo ""
echo -e "${BLUE}Final Results: $passed_services/$total_services services passed${NC}"

# Final cleanup
docker compose down > /dev/null 2>&1

if [ $passed_services -eq $total_services ]; then
    echo -e "${GREEN}🎉 All unit tests passed!${NC}"
    exit 0
else
    failed=$((total_services - passed_services))
    echo -e "${YELLOW}⚠️  $failed service(s) have failing unit tests${NC}"
    echo ""
    echo -e "${YELLOW}📋 Failed Service Details:${NC}"
    for service in "${SERVICES[@]}"; do
        if [ "${test_results[$service]}" = "FAIL" ]; then
            echo -e "  ${RED}• $service${NC}: ${test_details[$service]}"
            echo -e "    Log available at: ${BLUE}/tmp/${service}_test.log${NC}"
        fi
    done
    exit 1
fi