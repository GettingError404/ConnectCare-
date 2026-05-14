"""
VoiceOS Configuration Settings
Loads from environment variables and config files.
All settings are typed and validated.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


def _env_float(key: str, default: float = 0.0) -> float:
    try:
        return float(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def _env_int(key: str, default: int = 0) -> int:
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


@dataclass
class WakeWordSettings:
    keyword: str = field(default_factory=lambda: _env("WAKE_WORD_KEYWORD", "hello"))
    sensitivity: float = field(default_factory=lambda: _env_float("WAKE_WORD_SENSITIVITY", 0.5))
    engine: str = field(default_factory=lambda: _env("WAKE_WORD_ENGINE", "energy"))
    porcupine_access_key: str = field(default_factory=lambda: _env("PORCUPINE_ACCESS_KEY", ""))


@dataclass
class STTSettings:
    model_dir: str = field(default_factory=lambda: _env("VOSK_MODEL_DIR", "./models/vosk-model-en-us-0.22"))
    sample_rate: int = field(default_factory=lambda: _env_int("STT_SAMPLE_RATE", 16000))
    engine: str = field(default_factory=lambda: _env("STT_ENGINE", "vosk"))
    whisper_model: str = field(default_factory=lambda: _env("WHISPER_MODEL", "base"))


@dataclass
class LanguageSettings:
    default_language: str = field(default_factory=lambda: _env("DEFAULT_LANGUAGE", "en"))
    engine: str = field(default_factory=lambda: _env("LANG_DETECT_ENGINE", "auto"))


@dataclass
class TranslationSettings:
    libretranslate_url: str = field(
        default_factory=lambda: _env("LIBRETRANSLATE_URL", "http://localhost:5000")
    )
    libretranslate_api_key: str = field(
        default_factory=lambda: _env("LIBRETRANSLATE_API_KEY", "")
    )
    pivot_language: str = "en"


@dataclass
class NLPSettings:
    rasa_url: str = field(default_factory=lambda: _env("RASA_URL", "http://localhost:5005"))
    rasa_confidence_threshold: float = field(
        default_factory=lambda: _env_float("RASA_CONFIDENCE_THRESHOLD", 0.7)
    )

    # Optional: automatically launch Rasa server using a dedicated conda env
    # (so the Rasa HTTP server is available for pipeline/nlp_hybrid.py)
    rasa_conda_env_name: str = field(default_factory=lambda: _env("RASA_CONDA_ENV", "rasa_env"))
    rasa_workdir: str = field(default_factory=lambda: _env("RASA_WORKDIR", "./rasa"))
    rasa_force_start: bool = field(default_factory=lambda: _env_bool("RASA_FORCE_START", False))

    ollama_url: str = field(default_factory=lambda: _env("OLLAMA_URL", "http://127.0.0.1:11434"))
    ollama_model: str = field(default_factory=lambda: _env("OLLAMA_MODEL", "phi"))



@dataclass
class SentimentSettings:
    use_transformers: bool = field(
        default_factory=lambda: _env_bool("USE_TRANSFORMER_SENTIMENT", False)
    )
    backend: str = field(default_factory=lambda: _env("SENTIMENT_BACKEND", "vader"))


@dataclass
class SkillSettings:
    custom_skills_dir: str = field(
        default_factory=lambda: _env("CUSTOM_SKILLS_DIR", "./skills/custom")
    )
    enabled_skills: str = field(default_factory=lambda: _env("ENABLED_SKILLS", "all"))


@dataclass
class ActionSettings:
    newsapi_key: str = field(default_factory=lambda: _env("NEWSAPI_KEY", ""))
    openweather_key: str = field(default_factory=lambda: _env("OPENWEATHER_KEY", ""))
    spotify_client_id: str = field(default_factory=lambda: _env("SPOTIFY_CLIENT_ID", ""))
    spotify_client_secret: str = field(default_factory=lambda: _env("SPOTIFY_CLIENT_SECRET", ""))
    home_assistant_url: str = field(
        default_factory=lambda: _env("HOME_ASSISTANT_URL", "")
    )
    home_assistant_token: str = field(
        default_factory=lambda: _env("HOME_ASSISTANT_TOKEN", "")
    )


@dataclass
class ResponseSettings:
    ollama_url: str = field(default_factory=lambda: _env("OLLAMA_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: _env("OLLAMA_MODEL", "llama3.2"))
    max_response_length: int = field(
        default_factory=lambda: _env_int("MAX_RESPONSE_LENGTH", 300)
    )


@dataclass
class TTSSettings:
    backend: str = field(default_factory=lambda: _env("TTS_BACKEND", "auto"))
    prefer_coqui: bool = field(default_factory=lambda: _env_bool("PREFER_COQUI_TTS", False))
    speech_rate: int = field(default_factory=lambda: _env_int("TTS_SPEECH_RATE", 175))
    volume: float = field(default_factory=lambda: _env_float("TTS_VOLUME", 1.0))
    coqui_model: str = field(
        default_factory=lambda: _env("COQUI_MODEL", "tts_models/en/ljspeech/tacotron2-DDC")
    )


@dataclass
class SessionSettings:
    """Session state management settings"""
    silence_timeout_seconds: float = field(
        default_factory=lambda: _env_float("SESSION_SILENCE_TIMEOUT", 60.0)
    )
    enable_state_management: bool = field(
        default_factory=lambda: _env_bool("ENABLE_STATE_MANAGEMENT", True)
    )


@dataclass
class Settings:
    """Master settings object - composed of all sub-settings"""
    wake_word: WakeWordSettings = field(default_factory=WakeWordSettings)
    stt: STTSettings = field(default_factory=STTSettings)
    language: LanguageSettings = field(default_factory=LanguageSettings)
    translation: TranslationSettings = field(default_factory=TranslationSettings)
    nlp: NLPSettings = field(default_factory=NLPSettings)
    sentiment: SentimentSettings = field(default_factory=SentimentSettings)
    skills: SkillSettings = field(default_factory=SkillSettings)
    actions: ActionSettings = field(default_factory=ActionSettings)
    response: ResponseSettings = field(default_factory=ResponseSettings)
    tts: TTSSettings = field(default_factory=TTSSettings)
    session: SessionSettings = field(default_factory=SessionSettings)

    # General
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    debug: bool = field(default_factory=lambda: _env_bool("DEBUG", False))
    api_host: str = field(default_factory=lambda: _env("API_HOST", "0.0.0.0"))
    api_port: int = field(default_factory=lambda: _env_int("API_PORT", 8000))


def configure_clean_logging(log_level: str = "INFO"):
    """
    Configure logging for a clean terminal experience.
    Suppresses noisy third-party libraries and avoids timestamp clutter.
    """
    import logging

    level = getattr(logging, log_level.upper(), logging.INFO)

    # Root handler: simple format without timestamps for clean terminal
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()]
    )

    # Suppress noisy libraries
    for noisy in [
        "vosk",
        "aiohttp",
        "urllib3",
        "pyaudio",
        "sounddevice",
        "TTS",
        "transformers",
        "langdetect",
        "lingua",
    ]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Keep our own modules at requested level
    for ours in ["pipeline", "utils", "core", "config", "skills"]:
        logging.getLogger(ours).setLevel(level)


def load_settings() -> Settings:
    """Load settings from environment"""
    settings = Settings()
    return settings
