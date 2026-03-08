# SarkarSaathi MVP Architecture ($90/month Budget)

## MVP Scope Reduction

For an MVP with $90/month budget, we'll focus on:
- **Single interface**: WhatsApp only (most accessible for target users)
- **Core functionality**: Profile collection → Eligibility check → Top 3 schemes
- **Simplified tech stack**: Minimize AWS services
- **Manual data**: Start with 20-30 curated schemes (not 100+)
- **No voice**: Text-only to reduce costs
- **No RAG**: Use simple keyword search initially

## Cost-Optimized AWS Architecture

```
User (WhatsApp)
    ↓
API Gateway ($3.50/million requests) → ~$5/month
    ↓
Lambda Functions (Free tier: 1M requests, 400K GB-seconds) → ~$0/month
    ↓
┌─────────────┬─────────────┬─────────────┐
│   Bedrock   │  DynamoDB   │     S3      │
│  (Claude)   │  (Sessions) │   (Data)    │
│  ~$40/month │  ~$5/month  │  ~$1/month  │
└─────────────┴─────────────┴─────────────┘
```

## Simplified Architecture

### 1. Single Lambda Function (Monolith for MVP)
Instead of 10+ Lambda functions, use ONE Lambda function that handles:
- WhatsApp webhook processing
- Intent parsing (using Bedrock Claude 3 Haiku)
- Profile collection
- Eligibility checking (rule-based, no ML)
- Response formatting

**Cost**: $0 (within free tier: 1M requests/month, 400K GB-seconds)

### 2. Amazon Bedrock (Claude 3 Haiku Only)
- Use ONLY Claude 3 Haiku (cheapest model)
- Haiku: $0.00025 input, $0.00125 output per 1K tokens
- Estimated usage: 10K requests/month × 500 tokens avg = 5M tokens
- Cost: 5M × $0.00075 avg = **$37.50/month**

**Optimization**: Cache common responses in DynamoDB to reduce Bedrock calls by 50%
**Optimized cost**: **$20/month**

### 3. DynamoDB (Instead of RDS + ElastiCache + OpenSearch)
Replace expensive databases with DynamoDB:
- **Schemes table**: Store 30 schemes with eligibility rules
- **Sessions table**: Store user sessions (TTL: 24 hours)
- **Cache table**: Store Bedrock response cache (TTL: 1 hour)

**Cost**: 
- On-demand pricing: $1.25 per million write requests, $0.25 per million read requests
- Storage: $0.25 per GB-month
- Estimated: 100K writes, 500K reads, 1GB storage = **$5/month**

### 4. S3 (Minimal Usage)
- Store scheme data JSON file (backup)
- Store WhatsApp media temporarily (7-day lifecycle)

**Cost**: $0.023 per GB-month + $0.0004 per 1K requests = **$1/month**

### 5. API Gateway (WhatsApp Webhook)
- REST API for WhatsApp webhook endpoint
- ~10K requests/month

**Cost**: $3.50 per million requests = **$0.04/month** (negligible)

### 6. CloudWatch Logs
- Basic logging for Lambda function
- 1GB ingestion, 30-day retention

**Cost**: $0.50 per GB ingestion = **$0.50/month**

### 7. Secrets Manager
- Store WhatsApp API credentials

**Cost**: $0.40 per secret per month = **$0.40/month**

## Total MVP Cost Breakdown

| Service | Monthly Cost |
|---------|--------------|
| Lambda | $0 (free tier) |
| Bedrock (Haiku with caching) | $20 |
| DynamoDB | $5 |
| S3 | $1 |
| API Gateway | $0.04 |
| CloudWatch Logs | $0.50 |
| Secrets Manager | $0.40 |
| **Total** | **$26.94/month** |

**Buffer for overages**: $90 - $27 = **$63 buffer** (plenty of room!)

## What We're Cutting for MVP

### Removed Services (Save $753/month):
- ❌ RDS PostgreSQL ($150) → Use DynamoDB
- ❌ ElastiCache Redis ($120) → Use DynamoDB with TTL
- ❌ OpenSearch ($300) → Use simple keyword search
- ❌ Amazon Transcribe ($50) → No voice for MVP
- ❌ Amazon Polly ($30) → No voice for MVP
- ❌ Amazon Translate ($20) → Manual translations for 2-3 languages
- ❌ Step Functions ($7) → Simple Lambda logic
- ❌ CloudFront ($50) → No web interface for MVP
- ❌ SQS ($2) → Direct Lambda invocation
- ❌ Multiple Lambda functions → Single monolith Lambda
- ❌ VPC, NAT Gateway ($26) → Lambda without VPC

### Reduced Scope:
- ❌ Voice interface → WhatsApp text only
- ❌ Web chat interface → WhatsApp only
- ❌ 100 schemes → 30 curated schemes
- ❌ RAG with embeddings → Keyword search
- ❌ 10 languages → 2 languages (Hindi + English)
- ❌ Complex MCP architecture → Simple function calls
- ❌ Step Functions orchestration → Linear logic
- ❌ Advanced monitoring → Basic CloudWatch

