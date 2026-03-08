import { LOCALES } from '../locales'

const LANG_SYNC = {
    'English': 'en', 'Hindi': 'hi', 'Gujarati': 'gu', 'Marathi': 'mr',
    'Tamil': 'ta', 'Telugu': 'te', 'Bengali': 'bn', 'Kannada': 'kn',
    'Urdu': 'ur', 'Malayalam': 'ml'
}

export default function ProfileCard({ profile, message, selectedLang }) {
    const langKey = (LANG_SYNC[selectedLang] || selectedLang || 'en').toLowerCase()
    const t = LOCALES[langKey] || LOCALES.en

    const FIELD_LABELS = {
        age: { icon: '🎂', label: t.age },
        gender: { icon: '👤', label: t.gender },
        marital_status: { icon: '💍', label: t.marital },
        occupation: { icon: '💼', label: t.occupation },
        income_level: { icon: '💰', label: t.income_year.split('/')[0] },
        location_type: { icon: '📍', label: t.location },
        state: { icon: '🗺️', label: t.state },
        caste: { icon: '📋', label: t.category },
        children: { icon: '👶', label: t.children },
        language: { icon: '🌐', label: t.language },
    }

    const LANG_DISPLAY = {
        'en': 'English', 'hi': 'Hindi', 'gu': 'Gujarati', 'mr': 'Marathi',
        'ta': 'Tamil', 'te': 'Telugu', 'bn': 'Bengali', 'kn': 'Kannada',
        'ur': 'Urdu', 'ml': 'Malayalam'
    }

    function formatValue(key, val) {
        if (key === 'income_level') return `₹${val.toLocaleString('en-IN')}`
        if (key === 'age') return `${val}`
        if (key === 'language') return LANG_DISPLAY[val] || val
        if (Array.isArray(val)) return val.join(', ')
        return String(val).replace(/_/g, ' ')
    }

    const entries = Object.entries(profile).filter(([k, v]) => {
        if (k === 'needs') return false
        if (v === null || v === undefined) return false
        if (Array.isArray(v) && v.length === 0) return false
        return true
    })

    return (
        <div className="profile-section">
            <p className="section-title"><span>👤 {t.your_profile}</span></p>
            <div className="profile-card">
                {entries.map(([k, v]) => {
                    const { icon, label } = FIELD_LABELS[k] || { icon: '•', label: k }
                    return (
                        <div key={k} className="profile-item">
                            <span>{icon}</span>
                            <span className="label">{label}:</span>
                            <span className="value">{formatValue(k, v)}</span>
                        </div>
                    )
                })}
                {profile.needs && profile.needs.length > 0 && (
                    <div className="profile-item">
                        <span>🎯</span>
                        <span className="label">Needs:</span>
                        <span className="value">{profile.needs.join(', ')}</span>
                    </div>
                )}
                <div className="result-message">ℹ️ {message}</div>
            </div>
        </div>
    )
}
