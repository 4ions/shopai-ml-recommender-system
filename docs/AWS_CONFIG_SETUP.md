# AWS Configuration - Sensitive Files

## Important

The following files contain sensitive information (Account ID, ARNs, etc.) and **should NOT be committed to the repository**:

- `ecs-task-definition.json`
- `shopai-ecs-policy.json`
- `ecs-trust-policy.json`
- `scripts/deploy.sh`
- `scripts/push_to_ecr.sh`
- `scripts/setup_aws_ecs.sh`

## Example Files

Example versions (`.example.json` and `.example.sh`) have been created that you can use as templates:

- `ecs-task-definition.example.json`
- `shopai-ecs-policy.example.json`
- `ecs-trust-policy.example.json`
- `scripts/deploy.example.sh`
- `scripts/push_to_ecr.example.sh`
- `scripts/setup_aws_ecs.example.sh`

## How to Configure

### Option 1: Use Environment Variables (Recommended)

```bash
# Set variables
export AWS_ACCOUNT_ID="your-account-id"
export AWS_REGION="us-east-1"
export VPC_ID="vpc-xxx"
export SUBNET_1="subnet-xxx"
export SUBNET_2="subnet-yyy"
export SECURITY_GROUP="sg-xxx"

# Copy example scripts
cp scripts/deploy.example.sh scripts/deploy.sh
cp scripts/push_to_ecr.example.sh scripts/push_to_ecr.sh
cp scripts/setup_aws_ecs.example.sh scripts/setup_aws_ecs.sh

# Make executable
chmod +x scripts/*.sh
```

### Option 2: Edit Files Manually

1. Copy the example files:
   ```bash
   cp ecs-task-definition.example.json ecs-task-definition.json
   cp shopai-ecs-policy.example.json shopai-ecs-policy.json
   cp ecs-trust-policy.example.json ecs-trust-policy.json
   ```

2. Replace placeholders:
   - `YOUR_ACCOUNT_ID` → Your AWS Account ID
   - `YOUR_VPC_ID` → Your VPC ID
   - `subnet-xxx` → Your Subnet IDs
   - `sg-xxx` → Your Security Group ID
   - `arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:shopai/openai-api-key-XXXXXX` → Real secret ARN

## Security

- Files with credentials are in `.gitignore`
- Only `.example.*` files are committed to the repository
- Use AWS Secrets Manager for API keys
- Never commit Account IDs or ARNs to the repository

## Notes

- Example scripts use environment variables when available
- If variables are not configured, scripts will show a clear error
- Real files are created locally and never committed
