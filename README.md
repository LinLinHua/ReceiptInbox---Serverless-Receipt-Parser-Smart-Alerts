# Receipt Processing System - Final Project

**Course**: EE 547 - Applied and Cloud Computing for Electrical Engineers  
**Project Title**: ReceiptInbox - Serverless Receipt Parser, Spend Categorizer, and Smart Alerts  
**Team Members**: Harry Kang, Lin Lin Hua, Vivin Thiyagarajan

Automated receipt processing with ML-powered categorization and anomaly detection.

**Live Demo**: https://receipt-inbox-app.netlify.app

---

## Architecture

```
Frontend (React) -> API Gateway -> Lambda -> SQS -> ML Lambda -> Bedrock
                                    |              |
                                DynamoDB        S3 + SNS
```

**Components**: React frontend, FastAPI backend, Python ML pipeline, AWS Rekognition OCR, AWS Bedrock AI, DynamoDB storage, S3 file storage, SQS queue, SNS notifications

---

## Quick Start

### Prerequisites
- AWS Account with CLI configured
- Node.js 18+ and npm
- Python 3.10+
- AWS SAM CLI
- Bedrock access (Claude 3 Haiku enabled)

### 1. Deploy Backend

```bash
cd backend
sam build
sam deploy --guided
# Stack name: receiptinbox-ml-stack-v2
# Region: us-east-1
# Confirm: Y to all prompts
```

### 2. Configure Bedrock (If Using Cross-Account)

**IMPORTANT**: Credentials NOT included for security.

```bash
aws lambda update-function-configuration \
  --function-name receiptinbox-ml-stack-v2-MLProcessorFunction-XXXXX \
  --environment Variables="{
    BEDROCK_ACCESS_KEY=YOUR_KEY,
    BEDROCK_SECRET_KEY=YOUR_SECRET
  }"
```

### 3. Run Frontend

```bash
cd frontend
npm install

# Update src/constants.js with your API Gateway URL
npm start
# Open http://localhost:3000
```

### 4. Deploy Frontend (Optional)

```bash
npm run build
npm install -g netlify-cli
netlify deploy --prod --dir=build
```

---

## Features

- User authentication (JWT)
- Receipt upload (drag-and-drop)
- ML categorization (15 categories)
- OCR extraction (Rekognition)
- Anomaly detection:
  - High totals (>$200)
  - Math inconsistencies
  - Duplicate receipts
- Email notifications (SNS)
- Analytics dashboard


**Categories**: Groceries, Restaurants, Entertainment, Travel, Transportation, Gas, Shopping, Health, Utilities, Subscriptions, Education, Home, Personal Care, Insurance, Other

---

## Testing

1. Register at https://receipt-inbox-app.netlify.app
2. Upload receipt image
3. Wait 15-20 seconds for processing
4. View extracted data and anomalies

**Test Anomalies**:
- Upload receipt >$200 -> HIGH_TOTAL alert
- Upload same receipt twice -> DUPLICATE alert
- Upload receipt with OCR errors -> POSSIBLE_ERROR alert

---

## API Endpoints

- `POST /signup` - Register
- `POST /login` - Login (returns JWT)
- `POST /` - Upload receipt
- `GET /receipts` - List receipts
- `GET /receipts/{id}/image` - Get image URL
- `POST /admin/subscribe-anomaly-alerts?email=EMAIL` - Subscribe to alerts

---

## Configuration

### Backend (template.yaml)
- `RECEIPT_BUCKET_NAME` - S3 bucket
- `SQS_QUEUE_URL` - Processing queue
- `DYNAMODB_TABLE` - Metadata storage
- `ANOMALY_TOPIC_ARN` - SNS alerts
- `BEDROCK_MODEL_ID` - AI model
- `HIGH_TOTAL_THRESHOLD` - Anomaly threshold ($200)

### Frontend (constants.js)
```javascript
export const BASE_URL = "https://YOUR_API_GATEWAY_URL";
```

---

## Technologies

**Frontend**: React, Ant Design, Recharts, Axios, React Router

**Backend**: FastAPI, AWS Lambda, API Gateway, SAM, JWT, Boto3

**ML**: Rekognition (OCR), Bedrock (Claude 3), Pydantic, Custom anomaly detection

**Infrastructure**: S3, DynamoDB, SQS, SNS, Netlify




