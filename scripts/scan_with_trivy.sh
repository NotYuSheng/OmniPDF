#!/bin/bash

# Trivy Security Scanner for OmniPDF Services
# Scans all Docker images for security vulnerabilities

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}🔒 OmniPDF Trivy Security Scanner${NC}"
echo "=========================================="

# Services to scan (those with Dockerfiles or Docker images)
CUSTOM_SERVICES=(
    "chat_service"
    "pdf_extraction_service" 
    "docling_translation_service"
    "pdf_renderer_service"
    "embedder_service"
    "pdf_processor_service"
    "image_captioner_service"
    "frontend"
    "cleaner"
    "nginx"
)

# External Docker images (pre-built)
EXTERNAL_IMAGES=(
    "redis:7.4.4-alpine"
    "chromadb/chroma:1.0.13"
    "minio/minio:RELEASE.2025-07-23T15-54-02Z"
    "minio/mc:RELEASE.2025-07-21T05-28-08Z"
)

# Combine all services for processing
ALL_SERVICES=("${CUSTOM_SERVICES[@]}" "${EXTERNAL_IMAGES[@]}")

# Scan options
SEVERITY="HIGH,CRITICAL"  # Default severity levels
OUTPUT_FORMAT="table"     # Default output format
SCAN_TYPE="all"          # all, image, fs

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --service)
            SINGLE_SERVICE="$2"
            shift 2
            ;;
        --severity)
            SEVERITY="$2"
            shift 2
            ;;
        --format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --type)
            SCAN_TYPE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --service <name>    Scan specific service only"
            echo "  --severity <level>  Severity levels (LOW,MEDIUM,HIGH,CRITICAL)"
            echo "  --format <format>   Output format (table,json,sarif)"
            echo "  --type <type>       Scan type (all,image,fs)"
            echo "  --help             Show this help"
            echo ""
            echo "Available services: ${ALL_SERVICES[*]}"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if Trivy is installed
check_trivy() {
    if ! command -v trivy &> /dev/null; then
        echo -e "${RED}❌ Trivy is not installed${NC}"
        echo ""
        echo "Install Trivy:"
        echo "  # Ubuntu/Debian:"
        echo "  sudo apt-get update && sudo apt-get install wget apt-transport-https gnupg lsb-release"
        echo "  wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -"
        echo "  echo \"deb https://aquasecurity.github.io/trivy-repo/deb \$(lsb_release -sc) main\" | sudo tee -a /etc/apt/sources.list.d/trivy.list"
        echo "  sudo apt-get update && sudo apt-get install trivy"
        echo ""
        echo "  # Or with snap:"
        echo "  sudo snap install trivy"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Trivy $(trivy --version | head -n1 | cut -d' ' -f2) found${NC}"
}

# Check if specific service requested
if [ ! -z "$SINGLE_SERVICE" ]; then
    if [[ " ${ALL_SERVICES[@]} " =~ " $SINGLE_SERVICE " ]]; then
        ALL_SERVICES=("$SINGLE_SERVICE")
        echo -e "${YELLOW}Scanning specific service: $SINGLE_SERVICE${NC}"
    else
        echo -e "${RED}❌ Unknown service: $SINGLE_SERVICE${NC}"
        echo "Available services: ${ALL_SERVICES[*]}"
        exit 1
    fi
fi

# Scan results tracking
declare -A scan_results
total_services=0
clean_services=0

