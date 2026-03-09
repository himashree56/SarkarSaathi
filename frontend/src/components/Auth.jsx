/**
 * Auth.jsx — Full-page login gate + header status when logged in
 * Uses direct Cognito REST API via fetch() — zero Node.js dependencies.
 */
import { useState } from 'react';

const REGION = import.meta.env.VITE_REGION || 'us-east-1';
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID || '';
const COGNITO_URL = `https://cognito-idp.${REGION}.amazonaws.com/`;

async function cognitoPost(target, body) {
    const res = await fetch(COGNITO_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-amz-json-1.1',
            'X-Amz-Target': target,
        },
        body: JSON.stringify(body),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.message || json.__type || 'Request failed');
    return json;
}

/** Small header badge shown when logged in */
export function AuthStatus({ user, onLogout }) {
    return (
        <div className="auth-status">
            <span className="auth-user-email">👤 {user.email}</span>
            <button className="auth-btn-small" onClick={onLogout}>Logout</button>
        </div>
    );
}

/** Full-page login/signup gate */
export default function Auth({ onLogin, theme, setTheme }) {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [code, setCode] = useState('');
    const [consentChecked, setConsentChecked] = useState(false);
    const [needsVerification, setNeedsVerification] = useState(false);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const [loading, setLoading] = useState(false);

    const switchMode = (login) => { setIsLogin(login); setError(''); setMessage(''); };

    const handleSignup = async (e) => {
        e.preventDefault(); setError(''); setLoading(true);
        try {
            await cognitoPost('AWSCognitoIdentityProviderService.SignUp', {
                ClientId: CLIENT_ID, Username: email, Password: password,
                UserAttributes: [{ Name: 'email', Value: email }],
            });
            setNeedsVerification(true);
            setMessage('📧 Check your email for a 6-digit verification code.');
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    };

    const handleVerify = async (e) => {
        e.preventDefault(); setError(''); setLoading(true);
        try {
            await cognitoPost('AWSCognitoIdentityProviderService.ConfirmSignUp', {
                ClientId: CLIENT_ID, Username: email, ConfirmationCode: code.trim(),
            });
            setNeedsVerification(false); setIsLogin(true);
            setMessage('✅ Email verified! Please log in now.');
        } catch (err) {
            alert('Invalid OTP! Please try again. Your OTP is valid for 5 minutes.');
            setCode('');
        }
        finally { setLoading(false); }
    };

    const handleLogin = async (e) => {
        e.preventDefault(); setError(''); setLoading(true);
        try {
            const res = await cognitoPost('AWSCognitoIdentityProviderService.InitiateAuth', {
                AuthFlow: 'USER_PASSWORD_AUTH', ClientId: CLIENT_ID,
                AuthParameters: { USERNAME: email, PASSWORD: password },
            });
            const t = res.AuthenticationResult;
            onLogin({ email, idToken: t.IdToken, accessToken: t.AccessToken, refreshToken: t.RefreshToken });
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    };

    return (
        <div className="auth-gate">
            {/* Theme switcher — floating top-right */}
            {setTheme && (
                <div className="auth-gate-theme">
                    <button className={`theme-btn ${theme === 'dark' ? 'active' : ''}`} onClick={() => setTheme('dark')} title="Dark">🌙</button>
                    <button className={`theme-btn ${theme === 'light' ? 'active' : ''}`} onClick={() => setTheme('light')} title="Light">☀️</button>
                    <button className={`theme-btn ${theme === 'neon' ? 'active' : ''}`} onClick={() => setTheme('neon')} title="Neon">🌈</button>
                </div>
            )}

            {/* Left — Branding */}
            <div className="auth-gate-left">
                <div className="auth-gate-logo">🏛️</div>
                <h1 className="auth-gate-title">SarkarSaathi</h1>
                <p className="auth-gate-subtitle">
                    AI-powered Government Scheme Navigator<br />
                    सरकारी योजना मार्गदर्शक
                </p>
                <ul className="auth-gate-features">
                    <li>🎤 Voice input in Hindi &amp; English</li>
                    <li>🌍 Output in 8 regional languages</li>
                    <li>🗺️ Office locations on Google Maps</li>
                    <li>📋 100+ government schemes matched to you</li>
                    <li>📊 Search history dashboard</li>
                </ul>
            </div>

            {/* Right — Form */}
            <div className="auth-gate-right">
                <div className="auth-form-card">
                    {!needsVerification && (
                        <div className="auth-tabs">
                            <button className={`auth-tab ${isLogin ? 'active' : ''}`} onClick={() => switchMode(true)}>Login</button>
                            <button className={`auth-tab ${!isLogin ? 'active' : ''}`} onClick={() => switchMode(false)}>Sign Up</button>
                        </div>
                    )}

                    <h2 className="auth-form-title">
                        {needsVerification ? '📧 Verify your email' : (isLogin ? 'Welcome back' : 'Create your account')}
                    </h2>

                    {error && <p className="auth-error">{error}</p>}
                    {message && <p className="auth-message">{message}</p>}

                    <form className="auth-form" onSubmit={needsVerification ? handleVerify : (isLogin ? handleLogin : handleSignup)}>
                        {!needsVerification && (
                            <>
                                <div className="auth-field">
                                    <label>Email address</label>
                                    <input type="email" placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} required autoFocus />
                                </div>
                                <div className="auth-field">
                                    <label>Password</label>
                                    <input type="password" placeholder={isLogin ? 'Your password' : 'Min 8 characters'} value={password} onChange={e => setPassword(e.target.value)} required minLength={8} />
                                </div>
                                {!isLogin && (
                                    <div className="auth-field-checkbox" style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginTop: '10px' }}>
                                        <input type="checkbox" required checked={consentChecked} onChange={e => setConsentChecked(e.target.checked)} id="authConsent" style={{ marginTop: '4px' }} />
                                        <label htmlFor="authConsent" style={{ fontSize: '0.85rem', color: '#666', lineHeight: '1.4' }}>
                                            I consent to SarkarSaathi processing my sensitive information (such as income and caste category) strictly to match me with eligible government schemes.
                                        </label>
                                    </div>
                                )}
                            </>
                        )}
                        {needsVerification && (
                            <div className="auth-field">
                                <label>Verification code</label>
                                <input type="text" placeholder="6-digit code from your email" value={code} onChange={e => setCode(e.target.value)} required autoFocus />
                            </div>
                        )}
                        <button type="submit" className="auth-submit-btn" disabled={loading}>
                            {loading ? '⏳ Please wait…' : (needsVerification ? 'Verify Email' : (isLogin ? 'Login →' : 'Create Account →'))}
                        </button>
                    </form>

                    {!needsVerification && (
                        <p className="auth-switch">
                            {isLogin ? "Don't have an account?" : 'Already have an account?'}
                            <button className="link-btn" onClick={() => switchMode(!isLogin)}>
                                {isLogin ? ' Sign up free' : ' Login'}
                            </button>
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
