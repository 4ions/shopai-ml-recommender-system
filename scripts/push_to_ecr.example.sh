#!/bin/bash
# Script para construir y subir imagen Docker a ECR
#
# IMPORTANTE: Copia este archivo a push_to_ecr.sh y configura tus variables
# o usa variables de entorno:
#   export AWS_ACCOUNT_ID="your-account-id"
#   export AWS_REGION="us-east-1"

set -e

ACCOUNT_ID="${AWS_ACCOUNT_ID:-YOUR_ACCOUNT_ID}"
REGION="${AWS_REGION:-us-east-1}"
REPO_NAME="shopai-api"
IMAGE_NAME="shopai-api:latest"

if [ "$ACCOUNT_ID" = "YOUR_ACCOUNT_ID" ]; then
    echo "❌ Error: Configura AWS_ACCOUNT_ID como variable de entorno o edita este script"
    exit 1
fi

echo "Building and pushing Docker image to ECR..."

echo "1. Logging in to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

echo "2. Building and pushing Docker image for linux/amd64..."
docker buildx build \
    --platform linux/amd64 \
    -f docker/Dockerfile \
    -t $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest \
    --push \
    .

echo "Image pushed successfully!"

