"""
Pydantic models for SarkarSaathi API request/response objects.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class UserQuery(BaseModel):
    """Incoming query from user."""
    query: str
    session_id: Optional[str] = None


class UserProfile(BaseModel):
    """Structured profile extracted from user query."""
    age: Optional[int] = None
    gender: Optional[str] = None          # male / female / other
    marital_status: Optional[str] = None  # unmarried / married / widowed / divorced
    children: Optional[int] = None
    occupation: Optional[str] = None      # farmer / student / unemployed / salaried / ...
    income_level: Optional[int] = None    # annual income in INR
    location_type: Optional[str] = None   # rural / urban / semi-urban
    state: Optional[str] = None
    caste: Optional[str] = None           # general / obc / sc / st
    needs: List[str] = []                 # housing / education / health / food / ...
    language: str = "en"


class SchemeMatch(BaseModel):
    """A single matched scheme with score and reason."""
    id: str
    name_en: str
    name_hi: str
    category: str
    state: str
    benefit_amount: Optional[int] = None
    benefit_description: str
    eligibility_reason: str
    match_score: int
    required_documents: List[str] = []
    how_to_apply: str
    application_steps: List[str] = []
    office_info: str
    website: Optional[str] = None


class QueryResponse(BaseModel):
    """Full API response for a query."""
    profile: UserProfile
    schemes: List[SchemeMatch]
    total_matched: int
    query_lang: str
    message: str


# ── Chatbot Models ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Incoming chat message for the conversational chatbot."""
    message: str
    session_id: Optional[str] = None
    language: Optional[str] = None        # "en" or "hi" — auto-detected if not set
    include_summary: bool = False          # Whether to include AI-generated scheme summary
    mode: str = "text"                     # "text" or "voice" (voice handled by frontend TTS)


class ChatResponse(BaseModel):
    """Response from the conversational chatbot."""
    session_id: str
    response: str                          # Main AI conversational reply
    summary: Optional[str] = None         # Personalized scheme recommendation summary
    schemes: List[SchemeMatch] = []       # Top matched schemes (RAG context)
    profile: Optional[UserProfile] = None # Extracted user profile
    language: str = "en"                  # Detected/used language
