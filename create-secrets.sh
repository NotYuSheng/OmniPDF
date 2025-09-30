#!/bin/bash
# Create Kubernetes secrets from .env files for all OmniPDF services
# 
# SECURITY NOTE: All Helm chart secret templates have been removed to prevent
# accidental exposure of secrets in version control. This script creates secrets
# from local .env files, which is the recommended secure approach.

set -e

NAMESPACE="omnipdf"

echo "🔐 Creating Kubernetes secrets from .env files for OmniPDF services..."
echo "🔒 Security: Using external secret creation (no secret templates in charts)"

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

# Auto-discover services by checking helm charts and .env files
echo "🔍 Auto-discovering services from helm charts and .env files..."

# Create secrets for services with helm charts (excluding assets)
for helm_dir in helm/*/; do
    chart_name=$(basename "$helm_dir")
    if [ "$chart_name" != "assets" ]; then
        # Convert chart name to directory name pattern
        if [ "$chart_name" = "chat-service" ]; then
            env_dir="chat_service"
        elif [ "$chart_name" = "pdf-processor-service" ]; then
            env_dir="pdf_processor_service"
        elif [ "$chart_name" = "pdf-extraction-service" ]; then
            env_dir="pdf_extraction_service"
        elif [ "$chart_name" = "docling-translation-service" ]; then
            env_dir="docling_translation_service"
        elif [ "$chart_name" = "pdf-renderer-service" ]; then
            env_dir="pdf_renderer_service"
        elif [ "$chart_name" = "embedder-service" ]; then
            env_dir="embedder_service"
        elif [ "$chart_name" = "metadata-service" ]; then
            env_dir="metadata_service"
        elif [ "$chart_name" = "image-captioner-service" ]; then
            env_dir="image_captioner_service"
        else
            # For services like cleaner, nginx, frontend - use chart name as directory name
            env_dir="$chart_name"
        fi
        
        env_file="${env_dir}/.env"
        echo "Checking for service: $chart_name (env file: $env_file)"
        create_secret_from_env "$chart_name" "$env_file"
    fi
done

# Also check for any additional .env files in root directories not covered by helm charts
echo ""
echo "🔍 Checking for additional .env files..."
for service_dir in */; do
    service_name=$(basename "$service_dir")
    env_file="${service_dir}.env"
    
    # Skip if already processed via helm chart
    if [ ! -d "helm/${service_name}" ] && [ -f "$env_file" ]; then
        echo "Found additional service: $service_name"
        create_secret_from_env "$service_name" "$env_file"
    fi
done

# Interactive creation of infrastructure secrets
echo ""
echo "📦 Creating infrastructure secrets..."

# MinIO secrets
echo ""
echo "🗂️  MinIO Storage Configuration:"
read -p "Enter MinIO root username [minioadmin]: " minio_user
minio_user=${minio_user:-minioadmin}
read -s -p "Enter MinIO root password (required): " minio_password
echo ""

# Validate that password is not empty
if [[ -z "$minio_password" ]]; then
    echo "❌ Error: MinIO password cannot be empty for security reasons"
    echo "Please run the script again and provide a secure password"
    exit 1
fi

# Delete existing secret if it exists
oc delete secret "minio-secrets" -n "$NAMESPACE" 2>/dev/null || true

# Create MinIO secret
oc create secret generic "minio-secrets" \
    --from-literal=MINIO_ROOT_USER="$minio_user" \
    --from-literal=MINIO_ROOT_PASSWORD="$minio_password" \
    -n "$NAMESPACE"

echo "✅ Created secret: minio-secrets"

# Optional: Redis secrets (if authentication is needed)
echo ""
read -p "Configure Redis authentication? (y/N): " configure_redis
if [[ "$configure_redis" =~ ^[Yy]$ ]]; then
    read -s -p "Enter Redis password: " redis_password
    echo ""
    
    # Delete existing secret if it exists
    oc delete secret "redis-secrets" -n "$NAMESPACE" 2>/dev/null || true
    
    # Create Redis secret
    oc create secret generic "redis-secrets" \
        --from-literal=REDIS_PASSWORD="$redis_password" \
        -n "$NAMESPACE"
    
    echo "✅ Created secret: redis-secrets"
fi

# Optional: ChromaDB secrets (if authentication is needed)  
echo ""
read -p "Configure ChromaDB authentication? (y/N): " configure_chroma
if [[ "$configure_chroma" =~ ^[Yy]$ ]]; then
    read -s -p "Enter ChromaDB auth token (optional): " chroma_token
    echo ""
    
    if [[ -n "$chroma_token" ]]; then
        # Delete existing secret if it exists
        oc delete secret "chromadb-secrets" -n "$NAMESPACE" 2>/dev/null || true
        
        # Create ChromaDB secret
        oc create secret generic "chromadb-secrets" \
            --from-literal=CHROMA_SERVER_AUTH_TOKEN="$chroma_token" \
            -n "$NAMESPACE"
        
        echo "✅ Created secret: chromadb-secrets"
    fi
fi

echo ""
echo "🎉 All secrets created successfully!"
echo ""
echo "📋 List of created secrets:"
oc get secrets -n "$NAMESPACE" | grep -E "(chat-service|pdf-|docling-|embedder-|metadata-|image-captioner-|cleaner|nginx|frontend|minio|redis|chromadb)-secrets" || echo "No service secrets found"