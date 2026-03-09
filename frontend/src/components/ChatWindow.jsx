import { useState, useRef, useEffect, useCallback } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/* ── TTS (AWS Polly) ───────────────────────────────────────── */
function speak(text, lang, user, onEnd) {
    if (!text || !window.speechSynthesis) { onEnd?.(); return }

    window.speechSynthesis.cancel() // Stop any previous speech
    const clean = text.replace(/[*_#\-•→]/g, '').replace(/\s+/g, ' ').trim()
    const utt = new SpeechSynthesisUtterance(clean)

    const browserLangMap = {
        hi: 'hi-IN', en: 'en-IN', mr: 'mr-IN', bn: 'bn-IN',
        ta: 'ta-IN', te: 'te-IN', gu: 'gu-IN', kn: 'kn-IN',
        ur: 'ur-PK', ml: 'ml-IN'
    }
    const targetLang = browserLangMap[lang] || 'en-IN'
    utt.lang = targetLang
    utt.rate = 0.95
    utt.pitch = 1.0

    // Target high-quality Google voices
    const voices = window.speechSynthesis.getVoices()
    const bestVoice = voices.find(v => v.lang === targetLang && v.name.includes('Google'))
        || voices.find(v => v.lang === targetLang)
        || voices.find(v => v.lang.startsWith(targetLang.split('-')[0]))

    if (bestVoice) utt.voice = bestVoice
    if (onEnd) utt.onend = onEnd
    utt.onerror = () => onEnd?.()

    window.speechSynthesis.speak(utt)
}

/* ── STT ─────────────────────────────────────────────────────── */
function startListening(lang, onResult, onEnd) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) {
        console.error("Speech Recognition not supported")
        return null
    }
    const rec = new SR()
    const sttLangMap = {
        hi: 'hi-IN', en: 'en-IN', te: 'te-IN', ta: 'ta-IN',
        mr: 'mr-IN', gu: 'gu-IN', kn: 'kn-IN', bn: 'bn-IN',
        ml: 'ml-IN', ur: 'ur-PK'
    }
    rec.lang = sttLangMap[lang] || 'en-IN'
    rec.interimResults = false
    rec.onresult = e => onResult(e.results[0][0].transcript)
    rec.onerror = () => onEnd?.()
    rec.onend = () => onEnd?.()
    rec.start()
    return rec
}

/* ── Bubble ──────────────────────────────────────────────────── */
function Bubble({ msg, onSpeak }) {
    const isUser = msg.role === 'user'
    return (
        <div className={`cp-row ${isUser ? 'cp-user-row' : 'cp-bot-row'}`}>
            {!isUser && <div className="cp-avatar">🏛️</div>}
            <div className={`cp-bubble ${isUser ? 'cp-bubble-user' : 'cp-bubble-bot'}`}>
                <div className="cp-bubble-text">{msg.content}</div>
                {!isUser && (
                    <div className="cp-bubble-actions">
                        <button className="cp-action-btn" onClick={() => onSpeak(msg.content)}>🔊</button>
                    </div>
                )}
            </div>
        </div>
    )
}

/* ── ModeSelector ────────────────────────────────────────────── */
function ModeSelector({ mode, onChange }) {
    return (
        <div className="cp-mode-bar">
            <button className={`cp-mode-btn ${mode === 'text' ? 'active' : ''}`} onClick={() => onChange('text')}>💬 Text</button>
            <button className={`cp-mode-btn ${mode === 'voice' ? 'active' : ''}`} onClick={() => onChange('voice')}>🎙️ Voice</button>
        </div>
    )
}

/* ── VoiceOrb ────────────────────────────────────────────────── */
function VoiceOrb({ state }) {
    const labels = { idle: 'Tap to start', listening: 'Listening...', thinking: 'Thinking...', speaking: 'Speaking...' }
    const icons = { idle: '🎤', listening: '🎙️', thinking: '⏳', speaking: '🔊' }
    return (
        <div className="voice-orb-wrap">
            <div className={`voice-orb voice-orb-${state}`}><span className="voice-orb-icon">{icons[state]}</span></div>
            <div className="voice-orb-label">{labels[state]}</div>
        </div>
    )
}

/* ── Profile summary bar ─────────────────────────────────────── */
function ProfileBar({ profile }) {
    if (!profile) return null
    const fields = []
    if (profile.age) fields.push(`${profile.age}y`)
    if (profile.gender) fields.push(profile.gender)
    if (profile.occupation) fields.push(profile.occupation)
    if (profile.state) fields.push(profile.state)
    if (fields.length === 0) return null
    return (
        <div className="cp-profile-bar">
            <span className="cp-profile-label">📋 Known:</span>
            <span className="cp-profile-pills">{fields.join(' · ')}</span>
        </div>
    )
}

