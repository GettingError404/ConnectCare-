"""
VoiceOS Test Suite
Tests each pipeline stage in isolation and end-to-end.
"""

import asyncio
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import load_settings


# ─────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def settings():
    return load_settings()


@pytest.fixture
async def pipeline(settings):
    from pipeline.orchestrator import VoiceAssistantPipeline
    return VoiceAssistantPipeline(settings)


# ─────────────────────────────────────────────────────────────
# Language Detection Tests
# ─────────────────────────────────────────────────────────────

class TestLanguageDetection:
    @pytest.mark.asyncio
    async def test_english_detection(self, settings):
        from pipeline.language import LanguageDetector
        detector = LanguageDetector(settings.language)
        result = await detector.detect("Hello, how are you today?")
        assert result.language_code == "en"
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_arabic_heuristic(self, settings):
        from pipeline.language import LanguageDetector
        detector = LanguageDetector(settings.language)
        result = await detector.detect("مرحبا كيف حالك اليوم")
        assert result.language_code == "ar"

    @pytest.mark.asyncio
    async def test_chinese_heuristic(self, settings):
        from pipeline.language import LanguageDetector
        detector = LanguageDetector(settings.language)
        result = await detector.detect("今天天气怎么样")
        assert result.language_code == "zh"

    @pytest.mark.asyncio
    async def test_short_text_defaults_english(self, settings):
        from pipeline.language import LanguageDetector
        detector = LanguageDetector(settings.language)
        result = await detector.detect("Hi")
        assert result.language_code == "en"


# ─────────────────────────────────────────────────────────────
# Sentiment Analysis Tests
# ─────────────────────────────────────────────────────────────

class TestSentiment:
    @pytest.mark.asyncio
    async def test_positive_sentiment(self, settings):
        from pipeline.sentiment import SentimentAnalyzer
        analyzer = SentimentAnalyzer(settings.sentiment)
        result = await analyzer.analyze("This is absolutely wonderful! I love it!")
        assert result.label == "positive"
        assert result.polarity > 0

    @pytest.mark.asyncio
    async def test_negative_sentiment(self, settings):
        from pipeline.sentiment import SentimentAnalyzer
        analyzer = SentimentAnalyzer(settings.sentiment)
        result = await analyzer.analyze("This is terrible and I hate it completely")
        assert result.label == "negative"
        assert result.polarity < 0

    @pytest.mark.asyncio
    async def test_urgency_detection(self, settings):
        from pipeline.sentiment import SentimentAnalyzer
        analyzer = SentimentAnalyzer(settings.sentiment)
        result = await analyzer.analyze("URGENT: I need help immediately!")
        assert result.urgency > 0.3

    @pytest.mark.asyncio
    async def test_question_detection(self, settings):
        from pipeline.sentiment import SentimentAnalyzer
        analyzer = SentimentAnalyzer(settings.sentiment)
        result = await analyzer.analyze("What is the weather today?")
        assert result.is_question is True

    @pytest.mark.asyncio
    async def test_empty_text(self, settings):
        from pipeline.sentiment import SentimentAnalyzer
        analyzer = SentimentAnalyzer(settings.sentiment)
        result = await analyzer.analyze("")
        assert result.label == "neutral"


# ─────────────────────────────────────────────────────────────
# Skill Manager Tests
# ─────────────────────────────────────────────────────────────

