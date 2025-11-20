# Guía Completa de Despliegue en AWS

## Resumen

Esta guía explica cómo desplegar el sistema ShopAI en AWS usando boto3, S3, ECS/EKS, y otros servicios de AWS.

## Requisitos Previos

### 1. Cuenta AWS

- Cuenta de AWS activa
- Acceso a la consola de AWS
- Permisos para crear recursos (IAM, S3, ECS/EKS, Secrets Manager)

### 2. AWS CLI Instalado

```bash
# macOS
brew install awscli

# Verificar instalación
aws --version
```

### 3. Configurar Credenciales AWS

```bash
aws configure
```

Ingresa:
- AWS Access Key ID
- AWS Secret Access Key
- Default region: `us-east-1`
- Default output format: `json`

## Paso 1: Configurar S3

### Crear Bucket

```bash
aws s3 mb s3://shopai-data --region us-east-1
```

O desde la consola:
1. Ir a S3 → Create bucket
2. Nombre: `shopai-data`
3. Región: `us-east-1`
4. Configurar versionado (opcional pero recomendado)

### Estructura del Bucket

```
s3://shopai-data/
└── ml-recommender/
    ├── raw/
    │   └── transactions.csv
    ├── processed/
    │   └── ratings.parquet
    ├── embeddings/
    │   └── 20250118/
    │       └── embeddings_20250118.npy
    ├── models/
    │   └── collaborative/
    │       └── 20250118/
    │           └── collaborative_model.pkl
    ├── indices/
    │   └── 20250118/
    │       └── faiss_index_20250118.pkl
    └── catalogs/
        └── 20250118/
            ├── user_catalog.json
            └── product_catalog.json
```

### Subir Datos a S3

```bash
# Configurar variables de entorno
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
export S3_BUCKET=shopai-data

# Subir datos
make upload-s3

# O manualmente:
poetry run python scripts/upload_to_s3.py --all
```

## Paso 2: Configurar Secrets Manager

### Crear Secret para OpenAI API Key

```bash
aws secretsmanager create-secret \
    --name shopai/openai-api-key \
    --secret-string "sk-your-openai-api-key" \
    --region us-east-1 \
    --description "OpenAI API key for ShopAI ML system"
```

### Actualizar Código para Usar Secrets Manager

Crear `src/infrastructure/secrets.py`:

```python
import json
import boto3
from botocore.exceptions import ClientError
from src.config.settings import settings
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


def get_secret(secret_name: str, region: str = None) -> str:
    region = region or settings.aws_region
    
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name="secretsmanager",
            region_name=region,
        )
        
        response = client.get_secret_value(SecretId=secret_name)
        
        if "SecretString" in response:
            secret = response["SecretString"]
            try:
                return json.loads(secret)
            except json.JSONDecodeError:
                return secret
        else:
            import base64
            return base64.b64decode(response["SecretBinary"]).decode("utf-8")
            
    except ClientError as e:
        logger.error("Error retrieving secret", secret_name=secret_name, error=str(e))
        raise
    except Exception as e:
        logger.error("Unexpected error retrieving secret", error=str(e))
        raise
```

Actualizar `src/config/settings.py`:

```python
@property
def openai_api_key(self) -> str:
    if self.environment == "production" and not self._openai_api_key:
        from src.infrastructure.secrets import get_secret
        return get_secret("shopai/openai-api-key")
    return self._openai_api_key
```

## Paso 3: Crear IAM Role

### Política IAM para ECS Task

Crear política `shopai-ecs-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::shopai-data",
        "arn:aws:s3:::shopai-data/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:shopai/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:*:log-group:/aws/ecs/shopai-api:*"
    }
  ]
}
```

Crear política:

```bash
aws iam create-policy \
    --policy-name ShopAIECSPolicy \
    --policy-document file://shopai-ecs-policy.json
```

Crear rol:

```bash
aws iam create-role \
    --role-name ShopAIECSTaskRole \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }'

aws iam attach-role-policy \
    --role-name ShopAIECSTaskRole \
    --policy-arn arn:aws:iam::074478993856:policy/ShopAIECSPolicy
```

## Paso 4: Desplegar en ECS Fargate

### 1. Crear ECR Repository

```bash
aws ecr create-repository --repository-name shopai-api --region us-east-1
```

### 2. Build y Push Docker Image

```bash
# Login a ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin 074478993856.dkr.ecr.us-east-1.amazonaws.com

# Build
docker build -f docker/Dockerfile -t shopai-api:latest .

# Tag
docker tag shopai-api:latest \
    074478993856.dkr.ecr.us-east-1.amazonaws.com/shopai-api:latest

# Push
docker push 074478993856.dkr.ecr.us-east-1.amazonaws.com/shopai-api:latest
```

### 3. Crear Task Definition

Crear `ecs-task-definition.json`:

