# 🏛️ SarkarSaathi: Design Philosophy

The design of SarkarSaathi is centered around **Trust, Inclusivity, and Modernity**. It aims to provide a premium, accessible experience for all Indian citizens, regardless of their technological literacy.

## 🎨 Color Palette & Aesthetics

SarkarSaathi uses a **Vibrant Dark Mode** to maximize contrast and reduce eye strain, while employing high-end visual effects to feel state-of-the-art.

- **Primary Background**: `#0f0913` (Deep Obsidian) - A rich, dark base that makes content pop.
- **Surface/Cards**: `rgba(255, 255, 255, 0.05)` (Glassmorphism) - Uses semi-transparent backgrounds with background-blur for a "frosted glass" look.
- **Accent 1 (Action)**: `#ff2e63` (Vibrant Pink/Red) - High-visibility call-to-actions and numbers.
- **Accent 2 (Trust)**: `#08d9d6` (Neon Cyan) - Used for AI-recommended highlighting and status indicators.
- **Accent 3 (Growth)**: `#21bf73` (Emerald Green) - Used for financial benefits and positive scores.

## ✨ Visual Elements

### 1. Glassmorphism
Every card (`SchemeCard`, `ProfileCard`, `ChatWindow`) uses a glassmorphic design:
- **Rounded Corners**: `16px` to `24px` for a friendly, approachable feel.
- **Subtle Borders**: `1px solid rgba(255, 255, 255, 0.1)` to define edges without being harsh.
- **Shadows**: Soft, multi-layered shadows to provide depth.

### 2. Holographic Glow
AI-recommended schemes feature a **Cyan outer glow** (`box-shadow: 0 0 20px rgba(8, 217, 214, 0.4)`) to immediately draw the user's attention.

### 3. Typography
- **Primary Font**: `Inter` or `Outfit` (Modern Sans-serif) - Chosen for its high legibility across different script weights.
- **Native Scripts**: Carefully balanced weights for Devanagari, Kannada, and other scripts to ensure they don't look "cramped" compared to English.

## 🧩 Component Interaction

- **Collapsible Sections**: To avoid overwhelming users, complex details are hidden behind "See details" toggles.
- **Space Management**: The **Results Dashboard** uses a `32px` top margin to ensure search inputs and results remain distinct and logically separated.
- **Micro-animations**: Smooth transitions (`0.3s ease`) when switching tabs or hovering over schemes.
- **Responsive Layout**: A mobile-first approach ensuring the chatbot and scheme results are stackable on smaller screens.

## 🗣️ Voice-First UX
The design acknowledges that many users prefer speaking over typing:
- **Prominent Mic Icon**: Located centrally in the chat input with specific BCP-47 language mapping for accuracy.
- **Visual Feedback**: **Voice Mode** features a custom "Voice Orb" and pulse animations to signify active listening.

---
*Designing for the next billion users.* 🏛️🖌️✨

---

# Design Document: SarkarSaathi

## Overview

SarkarSaathi is an AI-powered government scheme navigation assistant built on a modular, tool-oriented architecture. The system uses the Model Context Protocol (MCP) to integrate specialized capabilities, the Kiro agent framework for intelligent orchestration, and Retrieval-Augmented Generation (RAG) for knowledge retrieval. The design prioritizes accessibility, explainability, and operation in resource-constrained environments.

The architecture separates concerns into distinct layers: user interfaces (voice and text), agent orchestration (planning and reasoning), tool services (MCP servers), AI models (embeddings and reasoning), and data storage. This separation enables independent scaling, testing, and evolution of components.

## Architecture

### System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                      │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │  Voice Interface │              │  Chat Interface  │         │
│  │  (Speech-to-Text │              │  (Text I/O with  │         │
│  │   Text-to-Speech)│              │   Mobile UI)     │         │
│  └────────┬─────────┘              └────────┬─────────┘         │
└───────────┼──────────────────────────────────┼──────────────────┘
            │                                  │
            └──────────────┬───────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                          ▼                                       │
│                 Agent Orchestration Layer (Kiro)                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Intent Parser → Planning Engine → Reasoning Workflow      │ │
│  │                  → Tool Orchestrator                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
┌───────────────────▼───┐   ┌───▼────┐  ┌──▼──────────────────────┐
│  MCP Tool Layer       │   │        │  │                          │
│ ┌───────────────────┐ │   │  AI    │  │   Data Layer            │
│ │ Scheme Knowledge  │ │   │ Model  │  │ ┌────────────────────┐  │
│ │ MCP Server        │ │   │ Layer  │  │ │ Scheme Database    │  │
│ ├───────────────────┤ │   │        │  │ │ (Structured JSON)  │  │
│ │ Eligibility Engine│ │   │ • LLM  │  │ ├────────────────────┤  │
│ │ MCP Server        │ │   │ • Embed│  │ │ User Session Store │  │
│ ├───────────────────┤ │   │ • Rank │  │ │ (Temporary)        │  │
│ │ Document Guidance │ │   │        │  │ ├────────────────────┤  │
│ │ MCP Server        │ │   │        │  │ │ Knowledge Corpus   │  │
│ ├───────────────────┤ │   │        │  │ │ (Vector Store)     │  │
│ │ Knowledge RAG     │ │   │        │  │ └────────────────────┘  │
│ │ MCP Server        │ │   │        │  │                          │
│ └───────────────────┘ │   └────────┘  └──────────────────────────┘
└───────────────────────┘
```

### Component Architecture

#### User Interface Layer

**Voice Interface**
- Accepts audio input via WebRTC or telephony integration
- Uses speech-to-text (STT) service with Indic language support (Google Cloud Speech-to-Text, Azure Speech, or Bhashini)
- Implements adaptive bitrate encoding (Opus codec) for low-bandwidth scenarios
- Converts agent responses to speech using text-to-speech (TTS) with natural-sounding voices
- Provides visual feedback for hearing-impaired users (waveform display, transcription)
- Handles noise cancellation and accent adaptation

**Chat Interface**
- Web-based responsive UI built with React or similar framework
- Mobile-first design optimized for small screens and touch interaction
- Supports Unicode rendering for all Indic scripts
- Implements progressive web app (PWA) features for offline capability
- Provides typing indicators, message history, and quick-reply buttons
- Allows seamless switching between voice and text modes

**Accessibility Features**
- Screen reader compatibility (ARIA labels, semantic HTML)
- High-contrast mode and adjustable font sizes
- Keyboard navigation support
- Alternative text for all visual elements

#### Agent Orchestration Layer (Kiro)

**Intent Parser**
- Analyzes user input to determine intent (scheme discovery, eligibility check, application guidance, general query)
- Extracts entities (scheme names, user attributes, document types)
- Handles multi-intent queries by decomposing into sub-intents
- Uses few-shot prompting with LLM for intent classification
- Maintains conversation context across turns

**Planning Engine**
- Generates execution plans based on parsed intent
- Identifies required tools and data dependencies
- Creates directed acyclic graph (DAG) of tasks
- Estimates plan complexity and execution time
- Adapts plans dynamically based on intermediate results

Example plan for "What schemes am I eligible for?":
```
1. Check if user profile exists in session
   - If not: Execute profile collection sub-plan
