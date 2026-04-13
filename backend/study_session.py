"""
Sphinx-SCA — Study Mode: Session Management
============================================
Handles all in-memory session state for Study Mode.

Responsibilities:
    - Create, retrieve, update, and end study sessions
    - Track student attempts and feedback
    - Manage hint usage with a hard limit
    - Track weak concepts without duplicates
    - Enforce valid phase transitions
    - Auto-cleanup expired sessions
"""

from typing import TypedDict, List, Optional, Literal
import uuid
from datetime import datetime

# ─────────────────────────────────────────────
# SUPPORTING TYPES
# ─────────────────────────────────────────────

class AttemptRecord(TypedDict):
    """Represents a single student attempt and its feedback."""
    attempt:   str
    feedback:  str
    correct:   bool
    timestamp: str


class PracticeProblem(TypedDict):
    """Represents a generated practice problem."""
    question:   str
    difficulty: str   # "similar" | "harder"
    branch:     str


# ─────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────

class StudySessionState(TypedDict):
    """
    The complete state of a single study session.
    All fields are required and must be initialized via create_session().
    """
    session_id: str
    question:   str
    branch:     str

    # Progress Tracking
    phase:           Literal["explain", "socratic", "check", "practice", "summary"]
    hints_used:      int
    attempt:         str
    attempt_history: List[AttemptRecord]

    # AI Generated Content
    concept_explanation: str
    socratic_questions:  List[str]
    mistake_feedback:    str
    practice_problems:   List[PracticeProblem]

    # Performance Summary
    problems_solved: int
    weak_concepts:   List[str]
    session_start:   str


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

MAX_HINTS:           int = 3
SESSION_TTL_MINUTES: int = 60

VALID_PHASES = ["explain", "socratic", "check", "practice", "summary"]

# ─────────────────────────────────────────────
# IN-MEMORY STORE
# ─────────────────────────────────────────────

sessions_db: dict[str, StudySessionState] = {}


# ─────────────────────────────────────────────
# CORE CRUD FUNCTIONS
# ─────────────────────────────────────────────

def create_session(question: str, branch: str) -> str:
    """
    Initializes a new study session with default values.
    Also triggers cleanup of any expired sessions.

    Args:
        question: The math problem the student is studying.
        branch:   The math branch (e.g. algebra, calculus).

    Returns:
        A unique session_id string (UUID4).
    """
    cleanup_expired_sessions()
    session_id = str(uuid.uuid4())
    sessions_db[session_id] = StudySessionState(
        session_id          = session_id,
        question            = question,
        branch              = branch,
        phase               = "explain",
        hints_used          = 0,
        attempt             = "",
        attempt_history     = [],
        concept_explanation = "",
        socratic_questions  = [],
        mistake_feedback    = "",
        practice_problems   = [],
        problems_solved     = 0,
        weak_concepts       = [],
        session_start       = datetime.now().isoformat(),
    )
    return session_id


def get_session(session_id: str) -> Optional[StudySessionState]:
    """
    Retrieves an active session by its ID.

    Args:
        session_id: The UUID of the target session.

    Returns:
        The StudySessionState dict, or None if not found.
    """
    return sessions_db.get(session_id)


def update_session(session_id: str, updates: dict) -> bool:
    """
    Safely updates one or more fields in an existing session.
    Validates all keys against the schema before applying any changes.
    Updates field-by-field to prevent accidental bulk overwrites.

    Args:
        session_id: The UUID of the target session.
        updates:    A dict of field names and their new values.

    Returns:
        True if the update succeeded.

    Raises:
        KeyError:  If any key in updates is not a valid session field.
        ValueError: If the session does not exist.
    """
    if session_id not in sessions_db:
        raise ValueError(f"Session '{session_id}' not found.")

    valid_keys = set(StudySessionState.__annotations__.keys())
    invalid    = [k for k in updates if k not in valid_keys]
    if invalid:
        raise KeyError(f"Invalid session fields: {invalid}")

    for key, value in updates.items():
        sessions_db[session_id][key] = value

    return True


def end_session(session_id: str) -> bool:
    """
    Removes a session from the store to free memory.

    Args:
        session_id: The UUID of the session to remove.

    Returns:
        True if the session existed and was deleted, False otherwise.
    """
    if session_id in sessions_db:
        del sessions_db[session_id]
        return True
    return False


# ─────────────────────────────────────────────
# PHASE MANAGEMENT
# ─────────────────────────────────────────────

