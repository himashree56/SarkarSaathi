# SarkarSaathi Ultra-Optimized MVP ($60/month Budget)

## Reality Check: What's Actually Possible?

Let me break down the costs honestly:

### ❌ What's NOT Possible at $60/month:

1. **OpenSearch for RAG**: 
   - Minimum cost: $24/month (t3.small.search single node)
   - This alone takes 40% of your budget
   - **Alternative**: Use DynamoDB + simple keyword search (free tier)

2. **Voice Interface (Transcribe + Polly)**:
   - Transcribe: $0.024 per minute (100 hours = $144/month)
   - Polly: $4 per 1M characters (500K chars = $2/month)
   - Even with 10 hours/month: $14.40 + $2 = $16.40
   - **Alternative**: Text-only for MVP, add voice later

3. **Step Functions**:
   - Express: $1 per million requests (~$0.10/month for MVP)
   - Standard: $0.025 per 1K state transitions (~$0.50/month)
   - **This is actually affordable!** ✅

4. **CloudFront + S3 Web Interface**:
   - S3: $0.023 per GB (~$0.50/month)
   - CloudFront: $0.085 per GB transfer (~$2/month for 25GB)
   - **This is actually affordable!** ✅

### ✅ What IS Possible at $60/month:

Here's an optimized architecture that fits:

## Ultra-Optimized Architecture ($58/month)

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces                           │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │  WhatsApp    │      │   Web Chat   │                     │
│  │   (Text)     │      │ (CloudFront) │                     │
│  └──────┬───────┘      └──────┬───────┘                     │
└─────────┼─────────────────────┼──────────────────────────────┘
          │                     │
          └─────────────────────┼─────────────────────────
                                │
                                ▼
                    ┌───────────────────────┐
                    │   API Gateway         │
                    │   ($0.10/month)       │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Lambda Functions    │
                    │   ($0 - free tier)    │
                    └───────────┬───────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐   ┌───────────────────┐   ┌──────────────────┐