```json
{
  "family": "shopai-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::074478993856:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::074478993856:role/ShopAIECSTaskRole",
  "containerDefinitions": [
    {
      "name": "shopai-api",
      "image": "074478993856.dkr.ecr.us-east-1.amazonaws.com/shopai-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        },
        {
          "name": "AWS_REGION",
          "value": "us-east-1"
        },
        {
          "name": "S3_BUCKET",
          "value": "shopai-data"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:074478993856:secret:shopai/openai-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/shopai-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

Registrar task definition:

```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
```

### 4. Crear ECS Service

```bash
aws ecs create-service \
    --cluster shopai-cluster \
    --service-name shopai-api \
    --task-definition shopai-api \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:leovalsan:targetgroup/shopai-api/xxx,containerName=shopai-api,containerPort=8000"
```

## Paso 5: Configurar Application Load Balancer

### Crear Target Group

```bash
aws elbv2 create-target-group \
    --name shopai-api-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id vpc-xxx \
    --target-type ip \
    --health-check-path /api/v1/health \
    --health-check-interval-seconds 30
```

### Crear Load Balancer

```bash
aws elbv2 create-load-balancer \
    --name shopai-api-alb \
    --subnets subnet-xxx subnet-yyy \
    --security-groups sg-xxx
```

### Crear Listener

```bash
aws elbv2 create-listener \
    --load-balancer-arn arn:aws:elasticloadbalancing:... \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

## Paso 6: Actualizar Scripts para Usar S3

### Modificar `scripts/ingest.py`

```python
# Cambiar de:
df = load_from_local("transactions.csv")

# A:
from src.config.settings import settings
df = load_from_s3(f"{settings.s3_prefix}/raw/transactions.csv")
```

### Modificar `scripts/train.py`

```python
# Cambiar de:
df = load_from_local("data/processed/ratings.parquet")

# A:
df = load_from_s3(f"{settings.s3_prefix}/processed/ratings.parquet")
```

## Paso 7: Configurar Auto-scaling

### Crear Auto-scaling Policy

```bash
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --resource-id service/shopai-cluster/shopai-api \
    --scalable-dimension ecs:service:DesiredCount \
    --min-capacity 1 \
    --max-capacity 10

aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --resource-id service/shopai-cluster/shopai-api \
    --scalable-dimension ecs:service:DesiredCount \
    --policy-name shopai-api-scaling \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration '{
      "TargetValue": 70.0,
      "PredefinedMetricSpecification": {
        "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
      }
    }'
```

## Paso 8: Monitoreo con CloudWatch

### Crear Log Group

```bash
aws logs create-log-group --log-group-name /ecs/shopai-api
```

### Configurar Alarmas

```bash
# Alarma de latencia alta
aws cloudwatch put-metric-alarm \
    --alarm-name shopai-api-high-latency \
    --alarm-description "Alert when API latency is high" \
    --metric-name ResponseTime \
    --namespace AWS/ApplicationELB \
    --statistic Average \
    --period 300 \
    --threshold 500 \
    --comparison-operator GreaterThanThreshold

# Alarma de errores
aws cloudwatch put-metric-alarm \
    --alarm-name shopai-api-high-errors \
    --alarm-description "Alert when error rate is high" \
    --metric-name HTTPCode_Target_5XX_Count \
    --namespace AWS/ApplicationELB \
    --statistic Sum \
    --period 300 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold
```

## Costos Estimados (AWS)

### ECS Fargate
- 2 tasks × 1 vCPU × 2GB = ~$60-80/mes

### Application Load Balancer
- ~$20/mes base + $0.008/GB transferido

### S3
- Storage: ~$0.01/mes (100MB)
- Requests: ~$0.10/mes

### CloudWatch
- Logs: ~$0.50/mes
- Metrics: ~$0.30/mes

### Total Estimado
- **~$80-100/mes** para deployment básico

## Verificación Post-Despliegue

### 1. Verificar Health Check

```bash
# Obtener ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --names shopai-api-alb \
    --query 'LoadBalancers[0].DNSName' \
    --output text)

# Test health
curl http://$ALB_DNS/api/v1/health
```

### 2. Test Endpoints

```bash
# Recommendations
curl -X POST http://$ALB_DNS/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id": "U001", "top_k": 5}'

# Search
curl -X POST http://$ALB_DNS/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "electronics", "top_k": 5}'
```

### 3. Verificar Logs

```bash
aws logs tail /ecs/shopai-api --follow
```

## Troubleshooting

### Problemas Comunes

**1. Task no inicia**
- Verificar IAM role tiene permisos
- Verificar secrets manager access
- Revisar CloudWatch logs

**2. No puede acceder a S3**
- Verificar IAM policy
- Verificar bucket existe
- Verificar región correcta

**3. API no responde**
- Verificar security groups (puerto 8000)
- Verificar target group health
- Verificar modelos cargados desde S3

## Scripts Útiles

### Upload Everything to S3

```bash
make upload-s3
```

### Download from S3

```bash
make download-s3
```

### Test S3 Connection

```python
import boto3
from src.config.settings import settings

s3 = boto3.client('s3',
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region)

# List buckets
print(s3.list_buckets())

# Test access
s3.head_bucket(Bucket=settings.s3_bucket)
print(f"Access to {settings.s3_bucket} confirmed")
```

## Next Steps

1. Configure S3 bucket
2. Upload data and artifacts
3. Configure Secrets Manager
4. Create IAM roles
5. Build and push Docker image
6. Create ECS service
7. Configure ALB
8. Configure auto-scaling
9. Configure monitoring
10. Verify operation


