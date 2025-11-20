# Deployment Guide

## Local Development

### Prerequisites

- Python 3.11+
- Poetry
- OpenAI API Key

### Setup

```bash
# Install dependencies
make setup

# Configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run pipeline
make pipeline

# Start API
make serve
```

## Docker Deployment

### Build Image

```bash
make docker-build
# or
docker build -f docker/Dockerfile -t shopai-api:latest .
```

### Run Container

```bash
make docker-run
# or
docker-compose -f docker/docker-compose.yml up --build
```

### Environment Variables

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `ENVIRONMENT`: `development` or `production`
- `LOG_LEVEL`: `INFO`, `DEBUG`, `WARNING`, `ERROR`

Optional:
- `AWS_REGION`: AWS region for S3
- `S3_BUCKET`: S3 bucket name
- `REDIS_URL`: Redis connection string for caching

## Current Deployment Status

**Note:** The system currently runs entirely locally. AWS integration (S3, Secrets Manager) is implemented but not actively used. All data and artifacts are stored in the local filesystem.

**Current Setup:**
- Data storage: Local files (`data/` directory)
- Artifacts: Local files (`data/artifacts/` directory)
- Secrets: Environment variables (`.env` file)
- No AWS services required for local operation

## AWS Deployment (Future/Production)

### ECS Fargate

1. **Build and Push Image:**
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker build -f docker/Dockerfile -t shopai-api .
docker tag shopai-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/shopai-api:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/shopai-api:latest
```

2. **Create ECS Task Definition:**
- Use the image from ECR
- Set environment variables from Secrets Manager
- Configure IAM role with S3 and Secrets Manager permissions
- Set memory: 2GB, CPU: 1 vCPU

3. **Create ECS Service:**
- Use Application Load Balancer
- Configure auto-scaling (min: 1, max: 10)
- Set health check: `/api/v1/health`

### EKS (Kubernetes)

1. **Create Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shopai-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: shopai-api
  template:
    metadata:
      labels:
        app: shopai-api
    spec:
      containers:
      - name: api
        image: <account-id>.dkr.ecr.us-east-1.amazonaws.com/shopai-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: shopai-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

2. **Create Service:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: shopai-api
spec:
  selector:
    app: shopai-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Environment Configuration

### Development

```bash
ENVIRONMENT=development
LOG_LEVEL=INFO
CACHE_TYPE=memory
```

### Production

```bash
ENVIRONMENT=production
LOG_LEVEL=WARNING
CACHE_TYPE=redis
REDIS_URL=redis://redis-cluster:6379/0
```

## Secrets Management

### Local
Use `.env` file (not committed to git)

### AWS
Store secrets in AWS Secrets Manager:
- `shopai/openai-api-key`
- `shopai/aws-credentials`

Access via IAM role in ECS/EKS.

## Monitoring

### CloudWatch Logs
Logs are automatically sent to CloudWatch in production.

### Prometheus
Metrics available at `/metrics` endpoint. Configure Prometheus to scrape:
- Target: `http://shopai-api:8000/metrics`
- Interval: 15s

### Health Checks
- Endpoint: `/api/v1/health`
- Interval: 30s
- Timeout: 10s
- Failure threshold: 3

## Scaling

### Horizontal Scaling
- ECS: Auto-scaling based on CPU/memory
- EKS: HPA (Horizontal Pod Autoscaler)

### Vertical Scaling
- Increase container memory/CPU
- Use larger instance types

## Backup and Recovery

### Artifacts
- Models and embeddings stored in S3
- Versioned by date/model ID
- Regular backups via S3 lifecycle policies

### Database
- If using external database, configure automated backups
- Point-in-time recovery if supported

## Security

### Network
- Use VPC with private subnets
- Security groups with minimal required ports
- WAF for API protection

### Access
- IAM roles for service access
- No hardcoded credentials
- Secrets in Secrets Manager

### API
- Rate limiting enabled
- Input validation
- CORS configured appropriately

## Troubleshooting

### API Not Starting
- Check environment variables
- Verify models are in `data/artifacts/`
- Check logs: `docker logs <container-id>`

### High Latency
- Check cache hit rate
- Monitor OpenAI API latency
- Consider increasing resources

### Memory Issues
- Increase container memory
- Check for memory leaks
- Monitor with CloudWatch

