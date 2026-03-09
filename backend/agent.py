"""
SarkarSaathi — ReAct Agent Loop
Uses AWS Bedrock (Amazon Nova Micro) for intent understanding, tools calling,
eligibility reasoning, and scheme summarization.
"""
import os
import json
import re
import boto3
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError

from models import UserProfile, SchemeMatch

# ── AWS Configuration ────────────────────────────────────────────────────────
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
NOVA_MODEL_ID = os.environ.get("NOVA_MODEL_ID", "amazon.nova-micro-v1:0")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))

_bedrock_client = None


def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        try:
            _bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        except NoCredentialsError:
            print("[agent] WARNING: AWS credentials not found. Chat will use fallback mode.")
    return _bedrock_client


def _invoke_nova(system_prompt: str, user_message: str, stop_sequences: List[str] = None) -> str:
    client = get_bedrock_client()
    if client is None:
        return "Final Answer: [AI unavailable — AWS credentials not configured]"

    inference_config = {
        "maxTokens": MAX_TOKENS,
        "temperature": 0.4,
        "topP": 0.9,
    }
    if stop_sequences:
        inference_config["stopSequences"] = stop_sequences

    try:
        response = client.converse(
            modelId=NOVA_MODEL_ID,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_message}]}],
            inferenceConfig=inference_config,
        )
        return response["output"]["message"]["content"][0]["text"]
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        print(f"[agent] Bedrock ClientError: {error_code}")
        return f"Final Answer: [Error calling AI service: {error_code}]"
    except Exception as e:
        print(f"[agent] Unexpected error: {e}")
        return "Final Answer: [Unexpected error calling AI service]"


# ── System Prompts ───────────────────────────────────────────────────────────

_REACT_SYSTEM_PROMPT = """You are SarkarSaathi, a helpful Indian government scheme assistant.
You solve tasks using a Reasoning and Acting (ReAct) loop.

You have access to the following tools:

1. ask_user(question: str): Ask the user a clarifying question or ask for their PII consent.
2. check_eligibility(): You have already been provided the user's profile and matching schemes in the context. Use this tool when you have enough profile information (like age, income, state, caste) to give scheme recommendations to the user based on the context.
3. record_consent(): Use this when the user explicitly agrees to share their information.

You must follow this exact format:

Thought: [Consider the current state, missing profile information, consent status, etc.]
Action: [The name of the tool to use: 'ask_user', 'check_eligibility', or 'record_consent']
Action Input: [The input string for the tool, if applicable. Leave blank if not]
Observation: [The result of the action - this will be provided by the system]
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now have the final answer.
Final Answer: [The final response to send to the user, in Hindi or English, based on their language.]

CRITICAL RULES:
- The user MUST give explicit consent before you can process their caste, income, or other sensitive data. If `consent_given` is False, your FIRST action must be to ask for their consent using `ask_user`.
- Once they consent, use `record_consent`.
- Provide the final answer in the exact same language the user requested. If Hindi (Devanagari), respond in Hindi.
- If there are 0 schemes returned from `check_eligibility`, you MUST handle this gracefully in the Final Answer, empathetically telling them there are no specific schemes right now, but offering general advice.
"""

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
    Executes the ReAct Agent loop to formulate a response.
    """
    # Context Assembly
    profile_context = ""
    if profile:
        parts = []
        if profile.age: parts.append(f"Age: {profile.age}")
        if profile.gender: parts.append(f"Gender: {profile.gender}")
        if profile.occupation: parts.append(f"Occupation: {profile.occupation}")
        if profile.income_level: parts.append(f"Income: \u20b9{profile.income_level:,}/year")
        if profile.state: parts.append(f"State: {profile.state}")
        if profile.caste: parts.append(f"Category: {profile.caste.upper()}")
        parts.append(f"Consent Given: {profile.consent_given}")
        profile_context = "\n\nUser profile: " + " | ".join(parts)

    scheme_context = ""
    if matched_schemes:
        scheme_lines = []
        for i, scheme in enumerate(matched_schemes[:5], 1):
            name = scheme.name_hi if language == "hi" else scheme.name_en
            scheme_lines.append(f"{i}. {name} — {scheme.benefit_description} (Why: {scheme.eligibility_reason})")
        scheme_context = "\n\nAvailable matching schemes:\n" + "\n".join(scheme_lines)
    else:
        scheme_context = "\n\nAvailable matching schemes: NONE (0 eligible schemes found)."

    history_context = ""
    if conversation_history:
        recent = conversation_history[-4:]
        history_lines = [f"{'User' if t['role']=='user' else 'Assistant'}: {t['content']}" for t in recent]
        history_context = "\n\nConversation history:\n" + "\n".join(history_lines)

    # ReAct Loop
    prompt_context = f"User query: {user_message}{profile_context}{scheme_context}{history_context}\n\n"
    
    max_steps = 4
    for step in range(max_steps):
        # We stop the generation when it attempts to wait for an Observation
        response = _invoke_nova(_REACT_SYSTEM_PROMPT, prompt_context, stop_sequences=["Observation:"])
        
        prompt_context += response + "\n"
        
        # Check if it reached a final answer
        if "Final Answer:" in response:
            final_answer = response.split("Final Answer:", 1)[1].strip()
            return final_answer
        
        # Extract Action and Action Input
        action_match = re.search(r"Action:\s*(.*)", response)
        input_match = re.search(r"Action Input:\s*(.*)", response)
        
        if not action_match:
            # Malformed generation, fallback
            return "Final Answer: Error processing request."
            
        action = action_match.group(1).strip()
        action_input = input_match.group(1).strip() if input_match else ""
        
        observation = ""
        # Mocking Tool Executions
        if action == "ask_user":
            # The agent decided to ask a question, we just return this directly as the final answer
            return action_input
            
        elif action == "check_eligibility":
            if matched_schemes:
                observation = f"Found {len(matched_schemes)} schemes. Ready to provide final answer."
            else:
                observation = "0 schemes found. Must handle rejection gracefully in Final Answer."
                
        elif action == "record_consent":
            # Here we would theoretically update the reference, but for the prompt context we just inject success
            if profile:
                profile.consent_given = True
            observation = "Consent successfully recorded."
            
        else:
            observation = f"Tool '{action}' not found."

        prompt_context += f"Observation: {observation}\n"

    return "मुझे क्षमा करें, मैं आपके अनुरोध पर प्रक्रिया नहीं कर सका।" if language == "hi" else "I apologize, but I could not process your request at this time."


def generate_summary(profile: UserProfile, matched_schemes: List[SchemeMatch], language: str = "en") -> str:
    if not matched_schemes:
        return "आपकी प्रोफ़ाइल के लिए कोई योजना नहीं मिली।" if language == "hi" else "No schemes found for your profile."

    scheme_lines = []
    for i, s in enumerate(matched_schemes[:5], 1):
        name = s.name_hi if language == "hi" else s.name_en
        scheme_lines.append(f"{i}. {name}\n   Benefit: {s.benefit_description}\n   Why eligible: {s.eligibility_reason}\n   Apply at: {s.how_to_apply}")

    profile_parts = []
    if profile.age: profile_parts.append(f"age {profile.age}")
    if profile.income_level: profile_parts.append(f"income \u20b9{profile.income_level:,}/year")
    profile_desc = ", ".join(profile_parts) if profile_parts else "a citizen"
    lang_instruction = "Respond in Hindi (Devanagari script)." if language == "hi" else "Respond in English."

    user_message = f"User profile: {profile_desc}\n\nMatching schemes:\n" + "\n".join(scheme_lines) + f"\n\n{lang_instruction}"
    return _invoke_nova(_SUMMARIZER_SYSTEM_PROMPT, user_message)


def detect_language(text: str) -> str:
    devanagari_count = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    return "hi" if devanagari_count > 2 else "en"


import time
import random

def translate_single_scheme(s_dict: dict, target_lang_name: str) -> dict:
    system_prompt = f"You are a professional translator for the Government of India. Translate the provided scheme details into {target_lang_name}."
    
    # We remove 'id' from translation payload to simplify it for the LLM
    s_id = s_dict.pop("id", "")
    
    user_prompt = f"""