## MVP Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    WhatsApp Business API                     │
│                  (User sends text message)                   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS Webhook
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (REST)                        │
│              POST /webhook (WhatsApp events)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Lambda Function (Monolith - 1024MB)             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 1. Webhook Handler                                    │  │
│  │    - Verify signature                                 │  │
│  │    - Parse message                                    │  │
│  │                                                        │  │
│  │ 2. Session Manager                                    │  │
│  │    - Get/Create session from DynamoDB                 │  │
│  │    - Phone number as session ID                       │  │
│  │                                                        │  │
│  │ 3. Intent Parser (Bedrock Claude 3 Haiku)            │  │
│  │    - Classify intent                                  │  │
│  │    - Extract entities                                 │  │
│  │                                                        │  │
│  │ 4. Profile Collector                                  │  │
│  │    - Ask questions                                    │  │
│  │    - Store in session                                 │  │
│  │                                                        │  │
│  │ 5. Eligibility Engine (Rule-based)                   │  │
│  │    - Load schemes from DynamoDB                       │  │
│  │    - Evaluate rules                                   │  │
│  │    - Rank by benefit value                            │  │
│  │                                                        │  │
│  │ 6. Response Formatter                                 │  │
│  │    - Format for WhatsApp                              │  │
│  │    - Add emojis, formatting                           │  │
│  │                                                        │  │
│  │ 7. WhatsApp Sender                                    │  │
│  │    - Send via WhatsApp Business API                   │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Bedrock    │  │  DynamoDB    │  │      S3      │
│ Claude Haiku │  │              │  │              │
├──────────────┤  ├──────────────┤  ├──────────────┤
│ Intent parse │  │ schemes      │  │ scheme_data  │
│ Response gen │  │ sessions     │  │ .json        │
│              │  │ cache        │  │ (backup)     │
└──────────────┘  └──────────────┘  └──────────────┘
```

## MVP Data Model (DynamoDB)

### Table 1: schemes
```json
{
  "scheme_id": "PM-KISAN",  // Partition Key
  "name_en": "PM-KISAN",
  "name_hi": "पीएम-किसान",
  "description_en": "Direct income support to farmers",
  "description_hi": "किसानों को प्रत्यक्ष आय सहायता",
  "category": "agriculture",
  "state": "ALL",
  "benefit_amount": 6000,
  "eligibility_rules": {
    "occupation": ["farmer"],
    "land_ownership": {"min": 0.01},
    "income": {"max": 200000}
  },
  "required_documents": ["Aadhaar", "Land Records", "Bank Account"],
  "application_url": "https://pmkisan.gov.in"
}
```

### Table 2: sessions
```json
{
  "session_id": "whatsapp:+919876543210",  // Partition Key
  "phone_number": "+919876543210",
  "language": "hi",
  "user_profile": {
    "age": 45,
    "gender": "male",
    "income": 150000,
    "state": "Punjab",
    "occupation": "farmer",
    "land_ownership": 2.5
  },
  "conversation_history": [
    {"role": "assistant", "content": "आपकी उम्र क्या है?"},
    {"role": "user", "content": "45"}
  ],
  "created_at": 1705315800,
  "ttl": 1705402200  // 24 hours
}
```

### Table 3: cache
```json
{
  "cache_key": "intent:what_schemes_farming",  // Partition Key
  "response": "You are eligible for 3 schemes...",
  "ttl": 1705319400  // 1 hour
}
```

## MVP Lambda Function Structure

```python
# lambda_function.py (single file for MVP)

import json
import boto3
import hashlib
import hmac
from datetime import datetime, timedelta

# AWS clients
bedrock = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')
secrets = boto3.client('secretsmanager')

# DynamoDB tables
schemes_table = dynamodb.Table('sarkar-saathi-schemes')
sessions_table = dynamodb.Table('sarkar-saathi-sessions')
cache_table = dynamodb.Table('sarkar-saathi-cache')

def lambda_handler(event, context):
    """Main Lambda handler for WhatsApp webhook"""
    
    # 1. Verify webhook signature
    if not verify_signature(event):
        return {'statusCode': 403, 'body': 'Invalid signature'}
    
    # 2. Parse WhatsApp message
    message = parse_webhook(event)
    if not message:
        return {'statusCode': 200, 'body': 'OK'}
    
    # 3. Get or create session
    session = get_session(message['phone_number'])
    
    # 4. Process message
    response_text = process_message(message['text'], session)
    
    # 5. Update session
    update_session(session)
    
    # 6. Send WhatsApp response
    send_whatsapp_message(message['phone_number'], response_text)
    
    return {'statusCode': 200, 'body': 'OK'}

