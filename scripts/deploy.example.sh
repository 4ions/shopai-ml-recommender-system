#!/bin/bash
# Script para desplegar cambios al servicio ECS
# 
# IMPORTANTE: Copia este archivo a deploy.sh y configura tus variables
# o usa variables de entorno:
#   export AWS_ACCOUNT_ID="your-account-id"
#   export AWS_REGION="us-east-1"

set -e

echo "🚀 Desplegando cambios a AWS ECS..."
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables (usar variables de entorno o configurar aquí)
REGION="${AWS_REGION:-us-east-1}"
CLUSTER="${ECS_CLUSTER:-shopai-cluster}"
SERVICE="${ECS_SERVICE:-shopai-api}"
IMAGE_NAME="shopai-api:latest"
ACCOUNT_ID="${AWS_ACCOUNT_ID:-YOUR_ACCOUNT_ID}"
ECR_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/shopai-api:latest"

if [ "$ACCOUNT_ID" = "YOUR_ACCOUNT_ID" ]; then
    echo "❌ Error: Configura AWS_ACCOUNT_ID como variable de entorno o edita este script"
    exit 1
fi

echo -e "${YELLOW}Paso 1/4: Reconstruyendo imagen Docker...${NC}"
docker build -f docker/Dockerfile -t $IMAGE_NAME . --platform linux/amd64
if [ $? -ne 0 ]; then
    echo "❌ Error al construir imagen Docker"
    exit 1
fi
echo -e "${GREEN}✅ Imagen construida${NC}"
echo ""

echo -e "${YELLOW}Paso 2/4: Autenticando con ECR...${NC}"
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com
if [ $? -ne 0 ]; then
    echo "❌ Error al autenticar con ECR"
    exit 1
fi
echo -e "${GREEN}✅ Autenticado${NC}"
echo ""

echo -e "${YELLOW}Paso 3/4: Etiquetando y subiendo imagen a ECR...${NC}"
docker tag $IMAGE_NAME $ECR_REPO
docker push $ECR_REPO
if [ $? -ne 0 ]; then
    echo "❌ Error al subir imagen a ECR"
    exit 1
fi
echo -e "${GREEN}✅ Imagen subida a ECR${NC}"
echo ""

echo -e "${YELLOW}Paso 4/4: Actualizando servicio ECS...${NC}"
aws ecs update-service \
    --cluster $CLUSTER \
    --service $SERVICE \
    --force-new-deployment \
    --region $REGION \
    --query 'service.[serviceName,status,desiredCount,runningCount]' \
    --output table

if [ $? -ne 0 ]; then
    echo "❌ Error al actualizar servicio"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Deployment iniciado!${NC}"
echo ""
echo "⏱️  Esperando ~2-3 minutos para que el nuevo deployment esté listo..."

