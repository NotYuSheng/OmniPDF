#!/bin/bash

# Fix hardcoded CRC registry URLs in staging and production values files
# Replace with proper GHCR registry URLs

echo "🔧 Fixing hardcoded CRC registry URLs in staging and production values files..."

# Find all staging and production values files with the CRC registry
FILES=$(find /home/ubuntu/Desktop/OmniPDF/helm -name "values-staging.yaml" -o -name "values-prod.yaml" | xargs grep -l "default-route-openshift-image-registry.apps-crc.testing")

for file in $FILES; do
    echo "Processing: $file"
    
    # Extract service name from path
    service_dir=$(dirname "$file")
    service_name=$(basename "$service_dir")
    
    # Replace CRC registry with GHCR registry
    sed -i "s|default-route-openshift-image-registry.apps-crc.testing/omnipdf/$service_name|ghcr.io/notyusheng/$service_name|g" "$file"
    
    echo "  ✅ Updated registry URL for $service_name"
done

echo "🎉 All registry URLs updated successfully!"
echo ""
echo "Summary of changes:"
echo "  Old: default-route-openshift-image-registry.apps-crc.testing/omnipdf/SERVICE"
echo "  New: ghcr.io/notyusheng/SERVICE"