"""
Chat router for SarkarSaathi — Adaptive CoT RAG Chatbot endpoint.
Supports text-based multi-turn conversation powered by AWS Nova via Bedrock.
"""
from fastapi import APIRouter, HTTPException
from models import ChatRequest, ChatResponse
from extractor import extract_profile
from matcher import match_schemes, get_schemes
from database import create_session, get_session, save_session
from agent import generate_chat_response, generate_summary, detect_language

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """
    Multi-turn conversational endpoint using Adaptive CoT RAG.

    Flow:
    1. Detect language from user input
    2. Extract/merge user profile from message
    3. Match eligible schemes (RAG retrieval)
    4. Generate AI response with chain-of-thought reasoning
    5. Optionally generate a personalized summary of top scheme
    """
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Session handling
    session_id = body.session_id or create_session()
    existing = get_session(session_id)

    # Detect language (fallback to body preference or auto-detect)
    language = body.language or detect_language(message)

    # Extract profile from current message
    profile = extract_profile(message)
    profile.language = language

    # Merge with existing session profile
    if existing and existing.get("profile"):
        old = existing["profile"]
        for field in ["age", "gender", "marital_status", "occupation",
                      "income_level", "location_type", "state", "caste", "children"]:
            if getattr(profile, field) is None and old.get(field) is not None:
                setattr(profile, field, old[field])
        if not profile.needs and old.get("needs"):
            profile.needs = old["needs"]

    # Save updated session
    save_session(session_id, profile.model_dump(), message)

    # RAG: retrieve top matching schemes
    matched = match_schemes(profile, top_n=10)

    # Get conversation history from session
    history = existing.get("history", []) if existing else []

    # Generate AI chat response (CoT RAG)
    ai_response = generate_chat_response(
        user_message=message,
        profile=profile,
        matched_schemes=matched,
        conversation_history=history,
        language=language,
    )

    # Optionally generate summarizer output
    summary = None
    if body.include_summary and matched:
        summary = generate_summary(
            profile=profile,
            matched_schemes=matched,
            language=language,
        )

    # Update history for next turn
    updated_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": ai_response},
    ]
    # Keep only last 10 turns to avoid session bloat
    updated_history = updated_history[-10:]
    save_session(session_id, profile.model_dump(), message)

    return ChatResponse(
        session_id=session_id,
        response=ai_response,
        summary=summary,
        schemes=matched[:5],
        profile=profile,
        language=language,
    )


@router.get("/session/{session_id}")
async def get_chat_session(session_id: str):
    """Retrieve chat session info."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
