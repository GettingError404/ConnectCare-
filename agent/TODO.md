# VoiceOS - Session State Management

Status: ✅ Implementation Complete

## Features Implemented
1. Session State Management with Sleep/Wake behavior
2. Silence Detection (60 second timeout)
3. Exit Keyword Detection
4. WebSocket Integration with state events

## Implementation Steps
- [x] Step 1: Create `utils/session_manager.py` - Session state management module
- [x] Step 2: Add SessionSettings to `config/settings.py`
- [x] Step 3: Update `api.py` WebSocket handler with state management
- [x] Step 4: Verify syntax of all modified files

## Files Created/Modified

### Created: `utils/session_manager.py`
- `AssistantState` enum: SLEEP_MODE, ACTIVE_MODE, PROCESSING
- `SessionState` dataclass: per-connection session with timestamps
- `SessionManager`: manages multiple client sessions
- `detect_exit_keyword()`: case-insensitive exit keyword detection
- `is_meaningful_speech()`: validates speech input

### Modified: `config/settings.py`
- Added `SessionSettings` dataclass with:
  - `silence_timeout_seconds` (default: 60.0)
  - `enable_state_management` (default: True)

### Modified: `api.py`
- Integrated session state into WebSocket `/ws/stream` endpoint
- Added state change events: "sleep_mode", "active_mode"
- Added message types: "wake_word", "audio", "get_state"
- Silence timeout checking in main loop
- Exit keyword detection after STT

## Usage

### WebSocket Protocol
```javascript
// Client → Server
{ "type": "wake_word" }
{ "type": "text", "text": "hello", "language": "auto" }
{ "type": "audio", "data": "base64_audio..." }
{ "type": "ping" }
{ "type": "get_state" }

// Server → Client
{ "type": "state_change", "state": "sleep_mode", "reason": "silence_timeout" }
{ "type": "state_change", "state": "active_mode", "reason": "wake_word_detected" }
{ "stage": "started", "data": {...} }
{ "stage": "complete", "response_text": "..." }
{ "type": "pong", "state": "active_mode", "silence_seconds": 12.5 }
```

### State Transitions
1. Client connects → SLEEP_MODE
2. Client sends "wake_word" → ACTIVE_MODE
3. Client sends "text" → PROCESSING → ACTIVE_MODE
4. Silence > 60s → SLEEP_MODE
5. User says "bye" → SLEEP_MODE

## Environment Variables
- `SESSION_SILENCE_TIMEOUT`: Timeout in seconds (default: 60.0)
- `ENABLE_STATE_MANAGEMENT`: Enable state management (default: True)