2. Invoke Eligibility Engine MCP with user profile
3. Invoke Scheme Knowledge MCP to enrich scheme details
4. Rank results by relevance
5. Format response with top 5 schemes
6. Generate explainability for each scheme
```

**Reasoning Workflow (ReAct Agent Loop)**
- Executes plans using a Reasoning and Acting (ReAct) loop.
- The LLM iterates through `Thought -> Action -> Observation -> Final Answer` cycles.
- Missing information or ambiguous input naturally triggers a corrective `Thought` step (e.g., invoking an `ask_clarifying_question` tool).
- Maintains reasoning trace for explainability.
- Synthesizes information from multiple sources into a coherent narrative.

**Tool Orchestrator**
- Discovers available MCP servers on startup
- Maintains registry of tools with their schemas and capabilities
- Routes tool invocation requests to appropriate MCP servers
- Handles request serialization and response deserialization
- Implements circuit breaker pattern for failing servers
- Provides fallback mechanisms when primary tools are unavailable

#### MCP Tool Layer

**Scheme Knowledge MCP Server**

Exposes tools for querying and retrieving scheme information.

Tools:
- `search_schemes(query: str, filters: dict) -> List[Scheme]`
  - Semantic search over scheme database
  - Filters by category, state, benefit type, deadline
  - Returns ranked list of matching schemes

- `get_scheme_details(scheme_id: str) -> SchemeDetails`
  - Retrieves complete information for a specific scheme
  - Includes eligibility rules, benefits, application process, deadlines

- `list_scheme_categories() -> List[str]`
  - Returns available scheme categories for filtering

- `get_schemes_by_department(department: str) -> List[Scheme]`
  - Retrieves all schemes from a specific government department

Implementation:
- Built as a Python FastAPI service
- Connects to Scheme Database (PostgreSQL with JSON columns)
- Uses caching (Redis) for frequently accessed schemes
- Implements rate limiting to prevent abuse

**Eligibility Engine MCP Server**

Evaluates user eligibility against scheme criteria.

Tools:
- `evaluate_eligibility(user_profile: UserProfile, scheme_id: str) -> EligibilityResult`
  - Applies eligibility rules to user profile
  - Returns eligible/ineligible with confidence score
  - Provides reasoning trace showing which conditions passed/failed

- `batch_evaluate_eligibility(user_profile: UserProfile, scheme_ids: List[str]) -> List[EligibilityResult]`
  - Evaluates eligibility for multiple schemes efficiently
  - Uses parallel processing for performance

- `find_eligible_schemes(user_profile: UserProfile) -> List[EligibilityResult]`
  - Scans all schemes and returns eligible ones
  - Ranks by relevance score

- `suggest_qualification_paths(user_profile: UserProfile, scheme_id: str) -> List[Suggestion]`
  - For ineligible schemes, suggests what changes would qualify user
  - Example: "If your income were 10% lower, you would qualify"

Implementation:
- Built as a Python service using rule engine (e.g., python-rules or custom DSL)
- Eligibility rules stored as structured expressions in Scheme Database
- Supports complex logic: AND, OR, NOT, threshold comparisons, date ranges
- Implements caching for rule compilation

**Document Guidance MCP Server**

Generates application guidance and document checklists.

Tools:
- `generate_application_steps(scheme_id: str, user_location: str) -> ApplicationGuide`
  - Creates step-by-step application process
  - Customizes based on user location (online vs offline application centers)
  - Includes estimated time for each step

- `generate_document_checklist(scheme_id: str, user_profile: UserProfile) -> DocumentChecklist`
  - Lists required documents with descriptions
  - Marks documents user likely already has based on profile
  - Provides guidance on obtaining missing documents

- `assess_readiness(scheme_id: str, user_documents: List[str]) -> ReadinessAssessment`
  - Compares user's available documents against requirements
  - Returns completion percentage and missing items
  - Estimates time to complete application

Implementation:
- Built as a Python service
- Uses templates for common application processes
- Retrieves location-specific information from Scheme Database
- Integrates with document verification services where available

**Knowledge RAG MCP Server**

Provides retrieval-augmented generation for policy questions.

Tools:
- `retrieve_relevant_context(query: str, top_k: int) -> List[Document]`
  - Semantic search over knowledge corpus
  - Returns most relevant document chunks

- `answer_question(query: str, context: List[Document]) -> Answer`
  - Uses LLM to generate answer grounded in retrieved context
  - Includes citations to source documents

- `get_scheme_faq(scheme_id: str) -> List[QA]`
  - Returns frequently asked questions for a scheme

Implementation:
- Built using LangChain or LlamaIndex
- Vector store: Pinecone, Weaviate, or Qdrant
- Embeddings: OpenAI ada-002 or open-source alternatives (sentence-transformers)
- Chunking strategy: 512 tokens with 50-token overlap
- Retrieval: Hybrid search (semantic + keyword)

#### AI Model Layer

**Embeddings Model**
- Generates vector representations for semantic search
- Options: OpenAI ada-002, Cohere embed-multilingual, or sentence-transformers
- Supports multilingual embeddings for Indic languages
- Batch processing for efficiency

**Reasoning Model (LLM)**
- Primary model for agent reasoning, planning, and response generation
- Options: GPT-4, Claude, or open-source alternatives (Llama 3, Mistral)
- Configured with system prompts for role and behavior
- Uses structured output formats (JSON) for tool invocations
- Implements token budget management to control costs

**Ranking Model**
- Scores and ranks schemes by relevance to user
- Factors: eligibility match, benefit value, application complexity, deadline proximity
- Can be simple heuristic or learned model (LightGBM, neural ranker)
- Personalization based on user profile and interaction history

#### Data Layer

**Scheme Database**
- Storage: PostgreSQL with JSONB columns for flexible schema
- Schema:
  ```json
  {
    "scheme_id": "string",
    "name": {"en": "string", "hi": "string", ...},
    "description": {"en": "string", "hi": "string", ...},
    "department": "string",
    "category": "string",
    "eligibility_rules": "expression",
    "benefits": {"type": "string", "amount": "number", "description": "object"},
    "application_process": "object",
    "required_documents": ["string"],
    "deadlines": {"start": "date", "end": "date"},
    "target_demographics": ["string"],
    "state": "string",
    "url": "string",
    "last_updated": "timestamp"
  }
  ```
- Indexes on category, state, department, target_demographics
- Full-text search on name and description
- Versioning for audit trail

**User Session Store**
- Storage: Redis for fast access and automatic expiration
- Stores User_Profile, conversation history, and intermediate state
- TTL: 1 hour of inactivity
- Schema:
  ```json
  {
    "session_id": "string",
    "user_profile": {
      "age": "number",
      "gender": "string",
      "income": "number",
      "location": {"state": "string", "district": "string"},
      "occupation": "string",
      "family_size": "number",
      "caste_category": "string",
      "disability_status": "boolean",
      "land_ownership": "number"
    },
    "conversation_history": [{"role": "string", "content": "string", "timestamp": "string"}],
    "selected_language": "string",
    "created_at": "timestamp",
    "last_activity": "timestamp"
  }
  ```

**Knowledge Corpus (Vector Store)**
- Storage: Pinecone, Weaviate, or Qdrant
- Contains embedded chunks of policy documents, scheme guidelines, FAQs
- Metadata: source document, chunk index, scheme_id (if applicable)
- Updated periodically as new policy documents are published

### Data Flow

**End-to-End Request Lifecycle**

1. **User Input**
   - User speaks or types query: "What schemes can I get for farming?"
   - Voice Interface converts speech to text (if voice mode)
   - Input sent to Kiro Agent with session context

2. **Intent Parsing**
   - Kiro Agent analyzes input with LLM
   - Determines intent: scheme_discovery
   - Extracts entities: occupation=farming
   - Checks if User_Profile exists in session

3. **Profile Collection (if needed)**
   - Agent realizes profile is incomplete
   - Generates conversational prompts to collect missing attributes
   - "To help you better, I need to know a few things. What is your age?"
   - User responds, agent updates session store
   - Continues until sufficient profile data collected

4. **Planning**
   - Agent creates execution plan:
     ```
     1. Invoke Eligibility Engine: find_eligible_schemes(user_profile)
     2. For top results, invoke Scheme Knowledge: get_scheme_details(scheme_id)
     3. Rank schemes by relevance
     4. Generate explainability for top 3
     5. Format response
     ```

5. **Tool Invocation**
   - Agent sends MCP request to Eligibility Engine:
     ```json
     {
       "tool": "find_eligible_schemes",
       "parameters": {"user_profile": {...}}
     }
     ```
   - Eligibility Engine evaluates all schemes, returns eligible ones with scores
   - Agent sends MCP requests to Scheme Knowledge for details (parallel)

6. **Reasoning and Synthesis**
   - Agent ranks schemes using Ranking Model
   - Generates explainability for each scheme:
     "You qualify for PM-KISAN because you own agricultural land and your income is below ₹2 lakh per year."
   - Synthesizes response in user's language

7. **Response Generation**
   - Agent formats response with scheme names, benefits, and explanations
   - If voice mode, converts to speech via TTS
   - Sends response to user interface

8. **Follow-up Handling**
   - User asks: "How do I apply for PM-KISAN?"
   - Agent recognizes follow-up intent: application_guidance
   - Invokes Document Guidance MCP: generate_application_steps("PM-KISAN", user_location)
   - Returns step-by-step guide

### Eligibility Reasoning Framework

**Hybrid Reasoning Approach**

The Eligibility Engine uses a hybrid approach combining rule-based evaluation with LLM-assisted reasoning for complex cases.

**Rule-Based Evaluation**

Eligibility rules are expressed in a domain-specific language (DSL):

```python
# Example eligibility rule for PM-KISAN
{
  "scheme_id": "PM-KISAN",
  "rules": {
    "type": "AND",
    "conditions": [
      {"field": "occupation", "operator": "in", "value": ["farmer", "agricultural_worker"]},
      {"field": "land_ownership", "operator": ">", "value": 0},
      {
        "type": "OR",
        "conditions": [
          {"field": "land_ownership", "operator": "<=", "value": 2},
          {"field": "income", "operator": "<=", "value": 200000}
        ]
      }
    ]
  }
}
```

The engine evaluates rules recursively:
- AND: All conditions must be true
- OR: At least one condition must be true
- NOT: Condition must be false
- Operators: ==, !=, <, <=, >, >=, in, not_in, contains, matches (regex)

**LLM-Assisted Reasoning**

For ambiguous cases or complex natural language criteria, the engine invokes an LLM:

```python
def evaluate_complex_criteria(user_profile, criteria_text):
    prompt = f"""
    Determine if the user meets this eligibility criterion:
    Criterion: {criteria_text}
    
    User Profile:
    {json.dumps(user_profile, indent=2)}
    
    Respond with JSON:
    {{
      "eligible": true/false,
      "confidence": 0.0-1.0,
      "reasoning": "explanation"
    }}
    """
    response = llm.generate(prompt)
    return parse_json(response)
