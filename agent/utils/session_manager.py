"""
Session State Management for Voice Assistant
Manages stateful voice assistant with sleep/wake behavior.

Features:
- Assistant States: SLEEP_MODE, ACTIVE_MODE, PROCESSING
- Silence Detection (timeout logic)
- Exit Keyword Detection
- Per-connection session state

State Transitions:
1. SLEEP_MODE → waiting for wake word
2. ACTIVE_MODE → processing user speech continuously  
3. PROCESSING → STT + NLP + TTS running (sub-state of ACTIVE)

Exit Conditions:
- Silence > 60 seconds → SLEEP_MODE
- Exit keyword detected → SLEEP_MODE
- User explicitly exits
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class AssistantState(Enum):
    """Voice assistant states"""
    SLEEP_MODE = "sleep_mode"       
    ACTIVE_MODE = "active_mode"    
    PROCESSING = "processing"       


# Exit keywords that trigger sleep mode
EXIT_KEYWORDS: Set[str] = {
    "bye", "goodbye", "exit", "quit", "stop", "okay bye", "you can quit now"
}

# Minimum confidence for speech to be considered meaningful
MIN_SPEECH_CONFIDENCE = 0.65


@dataclass
class SessionState:
    """
    Per-connection session state.
    Tracks state, last speech timestamp, and conversation context.
    """
    session_id: str
    state: AssistantState = AssistantState.SLEEP_MODE
    last_speech_timestamp: float = field(default_factory=time.time)
    conversation_context: dict = field(default_factory=dict)
    silence_timeout_seconds: float = 60.0
    # Performance tracking
    total_processed_turns: int = 0
    error_count: int = 0
    
    def __post_init__(self):
        """Reset timestamps on creation"""
        self.last_speech_timestamp = time.time()
    
    def update_speech_time(self):
        """Update last speech timestamp to current time"""
        self.last_speech_timestamp = time.time()
    
    def get_silence_duration(self) -> float:
        """Get seconds since last meaningful speech"""
        return time.time() - self.last_speech_timestamp
    
    def should_sleep(self) -> bool:
        """Check if silence duration exceeds timeout"""
        if self.state == AssistantState.SLEEP_MODE:
            return False
        return self.get_silence_duration() > self.silence_timeout_seconds
    
    def transition_to(self, new_state: AssistantState):
        """Log and execute state transition"""
        old_state = self.state
        if old_state != new_state:
            logger.info(f"Session {self.session_id}: {old_state.value} → {new_state.value}")
            self.state = new_state
            
            # Reset speech timestamp on sleep
            if new_state == AssistantState.SLEEP_MODE:
                self.last_speech_timestamp = time.time()


class SessionManager:
    """
    Manages multiple client sessions.
    Each WebSocket connection gets its own SessionState.
    """
    
    def __init__(self, silence_timeout: float = 60.0):
        self.silence_timeout = silence_timeout
        self._sessions: Dict[str, SessionState] = {}
        self._lock = asyncio.Lock()
    
    def create_session(self, session_id: str) -> SessionState:
        """Create new session for a client"""
        session = SessionState(
            session_id=session_id,
            silence_timeout_seconds=self.silence_timeout
        )
        self._sessions[session_id] = session
        logger.debug(f"Created session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get existing session"""
        return self._sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """Remove session on disconnect"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.debug(f"Removed session: {session_id}")
    
    async def check_all_sessions(self):
        """Check all active sessions for sleep condition"""
        sleep_sessions = []
        
        async with self._lock:
            for session_id, session in self._sessions.items():
                if session.state != AssistantState.SLEEP_MODE:
                    if session.should_sleep():
                        logger.info(f"Session {session_id}: Silence timeout, going to sleep")
                        sleep_sessions.append(session_id)
        
        return sleep_sessions
    
    @property
    def active_session_count(self) -> int:
        """Count of non-sleep sessions"""
        return sum(
            1 for s in self._sessions.values() 
            if s.state != AssistantState.SLEEP_MODE
        )


def detect_exit_keyword(transcript: str) -> bool:
    """
    Detect exit keywords in transcript (case-insensitive).
    Handles partial sentences like "okay bye", "you can quit now".
    
    Args:
        transcript: STT output text
        
    Returns:
        True if exit keyword detected
    """
    if not transcript:
        return False
    
    text_lower = transcript.lower().strip()
    
    for keyword in EXIT_KEYWORDS:
        if keyword in text_lower:
            logger.info(f"Exit keyword detected: '{keyword}' in '{transcript}'")
            return True
    
    return False


def is_meaningful_speech(transcript: str, confidence: float = 0.0) -> bool:
    """
    Check if speech is meaningful.
    
    Args:
        transcript: STT transcript text
        confidence: STT confidence score
        
    Returns:
        True if speech is meaningful
    """
    if not transcript:
        return False
    
    cleaned = transcript.strip()
    if not cleaned:
        return False
    
    if confidence > 0 and confidence < MIN_SPEECH_CONFIDENCE:
        logger.debug(f"Low confidence speech ignored: {confidence:.2f}")
        return False
    
    return True


# Backwards compatibility
SessionStateMachine = SessionManager
