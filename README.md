# 🏛️ SarkarSaathi: Multilingual AI Government Scheme Assistant

SarkarSaathi is a sophisticated, AI-driven platform designed to bridge the gap between citizens and government schemes in India. By leveraging cutting-edge Large Language Models (LLMs) and a robust cloud architecture, it provides a seamless, multilingual experience for discovering and understanding eligible benefits.

## 🚀 Key Features

- **Multilingual Search**: Support for 10+ Indian languages (Hindi, Gujarati, Kannada, Marathi, Tamil, Telugu, Bengali, Punjabi, Malayalam, Urdu).
- **Conversational AI Chatbot**: An adaptive, context-aware chatbot that helps users identify eligible schemes through natural dialogue.
- **Automated Profile Extraction**: Intelligent extraction of user demographics (age, income, location, etc.) from natural language queries.
- **High-Quality Text-to-Speech (TTS)**: Realistic voice output using AWS Polly with Romanized transliteration for natural-sounding regional speech.
- **Real-time Translation**: Instant translation of scheme details, benefits, and eligibility criteria while maintaining original English context for accuracy.
- **Dynamic Localization**: 100% localized UI labels and headers across the entire platform.
- **Fast & Scalable**: Powered by AWS Lambda with parallel processing for low-latency translations.

## 🛠️ Technology Stack

### Frontend
- **Framework**: React.js (Vite)
- **Styling**: Vanilla CSS (Modern, premium dark-mode aesthetic)
- **State Management**: React Hooks (useState, useEffect)
- **Voice**: Native Web Speech API & AWS Polly Integration

### Backend (AWS Serverless)
- **Compute**: AWS Lambda (Python)
- **API Gateway**: HTTP API for low-latency communication
- **AI/LLM**: 
  - **Amazon Bedrock**: Anthropic Claude 3 Haiku (Extraction/Translation), Amazon Nova Micro (Chatbot)
  - **OpenRouter**: Fallback for high availability
- **Database**: Amazon DynamoDB (Session & Profile persistence)
- **Storage**: Amazon S3 (Frontend hosting)
- **CDN**: Amazon CloudFront (Global delivery & HTTPS)

## 📂 Project Structure

- `frontend/`: React source code and assets.
- `aws/`: Lambda function logic, deployment scripts, and OpenAPI specifications.
- `backend/`: Supporting scripts for database management and agent interactions.
- `data/`: Seed data and scheme JSON exports.

---
*Empowering every citizen with the right information, in their own language.* 🏛️🌍✨
