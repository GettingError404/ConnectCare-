"""
Hybrid NLP Engine
Primary: Rasa NLU (intent classification + entity extraction)
Fallback: Ollama (local LLM) for conversational understanding
Strategy: Try Rasa first; if confidence < threshold, use Ollama.
"""

import asyncio
import json
import logging
import aiohttp
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from config.settings import NLPSettings

logger = logging.getLogger(__name__)


@dataclass
class NLPResult:
    intent: str
    entities: Dict[str, Any]
    confidence: float
    source: str  # "rasa" | "ollama" | "fallback"
    raw_response: Optional[Dict] = None
    slots: Dict[str, Any] = field(default_factory=dict)
    action_type: Optional[str] = None  # "query" | "command" | "conversation"
    response: Optional[str] = None


class RasaNLUClient:
    """
    HTTP client for Rasa NLU server.
    Handles intent classification and entity extraction.
    """

    def __init__(self, server_url: str, confidence_threshold: float = 0.7):
        self.server_url = server_url.rstrip("/")
        self.confidence_threshold = confidence_threshold
        self._session: Optional[aiohttp.ClientSession] = None
        self._available = False

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=3.0)
            )
        return self._session

    async def parse(self, text: str) -> Optional[NLPResult]:
        """Parse text using Rasa NLU"""
        try:
            session = await self._get_session()
            url = f"{self.server_url}/model/parse"
            payload = {"text": text}

            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._available = True
                    return self._parse_rasa_response(data)
                else:
                    logger.warning(f"Rasa returned {resp.status}")
                    return None

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if self._available:
                logger.warning(f"Rasa NLU unavailable: {e}")
                self._available = False
            return None

    def _parse_rasa_response(self, data: Dict) -> NLPResult:
        """Parse Rasa response into NLPResult"""
        intent_data = data.get("intent", {})
        intent_name = intent_data.get("name", "unknown")
        confidence = intent_data.get("confidence", 0.0)

        # Extract entities
        entities = {}
        for entity in data.get("entities", []):
            entity_name = entity.get("entity")
            entity_value = entity.get("value")
            entities[entity_name] = entity_value

        # Extract ranked intents for debugging
        intent_ranking = data.get("intent_ranking", [])

        return NLPResult(
            intent=intent_name,
            entities=entities,
            confidence=confidence,
            source="rasa",
            raw_response=data,
            slots={}
        )

    async def check_health(self) -> bool:
        """Check if Rasa server is running"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.server_url}/",
                timeout=aiohttp.ClientTimeout(total=2.0)
            ) as resp:
                self._available = resp.status == 200
                return self._available
        except Exception:
            self._available = False
            return False

    @property
    def is_available(self) -> bool:
        return self._available


class OllamaClient:
    """
    Ollama local LLM client for NLP fallback.
    Uses structured prompting to extract intents and entities.
    """

    def __init__(self, server_url: str, model: str = "llama3.2"):
        self.server_url = server_url.rstrip("/")
        self.model = model
        self._session: Optional[aiohttp.ClientSession] = None
        self._available = False

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30.0)
            )
        return self._session

    async def parse(self, text: str) -> Optional[NLPResult]:
        """Use Ollama to extract intent and entities"""
        try:
            session = await self._get_session()
            url = f"{self.server_url}/api/chat"

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": text}
                ],
                "stream": True
            }
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    logger.warning("Ollama returned status %s", resp.status)
                    return None
            
                self._available = True
                full_response=""

                async for line in resp.content:
                    if not line:
                        continue

                    try:
                        chunk = json.loads(line.decode("utf-8"))
                        content = chunk.get("message", {}).get("content", "")
                        full_response += content

                        if chunk.get("done"):
                            break

                    except Exception:
                        continue

                logger.debug(f"Ollama response: {full_response[:100]}...")

                return NLPResult(
                    intent="llm_response",
                    entities={},
                    confidence=0.95,
                    source="ollama",
                    response=full_response
                )

        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return None


    def _keyword_fallback(self, text: str) -> NLPResult:
        """Last resort keyword-based intent detection"""
        text_lower = text.lower()

        # Simple keyword rules
        KEYWORD_MAP = {
            "weather": "get_weather",
            "timer": "set_timer",
            "music": "play_music",
            "news": "get_news",
            "time": "get_time",
            "date": "get_date",
            "joke": "tell_joke",
            "remind": "set_reminder",
            "search": "search_web",
            "define": "get_definition",
            "volume": "volume_control",
        }

        for keyword, intent in KEYWORD_MAP.items():
            if keyword in text_lower:
                return NLPResult(
                    intent=intent,
                    entities={},
                    confidence=0.6,
                    source="keyword_fallback"
                )

        return NLPResult(
            intent="unknown",
            entities={},
            confidence=0.3,
            source="keyword_fallback"
        )

    async def check_health(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.server_url}/api/version",
                timeout=aiohttp.ClientTimeout(total=2.0)
            ) as resp:
                self._available = resp.status == 200
                return self._available
        except Exception:
            self._available = False
            return False


class HybridNLP:
    """
    Hybrid NLP engine: Rasa NLU + Ollama LLM fallback.

    Strategy:
    1. Try Rasa NLU (fast, structured, trained on domain)
    2. If confidence < threshold OR Rasa unavailable → Ollama
    3. If Ollama unavailable → keyword-based fallback
    """

    def __init__(self, settings: NLPSettings):
        self.settings = settings
        self.rasa = RasaNLUClient(
            server_url=settings.rasa_url,
            confidence_threshold=settings.rasa_confidence_threshold
        )
        self.ollama = OllamaClient(
            server_url=settings.ollama_url,
            model=settings.ollama_model
        )
        self._healthy = True

        # Start background health checks
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._health_check_loop())
        except RuntimeError:
                # No loop running → skip background task
            pass

    async def process(self, text: str, context: Dict[str, Any] = None) -> NLPResult:
        """
        Process text through hybrid NLP pipeline.
        Tries Rasa first, falls back to Ollama if needed.
        """
        if not text or not text.strip():
            return NLPResult(
                intent="empty_input",
                entities={},
                confidence=0.0,
                source="fallback"
            )

        # Strategy 1: Try Rasa NLU (always prefer it)
        rasa_result = await self.rasa.parse(text)

        if rasa_result:
            # If Rasa gives a prediction with enough confidence → use it.
            # Otherwise, fall back to Ollama.
            if rasa_result.confidence >= self.settings.rasa_confidence_threshold:
                logger.debug(
                    f"Rasa NLU: {rasa_result.intent} ({rasa_result.confidence:.2f})"
                )
                return rasa_result

            logger.info(
                f"Rasa confidence too low ({rasa_result.confidence:.2f} < {self.settings.rasa_confidence_threshold:.2f}), "
                f"falling back to Ollama"
            )

        # Strategy 2: Use Ollama LLM
        ollama_result = await self.ollama.parse(text)


        if ollama_result:
            logger.debug(f"Ollama NLP: {ollama_result.intent} ({ollama_result.confidence:.2f})")
            return ollama_result

        # Strategy 3: Keyword fallback
        logger.warning("Both Rasa and Ollama unavailable, using keyword fallback")
        #return self.ollama._keyword_fallback(text)
        return self.ollama._keyword_fallback(text)

    async def _health_check_loop(self):
        """Periodically check health of NLP backends"""
        while True:
            await asyncio.sleep(30)
            await self.rasa.check_health()
            await self.ollama.check_health()

    def is_healthy(self) -> bool:
        return self._healthy

    def get_status(self) -> Dict[str, Any]:
        return {
            "rasa_available": self.rasa.is_available,
            "ollama_available": self.ollama.is_available,
            "rasa_url": self.settings.rasa_url,
            "ollama_url": self.settings.ollama_url,
        }