def set_phase(session_id: str, phase: str) -> bool:
    """
    Safely transitions the session to a new phase.
    Rejects any phase value not in VALID_PHASES.

    Args:
        session_id: The UUID of the target session.
        phase:      The new phase value.

    Returns:
        True if the phase was updated successfully.

    Raises:
        ValueError: If the phase is invalid or the session doesn't exist.
    """
    if phase not in VALID_PHASES:
        raise ValueError(f"Invalid phase '{phase}'. Must be one of: {VALID_PHASES}")

    if session_id not in sessions_db:
        raise ValueError(f"Session '{session_id}' not found.")

    sessions_db[session_id]["phase"] = phase
    return True


# ─────────────────────────────────────────────
# ATTEMPT TRACKING
# ─────────────────────────────────────────────

def add_attempt(session_id: str, attempt: str, feedback: str, correct: bool) -> bool:
    """
    Records a student's answer attempt and its feedback.
    Appends to attempt_history, updates the current attempt,
    and increments problems_solved when the attempt is correct.

    Args:
        session_id: The UUID of the target session.
        attempt:    The student's answer text.
        feedback:   The AI-generated feedback for this attempt.
        correct:    Whether the attempt was correct.

    Returns:
        True if the attempt was recorded successfully.

    Raises:
        ValueError: If the session does not exist.
    """
    if session_id not in sessions_db:
        raise ValueError(f"Session '{session_id}' not found.")

    record: AttemptRecord = {
        "attempt":   attempt,
        "feedback":  feedback,
        "correct":   correct,
        "timestamp": datetime.now().isoformat(),
    }

    sessions_db[session_id]["attempt_history"].append(record)
    sessions_db[session_id]["attempt"] = attempt

    if correct:
        sessions_db[session_id]["problems_solved"] += 1

    return True


# ─────────────────────────────────────────────
# HINT MANAGEMENT
# ─────────────────────────────────────────────

def can_use_hint(session_id: str) -> bool:
    """
    Checks whether the student is allowed to request another hint.

    Args:
        session_id: The UUID of the target session.

    Returns:
        True if hints_used < MAX_HINTS, False otherwise.
    """
    session = get_session(session_id)
    if not session:
        return False
    return session["hints_used"] < MAX_HINTS


def use_hint(session_id: str) -> bool:
    """
    Increments the hint counter for a session if the limit hasn't been reached.

    Args:
        session_id: The UUID of the target session.

    Returns:
        True if a hint was consumed successfully.

    Raises:
        ValueError: If the session doesn't exist or MAX_HINTS is already reached.
    """
    if session_id not in sessions_db:
        raise ValueError(f"Session '{session_id}' not found.")

    if not can_use_hint(session_id):
        raise ValueError(f"Hint limit reached ({MAX_HINTS}/{MAX_HINTS}).")

    sessions_db[session_id]["hints_used"] += 1
    return True


# ─────────────────────────────────────────────
# WEAK CONCEPT TRACKING
# ─────────────────────────────────────────────

def add_weak_concept(session_id: str, concept: str) -> bool:
    """
    Adds a concept to the student's weak_concepts list.
    Duplicate concepts are silently ignored.

    Args:
        session_id: The UUID of the target session.
        concept:    The name of the concept to flag (e.g. 'quadratic formula').

    Returns:
        True if the concept was added, False if it was already present.

    Raises:
        ValueError: If the session does not exist.
    """
    if session_id not in sessions_db:
        raise ValueError(f"Session '{session_id}' not found.")

    concept = concept.strip().lower()
    existing = sessions_db[session_id]["weak_concepts"]

    if concept in existing:
        return False

    sessions_db[session_id]["weak_concepts"].append(concept)
    return True


# ─────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────

def get_active_sessions_count() -> int:
    """
    Returns the total number of currently active sessions in memory.

    Returns:
        Integer count of active sessions.
    """
    return len(sessions_db)


def cleanup_expired_sessions() -> int:
    """
    Scans and removes all sessions older than SESSION_TTL_MINUTES.
    Uses total_seconds() for accurate duration calculation across hour boundaries.
    Called automatically on every create_session().

    Returns:
        The number of sessions that were removed.
    """
    now = datetime.now()
    expired = [
        sid for sid, s in sessions_db.items()
        if (now - datetime.fromisoformat(s["session_start"])).total_seconds()
           > SESSION_TTL_MINUTES * 60
    ]
    for sid in expired:
        del sessions_db[sid]
    return len(expired)
