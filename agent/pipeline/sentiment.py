"""
Sentiment Analysis
Uses VADER (fast, offline) + optional transformer-based analysis.
Extracts: polarity, emotions, urgency, tone for adaptive responses.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from config.settings import SentimentSettings

logger = logging.getLogger(__name__)

@dataclass
class SentimentResult:
    label: str          # positive | negative | neutral
    score: float        # 0.0 to 1.0
    polarity: float     # -1.0 to +1.0
    emotions: Dict[str, float] = field(default_factory=dict)
    urgency: float = 0.0
    is_question: bool = False
    tone: str = "neutral"  # formal | casual | emotional | urgent


class SentimentAnalyzer:
    """
    Multi-layer sentiment analysis:
    1. VADER for fast rule-based sentiment (offline)
    2. Transformers pipeline for deeper analysis (optional)
    3. Keyword-based emotion detection
    """

    # Urgency keywords
    URGENCY_KEYWORDS = [
        "urgent", "emergency", "help", "please", "now", "immediately",
        "asap", "quick", "hurry", "fast", "critical", "important"
    ]

    # Emotion keyword maps
    EMOTION_KEYWORDS = {
        "joy": ["happy", "great", "wonderful", "fantastic", "love", "amazing", "excellent"],
        "frustration": ["angry", "annoying", "frustrated", "terrible", "hate", "awful", "broken"],
        "sadness": ["sad", "unhappy", "depressed", "miss", "lonely", "sorry"],
        "surprise": ["wow", "really", "seriously", "unexpected", "shocking"],
        "fear": ["scared", "afraid", "worried", "anxious", "nervous"],
    }

    def __init__(self, settings: SentimentSettings):
        self.settings = settings
        self._vader = None
        self._transformer_pipeline = None
        self._backend = None

        self._init_analyzers()

    def _init_analyzers(self):
        """Initialize available sentiment backends"""

        # Try VADER (fast, offline, no GPU needed)
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self._vader = SentimentIntensityAnalyzer()
            self._backend = "vader"
            logger.info("Sentiment analyzer: VADER")
        except ImportError:
            pass

        # Try transformers for richer analysis (optional enhancement)
        if self.settings.use_transformers:
            try:
                from transformers import pipeline
                self._transformer_pipeline = pipeline(
                    "sentiment-analysis",
                    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                    device=-1  # CPU
                )
                logger.info("Enhanced sentiment: transformers pipeline loaded")
            except (ImportError, Exception) as e:
                logger.debug(f"Transformers sentiment not available: {e}")

        if not self._backend:
            self._backend = "rule_based"
            logger.warning("Sentiment: using basic rule-based fallback")

    async def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment of text"""
        if not text or not text.strip():
            return SentimentResult(
                label="neutral", score=0.5, polarity=0.0
            )

        return await asyncio.get_event_loop().run_in_executor(
            None, self._blocking_analyze, text
        )

    def _blocking_analyze(self, text: str) -> SentimentResult:
        """Full sentiment analysis"""
        text_lower = text.lower()

        # Get base sentiment
        if self._vader:
            base_result = self._vader_analyze(text)
        else:
            base_result = self._rule_based_analyze(text)

        # Enhance with transformers if available
        if self._transformer_pipeline:
            try:
                tf_result = self._transformer_pipeline(text[:512])[0]
                # Blend scores
                if tf_result["label"].upper() == "POSITIVE":
                    base_result.polarity = (base_result.polarity + tf_result["score"]) / 2
                elif tf_result["label"].upper() == "NEGATIVE":
                    base_result.polarity = (base_result.polarity - tf_result["score"]) / 2
            except Exception:
                pass

        # Detect emotions
        emotions = self._detect_emotions(text_lower)

        # Compute urgency
        urgency = self._compute_urgency(text_lower)

        # Detect if question
        is_question = text.strip().endswith("?") or text_lower.startswith(
            ("what", "when", "where", "who", "why", "how", "is", "are", "can", "could", "would", "should", "do", "does")
        )

        # Determine tone
        tone = self._determine_tone(text_lower, base_result.polarity, urgency, is_question)

        return SentimentResult(
            label=base_result.label,
            score=base_result.score,
            polarity=base_result.polarity,
            emotions=emotions,
            urgency=urgency,
            is_question=is_question,
            tone=tone
        )

    def _vader_analyze(self, text: str) -> SentimentResult:
        """VADER sentiment analysis"""
        scores = self._vader.polarity_scores(text)
        compound = scores["compound"]  # -1.0 to +1.0

        if compound >= 0.05:
            label = "positive"
            score = (compound + 1) / 2
        elif compound <= -0.05:
            label = "negative"
            score = (compound + 1) / 2
        else:
            label = "neutral"
            score = 0.5

        return SentimentResult(
            label=label,
            score=round(score, 3),
            polarity=round(compound, 3)
        )

    def _rule_based_analyze(self, text: str) -> SentimentResult:
        """Simple rule-based sentiment"""
        text_lower = text.lower()

        positive_words = ["good", "great", "thanks", "please", "help", "nice", "yes", "love"]
        negative_words = ["bad", "no", "not", "cant", "won't", "hate", "wrong", "error", "broken"]

        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)

        if pos_count > neg_count:
            return SentimentResult(label="positive", score=0.7, polarity=0.4)
        elif neg_count > pos_count:
            return SentimentResult(label="negative", score=0.3, polarity=-0.4)
        else:
            return SentimentResult(label="neutral", score=0.5, polarity=0.0)

    def _detect_emotions(self, text_lower: str) -> Dict[str, float]:
        """Detect emotions from keyword matching"""
        emotions = {}
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > 0:
                emotions[emotion] = min(1.0, matches * 0.4)
        return emotions

    def _compute_urgency(self, text_lower: str) -> float:
        """Compute urgency score from keywords"""
        urgency_count = sum(1 for kw in self.URGENCY_KEYWORDS if kw in text_lower)
        # Add urgency for exclamation marks
        urgency_count += text_lower.count("!")
        return min(1.0, urgency_count * 0.3)

    def _determine_tone(
        self, text_lower: str, polarity: float, urgency: float, is_question: bool
    ) -> str:
        """Determine conversational tone"""
        if urgency > 0.6:
            return "urgent"
        elif polarity < -0.3:
            return "frustrated"
        elif polarity > 0.3:
            return "positive"
        elif is_question:
            return "inquisitive"
        elif any(word in text_lower for word in ["please", "could you", "would you"]):
            return "formal"
        else:
            return "casual"
