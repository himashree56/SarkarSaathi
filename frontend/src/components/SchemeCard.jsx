import { useState } from 'react'
import { LOCALES } from '../locales'

const CAT_ICONS = {
    agriculture: '🌾', education: '📚', housing: '🏠', health: '❤️',
    employment: '💼', skill: '🎓', pension: '👴', disability: '♿',
    women: '👩', food: '🍚', social_welfare: '🤝', business: '🏢',
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const LANG_SYNC = {
    'English': 'en', 'Hindi': 'hi', 'Gujarati': 'gu', 'Marathi': 'mr',
    'Tamil': 'ta', 'Telugu': 'te', 'Bengali': 'bn', 'Kannada': 'kn',
    'Urdu': 'ur', 'Malayalam': 'ml'
}

export default function SchemeCard({ scheme, rank, user, selectedLang, isAIRecommended }) {
    const langKey = (LANG_SYNC[selectedLang] || selectedLang || 'en').toLowerCase()
    const t = LOCALES[langKey] || LOCALES.en
    const [expanded, setExpanded] = useState(rank <= 2 || isAIRecommended)  // auto-expand top 2 or AI choice
    const [isSpeaking, setIsSpeaking] = useState(false)

    function toggleSpeech(e) {
        e.stopPropagation()

        if (isSpeaking) {
            window.speechSynthesis.cancel()
            setIsSpeaking(false)
            return
        }

        const targetLang = (LANG_SYNC[selectedLang] || selectedLang || 'en').toLowerCase()
        const targetVoice = targetLang === 'hi' ? 'hi-IN' : (targetLang === 'kn' ? 'kn-IN' : (targetLang === 'en' ? 'en-IN' : targetLang + '-IN'))
        const text = `${scheme.name || scheme.name_en}. ${scheme.benefit_description || ''}`
        const cleanText = text.replace(/[*_#\-•→]/g, '').replace(/\s+/g, ' ').trim()

        setIsSpeaking(true)

        const utt = new SpeechSynthesisUtterance(cleanText)
        utt.lang = targetVoice
        utt.rate = 0.95
        utt.pitch = 1.0

        // High-quality Google Voice selection logic
        const voices = window.speechSynthesis.getVoices()
        const bestVoice = voices.find(v => v.lang === targetVoice && v.name.includes('Google'))
            || voices.find(v => v.lang === targetVoice)
            || voices.find(v => v.lang.startsWith(targetVoice.split('-')[0]))

        if (bestVoice) utt.voice = bestVoice

        utt.onend = () => setIsSpeaking(false)
        utt.onerror = () => setIsSpeaking(false)

        window.speechSynthesis.cancel()
        window.speechSynthesis.speak(utt)
    }

    function openMap(e) {
        e.stopPropagation()
        if (scheme.maps_url) {
            window.open(scheme.maps_url, '_blank')
        } else {
            const query = encodeURIComponent(`${scheme.office_address || scheme.office_info || ''} ${scheme.state}`)
            window.open(`https://www.google.com/maps/search/?api=1&query=${query}`, '_blank')
        }
    }

    const catIcon = CAT_ICONS[scheme.category] || '📋'
    const delay = `${rank * 0.05}s`

    return (
        <div
            className={`scheme-card${expanded ? ' expanded' : ''}${isAIRecommended ? ' ai-recommended' : ''}`}
            style={{ animationDelay: delay }}
        >
            <div className="scheme-header" onClick={() => setExpanded(e => !e)}>
                <div className="scheme-rank">{rank}</div>
                <div className="scheme-info">
                    <div className="scheme-name-en">
                        {scheme.name || scheme.name_en}
                        {isAIRecommended && <span className="ai-recommended-badge">AI BEST MATCH</span>}
                    </div>
                    {scheme.name_hi && scheme.name_hi !== (scheme.name || scheme.name_en) && (
                        <div className="scheme-name-hi">{scheme.name_hi}</div>
                    )}
                    <div className="scheme-badges">
                        <span className="badge badge-cat">{catIcon} {scheme.category.replace(/_/g, ' ')}</span>
                        <span className="badge badge-state">
                            {scheme.state === 'ALL' ? '🇮🇳 National' : `📍 ${scheme.state}`}
                        </span>
                        <span className="badge badge-score">⭐ Score {scheme.match_score}</span>
                    </div>
                </div>
                <div className="scheme-right">
                    {scheme.benefit_amount ? (
                        <div className="benefit-amount">
                            <div className="amount">₹{scheme.benefit_amount.toLocaleString('en-IN')}</div>
                            <div className="label">{t.benefit.replace('💡 ', '')}</div>
                        </div>
                    ) : (
                        <div className="benefit-amount">
                            <div className="amount" style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{t.see_details}</div>
                        </div>
                    )}
                    <span className="expand-icon">{expanded ? '▲' : '▼'}</span>
                </div>
            </div>

            {expanded && (
                <div className="scheme-body">
                    {scheme.benefit_description && (
                        <div className="scheme-section">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                <h4>{t.benefit}</h4>
                                <button className="tts-btn" onClick={toggleSpeech}>
                                    {isSpeaking ? t.stop : t.listen}
                                </button>
                            </div>
                            <p className="scheme-benefit-text">
                                {scheme.benefit_description.slice(0, 350)}
                                {scheme.benefit_description.length > 350 ? '…' : ''}
                            </p>
                        </div>
                    )}

                    <div className="scheme-section">
                        <h4>{t.match}</h4>
                        <div className="eligibility-reason">{scheme.eligibility_reason}</div>
                    </div>

                    {scheme.required_documents?.length > 0 && (
                        <div className="scheme-section">
                            <h4>{t.docs}</h4>
                            <div className="doc-list">
                                {scheme.required_documents.map(doc => (
                                    <span key={doc} className="doc-tag">{doc}</span>
                                ))}
                            </div>
                        </div>
                    )}

                    {scheme.application_steps?.length > 0 && (
                        <div className="scheme-section">
                            <h4>{t.apply}</h4>
                            <div className="steps-list">
                                {scheme.application_steps.map((step, i) => (
                                    <div key={i} className="step-item">
                                        <span className="step-num">{i + 1}</span>
                                        <span>{step}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="scheme-section">
                        <h4>{t.office}</h4>
                        {scheme.office_name && (
                            <p style={{ fontWeight: 600, marginBottom: '4px', color: 'var(--text-secondary)' }}>
                                {scheme.office_name}
                            </p>
                        )}
                        <p
                            className="office-info"
                            onClick={openMap}
                            title="Click to navigate in Google Maps"
                            style={{ cursor: 'pointer', color: 'var(--accent-blue)', textDecoration: 'underline' }}
                        >
                            📍 {scheme.office_address || scheme.office_info || 'Contact local district office'}
                        </p>
                        <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                            {t.maps}
                        </p>
                    </div>

                    {scheme.website && (
                        <a
                            href={scheme.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="scheme-link"
                        >
                            🌐 Apply / View on myscheme.gov.in →
                        </a>
                    )}
                </div>
            )}
        </div>
    )
}
