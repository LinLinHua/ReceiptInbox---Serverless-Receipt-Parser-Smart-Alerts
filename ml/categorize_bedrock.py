

import json
import boto3
from botocore.exceptions import ClientError
from typing import Optional

from config import get_logger, AWS_REGION

logger = get_logger(__name__)

# Category definitions
CATEGORIES = [
    "Groceries",
    "Restaurants",
    "Entertainment",  # Movies, concerts, events
    "Travel",  # Hotels, flights, vacation
    "Transportation",  # Uber, Lyft, public transit
    "Gas",  # Fuel stations
    "Shopping",  # Retail, clothing, electronics
    "Health",  # Medical, pharmacy, fitness
    "Utilities",  # Electric, water, internet
    "Subscriptions",  # Netflix, Spotify, etc.
    "Education",  # Books, courses, tuition
    "Home",  # Furniture, home improvement
    "Personal Care",  # Salon, spa, beauty
    "Insurance",  # Auto, health, life insurance
    "Other"
]

def bedrock_classify_receipt(
    merchant: Optional[str],
    item_descriptions: list[str]
) -> tuple[str, float]:
    
    try:
        # Support cross-account Bedrock access via environment variables
        import os
        bedrock_access_key = os.environ.get('BEDROCK_ACCESS_KEY')
        bedrock_secret_key = os.environ.get('BEDROCK_SECRET_KEY')
        
        if bedrock_access_key and bedrock_secret_key:
            # Use credentials from another AWS account
            logger.info("Using cross-account Bedrock credentials")
            bedrock = boto3.client(
                'bedrock-runtime',
                aws_access_key_id=bedrock_access_key,
                aws_secret_access_key=bedrock_secret_key,
                region_name=AWS_REGION
            )
        else:
            # Use default Lambda execution role
            bedrock = boto3.client('bedrock-runtime', region_name=AWS_REGION)
        
        # Build classification prompt for Claude
        merchant_text = f"Merchant: {merchant}" if merchant else "Merchant: Unknown"
        items_text = ", ".join(item_descriptions[:10]) if item_descriptions else "No items"
        
        prompt = f

        # Call Claude via Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1  # Low temperature for consistent categorization
        }
        
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",  # Fast, cheap Claude model
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # Extract JSON from response
        result = json.loads(content)
        
        category = result.get('category', 'Other')
        confidence = float(result.get('confidence', 0.5))
        reasoning = result.get('reasoning', '')
        
        # Validate category
        if category not in CATEGORIES:
            logger.warning(f"Bedrock returned invalid category '{category}', defaulting to Other")
            category = "Other"
            confidence = 0.3
        
        logger.info(f"Bedrock classified as '{category}' with confidence {confidence:.2f}")
        logger.debug(f"Reasoning: {reasoning}")
        
        return category, confidence
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        logger.warning(f"Bedrock API error ({error_code}): {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Bedrock response as JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Bedrock classification: {e}")
        raise