# Function to scan a service
scan_service() {
    local service=$1
    local service_path="$PROJECT_ROOT/$service"
    local image_name=""
    local is_external_image=false
    
    echo ""
    echo -e "${BLUE}🔍 Scanning $service${NC}"
    echo "----------------------------------------"
    
    # Check if it's an external image
    if [[ " ${EXTERNAL_IMAGES[@]} " =~ " $service " ]]; then
        image_name="$service"
        is_external_image=true
        echo "External image: $image_name"
    else
        # Custom service - check for Dockerfile
        if [ ! -f "$service_path/Dockerfile" ]; then
            echo -e "${YELLOW}⚠️  No Dockerfile found for $service${NC}"
            scan_results[$service]="SKIP"
            return 0
        fi
        
        image_name="omnipdf-${service}:latest"
        
        # Check if Docker image exists
        if ! docker images -q "$image_name" | grep -q .; then
            echo -e "${YELLOW}⚠️  Docker image $image_name not found${NC}"
            echo "Build the image first with: docker build -t $image_name $service_path"
            scan_results[$service]="SKIP"
            return 0
        fi
        echo "Custom image: $image_name"
    fi
    
    echo "Severity: $SEVERITY"
    echo "Format: $OUTPUT_FORMAT"
    echo ""
    
    # Create output directory
    mkdir -p "$PROJECT_ROOT/trivy_scan_results"
    local report_file="$PROJECT_ROOT/trivy_scan_results/${service//\//_}-report.txt"
    local log_file="$PROJECT_ROOT/trivy_scan_results/${service//\//_}-scan.log"
    
    # Run Trivy scan with logging
    local scan_exit_code=0
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting scan for $service ($image_name)" | tee "$log_file"
    
    case $SCAN_TYPE in
        "image")
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Running image scan..." | tee -a "$log_file"
            set +e  # Temporarily disable exit on error
            trivy image \
                --severity "$SEVERITY" \
                --format "$OUTPUT_FORMAT" \
                --output "$report_file" \
                "$image_name" 2>&1 | tee -a "$log_file"
            scan_exit_code=$?
            set -e  # Re-enable exit on error
            ;;
        "fs")
            if [ "$is_external_image" = true ]; then
                echo -e "${YELLOW}⚠️  Filesystem scan not available for external image${NC}"
                echo "$(date '+%Y-%m-%d %H:%M:%S') - Skipping filesystem scan for external image" | tee -a "$log_file"
                scan_results[$service]="SKIP"
                return 0
            fi
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Running filesystem scan..." | tee -a "$log_file"
            set +e  # Temporarily disable exit on error
            trivy fs \
                --severity "$SEVERITY" \
                --format "$OUTPUT_FORMAT" \
                --output "$report_file" \
                "$service_path" 2>&1 | tee -a "$log_file"
            scan_exit_code=$?
            set -e  # Re-enable exit on error
            ;;
        "all"|*)
            # For external images, only scan the image
            if [ "$is_external_image" = true ]; then
                echo "$(date '+%Y-%m-%d %H:%M:%S') - Running comprehensive image scan..." | tee -a "$log_file"
                set +e  # Temporarily disable exit on error
                trivy image \
                    --severity "$SEVERITY" \
                    --format "$OUTPUT_FORMAT" \
                    --output "$report_file" \
                    "$image_name" 2>&1 | tee -a "$log_file"
                scan_exit_code=$?
                set -e  # Re-enable exit on error
            else
                # Create consolidated report for custom services (image + filesystem)
                echo "$(date '+%Y-%m-%d %H:%M:%S') - Running comprehensive scan (image + filesystem)..." | tee -a "$log_file"
                
                # Create temporary files
                local temp_image_report="/tmp/trivy_image_${service//\//_}_$$.txt"
                local temp_fs_report="/tmp/trivy_fs_${service//\//_}_$$.txt"
                
                # Run image scan
                echo "  → Scanning Docker image..." | tee -a "$log_file"
                set +e  # Temporarily disable exit on error
                trivy image \
                    --severity "$SEVERITY" \
                    --format "$OUTPUT_FORMAT" \
                    --output "$temp_image_report" \
                    "$image_name" 2>&1 | tee -a "$log_file"
                scan_exit_code=$?
                set -e  # Re-enable exit on error
                
                # Run filesystem scan if directory exists
                if [ -d "$service_path" ]; then
                    echo "  → Scanning filesystem..." | tee -a "$log_file"
                    set +e  # Temporarily disable exit on error
                    trivy fs \
                        --severity "$SEVERITY" \
                        --format "$OUTPUT_FORMAT" \
                        --output "$temp_fs_report" \
                        "$service_path" 2>&1 | tee -a "$log_file"
                    local fs_exit_code=$?
                    set -e  # Re-enable exit on error
                    if [ $fs_exit_code -ne 0 ]; then
                        scan_exit_code=$((scan_exit_code + fs_exit_code))
                    fi
                else
                    echo "  → Skipping filesystem scan (directory not found: $service_path)" | tee -a "$log_file"
                fi
                
                # Combine reports into single file
                {
                    echo "TRIVY SECURITY SCAN REPORT"
                    echo "=========================="
                    echo "Service: $service"
                    echo "Image: $image_name"
                    echo "Scan Date: $(date '+%Y-%m-%d %H:%M:%S')"
                    echo "Severity Levels: $SEVERITY"
                    echo ""
                    
                    if [ -f "$temp_image_report" ]; then
                        echo "DOCKER IMAGE SCAN RESULTS"
                        echo "========================="
                        cat "$temp_image_report"
                        echo ""
                    fi
                    
                    if [ -f "$temp_fs_report" ]; then
                        echo "FILESYSTEM SCAN RESULTS"
                        echo "======================="
                        cat "$temp_fs_report"
                        echo ""
                    fi
                    
                    echo "End of Report"
                    echo "============="
                } > "$report_file"
                
                # Clean up temporary files
                rm -f "$temp_image_report" "$temp_fs_report"
            fi
            ;;
    esac
    
    # Display results and log completion
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    
    # Check if scan completed successfully (exit code 0 = scan ran, not necessarily clean)
    if [ $scan_exit_code -ne 0 ]; then
        echo -e "${RED}❌ $service: Scan failed${NC}"
        echo "$timestamp - Scan failed with exit code: $scan_exit_code" | tee -a "$log_file"
        scan_results[$service]="ERROR"
        total_services=$((total_services + 1))
        return 1
    fi
    
    # Parse report to check for actual vulnerabilities
    local has_vulnerabilities=false
    
    # Check main report file for vulnerabilities
    if [ -f "$report_file" ]; then
        # Look for vulnerability counts in report (format: "Total: X (HIGH: Y, CRITICAL: Z)")
        if grep -E "Total: [1-9][0-9]* \(" "$report_file" >/dev/null 2>&1; then
            has_vulnerabilities=true
        # Also check for individual vulnerability entries in table format
        elif grep -E "│.*│.*│ (HIGH|CRITICAL) │" "$report_file" >/dev/null 2>&1; then
            has_vulnerabilities=true
        fi
    fi
    
    # All vulnerability information is now in the single report file
    
    # Display results based on actual vulnerability detection
    if [ "$has_vulnerabilities" = true ]; then
        echo -e "${RED}🚨 $service: Vulnerabilities detected${NC}"
        echo "   📄 Report saved to: trivy_scan_results/${service//\//_}-report.txt"
        echo "   📄 Log saved to: trivy_scan_results/${service//\//_}-scan.log"
        echo "$timestamp - Scan completed: Vulnerabilities found" | tee -a "$log_file"
        scan_results[$service]="VULNERABILITIES"
    else
        echo -e "${GREEN}✅ $service: No vulnerabilities found${NC}"
        echo "$timestamp - Scan completed successfully: No vulnerabilities found" | tee -a "$log_file"
        scan_results[$service]="CLEAN"
        clean_services=$((clean_services + 1))
    fi
    
    total_services=$((total_services + 1))
}

