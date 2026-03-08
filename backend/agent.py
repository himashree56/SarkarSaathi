"""
SarkarSaathi — Adaptive CoT RAG Agent
Uses AWS Bedrock (Amazon Nova Micro) for intent understanding,
eligibility reasoning, and scheme summarization.
"""
import os
import json
import boto3
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError

from models import UserProfile, SchemeMatch

# ── AWS Configuration ────────────────────────────────────────────────────────
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
NOVA_MODEL_ID = os.environ.get("NOVA_MODEL_ID", "amazon.nova-micro-v1:0")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "512"))  # Budget-conscious limit

_bedrock_client = None


def get_bedrock_client():
    """Lazily initialize the Bedrock runtime client."""
    global _bedrock_client
    if _bedrock_client is None:
        try:
            _bedrock_client = boto3.client(
                "bedrock-runtime",
                region_name=AWS_REGION,
            )
        except NoCredentialsError:
            print("[agent] WARNING: AWS credentials not found. Chat will use fallback mode.")
            _bedrock_client = None
    return _bedrock_client


def _invoke_nova(system_prompt: str, user_message: str) -> str:
    """
    Call Amazon Nova Micro via Bedrock Converse API.
    Returns the model's text response, or a fallback string on error.
    """
    client = get_bedrock_client()
    if client is None:
        return "[AI unavailable — AWS credentials not configured]"

    try:
        response = client.converse(
            modelId=NOVA_MODEL_ID,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_message}]}],
            inferenceConfig={
                "maxTokens": MAX_TOKENS,
                "temperature": 0.4,
                "topP": 0.9,
            },
        )
        return response["output"]["message"]["content"][0]["text"]
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        print(f"[agent] Bedrock ClientError: {error_code}")
        return f"[Error calling AI service: {error_code}]"
    except Exception as e:
        print(f"[agent] Unexpected error: {e}")
        return "[Unexpected error calling AI service]"


# ── System Prompts ───────────────────────────────────────────────────────────

_CHAT_SYSTEM_PROMPT = """You are SarkarSaathi, a helpful Indian government scheme assistant.
Your role is to help citizens find and understand government welfare schemes they are eligible for.

Guidelines:
- Be warm, clear, and empathetic. Use simple language.
- Always respond in the SAME language the user writes in (Hindi or English).
- If the user writes in Hindi (Devanagari script), respond entirely in Hindi.
- If information about schemes is provided, refer to it directly.
- Guide users step-by-step using chain-of-thought reasoning:
  1. Understand the user's situation
  2. Identify the most relevant schemes
  3. Explain WHY they are eligible
  4. Give clear next steps
- Keep responses concise and actionable (2-4 sentences unless more detail is asked).
- Never make up schemes or benefits. Only reference what is provided."""


_SUMMARIZER_SYSTEM_PROMPT = """You are a government scheme advisor for Indian citizens.
Given a user's profile and a list of matching government schemes, write a personalized recommendation summary.

Your summary MUST:
1. Highlight the SINGLE best scheme for the user with a clear explanation of why
2. Briefly mention 2-3 other relevant schemes
3. Be written in the user's preferred language (Hindi or English)
4. Be concise — no more than 150 words
5. Include a clear call-to-action (e.g., visit website, go to nearest office)

Format: Plain text, no markdown, conversational tone."""


# ── Core Agent Functions ─────────────────────────────────────────────────────