```

**Explainability Generation**

For each eligibility determination, the engine generates a reasoning trace:

```python
{
  "scheme_id": "PM-KISAN",
  "eligible": true,
  "confidence": 0.95,
  "reasoning_trace": [
    {"condition": "occupation in [farmer, agricultural_worker]", "result": true, "user_value": "farmer"},
    {"condition": "land_ownership > 0", "result": true, "user_value": 2.5},
    {"condition": "land_ownership <= 2 OR income <= 200000", "result": true, "details": [
      {"condition": "land_ownership <= 2", "result": false, "user_value": 2.5},
      {"condition": "income <= 200000", "result": true, "user_value": 150000}
    ]}
  ],
  "explanation": "You qualify for PM-KISAN because you are a farmer, you own agricultural land, and your annual income is below ₹2 lakh."
}
```

**Marginal Ineligibility Detection**

When a user is ineligible, the engine identifies "near-miss" conditions:

```python
def suggest_qualification_paths(user_profile, scheme_rules):
    suggestions = []
    for condition in scheme_rules:
        if not evaluate(condition, user_profile):
            # Calculate how close user is to meeting condition
            if condition["operator"] in ["<", "<=", ">", ">="]:
                user_value = user_profile[condition["field"]]
                threshold = condition["value"]
                gap = abs(user_value - threshold)
                suggestions.append({
                    "condition": condition,
                    "gap": gap,
                    "suggestion": f"If your {condition['field']} were {threshold}, you would qualify"
                })
    return sorted(suggestions, key=lambda x: x["gap"])
```

### MCP Protocol Interaction Design

**MCP Message Format**

Request:
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "tools/call",
  "params": {
    "name": "evaluate_eligibility",
    "arguments": {
      "user_profile": {...},
      "scheme_id": "PM-KISAN"
    }
  }
}
```