# Check prerequisites
check_trivy

echo ""
echo -e "${YELLOW}📦 Scanning configuration:${NC}"
echo "Severity levels: $SEVERITY"
echo "Output format: $OUTPUT_FORMAT"
echo "Scan type: $SCAN_TYPE"

# Update Trivy vulnerability database
echo ""
echo -e "${YELLOW}📡 Updating Trivy vulnerability database...${NC}"
trivy image --download-db-only

# Scan each service
echo ""
echo -e "${BLUE}📋 Services to scan: ${#ALL_SERVICES[@]} total${NC}"
for i in "${!ALL_SERVICES[@]}"; do
    echo "  $((i+1)). ${ALL_SERVICES[i]}"
done
echo ""

for i in "${!ALL_SERVICES[@]}"; do
    service="${ALL_SERVICES[i]}"
    echo -e "${YELLOW}Progress: Scanning service $((i+1))/${#ALL_SERVICES[@]}${NC}"
    set +e  # Temporarily disable exit on error for individual service scans
    scan_service "$service"
    set -e  # Re-enable exit on error
done

# Summary
echo ""
echo "=========================================="
echo -e "${BLUE}📊 TRIVY SCAN SUMMARY${NC}"
echo "=========================================="

for service in "${ALL_SERVICES[@]}"; do
    result=${scan_results[$service]}
    case $result in
        "CLEAN")
            echo -e "$service: ${GREEN}✅ CLEAN${NC}"
            ;;
        "VULNERABILITIES") 
            echo -e "$service: ${RED}🚨 VULNERABILITIES FOUND${NC}"
            ;;
        "SKIP")
            echo -e "$service: ${YELLOW}⏭️  SKIPPED${NC}"
            ;;
        "ERROR")
            echo -e "$service: ${RED}❌ ERROR${NC}"
            ;;
        *)
            echo -e "$service: ${RED}❓ NOT SCANNED${NC}"
            ;;
    esac
done

echo ""
echo -e "${BLUE}Results: $clean_services/$total_services services clean${NC}"

if [ -d "$PROJECT_ROOT/trivy_scan_results" ] && [ "$(ls -A $PROJECT_ROOT/trivy_scan_results)" ]; then
    echo ""
    echo -e "${YELLOW}📄 Detailed reports and logs available in: trivy_scan_results/${NC}"
    ls -la "$PROJECT_ROOT/trivy_scan_results/"
fi

if [ $clean_services -eq $total_services ]; then
    echo -e "${GREEN}🎉 All scanned services are clean!${NC}"
    exit 0
else
    vulnerable=$((total_services - clean_services))
    echo -e "${RED}🚨 $vulnerable service(s) have security vulnerabilities${NC}"
    echo ""
    echo -e "${YELLOW}💡 Next steps:${NC}"
    echo "1. Review detailed reports and logs in trivy_scan_results/"
    echo "2. Update vulnerable dependencies in requirements.txt"
    echo "3. Rebuild Docker images"
    echo "4. Re-run this scan to verify fixes"
    exit 1
fi