Translate the following JSON object's values into {target_lang_name}. 
Keep the exact same JSON structure and keys (name, benefit_description, eligibility_reason, how_to_apply).
Return ONLY valid JSON and nothing else. Do NOT WRAP IN MARKDOWN BACKTICKS.

{json.dumps(s_dict, ensure_ascii=False)}
"""
    for attempt in range(4):
        try:
            response_text = _invoke_nova(system_prompt, user_prompt)
            response_text = response_text.strip()
            
            # Clean up potential markdown formatting that Nova might add
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
                
            return {"id": s_id, "translated": json.loads(response_text)}
        except Exception as e:
            print(f"[translation] Error translating scheme {s_id} on attempt {attempt+1}: {e}")
            # Exponential backoff with jitter to avoid thundering herd on rate limits
            sleep_time = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(sleep_time)
            
    return {"id": s_id, "translated": None}

def translate_schemes_to_lang(schemes: List[SchemeMatch], target_lang_code: str) -> List[SchemeMatch]:
    if target_lang_code in ["en", "hi"] or not schemes:
        return schemes

    LANG_MAP = {
        'gu': 'Gujarati', 'mr': 'Marathi', 'ta': 'Tamil', 'te': 'Telugu',
        'bn': 'Bengali', 'kn': 'Kannada', 'ur': 'Urdu', 'ml': 'Malayalam'
    }
    lang_name = LANG_MAP.get(target_lang_code, target_lang_code)

    payloads = []
    for s in schemes:
        payloads.append({
            "id": s.id,
            "name": s.name_en,
            "benefit_description": s.benefit_description,
            "eligibility_reason": s.eligibility_reason,
            "how_to_apply": s.how_to_apply
        })

    trans_map = {}
    
    for p in payloads:
        res = translate_single_scheme(p, lang_name)
        if res["translated"]:
            trans_map[res["id"]] = res["translated"]
        
    for s in schemes:
        if s.id in trans_map:
            t = trans_map[s.id]
            s.name_en = t.get("name", s.name_en) # Trick UI into using translated name
            s.benefit_description = t.get("benefit_description", s.benefit_description)
            s.eligibility_reason = t.get("eligibility_reason", s.eligibility_reason)
            s.how_to_apply = t.get("how_to_apply", s.how_to_apply)

    return schemes
