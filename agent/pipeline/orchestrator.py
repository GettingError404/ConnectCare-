"""
VoiceOS Pipeline Orchestrator
Manages the full voice assistant pipeline:
Wake Word → STT → Language Detection → Translation → NLP → Sentiment →
Skill Manager → Action Handler → Response → TTS
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

from pipeline.wake_word import WakeWordDetector
from pipeline.stt import SpeechToText
from pipeline.language import LanguageDetector
from pipeline.translator import Translator
from pipeline.nlp_hybrid import HybridNLP
from pipeline.sentiment import SentimentAnalyzer
from pipeline.skill_manager import SkillManager
from pipeline.action_handler import ActionHandler
from pipeline.response_generator import ResponseGenerator
from pipeline.tts import TextToSpeech
from utils.event_bus import EventBus
from utils.metrics import PipelineMetrics
from config.settings import Settings

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    ERROR = "error"


@dataclass
class PipelineContext:
    """Carries state through the entire pipeline"""
    session_id: str
    raw_audio: Optional[bytes] = None
    transcript: Optional[str] = None
    detected_language: str = "en"
    confidence: float = 0.0
    translated_text: Optional[str] = None  # English pivot
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    sentiment: Optional[Dict[str, Any]] = None
    skill_name: Optional[str] = None
    action_result: Optional[Dict[str, Any]] = None
    response_text: Optional[str] = None
    response_audio: Optional[bytes] = None
    pipeline_trace: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    start_time: float = field(default_factory=time.time)

    def trace(self, stage: str, data: Dict[str, Any]):
        self.pipeline_trace.append({
            "stage": stage,
            "timestamp": time.time() - self.start_time,
            "data": data
        })

    @property
    def latency_ms(self) -> float:
        return (time.time() - self.start_time) * 1000


class VoiceAssistantPipeline:
    """
    Production-grade voice assistant pipeline orchestrator.
    Manages modular pipeline with error recovery, metrics, and event streaming.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.state = PipelineState.IDLE
        self.event_bus = EventBus()
        self.metrics = PipelineMetrics()

        # Initialize pipeline stages
        self.wake_word = WakeWordDetector(settings.wake_word)
        self.stt = SpeechToText(settings.stt)
        self.language_detector = LanguageDetector(settings.language)
        self.translator = Translator(settings.translation)
        self.nlp = HybridNLP(settings.nlp)
        self.sentiment = SentimentAnalyzer(settings.sentiment)
        self.skill_manager = SkillManager(settings.skills)
        self.action_handler = ActionHandler(settings.actions)
        self.response_generator = ResponseGenerator(settings.response)
        self.tts = TextToSpeech(settings.tts)

        logger.debug("VoiceOS Pipeline initialized with all stages")

    async def run(self):
        """Main pipeline loop - continuously listens and processes"""
        logger.debug("Starting VoiceOS Pipeline...")
        self.event_bus.emit("pipeline_started")

        while True:
            try:
                await self._pipeline_cycle()
            except asyncio.CancelledError:
                logger.debug("Pipeline shutdown requested")
                break
            except Exception as e:
                logger.error(f"Pipeline cycle error: {e}", exc_info=True)
                self.metrics.record_error("pipeline_cycle")
                await asyncio.sleep(1)  # Brief recovery pause

    async def _pipeline_cycle(self):
        """Execute one full pipeline cycle"""
        self.state = PipelineState.IDLE

        # Stage 1: Wake Word Detection
        audio_chunk = await self.wake_word.listen_for_wake_word()
        if audio_chunk is None:
            return

        session_id = f"sess_{int(time.time() * 1000)}"

        self.event_bus.emit("wake_word_detected", {"session_id": session_id})
        while True:
            ctx = PipelineContext(session_id=session_id, raw_audio=audio_chunk)
            self.state = PipelineState.PROCESSING

            try:
                await self._process_pipeline(ctx)

                # 👉 Exit conditions
                if self._should_exit_conversation(ctx):
                    print("👋 Goodbye!\n")
                    break

                # 🎤 Listen again WITHOUT wake word
                print("🎤 Listening for next command...")
                try:
                    audio_chunk = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.wake_word.listen_continuous
                    )
                    if not audio_chunk:
                        logger.debug("No audio captured, retrying...")
                        continue
                except Exception as e:
                    logger.error(f"Continuous listen error: {e}")
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                ctx.error = str(e)
                ctx.trace("error", {"message": str(e)})
                logger.error(f"Pipeline error in session {session_id}: {e}")
                await self._handle_error(ctx)
            finally:
                self.metrics.record_session(ctx)
                self.state = PipelineState.IDLE

    async def process_audio_direct(self, audio_bytes: bytes) -> PipelineContext:
        """
        Process audio directly (useful for API/testing).
        Bypasses wake word detection.
        """
        session_id = f"api_{int(time.time() * 1000)}"
        ctx = PipelineContext(session_id=session_id, raw_audio=audio_bytes)
        await self._process_pipeline(ctx)
        return ctx

    async def process_chat(self, text: str) -> PipelineContext:
        """
        CLEAN chatbot pipeline (NO voice, NO translation)
        """
        session_id = f"chat_{int(time.time() * 1000)}"
        ctx = PipelineContext(session_id=session_id, transcript=text)

        try:
            # Skip language detection → assume English
            ctx.detected_language = "en"
            ctx.translated_text = text

            # NLP (force LLM if possible)
            result = await self.nlp.process(text)
            ctx.intent = result.intent
            ctx.entities = result.entities

            # Sentiment
            sentiment = await self.sentiment.analyze(text)
            ctx.sentiment = {
                "label": sentiment.label,
                "score": sentiment.score
            }

            # Skill routing
            skill = await self.skill_manager.route(
                intent=ctx.intent,
                entities=ctx.entities,
                sentiment=ctx.sentiment,
                transcript=text
            )
            ctx.skill_name = skill.name

            # Action
            ctx.action_result = await self.action_handler.execute(
                skill_name=ctx.skill_name,
                intent=ctx.intent,
                entities=ctx.entities,
                context={"text": text}
            )

            # Response
            response = await self.response_generator.generate(
                action_result=ctx.action_result,
                intent=ctx.intent,
                sentiment=ctx.sentiment,
                skill_name=ctx.skill_name,
                context={}
            )

            ctx.response_text = response.text

        except Exception as e:
            ctx.error = str(e)
            ctx.response_text = "Sorry, something went wrong."

        return ctx

    async def process_text_direct(self, text: str, language: str = "auto") -> PipelineContext:
        """
        Process text directly (useful for testing/chat mode).
        Bypasses STT.
        """
        session_id = f"text_{int(time.time() * 1000)}"
        ctx = PipelineContext(session_id=session_id, transcript=text)
        ctx.detected_language = language

        # Skip STT and language detection if language is provided
        if language != "auto":
            await self._run_from_translation(ctx)
        else:
            await self._stage_language_detection(ctx)
            await self._run_from_translation(ctx)

        return ctx

    def _should_exit_conversation(self, ctx: PipelineContext) -> bool:
        """Decide when to exit conversation mode"""

        if not ctx.transcript:
            return True

        text = ctx.transcript.lower()

        EXIT_KEYWORDS = ["bye", "exit", "stop", "quit", "goodbye"]

        if any(word in text for word in EXIT_KEYWORDS):
            return True

        return False

    async def _process_pipeline(self, ctx: PipelineContext):
        """Execute all pipeline stages in order"""

        # Stage 2: Speech-to-Text (Vosk)
        await self._stage_stt(ctx)
        if ctx.error:
            return

        # Stage 3: Language Detection
        await self._stage_language_detection(ctx)

        # Run from translation onwards
        await self._run_from_translation(ctx)

    async def _run_from_translation(self, ctx: PipelineContext):
        """Run pipeline stages from translation onwards"""

        # Stage 4: Translation to English (pivot language)
        await self._stage_translation(ctx)

        # Stage 5: Hybrid NLP (Rasa + Ollama fallback)
        await self._stage_nlp(ctx)
        if ctx.error:
            return

        # If Ollama gave a direct response, skip skill/action and go straight to TTS
        if getattr(ctx, "skip_skill", False) and ctx.response_text:
            print(f"🤖 Assistant: {ctx.response_text}")
            await self._stage_tts(ctx)

            logger.debug(f"✅ Pipeline complete (LLM direct): {ctx.latency_ms:.1f}ms")
            self.state = PipelineState.IDLE
            self.event_bus.emit("pipeline_complete", {
                "session_id": ctx.session_id,
                "latency_ms": ctx.latency_ms
            })
            return

        # Stage 6: Sentiment Analysis
        await self._stage_sentiment(ctx)

        # Stage 7: Skill Manager
        await self._stage_skill_manager(ctx)

        # Stage 8: Action Handler
        await self._stage_action_handler(ctx)
        if ctx.error:
            return

        # Stage 9: Response Generation
        await self._stage_response_generation(ctx)

        # Stage 10: Translate response back to user language
        await self._stage_response_translation(ctx)

        # Stage 11: TTS
        await self._stage_tts(ctx)

        logger.debug(f"✅ Pipeline complete: {ctx.latency_ms:.1f}ms | Response: {ctx.response_text[:50]}...")

        self.state = PipelineState.IDLE
        self.event_bus.emit("pipeline_complete", {
            "session_id": ctx.session_id,
            "latency_ms": ctx.latency_ms
        })

    # ─────────────────────────────────────────────────────────────
    # Pipeline Stages
    # ─────────────────────────────────────────────────────────────
    async def _stage_stt(self, ctx: PipelineContext):
        """Stage 2: Speech-to-Text using Vosk"""
        t0 = time.time()
        try:
            result = await self.stt.transcribe(ctx.raw_audio)
            ctx.transcript = result.text
            ctx.confidence = result.confidence
            ctx.trace("stt", {
                "transcript": ctx.transcript,
                "confidence": ctx.confidence,
                "duration_ms": (time.time() - t0) * 1000
            })
            self.metrics.record_stage("stt", time.time() - t0)
            if ctx.confidence < 0.65 or not ctx.transcript or not ctx.transcript.strip():
                logger.warning("Ignoring low-confidence or empty speech")
                ctx.error = "low_confidence"
                return
            if ctx.transcript:
                print(f"👤 You: {ctx.transcript}")
            logger.debug(f"[{ctx.session_id}] STT: '{ctx.transcript}' (conf={ctx.confidence:.2f})")
        except Exception as e:
            ctx.error = f"STT failed: {e}"
            logger.error(f"STT error: {e}")

    async def _stage_language_detection(self, ctx: PipelineContext):
        """Stage 3: Detect language of transcript"""
        # Short text is unreliable for langdetect — default to English
        if not ctx.transcript or len(ctx.transcript) < 10:
            ctx.detected_language = "en"
            ctx.trace("language_detection", {"skipped": True, "reason": "too_short", "language": "en"})
            logger.debug(f"[{ctx.session_id}] Language: English (default, short text)")
            return

        t0 = time.time()
        try:
            result = await self.language_detector.detect(ctx.transcript)
            ctx.detected_language = result.language_code
            ctx.trace("language_detection", {
                "language": result.language_code,
                "language_name": result.language_name,
                "confidence": result.confidence
            })
            self.metrics.record_stage("language_detection", time.time() - t0)
            logger.debug(f"[{ctx.session_id}] Language: {result.language_name} ({result.language_code})")
        except Exception as e:
            logger.warning(f"Language detection failed, defaulting to English: {e}")
            ctx.detected_language = "en"

    async def _stage_translation(self, ctx: PipelineContext):
        """Stage 4: Translate to English pivot (if needed)"""
        if ctx.detected_language == "en":
            ctx.translated_text = ctx.transcript
            ctx.trace("translation", {"skipped": True, "reason": "already_english"})
            return

        t0 = time.time()
        try:
            result = await self.translator.translate(
                ctx.transcript,
                source_lang=ctx.detected_language,
                target_lang="en"
            )
            ctx.translated_text = result.translated_text
            ctx.trace("translation", {
                "original": ctx.transcript,
                "translated": ctx.translated_text,
                "source_lang": ctx.detected_language
            })
            self.metrics.record_stage("translation", time.time() - t0)
            logger.debug(f"[{ctx.session_id}] Translated: '{ctx.translated_text}'")
        except Exception as e:
            logger.warning(f"Translation failed, using original: {e}")
            ctx.translated_text = ctx.transcript

    async def _stage_nlp(self, ctx: PipelineContext):
        t0 = time.time()

        try:
            result = await self.nlp.process(
                ctx.translated_text or ctx.transcript,
                context={"session_id": ctx.session_id}
            )

            if not result:
                ctx.response_text = "Sorry, NLP failed."
                ctx.intent = "error"
                return

            # ✅ Ollama direct response
            if result.source == "ollama" and result.response:
                ctx.response_text = result.response
                ctx.intent = "llm_response"
                ctx.skip_skill = True   # Skip skill/action stages

            # ✅ Rasa flow
            else:
                ctx.intent = result.intent
                ctx.entities = result.entities

            ctx.trace("nlp", {
                "intent": result.intent,
                "entities": result.entities,
                "confidence": result.confidence,
                "source": result.source,
                "duration_ms": (time.time() - t0) * 1000
            })

            self.metrics.record_stage("nlp", time.time() - t0)
            logger.debug(f"[{ctx.session_id}] Intent: {result.intent} via {result.source}")

        except Exception as e:
            ctx.error = f"NLP failed: {e}"
            logger.error(f"NLP error: {e}")

    async def _stage_sentiment(self, ctx: PipelineContext):
        """Stage 6: Sentiment Analysis"""
        t0 = time.time()
        try:
            result = await self.sentiment.analyze(
                ctx.translated_text or ctx.transcript
            )
            ctx.sentiment = {
                "label": result.label,
                "score": result.score,
                "emotions": result.emotions
            }
            ctx.trace("sentiment", ctx.sentiment)
            self.metrics.record_stage("sentiment", time.time() - t0)
            logger.debug(f"[{ctx.session_id}] Sentiment: {result.label} ({result.score:.2f})")
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            ctx.sentiment = {"label": "neutral", "score": 0.5, "emotions": {}}

    async def _stage_skill_manager(self, ctx: PipelineContext):
        """Stage 7: Route to appropriate skill"""
        t0 = time.time()
        try:
            skill = await self.skill_manager.route(
                intent=ctx.intent,
                entities=ctx.entities,
                sentiment=ctx.sentiment,
                transcript=ctx.translated_text
            )
            ctx.skill_name = skill.name
            ctx.trace("skill_manager", {
                "skill": skill.name,
                "confidence": skill.confidence
            })
            self.metrics.record_stage("skill_manager", time.time() - t0)
            logger.debug(f"[{ctx.session_id}] Skill: {skill.name}")
        except Exception as e:
            logger.warning(f"Skill routing failed, using fallback: {e}")
            ctx.skill_name = "general_conversation"

    async def _stage_action_handler(self, ctx: PipelineContext):
        """Stage 8: Execute skill action"""
        t0 = time.time()
        try:
            result = await self.action_handler.execute(
                skill_name=ctx.skill_name,
                intent=ctx.intent,
                entities=ctx.entities,
                context={
                    "session_id": ctx.session_id,
                    "sentiment": ctx.sentiment,
                    "transcript": ctx.translated_text or ctx.transcript
                }
            )
            ctx.action_result = result
            ctx.trace("action_handler", {
                "skill": ctx.skill_name,
                "result_type": type(result).__name__,
                "duration_ms": (time.time() - t0) * 1000
            })
            self.metrics.record_stage("action_handler", time.time() - t0)
        except Exception as e:
            ctx.error = f"Action failed: {e}"
            logger.error(f"Action handler error: {e}")

    async def _stage_response_generation(self, ctx: PipelineContext):
        """Stage 9: Generate natural language response"""
        t0 = time.time()
        try:
            # ✅ If already have response from Ollama → skip
            if ctx.response_text:
                ctx.trace("response_generation", {"skipped": True, "reason": "ollama_direct"})
                self.metrics.record_stage("response_generation", time.time() - t0)
                return

            response = await self.response_generator.generate(
                action_result=ctx.action_result,
                intent=ctx.intent,
                sentiment=ctx.sentiment,
                skill_name=ctx.skill_name,
                context={"transcript": ctx.translated_text or ctx.transcript}
            )
            ctx.response_text = response.text

            ctx.trace("response_generation", {
                "text": ctx.response_text[:100] + "..." if len(ctx.response_text) > 100 else ctx.response_text
            })
            self.metrics.record_stage("response_generation", time.time() - t0)

            # Clean terminal output
            if ctx.response_text:
                print(f"🤖 Assistant: {ctx.response_text}")

        except Exception as e:
            ctx.error = f"Response generation failed: {e}"
            logger.error(f"Response generation error: {e}")

    async def _stage_response_translation(self, ctx: PipelineContext):
        """Stage 10: Translate response back to user's language"""
        if ctx.detected_language == "en" or not ctx.response_text:
            ctx.trace("response_translation", {"skipped": True})
            return

        t0 = time.time()
        try:
            result = await self.translator.translate(
                ctx.response_text,
                source_lang="en",
                target_lang=ctx.detected_language
            )
            ctx.response_text = result.translated_text
            ctx.trace("response_translation", {
                "target_lang": ctx.detected_language,
                "translated": ctx.response_text
            })
            self.metrics.record_stage("response_translation", time.time() - t0)
        except Exception as e:
            logger.warning(f"Response translation failed, using English: {e}")

    async def _stage_tts(self, ctx: PipelineContext):
        """Stage 11: Text-to-Speech in user's language"""
        if not ctx.response_text:
            return

        t0 = time.time()
        self.state = PipelineState.RESPONDING
        try:
            audio = await self.tts.synthesize(
                text=ctx.response_text,
                language=ctx.detected_language,
                sentiment=ctx.sentiment
            )
            ctx.response_audio = audio.audio_bytes
            ctx.trace("tts", {
                "language": ctx.detected_language,
                "audio_bytes": len(audio.audio_bytes),
                "duration_ms": (time.time() - t0) * 1000
            })
            self.metrics.record_stage("tts", time.time() - t0)

            # Play the audio
            await self.tts.play(audio)
            logger.debug(f"[{ctx.session_id}] Response delivered in {ctx.latency_ms:.0f}ms")
        except Exception as e:
            logger.error(f"TTS error: {e}")

    async def _handle_error(self, ctx: PipelineContext):
        """Generate and play an error response"""
        try:
            error_text = "I'm sorry, I encountered an error. Please try again."
            print(f"🤖 Assistant: {error_text}")
            audio = await self.tts.synthesize(error_text, language="en", sentiment=None)
            await self.tts.play(audio)
        except Exception:
            pass

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Return current pipeline health status"""
        return {
            "state": self.state.value,
            "metrics": self.metrics.get_summary(),
            "components": {
                "wake_word": self.wake_word.is_healthy(),
                "stt": self.stt.is_healthy(),
                "nlp": self.nlp.is_healthy(),
                "tts": self.tts.is_healthy(),
            }
        }

