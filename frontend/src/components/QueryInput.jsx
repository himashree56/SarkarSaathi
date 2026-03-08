import { useState } from 'react'

const EXAMPLES = [
    { label: '🌾 Farmer (EN)', text: 'I am a 50 year old male farmer from rural Maharashtra, annual income 80000 rupees' },
    { label: '📚 Student (EN)', text: 'I am a 19 year old SC student looking for scholarship for higher education, income 1.5 lakh' },
    { label: '🏠 Widow (HI)', text: 'मैं 45 साल की विधवा हूं, गांव में रहती हूं, 2 बच्चे हैं, सालाना आमदनी 60 हजार' },
    { label: '💼 Unemployed (HI)', text: 'मैं बेरोजगार हूं, शहर में रहता हूं, मुझे घर चाहिए, आय 1.5 लाख' },
]

export default function QueryInput({ query, setQuery, onSubmit, loading, voiceLang }) {
    const [isListening, setIsListening] = useState(false)

    // Map selected UI language → BCP-47 for SpeechRecognition
    const LANG_MAP = {
        'English': 'en-IN',
        'Hindi': 'hi-IN',
        'Marathi': 'mr-IN',
        'Bengali': 'bn-IN',
        'Tamil': 'ta-IN',
        'Telugu': 'te-IN',
        'Gujarati': 'gu-IN',
        'Kannada': 'kn-IN',
    }

    function toggleListening() {
        if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
            alert("Speech recognition is not supported in this browser.")
            return
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
        const recognition = new SpeechRecognition()

        // Use the selected UI language, defaulting to Indian English
        recognition.lang = LANG_MAP[voiceLang] || 'en-IN'
        recognition.continuous = false
        recognition.interimResults = false

        recognition.onstart = () => setIsListening(true)
        recognition.onend = () => setIsListening(false)
        recognition.onerror = () => setIsListening(false)

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript
            setQuery(prev => prev ? `${prev} ${transcript}` : transcript)
        }

        if (isListening) {
            recognition.stop()
        } else {
            recognition.start()
        }
    }
    function handleChip(text) {
        setQuery(text)
        onSubmit(text)
    }

    return (
        <div className="query-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <p className="query-label" style={{ margin: 0 }}>📝 Describe Your Situation</p>
                <button
                    className={`voice-btn ${isListening ? 'listening' : ''}`}
                    onClick={toggleListening}
                    title="Speak your query"
                    type="button"
                >
                    {isListening ? '🛑' : '🎤'}
                </button>
            </div>

            <textarea
                className="query-textarea"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) onSubmit() }}
                placeholder={
                    'Example: "I am a 45 year old widow living in a village in Rajasthan, with 2 children and an annual income of ₹60,000. I need housing assistance."\n\n' +
                    'या हिंदी में: "मैं 45 साल की विधवा हूं, राजस्थान के गांव में रहती हूं..."'
                }
                disabled={loading}
            />

            <div className="example-chips">
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', alignSelf: 'center' }}>Try:</span>
                {EXAMPLES.map(ex => (
                    <button key={ex.label} className="chip" onClick={() => handleChip(ex.text)} disabled={loading}>
                        {ex.label}
                    </button>
                ))}
            </div>

            <button
                className="submit-btn"
                onClick={() => onSubmit()}
                disabled={loading || !query.trim()}
            >
                {loading ? (
                    <>
                        <span className="spinner" />
                        Analyzing your profile...
                    </>
                ) : (
                    <>🔍 Find My Eligible Schemes</>
                )}
            </button>
        </div>
    )
}
