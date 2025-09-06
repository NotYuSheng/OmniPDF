#!/bin/bash
# Update all Chart.yaml files to use the correct appVersion

set -e

NEW_VERSION="dev-v0.0.3-5d69f89"
OLD_PATTERN="dev-v0.0.0-6653136"

echo "🏷️  Updating all Chart.yaml appVersion to: $NEW_VERSION"

# Find all Chart.yaml files and update appVersion
for chart_file in helm/*/Chart.yaml; do
    if [[ -f "$chart_file" ]]; then
        service_name=$(basename $(dirname "$chart_file"))
        
        # Skip shared-values and assets directories
        if [[ "$service_name" == "shared-values" || "$service_name" == "assets" ]]; then
            continue
        fi
        
        echo "Updating $chart_file..."
        
        # Update appVersion line (portable across Linux/macOS)
        sed -i.bak "s/appVersion: \"$OLD_PATTERN\"/appVersion: \"$NEW_VERSION\"/g" "$chart_file"
        
        # Also check for other old version patterns and update
        sed -i.bak "s/appVersion: \"dev-v0.0.1-860e67e\"/appVersion: \"$NEW_VERSION\"/g" "$chart_file"
        
        # Clean up backup files
        rm -f "$chart_file.bak"
        
        echo "✅ Updated appVersion for $service_name"
    fi
done

echo ""
echo "🎉 All Chart.yaml files updated!"
echo ""
echo "📋 Verification - showing appVersion from all Chart.yaml files:"
grep -r "appVersion:" helm/*/Chart.yaml | grep -v shared-values | grep -v assets || echo "No Chart.yaml files found"