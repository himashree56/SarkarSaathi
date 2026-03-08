import { useState } from 'react'
import SchemeCard from './SchemeCard'
import ProfileCard from './ProfileCard'
import { LOCALES } from '../locales'

/**
 * ResultsDashboard — Shared component for showing schemes, profile, and chat.
 * Used by both live search and history views.
 */
const LANG_SYNC = {
    'English': 'en', 'Hindi': 'hi', 'Gujarati': 'gu', 'Marathi': 'mr',
    'Tamil': 'ta', 'Telugu': 'te', 'Bengali': 'bn', 'Kannada': 'kn',
    'Urdu': 'ur', 'Malayalam': 'ml'
}

export default function ResultsDashboard({ session, onNewSearch, user, selectedLang, isHistoryView = false }) {
    const langKey = (LANG_SYNC[selectedLang] || selectedLang || 'en').toLowerCase()
    const t = LOCALES[langKey] || LOCALES.en
    const {
        profile,
        schemes = [],
        title,
        last_query,
        updated_at,
        message,
        summary,
        recommended_id,
        history = []
    } = session

    const [tab, setTab] = useState('schemes') // 'schemes' | 'profile' | 'chat'

    // Prioritize recommended_id if present
    const sortedSchemes = [...schemes]
    if (recommended_id) {
        const idx = sortedSchemes.findIndex(s => s.id === recommended_id)
        if (idx > -1) {
            const [rec] = sortedSchemes.splice(idx, 1)
            sortedSchemes.unshift({ ...rec, isAIRecommended: true })
        }
    }

    const dateStr = updated_at
        ? new Date(updated_at + (updated_at.endsWith('Z') ? '' : 'Z')).toLocaleDateString('en-IN', {
            day: 'numeric', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        })
        : ''

    return (
        <div className={`results-dashboard ${isHistoryView ? 'is-history' : 'is-live'}`}>
            <div className="hd-header">
                <div className="hd-header-left">
                    {isHistoryView && onNewSearch && (
                        <button className="hd-back-btn" onClick={onNewSearch} title="Back to search">
                            ← Back
                        </button>
                    )}
                    <div>
                        <div className="hd-title">{title || (isHistoryView ? 'Saved Session' : 'Search Results')}</div>
                        {last_query && <div className="hd-query">"{last_query}"</div>}
                        {dateStr && <div className="hd-date">🕐 {dateStr}</div>}
                    </div>
                </div>
                {!isHistoryView && onNewSearch && (
                    <button className="hd-new-btn" onClick={onNewSearch}>
                        + New Search
                    </button>
                )}
            </div>

            <div className="hd-stats">
                <div className="hd-stat">
                    <span className="hd-stat-val">{schemes.length}</span>
                    <span className="hd-stat-label">{t.schemes_matched}</span>
                </div>
                {profile?.state && (
                    <div className="hd-stat">
                        <span className="hd-stat-val">{profile.state}</span>
                        <span className="hd-stat-label">{t.state}</span>
                    </div>
                )}
                {profile?.occupation && (
                    <div className="hd-stat">
                        <span className="hd-stat-val" style={{ textTransform: 'capitalize' }}>{profile.occupation}</span>
                        <span className="hd-stat-label">{t.occupation}</span>
                    </div>
                )}
                {profile?.income_level && (
                    <div className="hd-stat">
                        <span className="hd-stat-val">₹{(profile.income_level / 100000).toFixed(1)}L</span>
                        <span className="hd-stat-label">{t.income_year}</span>
                    </div>
                )}
                {sortedSchemes[0] && (
                    <div className="hd-stat accent">
                        <span className="hd-stat-val">{sortedSchemes[0].name || sortedSchemes[0].name_en}</span>
                        <span className="hd-stat-label">{sortedSchemes[0].isAIRecommended ? (t.ai_recommendation.split(' ')[2] || 'Recommendation') : 'Top Match'}</span>
                    </div>
                )}
            </div>

            <div className="hd-tabs">
                <button className={`hd-tab ${tab === 'schemes' ? 'active' : ''}`} onClick={() => setTab('schemes')}>
                    🎯 {t.matched_schemes} ({schemes.length})
                </button>
                <button className={`hd-tab ${tab === 'profile' ? 'active' : ''}`} onClick={() => setTab('profile')}>
                    👤 {t.your_profile}
                </button>
                {history.length > 0 && (
                    <button className={`hd-tab ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')}>
                        💬 {t.your_chat}
                    </button>
                )}
            </div>

            <div className="hd-content">
                {tab === 'schemes' && (
                    <div className="hd-schemes">
                        {summary && (
                            <div className="hd-ai-recommendation-card">
                                <div className="hd-arc-header">⭐ {t.ai_recommendation}</div>
                                <div className="hd-arc-text">{summary}</div>
                            </div>
                        )}
                        {sortedSchemes.length === 0 ? (
                            <div className="empty-state">
                                <div className="icon">🔍</div>
                                <p>No schemes found for this profile. Try adding more details.</p>
                            </div>
                        ) : (
                            sortedSchemes.map((scheme, i) => (
                                <SchemeCard
                                    key={scheme.id || i}
                                    scheme={scheme}
                                    rank={i + 1}
                                    user={user}
                                    selectedLang={selectedLang}
                                    isAIRecommended={scheme.isAIRecommended}
                                />
                            ))
                        )}
                    </div>
                )}

                {tab === 'profile' && profile && (
                    <div className="hd-profile-tab">
                        <ProfileCard profile={profile} message={message || ''} selectedLang={selectedLang} />
                    </div>
                )}

                {tab === 'chat' && history.length > 0 && (
                    <div className="hd-chat-tab">
                        <div className="hd-chat-transcript">
                            {[...history].reverse().map((turn, i) => (
                                <div key={i} className={`hd-chat-row ${turn.role === 'user' ? 'user' : 'bot'}`}>
                                    <div className="hd-chat-bubble">
                                        <div className="hd-chat-role">{turn.role === 'user' ? 'You' : 'SarkarSaathi'}</div>
                                        <div className="hd-chat-text">{turn.content}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