│   Bedrock     │   │    DynamoDB       │   │   S3 + CF        │
│   (Haiku)     │   │  (On-Demand)      │   │  (Web Assets)    │
│   $15/month   │   │   $8/month        │   │   $3/month       │
└───────────────┘   └───────────────────┘   └──────────────────┘
```

## Detailed Cost Breakdown ($58/month)

| Service | Usage | Cost | Notes |
|---------|-------|------|-------|
| **Lambda** | 500K requests, 200K GB-sec | $0 | Within free tier (1M requests, 400K GB-sec) |
| **Bedrock (Haiku)** | 20M tokens/month | $15 | With aggressive caching (50% reduction) |
| **DynamoDB** | 200K writes, 1M reads, 2GB | $8 | On-demand pricing, 3 tables |
| **S3** | 5GB storage, 100K requests | $1 | Static assets + media |
| **CloudFront** | 25GB transfer | $2 | Web interface CDN |
| **API Gateway** | 50K requests | $0.10 | REST + WebSocket |
| **Amazon Translate** | 2M characters | $30 | For 10 languages! |
| **CloudWatch Logs** | 2GB ingestion | $1 | Logging |
| **Secrets Manager** | 1 secret | $0.40 | WhatsApp credentials |
| **Step Functions** | 10K executions | $0.50 | Express workflows |
| **Total** | | **$58/month** | $2 buffer |

## What You GET for $60/month:

### ✅ Interfaces (2 of 3):
- **WhatsApp** (text only) ✅
- **Web Chat** (text only) ✅
- ~~Voice~~ ❌ (add later at $200/month budget)

### ✅ Languages (10 languages!):
- Using **Amazon Translate** instead of manual translations
- Hindi, English, Bengali, Telugu, Marathi, Tamil, Gujarati, Urdu, Kannada, Malayalam
- Cost: $30/month for 2M characters (enough for MVP)
- **This is the biggest win!** 🎉

### ✅ Schemes (100 schemes):
- Store in DynamoDB (2GB = 100 schemes with full details)
- No additional cost beyond storage

### ✅ Search (Keyword + Semantic):
- **Hybrid approach without OpenSearch**:
  - Keyword search: DynamoDB queries (free)
  - Semantic search: Pre-computed embeddings stored in DynamoDB
  - Generate embeddings once during data load (one-time cost: $0.10)
  - No real-time RAG, but good enough for MVP

### ✅ Orchestration:
- **Step Functions** for complex workflows
- Cost: $0.50/month (totally affordable!)

### ❌ What's Still Cut:
- **Voice interface** (Transcribe + Polly): Too expensive ($16+/month)
- **Real-time RAG** (OpenSearch): Too expensive ($24+/month)
- **Advanced monitoring** (X-Ray, detailed metrics): Use basic CloudWatch

## Architecture Details

### 1. Lambda Functions (3 functions, not 1 monolith)

**Function 1: API Handler** (256MB, 10s timeout)
- Handles WhatsApp webhook and web chat API
- Routes to appropriate handler
- Session management with DynamoDB

**Function 2: Agent Orchestrator** (512MB, 30s timeout)
- Intent parsing with Bedrock Haiku
- Starts Step Functions workflow
- Response formatting

**Function 3: Eligibility Engine** (512MB, 20s timeout)
- Rule-based eligibility checking
- Scheme ranking
- Explainability generation

**Cost**: $0 (within free tier)

### 2. Step Functions Workflow

```json
{
  "Comment": "Eligibility Check Workflow",
  "StartAt": "CheckProfile",
  "States": {
    "CheckProfile": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:ProfileChecker",
      "Next": "ProfileComplete?"
    },
    "ProfileComplete?": {
      "Type": "Choice",
      "Choices": [{
        "Variable": "$.profileComplete",
        "BooleanEquals": false,
        "Next": "CollectProfile"
      }],
      "Default": "EvaluateEligibility"
    },
    "CollectProfile": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:ProfileCollector",
      "End": true
    },
    "EvaluateEligibility": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:EligibilityEngine",
      "Next": "FormatResponse"
    },
    "FormatResponse": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:ResponseFormatter",
      "End": true
    }
  }
}
```

**Cost**: $0.50/month for 10K executions

### 3. DynamoDB Tables (On-Demand Pricing)

**Table 1: schemes** (100 schemes, 2GB)
- Partition key: scheme_id
- Attributes: name (10 languages), description, eligibility_rules, benefits, etc.
- Pre-computed embeddings for semantic search (1536 dimensions as JSON array)

**Table 2: sessions** (1000 active sessions, 100MB)
- Partition key: session_id
- TTL: 24 hours
- Attributes: user_profile, conversation_history, language

**Table 3: cache** (common responses, 50MB)
- Partition key: cache_key
- TTL: 1 hour
- Attributes: response, metadata

**Cost**: 
- Storage: 2.15GB × $0.25 = $0.54/month
- Writes: 200K × $1.25/million = $0.25/month
- Reads: 1M × $0.25/million = $0.25/month
- **Total: $1.04/month** (rounded to $8 with buffer)

### 4. Amazon Translate (10 Languages!)

**How it works**:
- User sends message in any language
- Translate detects language automatically
- Translate to English for processing
- Process with Bedrock (English)
- Translate response back to user's language

**Cost**:
- $15 per million characters
- Estimated usage: 2M characters/month (1M in, 1M out)
- **Cost: $30/month**

**This is expensive but worth it for 10 languages!**

### 5. Semantic Search WITHOUT OpenSearch

**Pre-compute embeddings approach**:

1. **One-time setup** (during data load):
   ```python
   # Generate embeddings for all 100 schemes
   for scheme in schemes:
       embedding = bedrock.invoke_model(
           modelId='amazon.titan-embed-text-v1',
           body={'inputText': scheme['description']}
       )
       scheme['embedding'] = embedding  # Store in DynamoDB
   ```
   **Cost**: 100 schemes × 500 tokens × $0.0001/1K tokens = **$0.005** (one-time)

2. **Search time** (no additional cost):
   ```python
   # User query: "farming schemes"
   query_embedding = get_cached_embedding("farming schemes")  # Cache common queries
   
   # Scan DynamoDB and compute cosine similarity in Lambda
   schemes = dynamodb.scan(TableName='schemes')
   for scheme in schemes:
       similarity = cosine_similarity(query_embedding, scheme['embedding'])
       scheme['score'] = similarity
   
   # Return top 10
   return sorted(schemes, key=lambda x: x['score'], reverse=True)[:10]
   ```

**Limitations**:
- Slower than OpenSearch (scan all 100 schemes)
- But 100 schemes is small enough (< 1 second)
- Good enough for MVP!

### 6. Web Chat Interface

**Frontend** (React SPA):
- Hosted on S3 + CloudFront
- Mobile-responsive design
- PWA for offline capability
- WebSocket connection to API Gateway

**Backend** (API Gateway WebSocket):
- Real-time bidirectional communication
- Lambda handles messages
- Session stored in DynamoDB

**Cost**:
- S3: $0.50/month (5GB storage)
- CloudFront: $2/month (25GB transfer)
- **Total: $2.50/month**

## What You're Getting vs Original Design

| Feature | Original ($780/month) | Ultra-MVP ($60/month) | Included? |
|---------|----------------------|----------------------|-----------|
| WhatsApp Interface | ✅ | ✅ | YES |
| Web Chat Interface | ✅ | ✅ | YES |
| Voice Interface | ✅ | ❌ | NO |
| Languages | 10 | 10 | YES (via Translate!) |
| Schemes | 100 | 100 | YES |
| RAG (Real-time) | ✅ (OpenSearch) | ❌ | NO |
| Semantic Search | ✅ (OpenSearch) | ✅ (Pre-computed) | YES (limited) |
| Keyword Search | ✅ | ✅ | YES |
| Step Functions | ✅ | ✅ | YES |
| Bedrock LLM | ✅ (Sonnet+Haiku) | ✅ (Haiku only) | YES |
| RDS Database | ✅ | ❌ (DynamoDB) | NO |
| ElastiCache | ✅ | ❌ (DynamoDB TTL) | NO |
| Advanced Monitoring | ✅ (X-Ray, detailed) | ❌ (Basic CloudWatch) | NO |

## Trade-offs & Limitations

### What Works Well:
✅ 2 interfaces (WhatsApp + Web)
✅ 10 languages (via Translate)
✅ 100 schemes
✅ Basic semantic search
✅ Step Functions orchestration
✅ Good user experience

### What's Limited:
⚠️ No voice (text only)
⚠️ Slower semantic search (scan vs index)
⚠️ No real-time RAG (pre-computed only)
⚠️ Basic monitoring (no X-Ray)
⚠️ Translate costs are high (50% of budget)

### What Breaks at Scale:
❌ DynamoDB scan becomes slow at 1000+ schemes
❌ Translate costs explode at 10M+ characters/month
❌ Lambda free tier exhausted at 1M+ requests/month

## Optimization Strategies

### 1. Reduce Translate Costs (Save $15/month)
**Option A**: Support only 3 languages initially (Hindi, English, Tamil)
- Reduces Translate usage by 70%
- **New cost: $9/month** (saves $21)

**Option B**: Pre-translate scheme content
- Translate 100 schemes × 10 languages = 1000 translations (one-time)
- Store in DynamoDB
- Only translate user messages (much less volume)
- **New cost: $5/month** (saves $25)

**Recommendation**: Use Option B
- **New total: $33/month** (saves $25)
- **Leaves $27 for future features!**

### 2. Add Voice with Saved Budget ($27 available)
With $27 saved from pre-translation:
- Transcribe: 5 hours/month × $0.024/min × 60 = $7.20
- Polly: 100K characters × $4/million = $0.40
- **Voice cost: $7.60/month**

**New total with voice: $33 + $7.60 = $40.60/month**
**Still under $60!** 🎉

## Final Recommendation: $41/month Architecture

| Service | Cost | Notes |
|---------|------|-------|
| Lambda | $0 | Free tier |
| Bedrock (Haiku) | $15 | With caching |
| DynamoDB | $8 | 3 tables, on-demand |
| S3 + CloudFront | $3 | Web interface |
| API Gateway | $0.10 | REST + WebSocket |
| Amazon Translate | $5 | Pre-translated schemes |
| Amazon Transcribe | $7.20 | 5 hours/month |
| Amazon Polly | $0.40 | 100K characters |
| CloudWatch Logs | $1 | Logging |
| Secrets Manager | $0.40 | Credentials |
| Step Functions | $0.50 | Orchestration |
| **Total** | **$40.60** | **$19.40 buffer!** |

## What You Get for $41/month:

✅ **3 Interfaces**: WhatsApp (text + voice), Web Chat (text + voice), Voice calls
✅ **10 Languages**: All Indian languages via pre-translation + Translate
✅ **100 Schemes**: Full scheme database
✅ **Semantic Search**: Pre-computed embeddings
✅ **Step Functions**: Complex workflow orchestration
✅ **Voice**: Basic voice input/output (5 hours/month)

## Implementation Priority

### Phase 1 (Week 1-2): Core MVP ($33/month)
- WhatsApp text interface
- Web chat text interface
- 10 languages (pre-translated)
- 100 schemes
- Basic semantic search
- Step Functions

### Phase 2 (Week 3): Add Voice ($41/month)
- Transcribe integration (5 hours/month)
- Polly integration (100K chars/month)
- Voice UI for both interfaces

### Phase 3 (Week 4): Polish & Launch
- Error handling
- Monitoring
- User testing
- Documentation

## Scaling Path

### At $100/month budget:
- Increase voice quota (20 hours/month)
- Add real-time Translate (no pre-translation)
- Better monitoring (X-Ray)
- More Lambda concurrency

### At $200/month budget:
- Add ElastiCache for better caching
- Increase to 500 schemes
- Add OpenSearch for real RAG
- Advanced analytics

### At $500/month budget:
- Full production architecture
- RDS for relational data
- Multi-region deployment
- 24/7 support

## Conclusion

**YES, you can fit most features into $60/month!**

The key optimizations:
1. **Pre-translate scheme content** (saves $25/month)
2. **Use DynamoDB instead of RDS/ElastiCache/OpenSearch** (saves $594/month)
3. **Pre-compute embeddings** (saves $24/month)
4. **Use Bedrock Haiku only** (saves $20/month)
5. **Limit voice usage** (5 hours/month instead of unlimited)

**Final architecture: $41/month**
- 3 interfaces (WhatsApp, Web, Voice)
- 10 languages
- 100 schemes
- Semantic search
- Step Functions
- Basic voice (5 hours/month)

**You have $19 buffer for overages!** 🎉
