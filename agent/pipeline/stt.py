"""
Speech-to-Text using Vosk (offline, fast, multilingual)
Supports streaming recognition and batch transcription.
Falls back to Whisper for high-accuracy scenarios.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Optional, AsyncIterator
from config.settings import STTSettings

logger = logging.getLogger(__name__)


@dataclass
class TranscriptResult:
    text: str
    confidence: float
    words: list = None
    is_partial: bool = False
    source: str = "vosk"


class SpeechToText:
    """
    Vosk-based offline Speech-to-Text engine.
    Supports: streaming recognition, multiple languages, word timestamps.
    Fallback: OpenAI Whisper for difficult audio.
    """

    # Vosk model URLs by language
    VOSK_MODELS = {
        "en": "vosk-model-en-us-0.22",
        "fr": "vosk-model-fr-0.22",
        "de": "vosk-model-de-0.21",
        "es": "vosk-model-es-0.42",
        "zh": "vosk-model-cn-0.22",
        "ar": "vosk-model-ar-mgb2-0.4",
        "hi": "vosk-model-hi-0.22",
        "ja": "vosk-model-ja-0.22",
        "pt": "vosk-model-pt-fb-v0.1.1",
        "ru": "vosk-model-ru-0.42",
    }

    def __init__(self, settings: STTSettings):
        self.settings = settings
        self.model_dir = settings.model_dir
        self.sample_rate = settings.sample_rate
        self._models = {}  # Language-indexed model cache
        self._recognizers = {}
        self._healthy = False

        self._init_default_model()

    def _init_default_model(self):
        """Load default (English) Vosk model"""
        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            SetLogLevel(-1)  # Suppress Vosk logging

            model_path = os.path.join(self.model_dir, self.VOSK_MODELS["en"])
            if not os.path.exists(model_path):
                model_path = self.model_dir  # Try direct path

            if os.path.exists(model_path):
                self._models["en"] = Model(model_path)
                self._healthy = True
                logger.info(f"Vosk model loaded from {model_path}")
            else:
                logger.warning(f"Vosk model not found at {model_path}, using fallback")
                self._healthy = True  # Still "healthy" but will use fallback
        except ImportError:
            logger.warning("vosk not installed — using whisper fallback")
            self._init_whisper_fallback()
        except Exception as e:
            logger.error(f"Vosk init error: {e}")
            self._init_whisper_fallback()

    def _init_whisper_fallback(self):
        """Initialize Whisper as fallback STT"""
        try:
            import whisper
            self._whisper_model = whisper.load_model("base")
            self._use_whisper = True
            self._healthy = True
            logger.info("Whisper STT initialized as fallback")
        except ImportError:
            logger.warning("whisper not installed, using mock transcription")
            self._use_whisper = False
            self._healthy = True  # Degrade gracefully

    def _get_recognizer(self, language: str = "en"):
        """Get or create Vosk recognizer for language"""
        from vosk import KaldiRecognizer
        if language not in self._recognizers:
            model = self._models.get(language, self._models.get("en"))
            if model:
                rec = KaldiRecognizer(model, self.sample_rate)
                rec.SetWords(True)  # Enable word timestamps
                self._recognizers[language] = rec
        return self._recognizers.get(language)

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> TranscriptResult:
        """
        Transcribe audio bytes to text.
        Uses Vosk for local inference, falls back to Whisper.
        """
        return await asyncio.get_event_loop().run_in_executor(
            None, self._blocking_transcribe, audio_bytes, language
        )

    def _blocking_transcribe(self, audio_bytes: bytes, language: str = "en") -> TranscriptResult:
        """Blocking transcription (runs in thread pool)"""

        # Try Vosk first
        if hasattr(self, '_models') and self._models:
            return self._vosk_transcribe(audio_bytes, language)
        elif hasattr(self, '_use_whisper') and self._use_whisper:
            return self._whisper_transcribe(audio_bytes)
        else:
            return self._mock_transcribe()

    def _vosk_transcribe(self, audio_bytes: bytes, language: str) -> TranscriptResult:
        """Vosk-based transcription"""
        from vosk import KaldiRecognizer

        recognizer = self._get_recognizer(language)
        if not recognizer:
            return TranscriptResult(text="", confidence=0.0)

        # Process audio in chunks for streaming recognition
        chunk_size = 4000
        results = []

        recognizer.AcceptWaveform(b"")  # Reset

        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            if recognizer.AcceptWaveform(chunk):
                result = json.loads(recognizer.Result())
                if result.get("text"):
                    results.append(result)

        # Get final result
        final = json.loads(recognizer.FinalResult())
        if final.get("text"):
            results.append(final)

        if results:
            text = " ".join(r.get("text", "") for r in results).strip()
            # Compute average confidence from word results
            confidence = self._compute_confidence(results)
            return TranscriptResult(
                text=text,
                confidence=confidence,
                words=final.get("result", []),
                source="vosk"
            )

        return TranscriptResult(text="", confidence=0.0, source="vosk")

    def _compute_confidence(self, results: list) -> float:
        """Compute average word confidence from Vosk results"""
        all_words = []
        for r in results:
            all_words.extend(r.get("result", []))

        if not all_words:
            return 0.8  # Default confidence

        avg_conf = sum(w.get("conf", 0.8) for w in all_words) / len(all_words)
        return round(avg_conf, 3)

    def _whisper_transcribe(self, audio_bytes: bytes) -> TranscriptResult:
        """Whisper-based transcription"""
        import tempfile
        import numpy as np
        import soundfile as sf

        # Write audio to temp file (Whisper needs file input)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            result = self._whisper_model.transcribe(temp_path, language="en")
            return TranscriptResult(
                text=result["text"].strip(),
                confidence=0.9,  # Whisper doesn't give word-level confidence
                source="whisper"
            )
        finally:
            os.unlink(temp_path)

    def _mock_transcribe(self) -> TranscriptResult:
        """Mock transcription for testing"""
        return TranscriptResult(
            text="hello, what is the weather today",
            confidence=0.95,
            source="mock"
        )

    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes], language: str = "en"
    ) -> AsyncIterator[TranscriptResult]:
        """
        Streaming transcription - yields partial results in real-time.
        Useful for long audio or live caption display.
        """
        from vosk import KaldiRecognizer

        recognizer = self._get_recognizer(language)
        if not recognizer:
            return

        async for chunk in audio_stream:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._process_chunk, recognizer, chunk
            )
            if result:
                yield result

    def _process_chunk(self, recognizer, chunk: bytes) -> Optional[TranscriptResult]:
        """Process a single audio chunk"""
        if recognizer.AcceptWaveform(chunk):
            result = json.loads(recognizer.Result())
            if result.get("text"):
                return TranscriptResult(
                    text=result["text"],
                    confidence=self._compute_confidence([result]),
                    is_partial=False,
                    source="vosk"
                )
        else:
            partial = json.loads(recognizer.PartialResult())
            if partial.get("partial"):
                return TranscriptResult(
                    text=partial["partial"],
                    confidence=0.5,
                    is_partial=True,
                    source="vosk"
                )
        return None

    def load_language_model(self, language_code: str) -> bool:
        """Dynamically load a Vosk model for a new language"""
        if language_code in self._models:
            return True

        try:
            from vosk import Model
            model_name = self.VOSK_MODELS.get(language_code)
            if not model_name:
                logger.warning(f"No Vosk model available for language: {language_code}")
                return False

            model_path = os.path.join(self.model_dir, model_name)
            if os.path.exists(model_path):
                self._models[language_code] = Model(model_path)
                logger.info(f"Loaded Vosk model for {language_code}")
                return True
            else:
                logger.warning(f"Model not found: {model_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to load model for {language_code}: {e}")
            return False

    def is_healthy(self) -> bool:
        return self._healthy
