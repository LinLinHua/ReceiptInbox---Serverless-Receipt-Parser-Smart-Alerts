# ReceiptInbox Backend API

This repository contains the serverless backend for **ReceiptInbox**, built by **Lin Lin Hua**. It handles user authentication, receipt upload coordination, and task dispatching to background workers.

## 🏗 System Architecture

* **Compute:** AWS Lambda (running FastAPI via Mangum).
* **Database (User Auth):** PostgreSQL on EC2.
* **Database (Metadata):** Amazon DynamoDB.
* **Storage:** Amazon S3 (Raw receipt files).
* **Async Messaging:** Amazon SQS (Dispatches jobs to Vivin's workers).

---

## 🚀 Getting Started

### Prerequisites
* Python 3.9+
* AWS CLI (`aws configure` must be set up)
* AWS SAM CLI

### Installation
1.  **Clone the repository:**
    ```bash
    git clone <repo_url>
    cd receipt-inbox-backend
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r src/requirements.txt
    ```

### Deployment
To deploy the API Gateway, Lambda functions, and Database tables to AWS:

```bash
sam build
sam deploy --guided