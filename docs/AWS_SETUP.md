# AWS Setup Guide

## Prerequisites

### 1. AWS Account Setup

1. Create an AWS account (if you don't have one)
2. Create an IAM user with programmatic access
3. Attach policies:
   - `AmazonS3FullAccess` (or custom policy with read/write to specific bucket)
   - `SecretsManagerReadWrite` (for production secrets)

### 2. S3 Bucket Creation

```bash
aws s3 mb s3://shopai-data --region us-east-1
```

Or via AWS Console:
1. Go to S3 service
2. Create bucket: `shopai-data`
3. Choose region: `us-east-1`
4. Configure permissions (block public access recommended)

### 3. Configure Credentials

**Option 1: Environment Variables (Local/Development)**

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

Or add to `.env` file:
```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET=shopai-data
S3_PREFIX=ml-recommender
```

**Option 2: AWS Credentials File**

```bash
aws configure
```

This creates `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
region = us-east-1
```

**Option 3: IAM Role (Production/ECS/EKS)**

- Attach IAM role to ECS task or EC2 instance
- No credentials needed in code
- More secure for production

## Using S3 with the System

### Upload Data to S3

```bash
# Upload raw transactions CSV
poetry run python scripts/upload_to_s3.py --data

# Upload all ML artifacts
poetry run python scripts/upload_to_s3.py --artifacts

# Upload everything
poetry run python scripts/upload_to_s3.py --all
```

### Download from S3

```bash
# Download raw data
poetry run python scripts/download_from_s3.py --data

# Download artifacts (latest version)
poetry run python scripts/download_from_s3.py --artifacts

# Download specific version
poetry run python scripts/download_from_s3.py --artifacts --version 20250118

# Download everything
poetry run python scripts/download_from_s3.py --all
```

### Modify Scripts to Use S3

**In `scripts/ingest.py`:**
```python
# Change from:
df = load_from_local("transactions.csv")

# To:
df = load_from_s3(f"{settings.s3_prefix}/raw/transactions.csv")
```

**In `scripts/train.py`:**
```python
# Change from:
df = load_from_local("data/processed/ratings.parquet")

# To:
df = load_from_s3(f"{settings.s3_prefix}/processed/ratings.parquet")
```

## S3 Bucket Structure

```
s3://shopai-data/ml-recommender/
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

## AWS Secrets Manager (Production)

### Store OpenAI API Key

```bash
aws secretsmanager create-secret \
    --name shopai/openai-api-key \
    --secret-string "your-openai-api-key" \
    --region us-east-1
```

### Retrieve in Code

```python
import boto3
import json

def get_secret(secret_name: str, region: str = "us-east-1") -> str:
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])
```

### Update Settings

Modify `src/config/settings.py`:
```python
def get_openai_key(self) -> str:
    if self.environment == "production":
        import boto3
        return get_secret("shopai/openai-api-key")
    return self.openai_api_key
```

## IAM Policy Example

For production, create a custom IAM policy with minimal permissions:

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
        "arn:aws:s3:::shopai-data/*",
        "arn:aws:s3:::shopai-data"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:shopai/*"
    }
  ]
}
```

## Testing S3 Connection

```python
import boto3
from src.config.settings import settings

# Test connection
s3_client = boto3.client(
    "s3",
    region_name=settings.aws_region,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
)

# List buckets
response = s3_client.list_buckets()
print("Buckets:", [b["Name"] for b in response["Buckets"]])

# Test access to your bucket
try:
    s3_client.head_bucket(Bucket=settings.s3_bucket)
    print(f"Access to bucket {settings.s3_bucket} confirmed")
except Exception as e:
    print(f"Error accessing bucket: {e}")
```

## Cost Considerations

**S3 Storage:**
- Standard storage: $0.023 per GB/month
- For ~100MB of artifacts: ~$0.002/month

**Data Transfer:**
- First 100GB/month: Free
- After that: $0.09 per GB

**Requests:**
- PUT requests: $0.005 per 1,000
- GET requests: $0.0004 per 1,000

**Estimated Monthly Cost:**
- Storage: < $0.01
- Requests: < $0.10
- **Total: < $0.20/month** for typical usage

## Migration from Local to S3

### Step 1: Upload Existing Data

```bash
# Upload raw data
poetry run python scripts/upload_to_s3.py --data

# Upload processed data (if exists)
# Manually upload data/processed/ratings.parquet to S3

# Upload artifacts
poetry run python scripts/upload_to_s3.py --artifacts
```

### Step 2: Update Scripts

Modify scripts to use `load_from_s3()` instead of `load_from_local()`.

### Step 3: Test

Run pipeline with S3:
```bash
# Test data loading
poetry run python -c "from src.data.ingestion import load_from_s3; from src.config.settings import settings; df = load_from_s3(f'{settings.s3_prefix}/raw/transactions.csv'); print(f'Loaded {len(df)} rows')"
```

## Troubleshooting

### Common Issues

**1. Access Denied**
- Check IAM permissions
- Verify bucket policy
- Check credentials are correct

**2. Bucket Not Found**
- Verify bucket name in settings
- Check region matches
- Ensure bucket exists

**3. Slow Uploads**
- Use multipart upload for large files
- Consider using `boto3` transfer config

**4. Credentials Not Found**
- Check environment variables
- Verify AWS credentials file
- For ECS/EKS, verify IAM role

## Next Steps

1. Set up S3 bucket
2. Configure credentials
3. Upload initial data
4. Test S3 integration
5. Update scripts to use S3
6. Deploy to AWS (ECS/EKS)


