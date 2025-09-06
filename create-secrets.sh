#!/bin/bash
# Create Kubernetes secrets from .env files for all OmniPDF services

set -e

NAMESPACE="omnipdf"

echo "🔐 Creating Kubernetes secrets from .env files for OmniPDF services..."

# Function to create secret from .env file
create_secret_from_env() {
    local service_name="$1"
    local env_file="$2"
    local secret_name="${service_name}-secrets"
    
    if [[ ! -f "$env_file" ]]; then
        echo "⚠️  No .env file found for $service_name, skipping..."
        return
    fi
    
    echo "Creating secret: $secret_name from $env_file"
    
    # Delete existing secret if it exists
    oc delete secret "$secret_name" -n "$NAMESPACE" 2>/dev/null || true
    
    # Create secret from .env file
    oc create secret generic "$secret_name" \
        --from-env-file="$env_file" \
        -n "$NAMESPACE"
    
    echo "✅ Created secret: $secret_name"
}

# Create secrets for all services
create_secret_from_env "chat-service" "chat_service/.env"
create_secret_from_env "pdf-processor-service" "pdf_processor_service/.env" 
create_secret_from_env "pdf-extraction-service" "pdf_extraction_service/.env"
create_secret_from_env "docling-translation-service" "docling_translation_service/.env"
create_secret_from_env "pdf-renderer-service" "pdf_renderer_service/.env"
create_secret_from_env "embedder-service" "embedder_service/.env"
create_secret_from_env "metadata-service" "metadata_service/.env"
create_secret_from_env "image-captioner-service" "image_captioner_service/.env"
create_secret_from_env "cleaner" "cleaner/.env"
create_secret_from_env "nginx" "nginx/.env"
create_secret_from_env "frontend" "frontend/.env"

echo ""
echo "🎉 All secrets created successfully!"
echo ""
echo "📋 List of created secrets:"
oc get secrets -n "$NAMESPACE" | grep -E "(chat-service|pdf-|docling-|embedder-|metadata-|image-captioner-|cleaner|nginx|frontend)-secrets" || echo "No service secrets found"