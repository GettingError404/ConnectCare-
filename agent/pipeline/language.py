"""
Language Detection and Translation
Detection: langdetect / lingua / fasttext
Translation: LibreTranslate (self-hosted) with Argos Translate fallback
"""

import asyncio
import logging
import aiohttp
from dataclasses import dataclass
from typing import Optional, Dict
from config.settings import LanguageSettings, TranslationSettings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Language Detection
# ─────────────────────────────────────────────────────────────

LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ru": "Russian",
    "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic",
    "hi": "Hindi", "tr": "Turkish", "pl": "Polish", "sv": "Swedish",
    "da": "Danish", "fi": "Finnish", "no": "Norwegian", "cs": "Czech",
    "mr": "Marathi", "gu": "Gujarati", "ta": "Tamil", "te": "Telugu",
    "bn": "Bengali", "ur": "Urdu", "fa": "Persian",
}


@dataclass
class LanguageResult:
    language_code: str
    language_name: str
    confidence: float
    alternatives: list = None


class LanguageDetector:
    """
    Multi-backend language detection.
    Priority: lingua > langdetect > fasttext > character-set heuristics
    """

    def __init__(self, settings: LanguageSettings):
        self.settings = settings
        self._detector = None
        self._backend = None
        self._init_detector()

    def _init_detector(self):
        """Initialize best available language detector"""

        # Try lingua (most accurate)
        try:
            from lingua import LanguageDetectorBuilder, Language
            self._detector = (
                LanguageDetectorBuilder
                .from_all_languages()
                .with_preloaded_language_models()
                .build()
            )
            self._backend = "lingua"
            logger.info("Language detector: lingua")
            return
        except ImportError:
            pass

        # Try langdetect
        try:
            import langdetect
            self._detector = "langdetect"
            self._backend = "langdetect"
            logger.info("Language detector: langdetect")
            return
        except ImportError:
            pass

        # Character-set heuristic fallback
        self._backend = "heuristic"
        logger.warning("Language detector: heuristic (install lingua or langdetect)")

    async def detect(self, text: str) -> LanguageResult:
        """Detect language of text"""
        if not text or len(text.strip()) < 3:
            return LanguageResult(
                language_code="en",
                language_name="English",
                confidence=0.5
            )

        return await asyncio.get_event_loop().run_in_executor(
            None, self._blocking_detect, text
        )

    def _blocking_detect(self, text: str) -> LanguageResult:
        if self._backend == "lingua":
            return self._lingua_detect(text)
        elif self._backend == "langdetect":
            return self._langdetect_detect(text)
        else:
            return self._heuristic_detect(text)

    def _lingua_detect(self, text: str) -> LanguageResult:
        """Lingua-based detection"""
        try:
            result = self._detector.detect_language_of(text)
            if result:
                lang_code = result.iso_code_639_1.name.lower()
                confidence_results = self._detector.compute_language_confidence_values(text)
                confidence = confidence_results[0].value if confidence_results else 0.8

                return LanguageResult(
                    language_code=lang_code,
                    language_name=LANGUAGE_NAMES.get(lang_code, lang_code),
                    confidence=round(confidence, 3)
                )
        except Exception as e:
            logger.warning(f"Lingua detection failed: {e}")
        return LanguageResult("en", "English", 0.5)

    def _langdetect_detect(self, text: str) -> LanguageResult:
        """langdetect-based detection"""
        try:
            import langdetect
            lang = langdetect.detect(text)
            probs = langdetect.detect_langs(text)
            confidence = probs[0].prob if probs else 0.8

            return LanguageResult(
                language_code=lang,
                language_name=LANGUAGE_NAMES.get(lang, lang),
                confidence=round(confidence, 3)
            )
        except Exception as e:
            logger.warning(f"langdetect failed: {e}")
            return LanguageResult("en", "English", 0.5)

    def _heuristic_detect(self, text: str) -> LanguageResult:
        """Simple character-set based heuristic"""
        # Check for non-Latin scripts
        has_arabic = any('\u0600' <= c <= '\u06FF' for c in text)
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
        has_devanagari = any('\u0900' <= c <= '\u097F' for c in text)
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        has_japanese = any('\u3040' <= c <= '\u30ff' for c in text)

        if has_arabic:
            return LanguageResult("ar", "Arabic", 0.7)
        elif has_chinese:
            return LanguageResult("zh", "Chinese", 0.7)
        elif has_devanagari:
            return LanguageResult("hi", "Hindi", 0.7)
        elif has_cyrillic:
            return LanguageResult("ru", "Russian", 0.7)
        elif has_japanese:
            return LanguageResult("ja", "Japanese", 0.7)
        else:
            return LanguageResult("en", "English", 0.6)


