"""In-memory session store — no database, just a dict.

Acceptable for single-user local dev. Sessions lost on server restart.
"""

from __future__ import annotations

from ..models import SessionData

# Global in-memory store
_sessions: dict[str, SessionData] = {}


def create_session(session_id: str) -> SessionData:
    """Create and store a new session."""
    session = SessionData(session_id=session_id)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> SessionData | None:
    """Retrieve a session by ID."""
    return _sessions.get(session_id)


def update_session(session: SessionData) -> None:
    """Update an existing session in the store."""
    _sessions[session.session_id] = session


def delete_session(session_id: str) -> bool:
    """Remove a session. Returns True if it existed."""
    return _sessions.pop(session_id, None) is not None
