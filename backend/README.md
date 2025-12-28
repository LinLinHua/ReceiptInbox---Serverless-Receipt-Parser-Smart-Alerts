# Backend - FastAPI on AWS Lambda

FastAPI backend deployed on AWS Lambda with API Gateway.

## Setup

### Prerequisites
- AWS CLI configured
- AWS SAM CLI installed
- Python 3.10+

### Deploy

```bash
# Build
sam build

# Deploy
sam deploy --guided
# Stack name: receiptinbox-ml-stack-v2
# Region: us-east-1
# Confirm changes: Y
# Allow IAM role creation: Y
```

### Configure Bedrock Credentials

**IMPORTANT**: Credentials NOT included for security.

```bash
aws lambda update-function-configuration \
  --function-name receiptinbox-ml-stack-v2-MLProcessorFunction-XXXXX \
  --environment Variables="{
    BEDROCK_ACCESS_KEY=YOUR_KEY,
    BEDROCK_SECRET_KEY=YOUR_SECRET
  }"
```

## Structure

```
backend/
├── src/
│   ├── main.py           # API endpoints
│   ├── requirements.txt  # Dependencies
│   └── models.py         # Database models
├── template.yaml         # SAM infrastructure
└── README.md
```

## API Endpoints

- `POST /signup` - Register user
- `POST /login` - Login (returns JWT)
- `POST /` - Upload receipt
- `GET /receipts` - List receipts
- `GET /receipts/{id}/image` - Get image URL
- `POST /admin/subscribe-anomaly-alerts?email=EMAIL` - Subscribe

## Environment Variables

Set in `template.yaml`:
- `RECEIPT_BUCKET_NAME` - S3 bucket
- `SQS_QUEUE_URL` - Processing queue
- `DYNAMODB_TABLE` - Metadata table
- `ANOMALY_TOPIC_ARN` - SNS topic
- `BEDROCK_MODEL_ID` - AI model
- `HIGH_TOTAL_THRESHOLD` - Anomaly threshold

## Tech Stack

- FastAPI
- AWS Lambda
- API Gateway (HTTP API)
- JWT authentication
- Boto3 (AWS SDK)
- Mangum (ASGI adapter)