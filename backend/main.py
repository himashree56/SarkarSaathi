"""
SarkarSaathi — FastAPI Backend
Main application entry point.
"""
import uuid
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import UserQuery, QueryResponse, SchemeMatch
from extractor import extract_profile
from matcher import load_schemes, match_schemes, get_schemes
from database import init_db, create_session, get_session, save_session
from routers.chat import router as chat_router
from routers.auth import router as auth_router
from routers.feedback import router as feedback_router
from agent import translate_schemes_to_lang


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle handler."""
    # Startup
    print("[startup] Initializing SarkarSaathi backend...")
    init_db()
    load_schemes()
    print("[startup] Ready.")
    yield
    # Shutdown (nothing to clean up)


app = FastAPI(
    title="SarkarSaathi API",
    description="AI Government Scheme Navigator — Find eligible Indian government schemes",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow React dev server and production builds
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "https://d1n5qc1s7kbyvb.cloudfront.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(feedback_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    schemes = get_schemes()
    return {
        "status": "ok",
        "schemes_loaded": len(schemes),
        "version": "1.0.0",
    }


@app.post("/query", response_model=QueryResponse)
async def query_schemes(body: UserQuery):
    """
    Main endpoint: extract user profile from natural language query
    and return top-10 matching government schemes.
    """
    query_text = body.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Session handling
    session_id = body.session_id or create_session()
    existing = get_session(session_id)

    # Extract structured profile
    profile = extract_profile(query_text, preferred_lang=body.lang)

    # Merge with existing session profile if available
    if existing and existing.get("profile"):
        old = existing["profile"]
        # Don't overwrite values that were already captured
        for field in ["age", "gender", "marital_status", "occupation",
                      "income_level", "location_type", "state", "caste", "children"]:
            if getattr(profile, field) is None and old.get(field) is not None:
                setattr(profile, field, old[field])
        if not profile.needs and old.get("needs"):
            profile.needs = old["needs"]

    # Save updated profile to session
    save_session(session_id, profile.model_dump(), query_text)

    # Match against schemes
    matched = match_schemes(profile, top_n=10)
    
    # Dynamically translate schemes if not English or Hindi
    if profile.language not in ["en", "hi"]:
        matched = translate_schemes_to_lang(matched, profile.language)
        
    total = len(match_schemes(profile, top_n=1000))  # full count

    # Build response message
    lang = profile.language
    if lang == "hi":
        msg = f"आपकी प्रोफ़ाइल के आधार पर {len(matched)} योजनाएं मिली हैं।"
    else:
        msg = f"Found {len(matched)} schemes matching your profile."

    if not matched:
        msg = ("कोई योजना नहीं मिली। अधिक जानकारी दें।"
               if lang == "hi"
               else "No schemes matched. Try providing more details like age, income, or occupation.")

    return QueryResponse(
        profile=profile,
        schemes=matched,
        total_matched=total,
        query_lang=lang,
        message=msg,
    )


@app.get("/schemes")
async def list_schemes(category: str = None, state: str = None):
    """Browse all schemes, optionally filtered by category or state."""
    schemes = get_schemes()
    if category:
        schemes = [s for s in schemes if s.get("category", "").lower() == category.lower()]
    if state:
        schemes = [s for s in schemes if s.get("state", "ALL").lower() in (state.lower(), "all")]
    return {"total": len(schemes), "schemes": schemes}


@app.get("/schemes/{scheme_id}")
async def get_scheme(scheme_id: str):
    """Get details of a specific scheme."""
    schemes = get_schemes()
    for s in schemes:
        if s["id"] == scheme_id:
            return s
    raise HTTPException(status_code=404, detail="Scheme not found")
