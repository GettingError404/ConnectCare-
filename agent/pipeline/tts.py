"""
Text-to-Speech Engine
Primary: Coqui TTS (local, multilingual, expressive)
Fallback: pyttsx3 (offline), gTTS (online), espeak
Adapts voice characteristics based on sentiment.
"""

import asyncio
import io
import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Optional, Dict
from config.settings import TTSSettings

logger = logging.getLogger(__name__)


@dataclass
class AudioResult:
    audio_bytes: bytes
    sample_rate: int = 22050
    channels: int = 1
    format: str = "wav"
    language: str = "en"
    backend: str = "unknown"


class TextToSpeech:
    """
    Multi-backend TTS engine with language support.
    Adapts voice speed/pitch based on sentiment.

    Priority:
    1. Coqui TTS (best quality, multilingual, local)
    2. pyttsx3 (offline, all platforms)
    3. gTTS (Google, requires internet)
    4. espeak (ultra-lightweight fallback)
    """

    # Language to Coqui model mapping
    COQUI_MODELS = {
        "en": "tts_models/en/ljspeech/tacotron2-DDC",
        "fr": "tts_models/fr/mai/tacotron2-DDC",
        "de": "tts_models/de/thorsten/tacotron2-DDC",
        "es": "tts_models/es/mai/tacotron2-DDC",
        "it": "tts_models/it/mai_female/glow-tts",
        "pt": "tts_models/pt/cv/vits",
        "zh": "tts_models/zh-CN/baker/tacotron2-DDC-GST",
        "ja": "tts_models/ja/kokoro/tacotron2-DDC",
        "multilingual": "tts_models/multilingual/multi-dataset/xtts_v2",
    }

    # gTTS language codes
    GTTS_LANG_MAP = {
        "en": "en", "es": "es", "fr": "fr", "de": "de", "it": "it",
        "pt": "pt", "ru": "ru", "zh": "zh-CN", "ja": "ja", "ar": "ar",
        "hi": "hi", "ko": "ko", "nl": "nl", "pl": "pl", "tr": "tr",
        "mr": "mr", "gu": "gu", "ta": "ta", "te": "te", "bn": "bn",
    }

    def __init__(self, settings: TTSSettings):
        self.settings = settings
        self._coqui_tts = None
        self._pyttsx3_engine = None
        self._backend = None
        self._healthy = False
        self._audio_player = None

        self._init_backends()

    def _init_backends(self):
        """Initialize TTS backends in priority order"""

        # Try Coqui TTS
        if self.settings.prefer_coqui:
            try:
                from TTS.api import TTS
                # Load multilingual model for broad language support
                model_name = self.COQUI_MODELS.get("multilingual")
                self._coqui_tts = TTS(model_name=model_name, progress_bar=False)
                self._backend = "coqui"
                self._healthy = True
                logger.info(f"Coqui TTS initialized: {model_name}")
                return
            except ImportError:
                logger.debug("TTS (Coqui) not installed")
            except Exception as e:
                logger.warning(f"Coqui TTS init failed: {e}")

        # Try pyttsx3 (offline, system voices)
        try:
            import pyttsx3
            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", self.settings.speech_rate)
            self._pyttsx3_engine.setProperty("volume", self.settings.volume)
            self._backend = "pyttsx3"
            self._healthy = True
            logger.info("pyttsx3 TTS initialized")
            return
        except ImportError:
            logger.debug("pyttsx3 not installed")
        except Exception as e:
            logger.warning(f"pyttsx3 init failed: {e}")

        # gTTS as online fallback
        try:
            from gtts import gTTS
            self._backend = "gtts"
            self._healthy = True
            logger.info("gTTS initialized (requires internet)")
            return
        except ImportError:
            logger.debug("gTTS not installed")

        # espeak as last resort
        if self._check_espeak():
            self._backend = "espeak"
            self._healthy = True
            logger.info("espeak TTS initialized")
        else:
            self._backend = "mock"
            self._healthy = True
            logger.warning("No TTS backend available — using silent mock")

    def _check_espeak(self) -> bool:
        """Check if espeak is installed"""
        import subprocess
        try:
            result = subprocess.run(["espeak", "--version"], capture_output=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    async def synthesize(
        self,
        text: str,
        language: str = "en",
        sentiment: Optional[Dict] = None
    ) -> AudioResult:
        """
        Synthesize text to audio bytes.
        Adjusts voice characteristics based on sentiment.
        """
        if not text or not text.strip():
            return AudioResult(audio_bytes=b"", backend="empty")

        # Adjust speech parameters based on sentiment
        speech_params = self._get_speech_params(sentiment)

        return await asyncio.get_event_loop().run_in_executor(
            None, self._blocking_synthesize, text, language, speech_params
        )

    def _blocking_synthesize(
        self, text: str, language: str, speech_params: Dict
    ) -> AudioResult:
        """Blocking TTS synthesis (runs in thread pool)"""

        if self._backend == "coqui":
            return self._coqui_synthesize(text, language, speech_params)
        elif self._backend == "pyttsx3":
            return self._pyttsx3_synthesize(text, speech_params)
        elif self._backend == "gtts":
            return self._gtts_synthesize(text, language)
        elif self._backend == "espeak":
            return self._espeak_synthesize(text, language, speech_params)
        else:
            return AudioResult(audio_bytes=b"", backend="mock")

    def _coqui_synthesize(self, text: str, language: str, params: Dict) -> AudioResult:
        """Coqui TTS synthesis"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name

            # Use multilingual XTTS for non-English
            if language != "en" and hasattr(self._coqui_tts, 'tts_to_file'):
                self._coqui_tts.tts_to_file(
                    text=text,
                    file_path=output_path,
                    language=language[:2]
                )
            else:
                self._coqui_tts.tts_to_file(text=text, file_path=output_path)

            with open(output_path, "rb") as f:
                audio_bytes = f.read()

            os.unlink(output_path)
            return AudioResult(audio_bytes=audio_bytes, language=language, backend="coqui")
        except Exception as e:
            logger.error(f"Coqui synthesis error: {e}")
            return self._gtts_synthesize(text, language)

    def _pyttsx3_synthesize(self, text: str, params: Dict) -> AudioResult:
        """pyttsx3 synthesis to bytes"""
        try:
            # Set rate and volume from sentiment params
            self._pyttsx3_engine.setProperty("rate", params.get("rate", self.settings.speech_rate))
            self._pyttsx3_engine.setProperty("volume", params.get("volume", self.settings.volume))

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name

            self._pyttsx3_engine.save_to_file(text, output_path)
            self._pyttsx3_engine.runAndWait()

            if os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    audio_bytes = f.read()
                os.unlink(output_path)
                return AudioResult(audio_bytes=audio_bytes, backend="pyttsx3")
        except Exception as e:
            logger.error(f"pyttsx3 synthesis error: {e}")

        return AudioResult(audio_bytes=b"", backend="pyttsx3_failed")

    def _gtts_synthesize(self, text: str, language: str) -> AudioResult:
        """gTTS synthesis"""
        try:
            from gtts import gTTS
            import io

            lang_code = self.GTTS_LANG_MAP.get(language, "en")
            tts = gTTS(text=text, lang=lang_code, slow=False)

            with io.BytesIO() as f:
                tts.write_to_fp(f)
                audio_bytes = f.getvalue()

            return AudioResult(audio_bytes=audio_bytes, language=language, backend="gtts", format="mp3")
        except Exception as e:
            logger.error(f"gTTS synthesis error: {e}")
            return AudioResult(audio_bytes=b"", backend="gtts_failed")

    def _espeak_synthesize(self, text: str, language: str, params: Dict) -> AudioResult:
        """espeak synthesis"""
        import subprocess

        rate = params.get("rate", 175)
        lang_map = {"en": "en", "fr": "fr", "de": "de", "es": "es", "zh": "zh"}
        lang = lang_map.get(language, "en")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name

        try:
            cmd = [
                "espeak", "-v", lang, "-s", str(rate),
                "-w", output_path, text
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            with open(output_path, "rb") as f:
                audio_bytes = f.read()

            return AudioResult(audio_bytes=audio_bytes, language=language, backend="espeak")
        except Exception as e:
            logger.error(f"espeak error: {e}")
            return AudioResult(audio_bytes=b"", backend="espeak_failed")
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def _get_speech_params(self, sentiment: Optional[Dict]) -> Dict:
        """Adapt speech parameters based on sentiment"""
        base_rate = self.settings.speech_rate
        base_volume = self.settings.volume

        if not sentiment:
            return {"rate": base_rate, "volume": base_volume}

        tone = sentiment.get("tone", "neutral")
        urgency = sentiment.get("urgency", 0.0)

        # Adjust rate based on tone and urgency
        if tone == "urgent":
            rate = int(base_rate * 1.15)
        elif tone == "positive":
            rate = int(base_rate * 1.05)
        elif tone == "frustrated":
            rate = int(base_rate * 0.95)  # Slightly slower for clarity
        else:
            rate = base_rate

        # Urgency increases rate slightly
        rate = min(rate + int(urgency * 20), 300)

        return {"rate": rate, "volume": base_volume}

    async def play(self, audio: AudioResult):
        """Play audio through speakers"""
        if not audio.audio_bytes:
            return

        await asyncio.get_event_loop().run_in_executor(
            None, self._blocking_play, audio
        )

    def _blocking_play(self, audio: AudioResult):
        """Blocking audio playback"""
        try:
            import pyaudio
            import wave
            import io

            if audio.format == "wav":
                with io.BytesIO(audio.audio_bytes) as f:
                    with wave.open(f, 'rb') as wf:
                        pa = pyaudio.PyAudio()
                        stream = pa.open(
                            format=pa.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True
                        )
                        chunk_size = 1024
                        data = wf.readframes(chunk_size)
                        while data:
                            stream.write(data)
                            data = wf.readframes(chunk_size)
                        stream.stop_stream()
                        stream.close()
                        pa.terminate()
            elif audio.format == "mp3":
                # Use pygame or playsound for MP3
                self._play_mp3(audio.audio_bytes)

        except ImportError:
            logger.debug("PyAudio not available, skipping audio playback")
        except Exception as e:
            logger.error(f"Audio playback error: {e}")

    def _play_mp3(self, audio_bytes: bytes):
        """Play MP3 audio"""
        try:
            import pygame
            import io
            pygame.mixer.init()
            pygame.mixer.music.load(io.BytesIO(audio_bytes))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                import time
                time.sleep(0.1)
        except ImportError:
            try:
                import playsound
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(audio_bytes)
                    temp_path = f.name
                playsound.playsound(temp_path)
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"MP3 playback failed: {e}")

    def is_healthy(self) -> bool:
        return self._healthy

    def get_backend(self) -> str:
        return self._backend
