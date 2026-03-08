# 🏛️ SarkarSaathi: Project Requirements

This document outlines the core functional and non-functional requirements for the SarkarSaathi platform.

## 🎯 Project Objectives

1.  **Inclusivity**: Provide a platform that is usable by all Indian citizens in their preferred language.
2.  **Efficiency**: Enable fast and accurate discovery of government schemes.
3.  **Accuracy**: Ensure profile extraction and scheme matching are reliable and evidence-based.

## ✅ Functional Requirements (FR)

### 1. Multilingual Support
- **FR-1.1**: Support for at least 10 major Indian languages (Hindi, Gujarati, Kannada, Marathi, Tamil, Telugu, Bengali, Punjabi, Malayalam, Urdu).
- **FR-1.2**: Full UI localization (labels, headers, buttons) for each supported language.
- **FR-1.3**: Real-time translation of dynamic content (scheme names, benefits, etc.).

### 2. Conversational Discovery
- **FR-2.1**: AI-powered chatbot capable of extracting profile data from natural dialogue.
- **FR-2.2**: Context-aware reasoning to identify missing profile fields and ask follow-up questions.
- **FR-2.3**: Ability to provide summaries and specific details for matched schemes.

### 3. Profile & Matching
- **FR-3.1**: Extraction of at least 8 demographic fields: **Age, Gender, Occupation, State, Income, Caste, Children, Marital Status**.
- **FR-3.2**: Weighted matching algorithm to find relevant schemes from a database of 1000+ items.
- **FR-3.3**: Highlighting AI-recommended "Best Matches" based on user needs.

### 4. Voice & Accessibility
- **FR-4.1**: Speech-to-Text (STT) for natural voice input in regional languages.
- **FR-4.2**: High-quality Text-to-Speech (TTS) for reading results aloud in the native script.

## ⚙️ Non-Functional Requirements (NFR)

### 1. Performance
- **NFR-1.1**: Initial search results should be returned in under 5 seconds.
- **NFR-1.2**: Parallelized translation of results should complete in under 10 seconds.
- **NFR-1.3**: TTS playback should start within 2 seconds of the user request.

### 2. Scalability
- **NFR-2.1**: Use serverless architecture (AWS Lambda) to handle variable user loads without manual provisioning.
- **NFR-2.2**: DynamoDB for low-latency session and profile data persistence.

### 3. Usability
- **NFR-3.1**: Interface should be clean, high-contrast, and modern (Dark Mode).
- **NFR-3.2**: Minimum interactive elements should have unique IDs for testing and accessibility.

### 4. Availability
- **NFR-4.1**: 99.9% uptime for the primary API.
- **NFR-4.2**: Graceful fallbacks for LLM failures (e.g., OpenRouter as a backup to Bedrock).

---
*Building for impact and reliability.* 🏛️🛡️✅