Response:
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"eligible\": true, \"confidence\": 0.95, ...}"
      }
    ]
  }
}
```

**Tool Discovery**

On startup, Kiro Agent sends `tools/list` request to each MCP server:

```json
{
  "jsonrpc": "2.0",
  "id": "discovery-1",
  "method": "tools/list"
}
```

Server responds with tool schemas:

```json
{
  "jsonrpc": "2.0",
  "id": "discovery-1",
  "result": {
    "tools": [
      {
        "name": "evaluate_eligibility",
        "description": "Evaluates user eligibility for a specific scheme",
        "inputSchema": {
          "type": "object",
          "properties": {
            "user_profile": {"type": "object", ...},
            "scheme_id": {"type": "string"}
          },
          "required": ["user_profile", "scheme_id"]
        }
      }
    ]
  }
}
```

**Error Handling**

MCP servers return structured errors:

```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "type": "database_connection_error",
      "details": "Failed to connect to Scheme Database"
    }
  }
}
```

Kiro Agent handles errors with retry logic and fallbacks:
- Transient errors (network, timeout): Retry with exponential backoff
- Invalid input errors: Reformulate request or ask user for clarification
- Server unavailable: Use cached data or alternative tool if available

### AI Decision Pipeline

**Multi-Step Reasoning Flow**

1. **Query Understanding**
   - LLM analyzes user input in context of conversation history
   - Identifies intent, entities, and implicit information needs
   - Determines if query is answerable with available information

2. **Information Gathering**
   - Agent identifies required information not yet available
   - Generates sub-queries or tool invocations to gather information
   - Example: User asks "Can I get a scholarship?" → Need to know user's education level, income, age

3. **Tool Selection**
   - Agent evaluates available tools against information needs
   - Selects most appropriate tool based on:
     - Tool description and capabilities
     - Input schema match with available data
     - Historical success rate
     - Estimated latency

4. **Execution and Monitoring**
   - Agent invokes selected tools
   - Monitors execution progress
   - Handles timeouts and errors
   - Collects results

5. **Result Integration**
   - Agent synthesizes results from multiple tools
   - Resolves conflicts (e.g., different sources provide different information)
   - Fills gaps with LLM-generated content when appropriate
   - Maintains citations and provenance

6. **Response Formulation**
   - Agent generates natural language response
   - Adapts language complexity to user's literacy level
   - Translates to user's selected language
   - Includes actionable next steps

7. **Confidence Assessment**
   - Agent evaluates confidence in response
   - If confidence is low, includes caveats or suggests manual verification
   - Logs low-confidence responses for human review

**Example Decision Trace**

User query: "I am a farmer with 3 acres of land. What can I get?"

```
[Intent Parsing]
Intent: scheme_discovery
Entities: occupation=farmer, land_ownership=3
Missing: age, income, location, family_size

[Planning]
Plan:
1. Collect missing profile attributes
2. Invoke find_eligible_schemes
3. Rank and filter top 5
4. Generate explanations
5. Format response

[Execution]
Step 1: Ask user for age, income, location
  User responds: "I am 45, I make about 1.5 lakh per year, I live in Punjab"
  Update profile: age=45, income=150000, location={state: "Punjab"}

Step 2: Invoke Eligibility Engine
  Tool: find_eligible_schemes
  Input: {age: 45, occupation: "farmer", land_ownership: 3, income: 150000, location: {state: "Punjab"}}
  Output: [
    {scheme_id: "PM-KISAN", eligible: true, confidence: 0.95},
    {scheme_id: "Punjab-Farmer-Subsidy", eligible: true, confidence: 0.90},
    {scheme_id: "Crop-Insurance", eligible: true, confidence: 0.85},
    ...
  ]

Step 3: Rank schemes
  Ranking factors: benefit_value=0.4, application_ease=0.3, deadline_proximity=0.3
  Top 5: [PM-KISAN, Punjab-Farmer-Subsidy, Crop-Insurance, ...]

Step 4: Generate explanations
  For PM-KISAN:
    "You qualify because you are a farmer, own agricultural land, and your income is below ₹2 lakh per year."

Step 5: Format response
  "Based on your profile, you are eligible for 5 schemes. Here are the top 3:
   1. PM-KISAN: ₹6,000 per year direct benefit transfer. You qualify because...
   2. Punjab Farmer Subsidy: Up to ₹10,000 for equipment. You qualify because...
   3. Crop Insurance: Coverage up to ₹50,000. You qualify because...
   
   Would you like to know how to apply for any of these?"

