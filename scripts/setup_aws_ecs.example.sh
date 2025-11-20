#!/bin/bash
# Script para configurar infraestructura AWS ECS
#
# IMPORTANTE: Copia este archivo a setup_aws_ecs.sh y configura tus variables
# o usa variables de entorno:
#   export AWS_ACCOUNT_ID="your-account-id"
#   export AWS_REGION="us-east-1"
#   export VPC_ID="your-vpc-id"
#   export SUBNET_1="subnet-xxx"
#   export SUBNET_2="subnet-yyy"
#   export SECURITY_GROUP="sg-xxx"

set -e

ACCOUNT_ID="${AWS_ACCOUNT_ID:-YOUR_ACCOUNT_ID}"
REGION="${AWS_REGION:-us-east-1}"
VPC_ID="${VPC_ID:-YOUR_VPC_ID}"
SUBNET_1="${SUBNET_1:-subnet-xxx}"
SUBNET_2="${SUBNET_2:-subnet-yyy}"
SECURITY_GROUP="${SECURITY_GROUP:-sg-xxx}"
CLUSTER_NAME="shopai-cluster"
SERVICE_NAME="shopai-api"
TASK_FAMILY="shopai-api"

if [ "$ACCOUNT_ID" = "YOUR_ACCOUNT_ID" ] || [ "$VPC_ID" = "YOUR_VPC_ID" ]; then
    echo "❌ Error: Configura las variables de entorno necesarias o edita este script"
    exit 1
fi

echo "Setting up AWS ECS infrastructure..."

# ... resto del script con variables de entorno

