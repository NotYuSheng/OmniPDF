#!/bin/bash

# Fix hardcoded CRC registry URLs in staging and production values files
# Handle service name variations properly

echo "🔧 Fixing remaining hardcoded CRC registry URLs..."

# Find all files with CRC registry URLs
find /home/ubuntu/Desktop/OmniPDF/helm -name "values-staging.yaml" -o -name "values-prod.yaml" | while read file; do
    if grep -q "default-route-openshift-image-registry.apps-crc.testing" "$file"; then
        echo "Processing: $file"
        
        # Extract the service name from the existing URL in the file
        service_name=$(grep "default-route-openshift-image-registry.apps-crc.testing/omnipdf/" "$file" | sed 's/.*omnipdf\/\([^"]*\).*/\1/')
        
        if [ -n "$service_name" ]; then
            # Replace with GHCR URL
            sed -i "s|default-route-openshift-image-registry.apps-crc.testing/omnipdf/$service_name|ghcr.io/notyusheng/$service_name|g" "$file"
            echo "  ✅ Updated $service_name -> ghcr.io/notyusheng/$service_name"
        else
            echo "  ❌ Could not extract service name from $file"
        fi
    fi
done

echo ""
echo "🎉 Registry URL fix complete!"

# Verify the changes
echo ""
echo "🔍 Verification - remaining CRC URLs:"
find /home/ubuntu/Desktop/OmniPDF/helm -name "values-staging.yaml" -o -name "values-prod.yaml" | xargs grep "default-route-openshift-image-registry.apps-crc.testing" || echo "  ✅ No CRC URLs found - all fixed!"