[Response]
Send formatted response to user
```

### Deployment Architecture

**Infrastructure**

- **Hosting**: Cloud platform (AWS, GCP, or Azure)
- **Compute**: Kubernetes cluster for container orchestration
- **Load Balancing**: Application load balancer with SSL termination
- **CDN**: CloudFlare or similar for static assets and caching
- **Database**: Managed PostgreSQL (RDS, Cloud SQL)
- **Cache**: Managed Redis (ElastiCache, Memorystore)
- **Vector Store**: Managed service (Pinecone) or self-hosted (Weaviate on K8s)
- **Object Storage**: S3 or equivalent for audio files, logs

**Service Deployment**

Each component runs as a separate microservice:

- **Kiro Agent Service**: 3+ replicas, autoscaling based on CPU/memory
- **MCP Servers**: 2+ replicas each, independent scaling
- **Voice Interface Service**: 2+ replicas, handles STT/TTS
- **Chat Interface**: Static frontend served via CDN, API gateway for backend

**Communication**

- **User → Interface**: HTTPS, WebSocket (for real-time chat)
- **Interface → Kiro Agent**: REST API or gRPC
- **Kiro Agent → MCP Servers**: HTTP/2 with JSON-RPC
- **Services → Database/Cache**: Private network, connection pooling

**Scaling Strategy**

- **Horizontal Scaling**: Add replicas based on load
- **Vertical Scaling**: Increase resources for LLM inference
- **Caching**: Aggressive caching of scheme data, embeddings, common queries
- **Rate Limiting**: Per-user and per-IP rate limits to prevent abuse
- **Queue-Based Processing**: For non-real-time tasks (batch eligibility evaluation, report generation)

### Security & Privacy Design

**Data Protection**

- **Encryption in Transit**: TLS 1.3 for all network communication
- **Encryption at Rest**: Database encryption, encrypted Redis snapshots
- **PII Handling**: User profiles stored with session-level encryption keys
- **Data Retention**: User profiles deleted after session expiry (1 hour inactivity)
- **Anonymization**: Logs and analytics anonymize PII

**Authentication & Authorization**

- **Citizen Authentication**: OTP-based login via mobile number (Cognito/JWT). Profiles and session histories are securely retained across sessions for returning users.
- **Operator Authentication**: Role-based access for CSC intermediaries via a dedicated Operator Dashboard, allowing them to manage multiple concurrent citizen sessions.
- **Service Authentication**: Mutual TLS between services.
- **API Keys**: For MCP server access, rotated regularly.
- **Explicit Consent**: The system implements a hard barrier requiring documented user consent via the UI before sensitive PII (like caste or income) is ingested by the Agent or processed.

**Compliance**

- **Data Localization**: User data stored in India (if required by regulation)
- **Audit Logging**: All eligibility determinations logged with reasoning
- **Right to Deletion**: Users can request deletion of any stored data
- **Transparency**: Clear privacy policy and data usage disclosure

### Observability & Monitoring

**Metrics**

- **System Metrics**: CPU, memory, disk, network per service
- **Application Metrics**: Request rate, latency (p50, p95, p99), error rate
- **Business Metrics**: Sessions per day, schemes queried, eligibility checks performed, application guidance requests
- **Model Metrics**: LLM token usage, embedding generation time, cache hit rate

**Logging**

- **Structured Logging**: JSON format with correlation IDs
- **Log Levels**: DEBUG, INFO, WARN, ERROR
- **Centralized Logging**: ELK stack or cloud-native solution (CloudWatch, Stackdriver)
- **Log Retention**: 90 days for audit logs, 30 days for application logs

**Tracing**

- **Distributed Tracing**: OpenTelemetry for request tracing across services
- **Trace Visualization**: Jaeger or Zipkin
- **Critical Paths**: Trace eligibility evaluation, tool invocations, LLM calls

**Alerting**

- **Error Rate Alerts**: Trigger when error rate > 5% for 5 minutes
- **Latency Alerts**: Trigger when p95 latency > 10 seconds
- **Availability Alerts**: Trigger when service health check fails
- **Business Alerts**: Trigger when daily sessions drop > 50%

**Dashboards**

- **System Health**: Service status, resource utilization
- **User Activity**: Active sessions, popular schemes, query patterns
- **Performance**: Latency distribution, throughput, cache performance
- **Errors**: Error types, frequency, affected services

### Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


#### Property 1: Multilingual Input Processing
*For any* supported language (Hindi, English, Bengali, Telugu, Marathi, Tamil, Gujarati, Urdu, Kannada, Malayalam) and any text input in that language, the system should successfully process and respond in the same language.
**Validates: Requirements 1.2, 2.1, 11.1, 11.2**

#### Property 2: Language Switching Preserves Context
*For any* active session, switching from one supported language to another should preserve all session context (user profile, conversation history) and continue interactions in the new language.
**Validates: Requirements 2.4, 11.5**

#### Property 3: Voice Recognition Failure Recovery
*For any* voice input with low recognition confidence, the system should trigger a retry flow prompting the user to repeat or rephrase.
**Validates: Requirements 1.5**

#### Property 4: Complete Profile Collection
*For any* new session, the profile collection process should gather all essential attributes (age, gender, income, location, occupation, family_size, caste_category, disability_status, land_ownership) before proceeding to eligibility evaluation.
**Validates: Requirements 3.1, 3.2**

#### Property 5: Ambiguous Input Triggers Clarification
*For any* user input that is ambiguous or incomplete, the system should generate clarifying questions before using the information in eligibility evaluation.
**Validates: Requirements 3.3**

#### Property 6: Profile Updates Reflect in Subsequent Operations
*For any* session where a user updates profile information, all subsequent eligibility evaluations and recommendations should use the updated profile data.
**Validates: Requirements 3.5**

#### Property 7: Comprehensive Eligibility Evaluation
*For any* complete user profile, the eligibility engine should evaluate the profile against all schemes in the database and return results for each scheme.
**Validates: Requirements 4.1**

#### Property 8: Rule Evaluation Correctness
*For any* eligibility rule (AND, OR, NOT, threshold comparisons) and any user profile, the evaluation result should correctly reflect whether the profile satisfies the rule according to boolean logic.
**Validates: Requirements 4.2**

#### Property 9: Scheme Ranking by Relevance
*For any* set of eligible schemes, the returned list should be ordered by relevance score in descending order, where relevance is computed from user attributes and benefit value.
**Validates: Requirements 4.3**

#### Property 10: Marginal Ineligibility Suggestions
*For any* scheme where a user is ineligible but close to qualifying (within one condition change), the system should generate suggestions describing what changes would make them eligible.
**Validates: Requirements 4.4**

#### Property 11: Low Confidence Flagging
*For any* eligibility determination with confidence score below a threshold (e.g., 0.7), the system should flag the scheme for manual verification.
**Validates: Requirements 4.5**

#### Property 12: Explainability Completeness
*For any* eligibility determination (eligible or ineligible), the system should generate an explanation that references all conditions that were evaluated and their results, in the user's selected language.
**Validates: Requirements 5.1, 5.2, 5.4, 5.5**

#### Property 13: Semantic Search Relevance
*For any* user query requesting scheme information, the retrieved schemes should be semantically relevant to the query (measured by embedding similarity above a threshold).
**Validates: Requirements 6.1**

#### Property 14: Scheme Presentation Completeness
*For any* scheme presented to the user, the response should include scheme name, benefit description, eligibility summary, and application deadline.
**Validates: Requirements 6.3**

#### Property 15: Filter Correctness
*For any* filter applied to scheme search (category, benefit amount, application complexity), the returned results should only include schemes that match the filter criteria.
**Validates: Requirements 6.4**

#### Property 16: Application Guide Generation
*For any* scheme selected for application, the system should generate a guide containing sequential steps for the application process.
**Validates: Requirements 7.1**

#### Property 17: Document Checklist Completeness
*For any* scheme, the generated document checklist should include all documents specified in the scheme's requirements.
**Validates: Requirements 7.2**

#### Property 18: Location-Based Guidance Customization
*For any* two users with different locations applying for the same scheme, if the application process differs by location, the generated guidance should differ accordingly.
**Validates: Requirements 7.3**

#### Property 19: Document Possession Inference
*For any* user profile and document checklist, the system should correctly infer which documents the user likely possesses based on profile attributes (e.g., farmers likely have land ownership documents).
**Validates: Requirements 7.4**

#### Property 20: Latest Procedure Retrieval
*For any* scheme with multiple versions of application procedures, the system should retrieve and present the most recent version.
**Validates: Requirements 7.5**

#### Property 21: Readiness Assessment Accuracy
*For any* document checklist and set of user-provided documents, the readiness assessment should correctly identify which required documents are missing.
**Validates: Requirements 8.1, 8.2**

#### Property 22: Missing Document Guidance
*For any* missing document identified in readiness assessment, the system should provide guidance on how to obtain that specific document.
**Validates: Requirements 8.3**

#### Property 23: Time Estimation Based on Missing Items
*For any* readiness assessment, the estimated completion time should be calculated based on the number and complexity of missing items.
**Validates: Requirements 8.4**

#### Property 24: MCP Server Discovery
*For any* configured MCP server that is running and accessible, the Kiro agent should discover it on startup and register its available tools.
**Validates: Requirements 9.1**

#### Property 25: MCP Protocol Compliance
*For any* tool invocation, the request message should conform to the MCP JSON-RPC 2.0 protocol specification.
**Validates: Requirements 9.2**

#### Property 26: Tool Response Integration
*For any* successful tool invocation, the returned results should be parsed and made available to the reasoning workflow for subsequent steps.
**Validates: Requirements 9.3**

#### Property 27: Tool Invocation Retry on Failure
*For any* tool invocation that fails with a transient error (network timeout, temporary unavailability), the system should retry the invocation with exponential backoff before reporting failure.
**Validates: Requirements 9.4**

#### Property 28: Contextual Tool Selection
*For any* request that can be satisfied by multiple tools, the selected tool should be the one with the highest relevance score based on the request context and tool capabilities.
**Validates: Requirements 9.5**

#### Property 29: Query Decomposition for Complex Requests
*For any* user query that requires information from multiple sources, the system should decompose it into sub-tasks that can be executed independently or sequentially.
**Validates: Requirements 10.1**

#### Property 30: Execution Plan Validity
*For any* generated execution plan, all tool invocations should have their input dependencies satisfied by either user input or outputs from earlier steps in the plan.
**Validates: Requirements 10.2**

#### Property 31: Adaptive Planning
*For any* execution plan where an intermediate result indicates the plan cannot be completed as designed, the system should modify the plan or generate an alternative approach.
**Validates: Requirements 10.3**

#### Property 32: Multi-Tool Result Synthesis
*For any* plan that invokes multiple tools, the final response should incorporate information from all tool results in a coherent manner.
**Validates: Requirements 10.4**

#### Property 33: Incomplete Plan Explanation
*For any* execution plan that cannot be completed, the system should generate an explanation identifying which information is missing and why it is needed.
**Validates: Requirements 10.5**

#### Property 34: Translation Consistency
*For any* scheme information originally in one language, when translated to the user's selected language, the semantic meaning should be preserved (verified through back-translation similarity).
**Validates: Requirements 11.3**

#### Property 35: Cache Hit Reduces Network Requests
*For any* scheme information that has been accessed within the cache TTL period, subsequent requests for the same information should be served from cache without making network requests to the database.
**Validates: Requirements 12.4**

#### Property 36: Offline Input Queuing
*For any* user input submitted while the network connection is unavailable, the input should be queued locally and transmitted when the connection is restored, preserving the order of inputs.
**Validates: Requirements 12.5**

#### Property 37: Unique Session Identifiers
*For any* two sessions created at any time, their session identifiers should be unique (no collisions).
**Validates: Requirements 13.1**

#### Property 38: Session Data Deletion on Expiry
*For any* session that ends (explicit logout or timeout), the user profile data should be deleted from storage unless the user has explicitly opted in to save it.
**Validates: Requirements 13.3**

#### Property 39: No Unauthorized Data Sharing
*For any* user profile, the system should not transmit profile data to external systems unless the user has provided explicit consent (verified by consent flag in session).
**Validates: Requirements 13.4**

#### Property 40: Log Anonymization
*For any* session log entry, personally identifiable information (name, phone, address) should be anonymized or redacted before storage.
**Validates: Requirements 13.5**

#### Property 41: Overload Triggers Queuing
*For any* system state where active sessions exceed capacity threshold, new requests should be queued and users should receive an estimated wait time.
**Validates: Requirements 14.5**

#### Property 42: Scheme Schema Completeness
*For any* scheme stored in the database, it should contain all required fields: name, description, eligibility_rules, benefits, application_process, required_documents, and deadlines.
**Validates: Requirements 15.1**

#### Property 43: Scheme Update Versioning
*For any* update to scheme information, a new version should be created with a timestamp, and the previous version should be retained in the update history.
**Validates: Requirements 15.2**

#### Property 44: Bulk Import Correctness
*For any* valid bulk import file (JSON or CSV) containing scheme data, all schemes in the file should be successfully imported into the database with correct field mappings.
**Validates: Requirements 15.3**

#### Property 45: Rule Syntax Validation
*For any* eligibility rule modification, if the rule syntax is invalid (malformed expression, undefined operators), the system should reject the change and return a validation error.
**Validates: Requirements 15.4**

#### Property 46: Query API Correctness
*For any* query to the scheme database with specific attribute filters, the returned schemes should match all specified filter criteria.
**Validates: Requirements 15.5**

#### Property 47: Fallback on Tool Failure
*For any* tool invocation that fails after retries, the system should attempt an alternative approach (different tool, cached data, or simplified query) before reporting failure to the user.
**Validates: Requirements 16.1**

#### Property 48: No-Results Handling
*For any* search query that returns zero results, the system should acknowledge the lack of results and suggest alternative queries or related schemes.
**Validates: Requirements 16.2**

#### Property 49: Incomplete Data Triggers Collection
*For any* operation that requires user profile data that is missing or incomplete, the system should identify the missing fields and prompt the user to provide them.
**Validates: Requirements 16.3**

#### Property 50: Error Logging with Context
*For any* error that occurs during system operation, a log entry should be created containing the error type, message, stack trace, and relevant context (session_id, user action, timestamp).
**Validates: Requirements 16.4**

#### Property 51: Audio Content Has Text Alternatives
*For any* audio content presented to the user (voice responses, audio notifications), a text alternative should be available and accessible.
**Validates: Requirements 17.2**

#### Property 52: Voice Interaction Visual Feedback
*For any* voice interaction (user speaking or system responding), visual feedback should be displayed (waveform, transcription, or status indicator).
**Validates: Requirements 17.4**

#### Property 53: Eligibility Decision Audit Logging
*For any* eligibility determination made by the eligibility engine, an audit log entry should be created containing the decision (eligible/ineligible), input user profile, eligibility rules evaluated, and reasoning trace.
**Validates: Requirements 18.1**

#### Property 54: Tool Invocation Logging
*For any* tool invocation, a log entry should be created containing the tool name, input parameters, output results, timestamp, and execution duration.
**Validates: Requirements 18.2**

#### Property 55: Usage Report Generation
*For any* 24-hour period, the system should generate a daily report containing system usage metrics (number of sessions, schemes queried, eligibility checks performed), error rates, and scheme query patterns.
**Validates: Requirements 18.4**

#### Property 56: Audit Log Retention
*For any* audit log entry, it should be retained in storage for at least 90 days from creation before being eligible for deletion.
**Validates: Requirements 18.5**

#### Property 57: Consistent Eligibility for Identical Profiles
*For any* two user profiles that are identical in all attributes relevant to a scheme's eligibility criteria, the eligibility determination should be the same for both profiles.
**Validates: Requirements 19.1**

#### Property 58: Ranking Factor Restriction
*For any* scheme ranking operation, the relevance score should only be computed from user eligibility match and benefit value, not from other user demographics.
**Validates: Requirements 19.2**

#### Property 59: Sensitive Attribute Collection Restriction
*For any* profile collection process, sensitive attributes (religion, political affiliation) should only be collected if at least one scheme in the database explicitly requires them for eligibility.
**Validates: Requirements 19.3**

#### Property 60: Health Check Endpoint Availability
*For any* critical system component (Kiro Agent, MCP Servers, Database), a health check endpoint should be exposed and should respond with status information when queried.
**Validates: Requirements 20.1**

#### Property 61: Metrics Collection and Reporting
*For any* system operation, relevant metrics (response time, error occurrence, resource usage) should be collected and made available through monitoring interfaces.
**Validates: Requirements 20.2**

#### Property 62: Threshold-Based Alerting
*For any* monitored metric that exceeds its configured threshold (e.g., error rate > 5%), an alert should be triggered and sent to system operators.
**Validates: Requirements 20.3**

#### Property 63: Automatic Server Failover
*For any* MCP server that becomes unavailable (health check fails), the system should automatically route requests to alternative servers or use cached data until the server recovers.
**Validates: Requirements 20.4**

### Error Handling

**Error Categories**

1. **User Input Errors**
   - Invalid or ambiguous profile information
   - Unsupported language selection
   - Malformed queries
   - Response: Request clarification, provide examples, suggest corrections

2. **System Errors**
   - Tool invocation failures
   - Database connection errors
   - LLM API failures
   - Response: Retry with backoff, use cached data, provide degraded service, log for investigation

3. **Data Errors**
   - Missing scheme information
   - Inconsistent eligibility rules
   - Outdated application procedures
   - Response: Flag for manual review, use best available data, inform user of uncertainty

4. **Network Errors**
   - Connection timeouts
   - Bandwidth limitations
   - Service unavailability
   - Response: Queue requests, compress data, provide offline functionality

**Error Recovery Strategies**

- **Graceful Degradation**: Provide reduced functionality when full service is unavailable
- **Retry Logic**: Exponential backoff for transient failures
- **Fallback Mechanisms**: Alternative tools, cached data, simplified queries
- **User Communication**: Clear error messages, suggested actions, support contact information

### Testing Strategy

**Dual Testing Approach**

The system requires both unit testing and property-based testing for comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs
- Both approaches are complementary and necessary

**Unit Testing Focus**

Unit tests should focus on:
- Specific examples that demonstrate correct behavior (e.g., a specific user profile qualifying for a specific scheme)
- Integration points between components (e.g., Kiro Agent invoking MCP servers)
- Edge cases and error conditions (e.g., empty database, network failures)
- Examples from requirements marked as "yes - example" in prework

Avoid writing too many unit tests for scenarios that property tests can cover through randomization.

**Property-Based Testing Configuration**

- **Library**: Use fast-check (JavaScript/TypeScript), Hypothesis (Python), or QuickCheck (Haskell) depending on implementation language
- **Iterations**: Minimum 100 iterations per property test to ensure comprehensive input coverage
- **Test Tagging**: Each property test must include a comment referencing its design document property
  - Format: `// Feature: sarkar-saathi, Property 1: Multilingual Input Processing`
