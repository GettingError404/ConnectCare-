"""
VoiceOS REST API
FastAPI-based HTTP interface for the voice assistant pipeline.
Supports: audio upload, text input, health checks, metrics, and WebSocket streaming.
"""

import asyncio
import base64
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline.orchestrator import VoiceAssistantPipeline
from config.settings import load_settings
from utils.session_manager import (
    SessionManager,
    AssistantState,
    detect_exit_keyword,
    is_meaningful_speech
)

logger = logging.getLogger(__name__)

# Global pipeline instance
pipeline: Optional[VoiceAssistantPipeline] = None

# Session manager for WebSocket connections
session_manager: Optional[SessionManager] = None

# Settings
settings = load_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle"""
    global pipeline, session_manager, settings
    settings = load_settings()

    # Ensure Rasa server is reachable (optionally auto-start via conda env)
    # This keeps the existing HTTP integration in pipeline/nlp_hybrid.py working.
    rasa_launcher = None
    try:
        from utils.rasa_launcher import RasaLauncherConfig, RasaServerLauncher

        cfg = RasaLauncherConfig(
            conda_env_name=settings.nlp.rasa_conda_env_name,
            rasa_workdir=settings.nlp.rasa_workdir,
            rasa_url=settings.nlp.rasa_url,
            force_start=settings.nlp.rasa_force_start,
        )
        rasa_launcher = RasaServerLauncher(cfg)
        await rasa_launcher.start_if_needed()
    except Exception as e:
        # If Rasa is already running or launcher fails, we still let the API start.
        # NLP stage will handle unavailability.
        logger.warning(f"Rasa launcher skipped/failed: {e}")

    pipeline = VoiceAssistantPipeline(settings)

    # Initialize session manager with silence timeout from settings
    session_manager = SessionManager(
        silence_timeout=settings.session.silence_timeout_seconds
    )
    logger.info(f"VoiceOS API started (silence timeout: {settings.session.silence_timeout_seconds}s)")
    yield

    if rasa_launcher is not None:
        try:
            await rasa_launcher.shutdown()
        except Exception:
            pass

    logger.info("VoiceOS API shutting down")



app = FastAPI(
    title="VoiceOS API",
    description="Production-grade voice assistant pipeline API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────

class TextRequest(BaseModel):
    text: str
    language: str = "auto"
    session_id: Optional[str] = None


class AudioRequest(BaseModel):
    audio_base64: str
    format: str = "wav"
    language: str = "auto"
    sample_rate: int = 16000


class PipelineResponse(BaseModel):
    session_id: str
    transcript: Optional[str]
    detected_language: str
    translated_text: Optional[str]
    intent: Optional[str]
    entities: dict
    sentiment: Optional[dict]
    skill_name: Optional[str]
    response_text: Optional[str]
    response_audio_base64: Optional[str]
    latency_ms: float
    pipeline_trace: list
    error: Optional[str]


# ─────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    return pipeline.get_pipeline_status()


@app.get("/metrics")
async def get_metrics():
    """Get pipeline performance metrics"""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    return pipeline.metrics.get_summary()


@app.post("/process/text", response_model=PipelineResponse)
async def process_text(request: TextRequest):
    """
    Process a text input through the full pipeline.
    Useful for testing and chat-mode integration.
    """
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    ctx = await pipeline.process_text_direct(request.text, request.language)

    audio_b64 = None
    if ctx.response_audio:
        audio_b64 = base64.b64encode(ctx.response_audio).decode("utf-8")

    return PipelineResponse(
        session_id=ctx.session_id,
        transcript=ctx.transcript,
        detected_language=ctx.detected_language,
        translated_text=ctx.translated_text,
        intent=ctx.intent,
        entities=ctx.entities,
        sentiment=ctx.sentiment,
        skill_name=ctx.skill_name,
        response_text=ctx.response_text,
        response_audio_base64=audio_b64,
        latency_ms=ctx.latency_ms,
        pipeline_trace=ctx.pipeline_trace,
        error=ctx.error
    )


@app.post("/process/audio", response_model=PipelineResponse)
async def process_audio(request: AudioRequest):
    """
    Process a base64-encoded audio input through the full pipeline.
    """
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        audio_bytes = base64.b64decode(request.audio_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 audio data")

    ctx = await pipeline.process_audio_direct(audio_bytes)

    audio_b64 = None
    if ctx.response_audio:
        audio_b64 = base64.b64encode(ctx.response_audio).decode("utf-8")

    return PipelineResponse(
        session_id=ctx.session_id,
        transcript=ctx.transcript,
        detected_language=ctx.detected_language,
        translated_text=ctx.translated_text,
        intent=ctx.intent,
        entities=ctx.entities,
        sentiment=ctx.sentiment,
        skill_name=ctx.skill_name,
        response_text=ctx.response_text,
        response_audio_base64=audio_b64,
        latency_ms=ctx.latency_ms,
        pipeline_trace=ctx.pipeline_trace,
        error=ctx.error
    )


@app.post("/process/audio-upload", response_model=PipelineResponse)
async def process_audio_upload(file: UploadFile = File(...)):
    """Process an uploaded audio file"""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    audio_bytes = await file.read()
    ctx = await pipeline.process_audio_direct(audio_bytes)

    audio_b64 = None
    if ctx.response_audio:
        audio_b64 = base64.b64encode(ctx.response_audio).decode("utf-8")

    return PipelineResponse(
        session_id=ctx.session_id,
        transcript=ctx.transcript,
        detected_language=ctx.detected_language,
        translated_text=ctx.translated_text,
        intent=ctx.intent,
        entities=ctx.entities,
        sentiment=ctx.sentiment,
        skill_name=ctx.skill_name,
        response_text=ctx.response_text,
        response_audio_base64=audio_b64,
        latency_ms=ctx.latency_ms,
        pipeline_trace=ctx.pipeline_trace,
        error=ctx.error
    )


@app.get("/skills")
async def list_skills():
    """List all registered skills"""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    return {"skills": pipeline.skill_manager.list_skills()}


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming pipeline execution with state management.
    Sends real-time updates as each stage completes.

    State Machine:
    - SLEEP_MODE: Waiting for wake word detection
    - ACTIVE_MODE: Processing user speech continuously
    - PROCESSING: STT + NLP + TTS running
    
    Protocol:
    - Client sends: {"type": "text", "text": "...", "language": "auto"}
    - Client sends: {"type": "audio", "data": "base64..."} (audio streaming)
    - Client sends: {"type": "wake_word"} - signal wake word detected
    - Server sends: {"state": "sleep_mode"} or {"state": "active_mode"}
    - Server sends: {"stage": "stt", "data": {...}}
    - Server sends: {"stage": "complete", "response": "..."}
    """
    await websocket.accept()
    
    # Generate unique session ID for this connection
    session_id = str(uuid.uuid4())
    
    # Create session state
    session = session_manager.create_session(session_id)
    logger.info(f"WebSocket connection opened: {session_id}")
    
    # Send initial state
    await websocket.send_json({
        "type": "state_change",
        "state": session.state.value,
        "session_id": session_id
    })

    try:
        while True:
            # Check for silence timeout
            if session.state != AssistantState.SLEEP_MODE:
                if session.should_sleep():
                    logger.info(f"Session {session_id}: Silence timeout, going to sleep")
                    session.transition_to(AssistantState.SLEEP_MODE)
                    await websocket.send_json({
                        "type": "state_change",
                        "state": "sleep_mode",
                        "reason": "silence_timeout"
                    })
                    continue
            
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            msg_type = data.get("type")

            # ─────────────────────────────────────────────────────────
            # WAKE WORD - Transition from SLEEP to ACTIVE
            # ─────────────────────────────────────────────────────────
            if msg_type == "wake_word":
                if session.state == AssistantState.SLEEP_MODE:
                    session.transition_to(AssistantState.ACTIVE_MODE)
                    session.update_speech_time()
                    await websocket.send_json({
                        "type": "state_change",
                        "state": "active_mode",
                        "reason": "wake_word_detected"
                    })
                    logger.info(f"Session {session_id}: Wake word detected, ACTIVE_MODE")
                continue

            # In SLEEP_MODE, ignore everything except wake word
            if session.state == AssistantState.SLEEP_MODE:
                logger.debug(f"Session {session_id}: Ignoring input in SLEEP_MODE")
                await websocket.send_json({
                    "type": "status",
                    "message": "Waiting for wake word"
                })
                continue

            # ─────────────────────────────────────────────────────────
            # TEXT INPUT - Process through pipeline
            # ─────────────────────────────────────────────────────────
            if msg_type == "text":
                text = data.get("text", "")
                language = data.get("language", "auto")

                if not is_meaningful_speech(text):
                    logger.debug(f"Session {session_id}: Empty or low-confidence text ignored")
                    continue

                # Update speech timestamp
                session.update_speech_time()
                
                # Transition to processing
                session.transition_to(AssistantState.PROCESSING)

                # Send processing started event
                await websocket.send_json({
                    "stage": "started",
                    "data": {"text": text, "language": language}
                })

                # Process through pipeline
                ctx = await pipeline.process_text_direct(text, language)

                # Send each stage trace
                for trace_item in ctx.pipeline_trace:
                    await websocket.send_json({
                        "stage": trace_item["stage"],
                        "timestamp_ms": trace_item["timestamp"] * 1000,
                        "data": trace_item["data"]
                    })

                # ─────────────────────────────────────────────────────────
                # EXIT KEYWORD DETECTION
                # ─────────────────────────────────────────────────────────
                response_text = ctx.response_text or ""
                transcript = ctx.transcript or ""
                
                # Check for exit keywords in transcript
                if detect_exit_keyword(transcript):
                    logger.info(f"Session {session_id}: Exit keyword detected")
                    session.transition_to(AssistantState.SLEEP_MODE)
                    
                    # Send goodbye response
                    await websocket.send_json({
                        "stage": "complete",
                        "session_id": ctx.session_id,
                        "response_text": "Goodbye, going to sleep",
                        "intent": ctx.intent,
                        "sentiment": ctx.sentiment,
                        "latency_ms": ctx.latency_ms,
                        "exiting": True,
                        "error": ctx.error
                    })
                    
                    # Send state change
                    await websocket.send_json({
                        "type": "state_change",
                        "state": "sleep_mode",
                        "reason": "exit_keyword"
                    })
                    continue

                # Back to ACTIVE after processing
                session.transition_to(AssistantState.ACTIVE_MODE)

                # Send final response
                await websocket.send_json({
                    "stage": "complete",
                    "session_id": ctx.session_id,
                    "response_text": response_text,
                    "intent": ctx.intent,
                    "sentiment": ctx.sentiment,
                    "latency_ms": ctx.latency_ms,
                    "error": ctx.error
                })

            # ─────────────────────────────────────────────────────────
            # AUDIO STREAMING - Real-time audio processing
            # ─────────────────────────────────────────────────────────
            elif msg_type == "audio":
                # Decode base64 audio
                audio_base64 = data.get("data", "")
                try:
                    audio_bytes = base64.b64decode(audio_base64)
                except Exception as e:
                    logger.warning(f"Failed to decode audio: {e}")
                    continue

                # Check if meaningful audio (Voice Activity Detection would go here)
                # For now, treat any audio as speech
                session.update_speech_time()
                session.transition_to(AssistantState.PROCESSING)

                # Process audio through pipeline
                ctx = await pipeline.process_audio_direct(audio_bytes)

                # Check for exit keywords
                if detect_exit_keyword(ctx.transcript or ""):
                    logger.info(f"Session {session_id}: Exit keyword in audio")
                    session.transition_to(AssistantState.SLEEP_MODE)
                    
                    await websocket.send_json({
                        "stage": "complete",
                        "response_text": "Goodbye, going to sleep",
                        "exiting": True
                    })
                    
                    await websocket.send_json({
                        "type": "state_change",
                        "state": "sleep_mode",
                        "reason": "exit_keyword"
                    })
                    continue

                # Back to ACTIVE
                session.transition_to(AssistantState.ACTIVE_MODE)

                # Send response
                await websocket.send_json({
                    "stage": "complete",
                    "session_id": ctx.session_id,
                    "response_text": ctx.response_text,
                    "transcript": ctx.transcript,
                    "latency_ms": ctx.latency_ms,
                    "error": ctx.error
                })

            # ─────────────────────────────────────────────────────────
            # PING - Keepalive
            # ─────────────────────────────────────────────────────────
            elif msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "session_id": session_id,
                    "state": session.state.value,
                    "silence_seconds": round(session.get_silence_duration(), 1)
                })

            # ─────────────────────────────────────────────────────────
            # GET_STATE - Request current state
            # ─────────────────────────────────────────────────────────
            elif msg_type == "get_state":
                await websocket.send_json({
                    "type": "state",
                    "session_id": session_id,
                    "state": session.state.value,
                    "silence_seconds": round(session.get_silence_duration(), 1)
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({"stage": "error", "error": str(e)})
    finally:
        # Clean up session
        session_manager.remove_session(session_id)
        logger.debug(f"Session cleaned up: {session_id}")


if __name__ == "__main__":
    import uvicorn
    settings = load_settings()
    uvicorn.run(
        "api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