def process_message(text, session):
    """Process user message and generate response"""
    
    # Check cache first
    cache_key = f"response:{hash(text)}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    
    # Parse intent using Bedrock
    intent = parse_intent(text, session)
    
    # Handle based on intent
    if intent == 'profile_collection':
        response = collect_profile(text, session)
    elif intent == 'eligibility_check':
        response = check_eligibility(session)
    elif intent == 'scheme_details':
        response = get_scheme_details(text, session)
    else:
        response = "मुझे समझ नहीं आया। कृपया फिर से पूछें।"
    
    # Cache response
    set_cache(cache_key, response, ttl=3600)
    
    return response

def parse_intent(text, session):
    """Use Bedrock Claude Haiku for intent classification"""
    
    prompt = f"""Classify the user's intent:
User message: {text}
Session context: {json.dumps(session.get('user_profile', {}))}

Respond with ONE of: profile_collection, eligibility_check, scheme_details, general_query"""
    
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-haiku-20240307-v1:0',
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 50,
            'messages': [{'role': 'user', 'content': prompt}]
        })
    )
    
    result = json.loads(response['body'].read())
    return result['content'][0]['text'].strip()

def check_eligibility(session):
    """Rule-based eligibility checking"""
    
    profile = session.get('user_profile', {})
    
    # Check if profile is complete
    required_fields = ['age', 'income', 'state', 'occupation']
    if not all(field in profile for field in required_fields):
        return "कृपया पहले अपनी जानकारी दें।"
    
    # Load schemes from DynamoDB
    schemes = schemes_table.scan()['Items']
    
    # Evaluate eligibility
    eligible_schemes = []
    for scheme in schemes:
        if evaluate_rules(scheme['eligibility_rules'], profile):
            eligible_schemes.append(scheme)
    
    # Rank by benefit amount
    eligible_schemes.sort(key=lambda x: x['benefit_amount'], reverse=True)
    
    # Format response (top 3)
    if not eligible_schemes:
        return "आप किसी योजना के लिए पात्र नहीं हैं।"
    
    response = f"आप {len(eligible_schemes)} योजनाओं के लिए पात्र हैं। शीर्ष 3:\n\n"
    for i, scheme in enumerate(eligible_schemes[:3], 1):
        response += f"{i}️⃣ *{scheme['name_hi']}*\n"
        response += f"💰 ₹{scheme['benefit_amount']:,} प्रति वर्ष\n"
        response += f"✅ {scheme['description_hi']}\n\n"
    
    return response

def evaluate_rules(rules, profile):
    """Simple rule evaluation"""
    
    # Check occupation
    if 'occupation' in rules:
        if profile.get('occupation') not in rules['occupation']:
            return False
    
    # Check income
    if 'income' in rules:
        if 'max' in rules['income']:
            if profile.get('income', 0) > rules['income']['max']:
                return False
        if 'min' in rules['income']:
            if profile.get('income', 0) < rules['income']['min']:
                return False
    
    # Check land ownership
    if 'land_ownership' in rules:
        if 'min' in rules['land_ownership']:
            if profile.get('land_ownership', 0) < rules['land_ownership']['min']:
                return False
    
    return True

# ... (other helper functions)
```

## MVP Implementation Timeline

### Week 1: Setup & Data
- Day 1-2: AWS account setup, DynamoDB tables, WhatsApp Business API
- Day 3-5: Curate 30 schemes with eligibility rules
- Day 6-7: Load schemes into DynamoDB

### Week 2: Core Lambda Function
- Day 1-3: Webhook handler, session management
- Day 4-5: Intent parsing with Bedrock
- Day 6-7: Profile collection logic

### Week 3: Eligibility & Testing
- Day 1-3: Rule-based eligibility engine
- Day 4-5: Response formatting for WhatsApp
- Day 6-7: End-to-end testing

### Week 4: Polish & Launch
- Day 1-2: Error handling, logging
- Day 3-4: User testing with 10 beta users
- Day 5-7: Bug fixes, documentation, launch

## Scaling Path (When Budget Increases)

### Phase 2 ($200/month):
- Add web chat interface (CloudFront + S3)
- Increase to 100 schemes
- Add 5 more languages
- Add ElastiCache for better caching

### Phase 3 ($500/month):
- Add voice interface (Transcribe + Polly)
- Add RAG with OpenSearch
- Split into microservices (multiple Lambdas)
- Add Step Functions for complex workflows

### Phase 4 ($1000/month):
- Full production architecture from original design
- RDS for relational data
- Advanced monitoring and analytics
- Multi-region deployment

## MVP Success Metrics

Track these in CloudWatch:
- Daily active users (WhatsApp sessions)
- Messages per session
- Eligibility checks performed
- Top 3 queried schemes
- Average response time
- Error rate

**Target for MVP**: 100 daily active users, 5 messages per session, <3s response time

## Cost Monitoring

Set up AWS Budget alerts:
- Alert at $50 (55% of budget)
- Alert at $70 (78% of budget)
- Hard limit at $90 (100% of budget)

Monitor daily in AWS Cost Explorer to catch overages early.
