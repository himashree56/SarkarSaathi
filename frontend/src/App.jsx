import { useState, useEffect } from 'react'
import './index.css'
import './components.css'
import QueryInput from './components/QueryInput'
import ProfileCard from './components/ProfileCard'
import SchemeCard from './components/SchemeCard'
import Auth, { AuthStatus } from './components/Auth'
import HistorySidebar from './components/HistorySidebar'
import ChatWindow from './components/ChatWindow'
import ResultsDashboard from './components/ResultsDashboard'
import ConsentBanner from './components/ConsentBanner'
import OperatorDashboard from './pages/OperatorDashboard'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const COGNITO_URL = `https://cognito-idp.${import.meta.env.VITE_REGION || 'us-east-1'}.amazonaws.com/`
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID || ''

async function refreshAccessToken(refreshToken) {
  const res = await fetch(COGNITO_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-amz-json-1.1', 'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth' },
    body: JSON.stringify({ AuthFlow: 'REFRESH_TOKEN_AUTH', ClientId: CLIENT_ID, AuthParameters: { REFRESH_TOKEN: refreshToken } }),
  })
  if (!res.ok) throw new Error('Token refresh failed')
  const data = await res.json()
  return data.AuthenticationResult.AccessToken
}

export default function App() {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('ss_user')) } catch { return null }
  })
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark')
  const [history, setHistory] = useState([])
  const [selectedLang, setSelectedLang] = useState('en')
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)

  function toggleChat() {
    setChatOpen(o => !o)
    if (!chatOpen) setIsSidebarOpen(false) // close history sidebar when chat opens
  }

  const [consentGiven, setConsentGiven] = useState(() => {
    return localStorage.getItem('ss_consent') === 'true'
  })

  function handleConsent(given) {
    setConsentGiven(given)
    localStorage.setItem('ss_consent', String(given))
  }

  // History dashboard — stores the loaded session data when user clicks a history item
  const [dashboardSession, setDashboardSession] = useState(null)
  const [dashboardLoading, setDashboardLoading] = useState(false)

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  // Persist user + fetch history
  useEffect(() => {
    if (user) {
      localStorage.setItem('ss_user', JSON.stringify(user))
      fetchHistory()
    } else {
      localStorage.removeItem('ss_user')
      setHistory([])
    }
  }, [user])

  async function fetchHistory() {
    if (!user) return
    try {
      let res = await fetch(`${API_BASE}/history`, {
        headers: { Authorization: `Bearer ${user.accessToken}` },
      })
      // Auto-refresh token if expired
      if (res.status === 401 && user.refreshToken) {
        try {
          const newToken = await refreshAccessToken(user.refreshToken)
          const updated = { ...user, accessToken: newToken }
          setUser(updated)
          localStorage.setItem('ss_user', JSON.stringify(updated))
          res = await fetch(`${API_BASE}/history`, {
            headers: { Authorization: `Bearer ${newToken}` },
          })
        } catch { return } // refresh failed — user needs to re-login
      }
      if (res.ok) {
        const data = await res.json()
        setHistory(Array.isArray(data) ? data : (data.sessions || []))
      }
    } catch { /* silent */ }
  }

  // ── Click a history item: load saved session, show dashboard ──
  async function handleSelectHistory(item) {
    setDashboardLoading(true)
    setResult(null)
    setDashboardSession(null)
    setIsSidebarOpen(false)
    try {
      const res = await fetch(`${API_BASE}/session/${item.session_id}`, {
        headers: user ? { Authorization: `Bearer ${user.accessToken}` } : {},
      })
      if (res.ok) {
        const data = await res.json()
        setDashboardSession(data)
        setResult(data) // Sync Copilot with loaded session
      } else {
        // Fallback: old re-query approach
        handleSubmit(item.last_query, item.session_id)
      }
    } catch {
      handleSubmit(item.last_query, item.session_id)
    } finally {
      setDashboardLoading(false)
    }
  }

  // ── Polling for regional translations ──────────────────────────
  async function pollTranslations(sid, lang) {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      if (attempts > 15) { clearInterval(interval); return; }
      try {
        const res = await fetch(`${API_BASE}/session/${sid}`);
        if (res.ok) {
          const data = await res.json();
          const names = data.schemes?.map(s => s.name).join('') || '';
          const hasRegional = /[\u0900-\u0DFF]/.test(names);
          if (hasRegional || lang === 'en') {
            setResult(data);
            clearInterval(interval);
          }
        }
      } catch { /* silent */ }
    }, 3000);
  }

  // ── Normal query submit ───────────────────────────────────────
  async function handleSubmit(q, overrideSessionId = null) {
    const text = (q || query).trim()
    if (!text) return
    setLoading(true); setError(''); setResult(null); setDashboardSession(null)
    const sessionId = overrideSessionId || localStorage.getItem('session_id') || null

    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(user ? { Authorization: `Bearer ${user.accessToken}` } : {}),
        },
        body: JSON.stringify({ query: text, lang: selectedLang, session_id: sessionId, known_profile: { consent_given: !!user } }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      setResult(data)
      if (data.session_id) {
        localStorage.setItem('session_id', data.session_id)
        if (selectedLang !== 'en' && data.message?.includes('in progress')) {
          pollTranslations(data.session_id, selectedLang)
        }
      }
      if (user) fetchHistory()
    } catch (e) {
      setError(e.message || 'Connection failed.')
    } finally { setLoading(false) }
  }

  function handleNewChat() {
    setResult(null); setQuery(''); setError(''); setDashboardSession(null)
    localStorage.removeItem('session_id')
  }

  async function deleteHistory(sessionId) {
    if (!user) return
    try {
      const res = await fetch(`${API_BASE}/history/${sessionId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${user.accessToken}` },
      })
      if (res.ok) {
        setHistory(prev => prev.filter(h => h.session_id !== sessionId))
        if (localStorage.getItem('session_id') === sessionId) handleNewChat()
      }
    } catch { /* silent */ }
  }

  async function renameHistory(sessionId, newTitle) {
    if (!user) return
    try {
      const res = await fetch(`${API_BASE}/history/${sessionId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${user.accessToken}`,
        },
        body: JSON.stringify({ title: newTitle }),
      })
      if (res.ok) setHistory(prev => prev.map(h =>
        h.session_id === sessionId ? { ...h, title: newTitle } : h
      ))
    } catch { /* silent */ }
  }

  const handleLogout = () => { setUser(null); setResult(null); setQuery(''); setHistory([]) }

  // ── Auth gate ────────────────────────────────────────────────
  if (!user) {
    return (
      <div className="app" data-theme={theme}>
        <Auth onLogin={setUser} theme={theme} setTheme={setTheme} />
      </div>
    )
  }

  const showDashboard = !!dashboardSession

  if (user?.role === 'operator') {
    return <OperatorDashboard user={user} onLogout={handleLogout} />
  }

  return (
    <div className={`app has-sidebar ${chatOpen ? 'chat-is-open' : ''}`}>
      <HistorySidebar
        history={history}
        currentSessionId={localStorage.getItem('session_id')}
        onSelect={handleSelectHistory}
        onDelete={deleteHistory}
        onRename={renameHistory}
        onNewChat={handleNewChat}
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
      />

      {/* ── Main content ──────────────────────────────────── */}
      <div className="main-content-wrapper">
        <header className="header">
          <div className="header-left">
            <button className="sidebar-toggle" onClick={() => setIsSidebarOpen(true)}>☰</button>
            <div className="header-logo">🏛️</div>
            <div className="header-text">
              <h1>SarkarSaathi</h1>
              <p>AI Government Scheme Navigator</p>
            </div>
          </div>

          <div className="header-right">
            <div className="theme-switcher">
              <button className={`theme-btn ${theme === 'dark' ? 'active' : ''}`} onClick={() => setTheme('dark')} title="Dark">🌙</button>
              <button className={`theme-btn ${theme === 'light' ? 'active' : ''}`} onClick={() => setTheme('light')} title="Light">☀️</button>
              <button className={`theme-btn ${theme === 'neon' ? 'active' : ''}`} onClick={() => setTheme('neon')} title="Neon">🌈</button>
            </div>

            <div className="language-selector">
              <select value={selectedLang} onChange={e => setSelectedLang(e.target.value)}>
                <option value="en">English</option>
                <option value="hi">हिंदी (Hindi)</option>
                <option value="kn">ಕನ್ನಡ (Kannada)</option>
                <option value="mr">मराठी (Marathi)</option>
                <option value="bn">বাংলা (Bengali)</option>
                <option value="ta">தமிழ் (Tamil)</option>
                <option value="te">తెలుగు (Telugu)</option>
                <option value="gu">ગુજરાતી (Gujarati)</option>
                <option value="ml">മലയാളം (Malayalam)</option>
                <option value="ur">اردو (Urdu)</option>
              </select>
            </div>

            {/* Copilot toggle — icon only, tooltip on hover */}
            <button
              className={`copilot-toggle-btn ${chatOpen ? 'active' : ''}`}
              onClick={toggleChat}
              title={chatOpen ? 'Close AI Chat' : 'Open AI Chat (Copilot)'}
              aria-label={chatOpen ? 'Close AI Chat' : 'Open AI Chat'}
            >
              <span className="copilot-btn-icon">{chatOpen ? '✕' : '✨'}</span>
            </button>
            <AuthStatus user={user} onLogout={handleLogout} />
          </div>
        </header>

        <main className="main">
          {/* Dashboard mode — show saved history results */}
          {showDashboard ? (
            <ResultsDashboard
              session={dashboardSession}
              user={user}
              selectedLang={selectedLang}
              onNewSearch={handleNewChat}
              isHistoryView={true}
            />
          ) : (
            <>
              {!result && (
                <section className="hero">
                  <h2 className="hero-title">Find Your <span className="accent">Government Benefits</span></h2>
                  <p className="hero-subtitle">
                    Describe your situation in Hindi or English — we'll find the schemes you're eligible for.
                  </p>
                </section>
              )}

              <QueryInput query={query} setQuery={setQuery} onSubmit={handleSubmit} loading={loading} voiceLang={selectedLang} />

              {/* Show the Mandatory Popup Modal if Consent is missing */}
              {!consentGiven && <ConsentBanner onConsent={handleConsent} lang={selectedLang} />}

              {dashboardLoading && (
                <div className="loading-session">
                  <div className="spinner" />
                  <p>Loading your saved results...</p>
                </div>
              )}
              {error && <div className="error-box">⚠️ {error}</div>}

              {result && (
                <ResultsDashboard
                  session={result}
                  user={user}
                  selectedLang={selectedLang}
                  onNewSearch={handleNewChat}
                  isHistoryView={false}
                />
              )}
            </>
          )}
        </main>

        <footer className="footer">
          SarkarSaathi — Data sourced from myscheme.gov.in &nbsp;•&nbsp; For informational purposes only
        </footer>
      </div>

      {/* ── Copilot Chat Sidebar ───────────────────────────── */}
      {chatOpen && (
        <div className="copilot-sidebar">
          <ChatWindow
            user={user}
            selectedLang={selectedLang}
            onClose={() => setChatOpen(false)}
            initialProfile={result?.profile || { consent_given: consentGiven }}
            initialSessionId={result?.session_id || null}
            initialSchemes={result?.schemes || []}
            onSessionUpdate={setResult}
          />
        </div>
      )}
    </div>
  )
}
