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
- **Micro-animations**: Smooth transitions (`0.3s ease`) when switching tabs or hovering over schemes.
- **Responsive Layout**: A mobile-first approach ensuring the chatbot and scheme results are stackable on smaller screens.

## 🗣️ Voice-First UX
The design acknowledges that many users prefer speaking over typing:
- **Prominent Mic Icon**: Located centrally in the chat input.
- **Visual Feedback**: Audio-visualizers or pulse animations during TTS playback to indicate activity.

---
*Designing for the next billion users.* 🏛️🖌️✨