- **One Property, One Test**: Each correctness property listed above should be implemented by exactly one property-based test

**Test Coverage Goals**

- **Code Coverage**: Minimum 80% line coverage, 70% branch coverage
- **Property Coverage**: All 63 correctness properties implemented as property tests
- **Integration Coverage**: All MCP tool interactions tested
- **End-to-End Coverage**: Critical user journeys tested (profile collection → eligibility check → application guidance)

**Testing Environments**

- **Local Development**: Unit and property tests run on developer machines
- **CI/CD Pipeline**: All tests run on every commit
- **Staging**: Integration and end-to-end tests with production-like data
- **Production**: Synthetic monitoring and canary testing

### Future Extensions

**Planned Enhancements**

1. **Proactive Notifications**
   - Alert users when new schemes matching their profile are added
   - Remind users of approaching application deadlines
   - Notify users when their eligibility status changes

2. **Application Submission Integration**
   - Direct integration with government portals for online application submission
   - Pre-fill application forms with user profile data
   - Track application status and provide updates

3. **Document Verification**
   - OCR and validation of uploaded documents
   - Automated document completeness checking
   - Integration with DigiLocker for document retrieval

4. **Community Features**
   - User forums for sharing application experiences
   - Success stories and testimonials
   - Peer support and guidance

