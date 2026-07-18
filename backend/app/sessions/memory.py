"""Session store — in-memory with optional S3 persistence.

For local development, sessions live in a Python dict (lost on restart).
For AWS Lambda / serverless, sessions are persisted as JSON files in S3,
enabling stateless function invocations.

Set ``S3_BUCKET_SESSIONS`` in your environment (or in Lambda env vars)
to enable S3 persistence.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import settings
from ..models import SessionData

logger = logging.getLogger(__name__)

# ── Global in-memory store (used only when S3 is NOT configured) ─
_sessions: dict[str, SessionData] = {}

# ── S3 client (lazy-initialised) ────────────────────────────────
_s3_client = None
_s3_lock = threading.Lock()


def _get_s3():
    """Initialise and return a boto3 S3 client (thread-safe)."""
    global _s3_client
    if _s3_client is None:
        with _s3_lock:
            if _s3_client is None:  # double-check
                import boto3
                _s3_client = boto3.client("s3")
    return _s3_client


def _s3_enabled() -> bool:
    """Check whether S3 session storage is configured."""
    return bool(settings.s3_bucket_sessions)


def _s3_key(session_id: str) -> str:
    """Return the S3 object key for a given session ID."""
    return f"sessions/{session_id}.json"


def _session_to_dict(session: SessionData) -> dict:
    """Convert a SessionData object to a JSON-serialisable dict."""
    data = session.model_dump(mode="json")
    # Convert datetime objects to ISO strings
    if "created_at" in data and isinstance(data["created_at"], datetime):
        data["created_at"] = data["created_at"].isoformat()
    return data


def _dict_to_session(data: dict) -> SessionData:
    """Convert a dict (from JSON) back to a SessionData object."""
    # Restore datetime from ISO string
    if "created_at" in data and isinstance(data["created_at"], str):
        data["created_at"] = datetime.fromisoformat(data["created_at"])
    return SessionData(**data)


# ── Public API ───────────────────────────────────────────────────


def create_session(session_id: str) -> SessionData:
    """Create and store a new session.

    In S3 mode, the session is immediately persisted.
    """
    session = SessionData(session_id=session_id)

    if _s3_enabled():
        try:
            s3 = _get_s3()
            s3.put_object(
                Bucket=settings.s3_bucket_sessions,
                Key=_s3_key(session_id),
                Body=json.dumps(_session_to_dict(session), ensure_ascii=False),
                ContentType="application/json",
            )
            logger.debug("Session %s saved to S3", session_id)
        except Exception as exc:
            logger.error("Failed to save session %s to S3: %s", session_id, exc)
            # Fall back to in-memory
            _sessions[session_id] = session
    else:
        _sessions[session_id] = session

    return session


def get_session(session_id: str) -> Optional[SessionData]:
    """Retrieve a session by ID.

    In S3 mode, reads from S3 on every call (enabling stateless Lambda).
    """
    if _s3_enabled():
        try:
            s3 = _get_s3()
            response = s3.get_object(
                Bucket=settings.s3_bucket_sessions,
                Key=_s3_key(session_id),
            )
            body = response["Body"].read().decode("utf-8")
            data = json.loads(body)
            return _dict_to_session(data)
        except s3.exceptions.NoSuchKey:
            return None
        except Exception as exc:
            logger.error("Failed to read session %s from S3: %s", session_id, exc)
            return None
    else:
        return _sessions.get(session_id)


def update_session(session: SessionData) -> None:
    """Update an existing session in the store.

    In S3 mode, overwrites the JSON file in S3.
    """
    session_id = session.session_id

    if _s3_enabled():
        try:
            s3 = _get_s3()
            s3.put_object(
                Bucket=settings.s3_bucket_sessions,
                Key=_s3_key(session_id),
                Body=json.dumps(_session_to_dict(session), ensure_ascii=False),
                ContentType="application/json",
            )
            logger.debug("Session %s updated in S3", session_id)
        except Exception as exc:
            logger.error("Failed to update session %s in S3: %s", session_id, exc)
            # Also update in-memory as fallback
            _sessions[session_id] = session
    else:
        _sessions[session_id] = session


def delete_session(session_id: str) -> bool:
    """Remove a session. Returns True if it existed."""
    if _s3_enabled():
        try:
            s3 = _get_s3()
            # Check if the session exists
            try:
                s3.head_object(
                    Bucket=settings.s3_bucket_sessions,
                    Key=_s3_key(session_id),
                )
            except s3.exceptions.ClientError as exc:
                if exc.response["Error"]["Code"] == "404":
                    return False
                raise

            s3.delete_object(
                Bucket=settings.s3_bucket_sessions,
                Key=_s3_key(session_id),
            )
            return True
        except Exception as exc:
            logger.error("Failed to delete session %s from S3: %s", session_id, exc)
            return False
    else:
        return _sessions.pop(session_id, None) is not None