# ─────────────────────────────────────────────────────────────
# Translation
# ─────────────────────────────────────────────────────────────

@dataclass
class TranslationResult:
    translated_text: str
    source_lang: str
    target_lang: str
    confidence: float = 1.0
    backend: str = "unknown"


class Translator:
    """
    Multi-backend translator.
    Priority: LibreTranslate (self-hosted) → Argos Translate (offline) → Deep Translator
    Uses English as pivot language for all translations.
    """

    def __init__(self, settings: TranslationSettings):
        self.settings = settings
        self._libre_url = settings.libretranslate_url
        self._libre_api_key = settings.libretranslate_api_key
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, str] = {}  # Simple in-memory translation cache
        self._argos_available = False

        self._init_argos()

    def _init_argos(self):
        """Initialize Argos Translate as offline fallback"""
        try:
            import argostranslate.package
            import argostranslate.translate
            self._argos_available = True
            logger.info("Argos Translate available as offline fallback")
        except ImportError:
            logger.debug("Argos Translate not available")

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5.0)
            )
        return self._session

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> TranslationResult:
        """
        Translate text from source_lang to target_lang.
        Uses English as pivot for non-direct language pairs.
        """
        if source_lang == target_lang:
            return TranslationResult(
                translated_text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                backend="passthrough"
            )

        # Check cache
        cache_key = f"{source_lang}|{target_lang}|{text[:100]}"
        if cache_key in self._cache:
            result = self._cache[cache_key]
            return TranslationResult(
                translated_text=result,
                source_lang=source_lang,
                target_lang=target_lang,
                backend="cache"
            )

        # Try LibreTranslate
        result = await self._libretranslate(text, source_lang, target_lang)
        if result:
            self._cache[cache_key] = result.translated_text
            return result

        # Try Argos Translate (offline)
        if self._argos_available:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._argos_translate, text, source_lang, target_lang
            )
            if result:
                self._cache[cache_key] = result.translated_text
                return result

        # Fallback: return original text
        logger.warning(f"All translation backends failed for {source_lang}→{target_lang}")
        return TranslationResult(
            translated_text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            backend="passthrough_fallback"
        )

    async def _libretranslate(
        self, text: str, source_lang: str, target_lang: str
    ) -> Optional[TranslationResult]:
        """LibreTranslate API call"""
        try:
            session = await self._get_session()
            payload = {
                "q": text,
                "source": source_lang,
                "target": target_lang,
                "format": "text",
            }
            if self._libre_api_key:
                payload["api_key"] = self._libre_api_key

            async with session.post(
                f"{self._libre_url}/translate", json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return TranslationResult(
                        translated_text=data.get("translatedText", text),
                        source_lang=source_lang,
                        target_lang=target_lang,
                        backend="libretranslate"
                    )
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.debug(f"LibreTranslate unavailable: {e}")
        return None

    def _argos_translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> Optional[TranslationResult]:
        """Argos Translate offline translation"""
        try:
            import argostranslate.translate

            installed_languages = argostranslate.translate.get_installed_languages()
            source = next((l for l in installed_languages if l.code == source_lang), None)
            target = next((l for l in installed_languages if l.code == target_lang), None)

            if source and target:
                translation = source.get_translation(target)
                if translation:
                    translated = translation.translate(text)
                    return TranslationResult(
                        translated_text=translated,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        backend="argos"
                    )
        except Exception as e:
            logger.warning(f"Argos Translate error: {e}")
        return None