5. **Advanced Analytics**
   - Predictive modeling for scheme uptake
   - Identification of underserved populations
   - Policy impact analysis

6. **Offline Mobile App**
   - Full-featured mobile application with offline capability
   - Sync when connectivity is available
   - Voice-first interface optimized for mobile

7. **Multi-Modal Interaction**
   - Video guidance for complex application processes
   - Visual document checklists with images
   - Interactive application walkthroughs

8. **Personalized Recommendations**
   - Machine learning-based scheme recommendations
   - Learning from user interactions and preferences
   - Collaborative filtering based on similar users

9. **Integration with Other Services**
   - Link to financial literacy resources
#### Property 46: Query API Correctness
*For any* query to the scheme database with specific attribute filters, the returned schemes should match all specified filter criteria.
**Validates: Requirements 15.5**

#### Property 47: Fallback on Tool Failure
*For any* tool invocation that fails after retries, the system should attempt an alternative approach (different tool, cached data, or simplified query) before reporting failure to the user.
**Validates: Requirements 16.1**

#### Property 48: No-Results Handling
*For any* search query that returns zero results, the system should acknowledge the lack of results and suggest alternative queries or related schemes.
**Validates: Requirements 16.2**

#### Property 49: Incomplete Data Triggers Collection
*For any* operation that requires user profile data that is missing or incomplete, the system should identify the missing fields and prompt the user to provide them.
**Validates: Requirements 16.3**

#### Property 50: Error Logging with Context
*For any* error that occurs during system operation, a log entry should be created containing the error type, message, stack trace, and relevant context (session_id, user action, timestamp).
**Validates: Requirements 16.4**

#### Property 51: Audio Content Has Text Alternatives
*For any* audio content presented to the user (voice responses, audio notifications), a text alternative should be available and accessible.
**Validates: Requirements 17.2**

