"""
Wake Word Detection
Supports: Porcupine (production), Snowboy, or keyword-based fallback.
Continuously streams microphone audio and triggers on wake word.
"""

import asyncio
import logging
import queue
import threading
from dataclasses import dataclass
from typing import Optional
import sounddevice as sd
from config.settings import WakeWordSettings

logger = logging.getLogger(__name__)


@dataclass
class WakeWordConfig:
    keyword: str = "hello"
    sensitivity: float = 0.5
    engine: str = "porcupine"  # porcupine | snowboy | vosk_kws | energy
    sample_rate: int = 16000
    frame_length: int = 512
    audio_capture_duration: float = 5.0  # seconds after wake word


class WakeWordDetector:
    """
    Continuously listens for wake word.
    Returns audio buffer of user command after wake word detected.
    """

    def __init__(self, settings: WakeWordSettings):
        self.settings = settings
        self.cfg = WakeWordConfig(
            keyword=settings.keyword,
            sensitivity=settings.sensitivity,
            engine=settings.engine
        )
        self._audio_queue = queue.Queue()
        self._porcupine = None
        self._pa = None
        self._stream = None
        self._initialized = False
        self._healthy = False
        self._engine_type = None

        self._init_engine()

    def _init_engine(self):
        """Initialize wake word engine with fallback chain"""
        if self.cfg.engine == "porcupine":
            self._init_porcupine()
        elif self.cfg.engine == "energy":
            self._init_energy_detector()
        else:
            self._init_energy_detector()  # Final fallback

    def _init_porcupine(self):
        """Initialize Picovoice Porcupine"""
        try:
            import pvporcupine
            import pyaudio
            import struct

            self._porcupine = pvporcupine.create(
                access_key=self.settings.porcupine_access_key,
                keywords=[self.cfg.keyword]
            )
            self._pa = pyaudio.PyAudio()
            self._stream = self._pa.open(
                rate=self._porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self._porcupine.frame_length
            )
            self._initialized = True
            self._healthy = True
            logger.info(f"Porcupine wake word initialized: '{self.cfg.keyword}'")

        except ImportError:
            logger.warning("pvporcupine not available, falling back to energy detection")
            self._init_energy_detector()
        except Exception as e:
            logger.warning(f"Porcupine init failed ({e}), falling back to energy detection")
            self._init_energy_detector()

    def _init_energy_detector(self):
        """
        Energy-based voice activity detection fallback.
        Triggers when audio energy exceeds threshold.
        """
        try:
            import pyaudio
            self._pa = pyaudio.PyAudio()
            self._engine_type = "energy"
            self._initialized = True
            self._healthy = True
            logger.info("Energy-based VAD initialized as wake word detector")
        except ImportError:
            logger.warning("PyAudio not available — using simulated audio mode")
            self._initialized = True
            self._healthy = True

    async def listen_for_wake_word(self) -> Optional[bytes]:
        """
        Block until wake word is detected.
        Returns audio bytes of the following command.
        """
        return await asyncio.get_event_loop().run_in_executor(
            None, self._blocking_listen
        )

    def _blocking_listen(self) -> Optional[bytes]:
        """Blocking wake word listen loop (runs in thread pool)"""
        import pyaudio
        import struct
        import audioop

        try:
            if self._porcupine:
                return self._porcupine_listen()

            # Energy fallback = pseudo wake
            print("🎧 Waiting for wake word...")

            audio = self._energy_listen()

            if audio:
                print("🎯 Wake word detected!")

            return audio

        except Exception as e:
            logger.error(f"Wake word listen error: {e}")
            return None

    def _porcupine_listen(self) -> Optional[bytes]:
        """Porcupine-based listening"""
        import struct
        while True:
            pcm = self._stream.read(self._porcupine.frame_length)
            pcm = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
            keyword_index = self._porcupine.process(pcm)

            if keyword_index >= 0:
                logger.info(f"Wake word detected!")
                return self._capture_command()

    def listen_continuous(self) -> Optional[bytes]:
        """
        ✅ PUBLIC METHOD: Continuous listening with energy-based wake word detection.
        Replaces private _energy_listen() for orchestrator compatibility.
        """
        return self._energy_listen()

    # ✅ AUTO-DETECT DEFAULT INPUT DEVICE
    def get_default_input_device(pa):
        try:
            default_host = pa.get_default_input_device_info()
            return default_host['index']
        except Exception:
            # Fallback: first available input device
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    return i
            raise RuntimeError("No input devices found")
        
    def _energy_listen(self) -> Optional[bytes]:

        """Energy-based voice activity detection"""

        import pyaudio
        import audioop

        def get_default_input_device(pa):
            try:
                return pa.get_default_input_device_info()['index']
            except Exception:
                for i in range(pa.get_device_count()):
                    info = pa.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        return i
                raise RuntimeError("No input devices found")

        pa = pyaudio.PyAudio()
        device_index = get_default_input_device(pa)
        logger.debug(f"Using input device: {device_index}")

        CHUNK = 1024
        THRESHOLD = 1500  # Adjusted for reliability
        SILENCE_LIMIT = 80  # ~2.5s silence before stopping

        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.cfg.sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK
        )

        frames = []
        num_silent = 0
        speaking = False

        print("🎤 Listening... (speak now)")

        try:
            while True:
                data = stream.read(CHUNK, exception_on_overflow=False)
                energy = audioop.rms(data, 2)

                if energy > THRESHOLD:
                    if not speaking:
                        print("🔊 Hearing you...")
                    speaking = True
                    num_silent = 0
                    frames.append(data)

                elif speaking:
                    num_silent += 1
                    frames.append(data)
                    
                    if num_silent > SILENCE_LIMIT:
                        logger.debug(f"Silence detected after {len(frames)/self.cfg.sample_rate:.1f}s")
                        break
                else:
                    frames = []  # Reset on silence

            audio_data = b"".join(frames)
            if len(audio_data) < self.cfg.sample_rate * 1:  # Minimum 1 second
                logger.debug(f"Audio too short ({len(audio_data)/(self.cfg.sample_rate*2):.1f}s), ignoring")
                return None
            logger.debug(f"Captured {len(audio_data)/(self.cfg.sample_rate*2):.1f}s audio")
            return audio_data
                
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

        return None

    def _capture_command(self) -> bytes:
        """Capture audio after wake word for the command"""
        import pyaudio
        frames = []
        CHUNK = self._porcupine.frame_length if self._porcupine else 1024
        RECORD_SECONDS = self.cfg.audio_capture_duration

        for _ in range(0, int(self.cfg.sample_rate / CHUNK * RECORD_SECONDS)):
            data = self._stream.read(CHUNK)
            frames.append(data)

        return b"".join(frames)

    async def _simulated_listen(self) -> Optional[bytes]:
        """Simulated mode for testing without microphone"""
        await asyncio.sleep(0.1)
        # Return empty bytes to trigger pipeline with test input
        return b"\x00" * (self.cfg.sample_rate * 2)  # 1 second of silence

    def is_healthy(self) -> bool:
        return self._healthy

    def cleanup(self):
        if self._stream:
            self._stream.close()
        if self._pa:
            self._pa.terminate()
        if self._porcupine:
            self._porcupine.delete()
        logger.info("WakeWordDetector cleaned up")

    