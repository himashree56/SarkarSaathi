import React, { useState } from 'react';
import '../index.css';

export default function ConsentBanner({ onConsent, lang }) {
    const [checked, setChecked] = useState(false);

    const text = {
        en: "We need your consent to process sensitive personal data (like age, income, and caste) to find the right schemes for you. We do not share this data with third parties.",
        hi: "आपके लिए सही योजनाएं खोजने के लिए हमें आपके व्यक्तिगत डेटा (जैसे आयु, आय, जाति) संसाधित करने की सहमति चाहिए। हम आपका डेटा किसी के साथ साझा नहीं करते हैं।"
    };

    const handleAccept = () => {
        if (!checked) return alert('Please check the box to agree.');
        onConsent(true);
    };

    const handleDecline = () => {
        onConsent(false);
    };

    return (
        <div className="modal-overlay">
            <div className="consent-modal">
                <h2>Privacy & Consent</h2>
                <div className="consent-text">
                    <span className="consent-icon">🔒</span>
                    <p>{text[lang] || text.en}</p>
                </div>

                <div className="consent-checkbox-group">
                    <input
                        type="checkbox"
                        id="consent-check"
                        checked={checked}
                        onChange={(e) => setChecked(e.target.checked)}
                    />
                    <label htmlFor="consent-check">
                        I agree to allow SarkarSaathi to process my sensitive information solely for discovering eligible government schemes.
                    </label>
                </div>

                <div className="consent-actions" style={{ marginTop: '20px', marginLeft: 0 }}>
                    <button className="consent-btn accept" onClick={handleAccept} disabled={!checked} style={{ opacity: checked ? 1 : 0.5 }}>
                        {lang === 'hi' ? 'सहमत हूँ' : 'I Agree & Continue'}
                    </button>
                    <button className="consent-btn decline" onClick={handleDecline}>
                        {lang === 'hi' ? 'अस्वीकार' : 'Decline'}
                    </button>
                </div>
            </div>
        </div>
    );
}