#### Property 52: Voice Interaction Visual Feedback
*For any* voice interaction (user speaking or system responding), visual feedback should be displayed (waveform, transcription, or status indicator).
**Validates: Requirements 17.4**

#### Property 53: Eligibility Decision Audit Logging
*For any* eligibility determination made by the eligibility engine, an audit log entry should be created containing the decision (eligible/ineligible), input user profile, eligibility rules evaluated, and reasoning trace.
**Validates: Requirements 18.1**

#### Property 54: Tool Invocation Logging
*For any* tool invocation, a log entry should be created containing the tool name, input parameters, output results, timestamp, and execution duration.
**Validates: Requirements 18.2**

#### Property 55: Usage Report Generation
*For any* 24-hour period, the system should generate a daily report containing system usage metrics (number of sessions, schemes queried, eligibility checks performed), error rates, and scheme query patterns.
**Validates: Requirements 18.4**

#### Property 56: Audit Log Retention
*For any* audit log entry, it should be retained in storage for at least 90 days from creation before being eligible for deletion.
**Validates: Requirements 18.5**

#### Property 57: Consistent Eligibility for Identical Profiles
*For any* two user profiles that are identical in all attributes relevant to a scheme's eligibility criteria, the eligibility determination should be the same for both profiles.
**Validates: Requirements 19.1**

#### Property 58: Ranking Factor Restriction
*For any* scheme ranking operation, the relevance score should only be computed from user eligibility match and benefit value, not from other user demographics.
**Validates: Requirements 19.2**

#### Property 59: Sensitive Attribute Collection Restriction
*For any* profile collection process, sensitive attributes (religion, political affiliation) should only be collected if at least one scheme in the database explicitly requires them for eligibility.
**Validates: Requirements 19.3**

#### Property 60: Health Check Endpoint Availability
*For any* critical system component (Kiro Agent, MCP Servers, Database), a health check endpoint should be exposed and should respond with status information when queried.
**Validates: Requirements 20.1**

#### Property 61: Metrics Collection and Reporting
*For any* system operation, relevant metrics (response time, error occurrence, resource usage) should be collected and made available through monitoring interfaces.
**Validates: Requirements 20.2**

#### Property 62: Threshold-Based Alerting
*For any* monitored metric that exceeds its configured threshold (e.g., error rate > 5%), an alert should be triggered and sent to system operators.
**Validates: Requirements 20.3**

#### Property 63: Automatic Server Failover
*For any* MCP server that becomes unavailable (health check fails), the system should automatically route requests to alternative servers or use cached data until the server recovers.
**Validates: Requirements 20.4**

### Error Handling

**Error Categories**

1. **User Input Errors**
   - Invalid or ambiguous profile information
   - Unsupported language selection
   - Malformed queries
   - Response: Request clarification, provide examples, suggest corrections

2. **System Errors**
   - Tool invocation failures
   - Database connection errors
   - LLM API failures
   - Response: Retry with backoff, use cached data, provide degraded service, log for investigation

3. **Data Errors**
   - Missing scheme information
   - Inconsistent eligibility rules
   - Outdated application procedures
   - Response: Flag for manual review, use best available data, inform user of uncertainty

4. **Network Errors**
   - Connection timeouts
   - Bandwidth limitations
   - Service unavailability
   - Response: Queue requests, compress data, provide offline functionality

**Error Recovery Strategies**

- **Graceful Degradation**: Provide reduced functionality when full service is unavailable
- **Retry Logic**: Exponential backoff for transient failures
- **Fallback Mechanisms**: Alternative tools, cached data, simplified queries
- **User Communication**: Clear error messages, suggested actions, support contact information

### Testing Strategy

**Dual Testing Approach**

The system requires both unit testing and property-based testing for comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs
- Both approaches are complementary and necessary

**Unit Testing Focus**

Unit tests should focus on:
- Specific examples that demonstrate correct behavior (e.g., a specific user profile qualifying for a specific scheme)
- Integration points between components (e.g., Kiro Agent invoking MCP servers)
- Edge cases and error conditions (e.g., empty database, network failures)
- Examples from requirements marked as "yes - example" in prework

Avoid writing too many unit tests for scenarios that property tests can cover through randomization.

**Property-Based Testing Configuration**

- **Library**: Use fast-check (JavaScript/TypeScript), Hypothesis (Python), or QuickCheck (Haskell) depending on implementation language
- **Iterations**: Minimum 100 iterations per property test to ensure comprehensive input coverage
- **Test Tagging**: Each property test must include a comment referencing its design document property
  - Format: `// Feature: sarkar-saathi, Property 1: Multilingual Input Processing`
- **One Property, One Test**: Each correctness property listed above should be implemented by exactly one property-based test

**Test Coverage Goals**

- **Code Coverage**: Minimum 80% line coverage, 70% branch coverage
- **Property Coverage**: All 63 correctness properties implemented as property tests
- **Integration Coverage**: All MCP tool interactions tested
- **End-to-End Coverage**: Critical user journeys tested (profile collection → eligibility check → application guidance)

**Testing Environments**

- **Local Development**: Unit and property tests run on developer machines
- **CI/CD Pipeline**: All tests run on every commit
- **Staging**: Integration and end-to-end tests with production-like data
- **Production**: Synthetic monitoring and canary testing

### Future Extensions

**Planned Enhancements**

1. **Proactive Notifications**
   - Alert users when new schemes matching their profile are added
   - Remind users of approaching application deadlines
   - Notify users when their eligibility status changes

2. **Application Submission Integration**
   - Direct integration with government portals for online application submission
   - Pre-fill application forms with user profile data
   - Track application status and provide updates

3. **Document Verification**
   - OCR and validation of uploaded documents
   - Automated document completeness checking
   - Integration with DigiLocker for document retrieval

4. **Community Features**
   - User forums for sharing application experiences
   - Success stories and testimonials
   - Peer support and guidance

5. **Advanced Analytics**
   - Predictive modeling for scheme uptake
   - Identification of underserved populations
   - Policy impact analysis

6. **Offline Mobile App**
   - Full-featured mobile application with offline capability
   - Sync when connectivity is available
   - Voice-first interface optimized for mobile

7. **Multi-Modal Interaction**
   - Video guidance for complex application processes
   - Visual document checklists with images
   - Interactive application walkthroughs

8. **Personalized Recommendations**
   - Machine learning-based scheme recommendations
   - Learning from user interactions and preferences
   - Collaborative filtering based on similar users

9. **Integration with Other Services**
   - Link to financial literacy resources
   - Connect with local service centers and NGOs
   - Integration with employment and skill development programs

10. **Expanded Language Support**
    - Support for additional regional languages and dialects
    - Voice recognition for low-resource languages
    - Dialect adaptation for better comprehension