class TestSkillManager:
    @pytest.mark.asyncio
    async def test_weather_routing(self, settings):
        from pipeline.skill_manager import SkillManager
        manager = SkillManager(settings.skills)
        match = await manager.route(intent="get_weather", entities={})
        assert match.name == "weather"
        assert match.confidence == 1.0

    @pytest.mark.asyncio
    async def test_timer_routing(self, settings):
        from pipeline.skill_manager import SkillManager
        manager = SkillManager(settings.skills)
        match = await manager.route(intent="set_timer", entities={"duration": "5 minutes"})
        assert match.name == "timer"

    @pytest.mark.asyncio
    async def test_unknown_intent_fallback(self, settings):
        from pipeline.skill_manager import SkillManager
        manager = SkillManager(settings.skills)
        match = await manager.route(intent="totally_unknown_xyz", entities={})
        assert match.name == "general_conversation"

    @pytest.mark.asyncio
    async def test_joke_routing(self, settings):
        from pipeline.skill_manager import SkillManager
        manager = SkillManager(settings.skills)
        match = await manager.route(intent="tell_joke", entities={})
        assert match.name == "entertainment"

    def test_list_skills(self, settings):
        from pipeline.skill_manager import SkillManager
        manager = SkillManager(settings.skills)
        skills = manager.list_skills()
        assert len(skills) > 0
        assert any(s["name"] == "weather" for s in skills)
        assert any(s["name"] == "timer" for s in skills)


# ─────────────────────────────────────────────────────────────
# Action Handler Tests
# ─────────────────────────────────────────────────────────────

class TestActionHandler:
    @pytest.mark.asyncio
    async def test_time_action(self, settings):
        from pipeline.action_handler import ActionHandler
        handler = ActionHandler(settings.actions)
        result = await handler.execute(
            skill_name="time",
            intent="get_time",
            entities={},
            context={}
        )
        assert result["success"] is True
        assert result["type"] == "time"
        assert "time" in result

    @pytest.mark.asyncio
    async def test_joke_action(self, settings):
        from pipeline.action_handler import ActionHandler
        handler = ActionHandler(settings.actions)
        result = await handler.execute(
            skill_name="entertainment",
            intent="tell_joke",
            entities={},
            context={}
        )
        assert result["success"] is True
        assert "joke" in result

    @pytest.mark.asyncio
    async def test_timer_set(self, settings):
        from pipeline.action_handler import ActionHandler
        handler = ActionHandler(settings.actions)
        result = await handler.execute(
            skill_name="timer",
            intent="set_timer",
            entities={"duration": "2 minutes"},
            context={}
        )
        assert result["success"] is True
        assert result["type"] == "timer"
        assert result["duration_seconds"] == 120

    @pytest.mark.asyncio
    async def test_duration_parsing(self, settings):
        from pipeline.action_handler import ActionHandler
        handler = ActionHandler(settings.actions)
        assert handler._parse_duration("5 minutes") == 300
        assert handler._parse_duration("1 hour") == 3600
        assert handler._parse_duration("30 seconds") == 30
        assert handler._parse_duration("2 hours 30 minutes") == 9000


# ─────────────────────────────────────────────────────────────
# Response Generation Tests
# ─────────────────────────────────────────────────────────────

class TestResponseGeneration:
    @pytest.mark.asyncio
    async def test_time_response(self, settings):
        from pipeline.response_generator import ResponseGenerator
        generator = ResponseGenerator(settings.response)
        result = await generator.generate(
            action_result={
                "type": "time",
                "time": "3:30 PM",
                "day_of_week": "Friday",
                "date": "Friday, April 17, 2026"
            },
            intent="get_time",
            sentiment={"tone": "neutral", "label": "neutral"},
            skill_name="time",
            context={}
        )
        assert result.text
        assert "3:30" in result.text or "Friday" in result.text

    @pytest.mark.asyncio
    async def test_joke_response(self, settings):
        from pipeline.response_generator import ResponseGenerator
        generator = ResponseGenerator(settings.response)
        result = await generator.generate(
            action_result={"type": "joke", "joke": "Why don't scientists trust atoms? Because they make up everything!"},
            intent="tell_joke",
            sentiment={"tone": "positive", "label": "positive"},
            skill_name="entertainment",
            context={}
        )
        assert "atoms" in result.text or "everything" in result.text

    @pytest.mark.asyncio
    async def test_sentiment_prefix_frustrated(self, settings):
        from pipeline.response_generator import ResponseGenerator
        generator = ResponseGenerator(settings.response)
        result = await generator.generate(
            action_result={"type": "time", "time": "3:00 PM", "day_of_week": "Monday", "date": "Monday"},
            intent="get_time",
            sentiment={"tone": "frustrated", "label": "negative"},
            skill_name="time",
            context={}
        )
        # Should start with empathetic prefix
        assert result.text


