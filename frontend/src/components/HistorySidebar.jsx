import { useState } from 'react';

export default function HistorySidebar({ history, currentSessionId, onSelect, onDelete, onRename, onNewChat, isOpen, setIsOpen }) {
    const [editingId, setEditingId] = useState(null);
    const [editTitle, setEditTitle] = useState('');

    const handleRenameSubmit = (id, e) => {
        e.preventDefault();
        if (editTitle.trim()) {
            onRename(id, editTitle.trim());
        }
        setEditingId(null);
    };

    const startEditing = (item, e) => {
        e.stopPropagation();
        setEditingId(item.session_id);
        setEditTitle(item.title || item.last_query || 'Chat Session');
    };

    const handleDelete = (id, e) => {
        e.stopPropagation();
        if (window.confirm('Are you sure you want to delete this chat?')) {
            onDelete(id);
        }
    };

    return (
        <>
            {/* Mobile overlay */}
            {isOpen && <div className="sidebar-overlay" onClick={() => setIsOpen(false)} />}

            <div className={`history-sidebar ${isOpen ? 'open' : ''}`}>
                <div className="sidebar-header">
                    <button className="new-chat-btn" onClick={() => { onNewChat(); setIsOpen(false); }}>
                        <span className="icon">➕</span> New Chat
                    </button>
                    <button className="close-sidebar-btn" onClick={() => setIsOpen(false)}>×</button>
                </div>

                <div className="history-list">
                    {!Array.isArray(history) || history.length === 0 ? (
                        <div className="empty-history">No previous chats</div>
                    ) : (
                        history.map((item) => (
                            <div
                                key={item.session_id}
                                className={`history-item ${item.session_id === currentSessionId ? 'active' : ''}`}
                                onClick={() => { onSelect(item); setIsOpen(false); }}
                            >
                                <span className="icon">💬</span>

                                {editingId === item.session_id ? (
                                    <form onSubmit={(e) => handleRenameSubmit(item.session_id, e)} className="rename-form">
                                        <input
                                            type="text"
                                            value={editTitle}
                                            onChange={(e) => setEditTitle(e.target.value)}
                                            onClick={e => e.stopPropagation()}
                                            autoFocus
                                            onBlur={() => setEditingId(null)}
                                        />
                                    </form>
                                ) : (
                                    <div className="history-title" title={item.last_query}>
                                        {item.title || item.last_query || 'Chat Session'}
                                    </div>
                                )}

                                <div className="history-actions">
                                    <button
                                        onClick={(e) => startEditing(item, e)}
                                        className="action-btn"
                                        title="Rename"
                                    >
                                        ✏️
                                    </button>
                                    <button
                                        onClick={(e) => handleDelete(item.session_id, e)}
                                        className="action-btn"
                                        title="Delete"
                                    >
                                        🗑️
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </>
    );
}
