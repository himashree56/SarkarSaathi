# 🏛️ SarkarSaathi: Operational Flow

This document details the step-by-step logic for the primary user flows: **Search**, **Conversational Chat**, and **Text-to-Speech**.

## 1. Scheme Search Flow (`/query`)

The search flow is triggered when a user enters their details on the landing page.

1.  **Request**: User submits a query (e.g., "I am 25, male, unemployed in Kerala").
2.  **Normalization**: Backend resolves the target language (defaulting to English if not specified).
3.  **Extraction**: 
    - Rule-based regex extracts basic facts.
    - Claude 3 Haiku performs a deeper extraction for nuanced details.
4.  **Matching**: System identifies Top 6 schemes from the database based on the extracted profile.
5.  **Parallel Translation**: 
    - The results are split into parallel tasks.
    - Claude 3 Haiku translates name, benefits, and eligibility in real-time.
    - **SYNC**: Regional name fields (`name_hi`, `name_kn`, etc.) are synchronized to prevent English leakage.
6.  **Response**: Results are returned to the frontend for rendering.

## 2. Conversational Chat Flow (`/chat`)

The chatbot helps users clarify their profile and understand scheme details.

1.  **Message**: User sends a message (e.g., "I have 0 children").
2.  **Context Loading**: History (last 10 turns) and existing profile are retrieved from DynamoDB.
3.  **Inference**: 
    - `_infer_from_context` checks if the user is answering a previous bot question.
    - **Fix**: Explicit `None` checks ensure **0** is recognized as a valid answer, not a missing field.
4.  **Bot Reasoning**: Amazon Nova Micro uses Chain-of-Thought (CoT) to:
    - Acknowledge the user's input.
    - Decide if enough information is present to show schemes.
    - Ask for exactly **one** missing piece of info if the profile is incomplete.
5.  **State Persistence**: Updated profile and history are saved back to DynamoDB.
6.  **Response**: The bot replies in the user's chosen language with localized content.

## 3. High-Quality Text-to-Speech Flow (`/tts`)

Used for reading scheme details aloud in the native language.

1.  **Request**: Frontend sends the regional text and language code (e.g., "kn").
2.  **Transliteration**: Bedrock (Haiku) converts the regional script into **Romanized Phonetic English**. 
3.  **Synthesis**: The Romanized text is sent to AWS Polly using the **Kajal (Neural)** voice. 
    - *Why?* Kajal excels at pronouncing Romanized Indian terms with natural inflection.
4.  **Playback**: The base64-encoded mp3 is returned and played instantly in the browser.

---
*Ensuring a smooth, intelligent journey for every user.* 🏛️🧬✨