/* ── ChatWindow ──────────────────────────────────────────────── */
export default function ChatWindow({
    user,
    selectedLang,
    onClose,
    initialProfile,
    initialSessionId,
    initialSchemes,
    onSessionUpdate
}) {
    // `selectedLang` is already the ISO code (e.g. 'hi', 'te', 'en')
    const [localLang, setLocalLang] = useState(selectedLang || 'en')
    useEffect(() => {
        if (selectedLang && selectedLang !== localLang) {
            setLocalLang(selectedLang);
        }
    }, [selectedLang, localLang])
    const lang = localLang

    // Build a generic opener greeting
    const buildOpener = () => {
        const msgs = {
            'hi': 'नमस्ते! मैं SarkarSaathi हूँ। मैं आपको सरकारी योजनाओं की जानकारी देने में कैसे मदद कर सकता हूँ?',
            'gu': 'નમસ્તે! હું રસરકારસાથી છું. હું તમને સરકારી યોજનાઓ વિશે જાણવામાં કેવી રીતે મદદ કરી શકું?',
            'te': 'నమస్కారం! నేను SarkarSaathi ని. ఈ రోజు ప్రభుత్వ పథకాలను తెలుసుకోవడంలో మరియు అర్థం చేసుకోవడంలో నేను మీకు ఎలా సహాయపడగలను?',
            'mr': 'नमस्कार! मी SarkarSaathi आहे. आज मी तुम्हाला सरकारी योजना शोधण्यात आणि समजून घेण्यात कशी मदत करू शकेन?',
            'bn': 'নমস্কার! আমি SarkarSaathi। আজ আমি আপনাকে কীভাবে সরকারি প্রকল্পগুলি আবিষ্কার করতে এবং বুঝতে সাহায্য করতে পারি?',
            'ta': 'வணக்கம்! நான் SarkarSaathi. இன்று அரசாங்க திட்டங்களை கண்டறியவும் புரிந்துகொள்ளவும் நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?',
            'kn': 'ನಮಸ್ಕಾರ! ನಾನು SarkarSaathi. ಇಂದು ಸರ್ಕಾರಿ ಯೋಜನೆಗಳನ್ನು ಅನ್ವೇಷಿಸಲು ಮತ್ತು ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?',
            'ml': 'നമസ്കാരം! ഞാൻ SarkarSaathi ആണ്. ഇന്ന് സർക്കാർ പദ്ധതികൾ കണ്ടെത്താനും മനസ്സിലാക്കാനും എനിക്ക് നിങ്ങളെ എങ്ങനെ സഹായിക്കാനാകും?',
            'ur': 'ہیلو! میں SarkarSaathi ہوں. آج میں آپ کو سرکاری اسکیموں کو دریافت کرنے اور سمجھنے میں کس طرح مدد کرسکتا ہوں؟',
        };
        return msgs[lang] || "Hi! I'm SarkarSaathi. How can I help you discover and understand government schemes today?";
    }

    const [mode, setMode] = useState('text')
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [sessionId, setSessionId] = useState(initialSessionId || null)
    const [schemes, setSchemes] = useState(initialSchemes || [])
    const [summary, setSummary] = useState(null)
    const [schemesOpen, setSchemesOpen] = useState(false)
    const [summaryOpen, setSummaryOpen] = useState(false)

    // SESSION SYNC: Reset copilot when user clicks a history item
    useEffect(() => {
        setSessionId(initialSessionId || null)
        setSchemes(initialSchemes || [])
        setSummary(initialProfile?.summary || null)

        // Use historical messages if they exist, otherwise show default opener
        if (initialSessionId && Array.isArray(initialProfile?.history) && initialProfile.history.length > 0) {
            setMessages(initialProfile.history)
        } else {
            setMessages([{ role: 'bot', content: buildOpener() }])
        }
    }, [initialSessionId])

    // Auto-update the opener if the user hasn't typed anything yet and changes the language
    useEffect(() => {
        setMessages(prev => {
            if (prev.length === 1 && prev[0].role === 'bot') {
                return [{ role: 'bot', content: buildOpener() }]
            }
            return prev
        })
    }, [lang])

    const [voiceState, setVoiceState] = useState('idle')
    const recRef = useRef(null)
    const bottomRef = useRef(null)
    const textareaRef = useRef(null)
    const voiceLoopRef = useRef(false)

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, loading])

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 130) + 'px'
        }
    }, [input])

    useEffect(() => {
        if (mode === 'voice') {
            voiceLoopRef.current = true
            const lastBot = [...messages].reverse().find(m => m.role === 'bot')
            if (lastBot) {
                setVoiceState('speaking')
                speak(lastBot.content, lang, user, () => { if (voiceLoopRef.current) listenNext() })
            }
            else listenNext()
        } else {
            voiceLoopRef.current = false
            recRef.current?.stop()
            setVoiceState('idle')
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [mode])

    // ── Core send ──────────────────────────────────────────────
    const callChat = useCallback(async (msg) => {
        if (!msg.trim() || loading) return null
        setLoading(true)
        try {
            const res = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(user ? { Authorization: `Bearer ${user.accessToken}` } : {}),
                },
                body: JSON.stringify({
                    message: msg,
                    session_id: sessionId,
                    language: lang,
                    include_summary: schemes.length === 0,
                    // Pass initial profile so backend doesn't ask for known info
                    known_profile: initialProfile || undefined,
                }),
            })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            const data = await res.json()
            if (data.session_id) setSessionId(data.session_id)
            if (data.summary) setSummary(data.summary)
            if (data.schemes?.length) setSchemes(data.schemes)

            // Propagate up to main ResultsDashboard
            if (onSessionUpdate) {
                onSessionUpdate({
                    session_id: data.session_id || sessionId,
                    profile: data.profile || initialProfile,
                    schemes: data.schemes || schemes,
                    summary: data.summary || summary,
                    recommended_id: data.recommended_id,
                    history: [...messages, { role: 'user', content: msg }, { role: 'bot', content: data.response }],
                    last_query: data.last_query,
                    message: data.message,
                    title: data.title
                })
            }

            return data.response
        } catch (e) {
            return 'Sorry, something went wrong. Please try again.'
        } finally {
            setLoading(false)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sessionId, lang, schemes.length, user, initialProfile])

    const sendMessage = useCallback(async (text) => {
        const msg = (text ?? input).trim()
        if (!msg || loading) return
        setInput('')
        setMessages(prev => [...prev, { role: 'user', content: msg }])
        const reply = await callChat(msg)
        if (reply) {
            setMessages(prev => [...prev, { role: 'bot', content: reply }])
            if (mode === 'voice' && voiceLoopRef.current) {
                setVoiceState('speaking')
                speak(reply, lang, user, () => { if (voiceLoopRef.current) listenNext() })
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [input, callChat, lang, mode, user])

    function listenNext() {
        if (!voiceLoopRef.current) return
        setVoiceState('listening')
        recRef.current = startListening(lang, async (t) => {
            setVoiceState('thinking')
            setMessages(prev => [...prev, { role: 'user', content: t }])
            recRef.current = null
            const reply = await callChat(t)
            if (reply) {
                setMessages(prev => [...prev, { role: 'bot', content: reply }])
                if (voiceLoopRef.current) {
                    setVoiceState('speaking')
                    speak(reply, lang, user, () => { if (voiceLoopRef.current) listenNext() })
                }
            }
        }, () => setVoiceState('idle'))
    }

    function handleKey(e) {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
    }

    function clearChat() {
        voiceLoopRef.current = false
        recRef.current?.stop()
        setMessages([{ role: 'bot', content: buildOpener(initialProfile) }])
        setSessionId(initialSessionId || null)
        setSchemes(initialSchemes || [])
        setSummary(null); setSchemesOpen(false); setSummaryOpen(false)
        setVoiceState('idle')
    }

    function handleManualMic() {
        if (voiceState === 'listening') { recRef.current?.stop(); setVoiceState('idle'); return }
        setVoiceState('listening')
        recRef.current = startListening(lang, (t) => { setInput(t); setVoiceState('idle') }, () => setVoiceState('idle'))
    }

    return (
        <div className="copilot-panel">
            <div className="cp-header">
                <div className="cp-header-brand">
                    <div className="cp-header-title">
                        <div className="cp-header-main">
                            <span className="cp-header-icon">🏛️</span>
                            SarkarSaathi AI
                        </div>
                        <div className="cp-header-sub">Powered by Claude</div>
                    </div>
                </div>
                <div className="cp-header-actions">
                    <select
                        className="cp-lang-select"
                        value={localLang}
                        onChange={e => setLocalLang(e.target.value)}
                        title="Chat Language"
                    >
                        <option value="en">English</option>
                        <option value="hi">हिंदी (Hindi)</option>
                        <option value="te">తెలుగు (Telugu)</option>
                        <option value="ta">தமிழ் (Tamil)</option>
                        <option value="mr">मराठी (Marathi)</option>
                        <option value="gu">ગુજરાતી (Gujarati)</option>
                        <option value="kn">ಕನ್ನಡ (Kannada)</option>
                        <option value="bn">বাংলা (Bengali)</option>
                        <option value="ml">മലയാളം (Malayalam)</option>
                        <option value="ur">اردو (Urdu)</option>
                    </select>
                    <button className="cp-icon-btn" onClick={clearChat} title="New chat">✏</button>
                    <button className="cp-icon-btn cp-close" onClick={onClose} title="Close">✕</button>
                </div>
            </div>

            <ModeSelector mode={mode} onChange={setMode} />

            {/* Profile awareness bar */}
            <ProfileBar profile={initialProfile} />

            {/* Collapsible Schemes */}
            {schemes.length > 0 && (
                <div className={`cp-collapsible-section ${schemesOpen ? 'open' : ''}`}>
                    <button className="cp-section-header" onClick={() => setSchemesOpen(!schemesOpen)}>
                        <span>🎯 Top Matches ({schemes.length})</span>
                        <span>{schemesOpen ? '▲' : '▼'}</span>
                    </button>
                    {schemesOpen && (
                        <div className="cp-schemes-strip">
                            <div className="cp-pills">
                                {schemes.slice(0, 4).map((s, i) => (
                                    <SchemePill key={s.id || i} scheme={s} rank={i + 1} />
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Collapsible Summary */}
            {summary && (
                <div className={`cp - collapsible - section ${summaryOpen ? 'open' : ''} `}>
                    <button className="cp-section-header" onClick={() => setSummaryOpen(!summaryOpen)}>
                        <span>⭐ AI Recommendation</span>
                        <span>{summaryOpen ? '▲' : '▼'}</span>
                    </button>
                    {summaryOpen && (
                        <div className="cp-summary">
                            <p className="cp-summary-text">{summary}</p>
                        </div>
                    )}
                </div>
            )}

            {/* Main scrollable area */}
            <div className="cp-main-scrollable">
                {mode === 'voice' ? (
                    <div className="cp-voice-ui">
                        <div className="cp-voice-transcript">
                            {messages.map((msg, i) => (
                                <div key={i} className={`cp-voice-line ${msg.role === 'user' ? 'vl-user' : 'vl-bot'}`}>
                                    <span className="vl-who">{msg.role === 'user' ? 'You' : 'AI'}:</span>
                                    <span className="vl-text">{msg.content}</span>
                                </div>
                            ))}
                        </div>
                        <VoiceOrb state={voiceState} />
                        {voiceState === 'idle' && <button className="voice-tap-btn" onClick={listenNext}>Tap to speak</button>}
                        {voiceState === 'listening' && <button className="voice-tap-btn stop" onClick={() => { recRef.current?.stop(); setVoiceState('idle') }}>Done</button>}
                    </div>
                ) : (
                    <div className="cp-messages">
                        {messages.map((msg, i) => (
                            <Bubble key={i} msg={msg} onSpeak={t => speak(t, lang, user)} />
                        ))}
                        {loading && (
                            <div className="cp-row cp-bot-row">
                                <div className="cp-avatar">🏛️</div>
                                <div className="cp-bubble cp-bubble-bot">
                                    <div className="cp-typing"><span /><span /><span /></div>
                                </div>
                            </div>
                        )}
                        <div ref={bottomRef} />
                    </div>
                )}
            </div>

            {mode === 'text' && (
                <div className="cp-input-area">
                    <div className="cp-input-box">
                        <textarea
                            ref={textareaRef}
                            className="cp-input"
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={handleKey}
                            placeholder={lang === 'hi' ? 'यहाँ लिखें...' : 'Ask anything about schemes...'}
                            disabled={loading}
                            rows={1}
                        />
                        <div className="cp-input-actions">
                            <button className={`cp-mic ${voiceState === 'listening' ? 'listening' : ''}`} onClick={handleManualMic}>🎤</button>
                            <button className="cp-send" onClick={() => sendMessage()} disabled={loading || !input.trim()}>{loading ? '⏳' : '↑'}</button>
                        </div>
                    </div>
                    <div className="cp-input-hint">Enter to send · Shift+Enter for newline</div>
                </div>
            )}
        </div>
    )
}

/* ── SchemePill ──────────────────────────────────────────────── */
function SchemePill({ scheme, rank }) {
    const [open, setOpen] = useState(false)
    return (
        <div className={`cp-scheme-pill ${open ? 'open' : ''}`} onClick={() => setOpen(o => !o)}>
            <div className="cp-pill-top">
                <span className="cp-pill-rank">#{rank}</span>
                <span className="cp-pill-name">{scheme.name_en || scheme.name}</span>
                {scheme.benefit_amount && <span className="cp-pill-amount">₹{scheme.benefit_amount?.toLocaleString('en-IN')}</span>}
                <span className="cp-pill-chevron">{open ? '▲' : '▼'}</span>
            </div>
            {open && (
                <div className="cp-pill-body">
                    <p>{scheme.benefit_description}</p>
                    <p className="cp-pill-why">✅ {scheme.eligibility_reason}</p>
                    {scheme.website && <a href={scheme.website} target="_blank" rel="noreferrer" className="cp-pill-link">Apply →</a>}
                </div>
            )}
        </div>
    )
}
