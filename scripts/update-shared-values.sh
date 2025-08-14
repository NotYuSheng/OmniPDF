#!/bin/bash
# Script to update shared values across all environments
# Usage: ./scripts/update-shared-values.sh <key=value>
# Example: ./scripts/update-shared-values.sh "networkPolicy.enabled=true"

set -e

SHARED_VALUES_DIR="helm/shared-values"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <key=value> [environment]"
    echo ""
    echo "Examples:"
    echo "  $0 'networkPolicy.enabled=true'                    # Update all environments"
    echo "  $0 'resources.limits.cpu=1000m' staging           # Update staging only"
    echo "  $0 'serviceMonitor.enabled=true' prod             # Update production only"
    echo ""
    echo "Available environments: dev, staging, prestaging, prod"
    exit 1
fi

KEY_VALUE="$1"
TARGET_ENV="${2:-all}"

# Parse key=value
KEY=$(echo "$KEY_VALUE" | cut -d'=' -f1)
VALUE=$(echo "$KEY_VALUE" | cut -d'=' -f2-)

echo "🔧 Updating shared values: $KEY_VALUE"
echo "🎯 Target environment: $TARGET_ENV"
echo ""

update_yaml_file() {
    local file="$1"
    local key="$2"
    local value="$3"
    
    if [ ! -f "$file" ]; then
        echo "⚠️  File not found: $file"
        return 1
    fi
    
    echo "📝 Updating $file..."
    
    # Use yq if available, otherwise use improved sed fallback
    if command -v yq >/dev/null 2>&1; then
        # Use strenv to preserve value types (boolean, number, string)
        yq eval ".$key = strenv(VALUE)" -i "$file"
    else
        echo "⚠️  Warning: yq not found, using sed fallback. Install yq for better YAML parsing."
        echo "   Install with: sudo snap install yq (or brew install yq on macOS)"
        
        # Check if this is a nested key (contains dots)
        if [[ "$key" == *.* ]]; then
            echo "⚠️  Warning: Nested key '$key' detected. Sed fallback may not work correctly."
            echo "   Please install yq for proper nested key support."
            return 1
        fi
        
        # Escape the key for regex
        escaped_key=$(echo "$key" | sed 's/[[\.*^$()+?{|]/\\&/g')
        
        # Check if key exists in file
        if ! grep -q "^[[:space:]]*$escaped_key[[:space:]]*:" "$file"; then
            echo "⚠️  Warning: Key '$key' not found in $file"
            return 1
        fi
        
        # Determine value type and format appropriately
        if [[ "$value" =~ ^(true|false)$ ]]; then
            # Boolean value - no quotes
            sed -i "s/^[[:space:]]*$escaped_key[[:space:]]*:.*/  $key: $value/" "$file"
        elif [[ "$value" =~ ^[0-9]+$ ]]; then
            # Numeric value - no quotes  
            sed -i "s/^[[:space:]]*$escaped_key[[:space:]]*:.*/  $key: $value/" "$file"
        else
            # String value - add quotes
            sed -i "s/^[[:space:]]*$escaped_key[[:space:]]*:.*/  $key: \"$value\"/" "$file"
        fi
    fi
}

# Update files based on target environment
cd "$ROOT_DIR"

if [ "$TARGET_ENV" = "all" ] || [ "$TARGET_ENV" = "dev" ]; then
    update_yaml_file "$SHARED_VALUES_DIR/common-dev.yaml" "$KEY" "$VALUE"
fi

if [ "$TARGET_ENV" = "all" ] || [ "$TARGET_ENV" = "staging" ]; then
    update_yaml_file "$SHARED_VALUES_DIR/common-staging.yaml" "$KEY" "$VALUE"
fi

if [ "$TARGET_ENV" = "all" ] || [ "$TARGET_ENV" = "prestaging" ]; then
    update_yaml_file "$SHARED_VALUES_DIR/common-prestaging.yaml" "$KEY" "$VALUE"
fi

if [ "$TARGET_ENV" = "all" ] || [ "$TARGET_ENV" = "prod" ]; then
    update_yaml_file "$SHARED_VALUES_DIR/common-prod.yaml" "$KEY" "$VALUE"
fi

echo ""
echo "✅ Shared values updated successfully!"
echo ""
echo "🚀 To apply changes, run:"
if [ "$TARGET_ENV" = "all" ]; then
    echo "   make upgrade-all ENV=dev"
    echo "   make upgrade-all ENV=staging" 
    echo "   make upgrade-all ENV=prestaging"
    echo "   make upgrade-all ENV=prod"
else
    echo "   make upgrade-all ENV=$TARGET_ENV"
fi