# ─────────────────────────────────────────────────────────────
# End-to-End Pipeline Tests
# ─────────────────────────────────────────────────────────────

class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_full_pipeline_text(self, settings):
        from pipeline.orchestrator import VoiceAssistantPipeline
        pipeline = VoiceAssistantPipeline(settings)

        ctx = await pipeline.process_text_direct("What time is it?")

        assert ctx.transcript == "What time is it?"
        assert ctx.detected_language is not None
        assert ctx.intent is not None
        assert ctx.response_text is not None
        assert ctx.latency_ms > 0
        assert ctx.error is None

    @pytest.mark.asyncio
    async def test_pipeline_with_joke(self, settings):
        from pipeline.orchestrator import VoiceAssistantPipeline
        pipeline = VoiceAssistantPipeline(settings)

        ctx = await pipeline.process_text_direct("Tell me a joke")

        assert ctx.intent == "tell_joke"
        assert ctx.skill_name == "entertainment"
        assert ctx.response_text
        assert ctx.error is None

    @pytest.mark.asyncio
    async def test_pipeline_error_recovery(self, settings):
        from pipeline.orchestrator import VoiceAssistantPipeline
        pipeline = VoiceAssistantPipeline(settings)

        # Empty input should not crash
        ctx = await pipeline.process_text_direct("")
        # Should handle gracefully

    @pytest.mark.asyncio
    async def test_pipeline_trace_populated(self, settings):
        from pipeline.orchestrator import VoiceAssistantPipeline
        pipeline = VoiceAssistantPipeline(settings)

        ctx = await pipeline.process_text_direct("Set a timer for 3 minutes")

        # Pipeline trace should have entries
        assert len(ctx.pipeline_trace) > 0
        stage_names = [t["stage"] for t in ctx.pipeline_trace]
        assert "language_detection" in stage_names

    @pytest.mark.asyncio
    async def test_pipeline_latency(self, settings):
        from pipeline.orchestrator import VoiceAssistantPipeline
        pipeline = VoiceAssistantPipeline(settings)

        start = time.time()
        ctx = await pipeline.process_text_direct("What is the weather today?")
        total = (time.time() - start) * 1000

        print(f"\nEnd-to-end latency: {total:.0f}ms")
        # Should complete within 30 seconds even with slow backends
        assert total < 30000

    @pytest.mark.asyncio
    async def test_multilingual_french(self, settings):
        from pipeline.orchestrator import VoiceAssistantPipeline
        pipeline = VoiceAssistantPipeline(settings)

        # French input
        ctx = await pipeline.process_text_direct("Quelle heure est-il?")
        assert ctx.response_text is not None

    @pytest.mark.asyncio
    async def test_pipeline_status(self, settings):
        from pipeline.orchestrator import VoiceAssistantPipeline
        pipeline = VoiceAssistantPipeline(settings)

        status = pipeline.get_pipeline_status()
        assert "state" in status
        assert "components" in status


# ─────────────────────────────────────────────────────────────
# Metrics Tests
# ─────────────────────────────────────────────────────────────

class TestMetrics:
    def test_metrics_recording(self, settings):
        from utils.metrics import PipelineMetrics
        metrics = PipelineMetrics()

        metrics.record_stage("stt", 0.150)  # 150ms
        metrics.record_stage("stt", 0.200)  # 200ms

        summary = metrics.get_summary()
        assert summary["stages"]["stt"]["calls"] == 2
        assert summary["stages"]["stt"]["avg_latency_ms"] == 175.0

    def test_metrics_error_tracking(self, settings):
        from utils.metrics import PipelineMetrics
        metrics = PipelineMetrics()

        metrics.record_stage("nlp", 0.1)
        metrics.record_error("nlp")

        summary = metrics.get_summary()
        assert summary["stages"]["nlp"]["errors"] == 1
        assert summary["stages"]["nlp"]["success_rate"] < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
