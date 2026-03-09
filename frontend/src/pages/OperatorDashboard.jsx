import React, { useState } from 'react';
import '../index.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function OperatorDashboard({ user, onLogout }) {
    const [formData, setFormData] = useState({
        age: '', gender: 'female', income_level: '', state: 'Maharashtra', occupation: '', caste: 'general'
    });
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const queryText = `I am a ${formData.age} year old ${formData.gender} ${formData.occupation} from ${formData.state}. I earn ${formData.income_level} per year and belong to ${formData.caste} category.`;
            const res = await fetch(`${API_BASE}/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${user.accessToken}`,
                },
                body: JSON.stringify({ query: queryText, lang: 'en' }),
            });
            if (res.ok) {
                setResult(await res.json());
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="operator-dashboard">
            <header className="op-header">
                <h2>CSC Operator Dashboard</h2>
                <div className="op-header-actions">
                    <span className="op-badge">Operator Mode</span>
                    <button onClick={onLogout} className="op-btn-outline">Logout</button>
                </div>
            </header>

            <div className="op-layout">
                <div className="op-sidebar">
                    <h3>New Citizen Entry</h3>
                    <form onSubmit={handleSubmit} className="op-form">
                        <div className="op-form-group">
                            <label>Age</label>
                            <input type="number" required value={formData.age} onChange={e => setFormData({ ...formData, age: e.target.value })} />
                        </div>
                        <div className="op-form-group">
                            <label>Gender</label>
                            <select value={formData.gender} onChange={e => setFormData({ ...formData, gender: e.target.value })}>
                                <option value="female">Female</option>
                                <option value="male">Male</option>
                                <option value="other">Other</option>
                            </select>
                        </div>
                        <div className="op-form-group">
                            <label>Occupation</label>
                            <input type="text" required placeholder="e.g. Farmer, Student" value={formData.occupation} onChange={e => setFormData({ ...formData, occupation: e.target.value })} />
                        </div>
                        <div className="op-form-group">
                            <label>Annual Income (₹)</label>
                            <input type="number" required value={formData.income_level} onChange={e => setFormData({ ...formData, income_level: e.target.value })} />
                        </div>
                        <div className="op-form-group">
                            <label>State</label>
                            <input type="text" required value={formData.state} onChange={e => setFormData({ ...formData, state: e.target.value })} />
                        </div>
                        <div className="op-form-group">
                            <label>Caste Category</label>
                            <select value={formData.caste} onChange={e => setFormData({ ...formData, caste: e.target.value })}>
                                <option value="general">General</option>
                                <option value="obc">OBC</option>
                                <option value="sc">SC</option>
                                <option value="st">ST</option>
                            </select>
                        </div>
                        <button type="submit" disabled={loading} className="op-btn-primary">
                            {loading ? 'Processing...' : 'Find Schemes'}
                        </button>
                    </form>
                </div>

                <div className="op-main">
                    <h3>Results</h3>
                    {!result && !loading && <div className="op-empty">Submit form to view eligible schemes.</div>}
                    {loading && <div className="spinner"></div>}
                    {result && (
                        <div className="op-results">
                            <p>Found <strong>{result.schemes.length}</strong> schemes for this profile.</p>
                            <div className="op-grid">
                                {result.schemes.map(s => (
                                    <div key={s.id} className="op-card">
                                        <h4>{s.name_en}</h4>
                                        <div className="op-card-body">
                                            <p className="op-benefit">{s.benefit_description}</p>
                                            <p className="op-reason">✓ {s.eligibility_reason}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