def generate_chat_response(
    user_message: str,
    profile: Optional[UserProfile],
    matched_schemes: List[SchemeMatch],
    conversation_history: List[Dict[str, str]],
    language: str = "en",
) -> str:
    """
    Adaptive CoT RAG: Given user message + context, produce a conversational reply.
    Injects top matched schemes as RAG context into the prompt.
    """
    # Build RAG context from top 3 schemes
    scheme_context = ""
    if matched_schemes:
        top_3 = matched_schemes[:3]
        scheme_lines = []
        for i, scheme in enumerate(top_3, 1):
            name = scheme.name_hi if language == "hi" else scheme.name_en
            scheme_lines.append(
                f"{i}. {name} — {scheme.benefit_description} "
                f"(Eligibility: {scheme.eligibility_reason})"
            )
        scheme_context = "\n\nTop matching schemes for this user:\n" + "\n".join(scheme_lines)

    # Build profile context
    profile_context = ""
    if profile:
        parts = []
        if profile.age:
            parts.append(f"Age: {profile.age}")
        if profile.gender:
            parts.append(f"Gender: {profile.gender}")
        if profile.occupation:
            parts.append(f"Occupation: {profile.occupation}")
        if profile.income_level:
            parts.append(f"Income: ₹{profile.income_level:,}/year")
        if profile.state:
            parts.append(f"State: {profile.state}")
        if profile.caste:
            parts.append(f"Category: {profile.caste.upper()}")
        if profile.needs:
            parts.append(f"Needs: {', '.join(profile.needs)}")
        if parts:
            profile_context = "\n\nUser profile: " + " | ".join(parts)

    # Build history context (last 4 turns to save tokens)
    history_context = ""
    if conversation_history:
        recent = conversation_history[-4:]
        history_lines = []
        for turn in recent:
            role = "User" if turn["role"] == "user" else "Assistant"
            history_lines.append(f"{role}: {turn['content']}")
        history_context = "\n\nConversation history:\n" + "\n".join(history_lines)

    full_user_message = (
        f"User query: {user_message}"
        f"{profile_context}"
        f"{scheme_context}"
        f"{history_context}"
    )

    return _invoke_nova(_CHAT_SYSTEM_PROMPT, full_user_message)


def generate_summary(
    profile: UserProfile,
    matched_schemes: List[SchemeMatch],
    language: str = "en",
) -> str:
    """
    Summarizer: Produces AI-generated personalized scheme recommendation.
    Highlights the #1 best scheme with reasoning.
    """
    if not matched_schemes:
        if language == "hi":
            return "आपकी प्रोफ़ाइल के लिए कोई योजना नहीं मिली। कृपया अधिक जानकारी दें जैसे आयु, आय, और व्यवसाय।"
        return "No schemes found for your profile. Please provide more details like age, income, and occupation."

    # Build scheme list for summarizer
    scheme_lines = []
    for i, scheme in enumerate(matched_schemes[:5], 1):
        name = scheme.name_hi if language == "hi" else scheme.name_en
        scheme_lines.append(
            f"{i}. {name}\n"
            f"   Benefit: {scheme.benefit_description}\n"
            f"   Why eligible: {scheme.eligibility_reason}\n"
            f"   Apply at: {scheme.how_to_apply}"
        )

    # Build profile summary
    profile_parts = []
    if profile.age:
        profile_parts.append(f"age {profile.age}")
    if profile.gender:
        profile_parts.append(profile.gender)
    if profile.occupation:
        profile_parts.append(profile.occupation)
    if profile.state:
        profile_parts.append(f"from {profile.state}")
    if profile.income_level:
        profile_parts.append(f"income ₹{profile.income_level:,}/year")
    if profile.caste:
        profile_parts.append(f"{profile.caste.upper()} category")

    profile_desc = ", ".join(profile_parts) if profile_parts else "a citizen"
    lang_instruction = "Respond in Hindi (Devanagari script)." if language == "hi" else "Respond in English."

    user_message = (
        f"User profile: {profile_desc}\n\n"
        f"Matching schemes:\n" + "\n".join(scheme_lines) + f"\n\n{lang_instruction}"
    )

    return _invoke_nova(_SUMMARIZER_SYSTEM_PROMPT, user_message)


def detect_language(text: str) -> str:
    """Simple heuristic: detect Hindi by checking for Devanagari characters."""
    devanagari_count = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    return "hi" if devanagari_count > 2 else "en"
