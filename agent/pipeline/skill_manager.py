"""
Skill Manager
Routes intents to registered skills.
Each skill handles specific domains: weather, timer, music, news, etc.
Supports dynamic skill registration and priority routing.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Type
from abc import ABC, abstractmethod
from config.settings import SkillSettings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Base Skill
# ─────────────────────────────────────────────────────────────

@dataclass
class SkillMatch:
    name: str
    confidence: float
    skill_instance: Any = None


class BaseSkill(ABC):
    """Abstract base class for all skills"""
    name: str = "base"
    description: str = ""
    intents: List[str] = []
    priority: int = 5  # 1-10, higher = checked first

    @abstractmethod
    async def execute(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the skill and return result dict"""
        pass

    def can_handle(self, intent: str) -> float:
        """Return confidence (0-1) that this skill can handle the intent"""
        if intent in self.intents:
            return 1.0
        # Fuzzy matching for partial intent names
        for skill_intent in self.intents:
            if intent.startswith(skill_intent.split("_")[0]):
                return 0.6
        return 0.0


# ─────────────────────────────────────────────────────────────
# Built-in Skills
# ─────────────────────────────────────────────────────────────

class WeatherSkill(BaseSkill):
    name = "weather"
    description = "Get current weather and forecasts"
    intents = ["get_weather", "weather_forecast", "temperature_query"]
    priority = 8

    async def execute(self, intent, entities, context):
        location = entities.get("location", "your location")
        return {
            "type": "weather",
            "location": location,
            "action": "fetch_weather",
            "params": {"location": location, "units": "metric"}
        }


class TimerSkill(BaseSkill):
    name = "timer"
    description = "Set, cancel, or check timers and alarms"
    intents = ["set_timer", "cancel_timer", "check_timer", "set_alarm"]
    priority = 9

    async def execute(self, intent, entities, context):
        duration = entities.get("duration", entities.get("time", "5 minutes"))
        label = entities.get("label", "timer")
        return {
            "type": "timer",
            "action": "set" if "set" in intent else "check",
            "duration": duration,
            "label": label
        }


class MusicSkill(BaseSkill):
    name = "music"
    description = "Play, pause, skip music and manage playlists"
    intents = ["play_music", "pause_music", "next_song", "previous_song",
               "volume_up", "volume_down", "shuffle", "repeat"]
    priority = 7

    async def execute(self, intent, entities, context):
        artist = entities.get("artist")
        song = entities.get("song")
        genre = entities.get("genre")
        return {
            "type": "music",
            "action": intent,
            "artist": artist,
            "song": song,
            "genre": genre
        }


class NewsSkill(BaseSkill):
    name = "news"
    description = "Get latest news and headlines"
    intents = ["get_news", "news_headlines", "news_search"]
    priority = 6

    async def execute(self, intent, entities, context):
        topic = entities.get("topic", entities.get("category", "general"))
        return {
            "type": "news",
            "action": "fetch_news",
            "topic": topic,
            "count": 5
        }


class SmartHomeSkill(BaseSkill):
    name = "smart_home"
    description = "Control smart home devices (lights, thermostat, etc.)"
    intents = ["control_device", "turn_on", "turn_off", "set_temperature",
               "dim_lights", "lock_door", "check_device_status"]
    priority = 8

    async def execute(self, intent, entities, context):
        device = entities.get("device", "device")
        room = entities.get("room")
        value = entities.get("value")
        return {
            "type": "smart_home",
            "action": intent,
            "device": device,
            "room": room,
            "value": value
        }


class ReminderSkill(BaseSkill):
    name = "reminder"
    description = "Set and manage reminders and notes"
    intents = ["set_reminder", "get_reminders", "cancel_reminder", "add_note"]
    priority = 8

    async def execute(self, intent, entities, context):
        message = entities.get("message", entities.get("text", ""))
        time_val = entities.get("time", entities.get("datetime"))
        return {
            "type": "reminder",
            "action": intent,
            "message": message,
            "time": time_val
        }


class SearchSkill(BaseSkill):
    name = "search"
    description = "Search the web and answer general knowledge questions"
    intents = ["search_web", "web_search", "find_information", "lookup"]
    priority = 5

    async def execute(self, intent, entities, context):
        query = entities.get("query", context.get("transcript", ""))
        return {
            "type": "search",
            "action": "web_search",
            "query": query
        }


class TimeSkill(BaseSkill):
    name = "time"
    description = "Get current time, date, and timezone information"
    intents = ["get_time", "get_date", "get_timezone", "world_clock"]
    priority = 9

    async def execute(self, intent, entities, context):
        import datetime
        timezone = entities.get("timezone", "local")
        now = datetime.datetime.now()

        return {
            "type": "time",
            "action": intent,
            "time": now.strftime("%I:%M %p"),
            "date": now.strftime("%A, %B %d, %Y"),
            "timezone": timezone
        }


class JokeSkill(BaseSkill):
    name = "entertainment"
    description = "Tell jokes and fun facts"
    intents = ["tell_joke", "fun_fact", "riddle"]
    priority = 4

    JOKES = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "I told my wife she was drawing her eyebrows too high. She looked surprised.",
        "Why don't eggs tell jokes? They'd crack each other up.",
        "What do you call a fake noodle? An impasta!",
        "Why did the scarecrow win an award? Because he was outstanding in his field!",
    ]

    async def execute(self, intent, entities, context):
        import random
        return {
            "type": "joke",
            "action": "tell_joke",
            "joke": random.choice(self.JOKES)
        }


class DefinitionSkill(BaseSkill):
    name = "dictionary"
    description = "Define words and explain concepts"
    intents = ["get_definition", "define_word", "explain_concept", "what_is"]
    priority = 6

    async def execute(self, intent, entities, context):
        word = entities.get("word", entities.get("term", ""))
        return {
            "type": "definition",
            "action": "define",
            "word": word
        }


class SystemControlSkill(BaseSkill):
    name = "system"
    description = "System controls: volume, brightness, settings"
    intents = ["volume_control", "mute", "unmute", "brightness_control",
               "system_control", "wifi_toggle"]
    priority = 9

    async def execute(self, intent, entities, context):
        level = entities.get("level", entities.get("value"))
        return {
            "type": "system",
            "action": intent,
            "level": level
        }


class ConversationSkill(BaseSkill):
    name = "general_conversation"
    description = "Handle general conversation and chitchat"
    intents = ["greet", "farewell", "thanks", "general_question",
               "unknown", "general_conversation", "chitchat"]
    priority = 1  # Lowest priority - fallback

    async def execute(self, intent, entities, context):
        return {
            "type": "conversation",
            "action": "respond",
            "transcript": context.get("transcript", ""),
            "intent": intent
        }


# ─────────────────────────────────────────────────────────────
# Skill Manager
# ─────────────────────────────────────────────────────────────

class SkillManager:
    """
    Routes intents to appropriate skills.
    Supports dynamic registration and priority-based routing.
    """

    # All built-in skills
    BUILT_IN_SKILLS: List[Type[BaseSkill]] = [
        WeatherSkill,
        TimerSkill,
        MusicSkill,
        NewsSkill,
        SmartHomeSkill,
        ReminderSkill,
        SearchSkill,
        TimeSkill,
        JokeSkill,
        DefinitionSkill,
        SystemControlSkill,
        ConversationSkill,  # Always last (fallback)
    ]

    def __init__(self, settings: SkillSettings):
        self.settings = settings
        self._skills: Dict[str, BaseSkill] = {}
        self._intent_map: Dict[str, str] = {}  # intent → skill_name

        self._register_built_in_skills()

    def _register_built_in_skills(self):
        """Register all built-in skills"""
        for skill_class in self.BUILT_IN_SKILLS:
            skill = skill_class()
            self._skills[skill.name] = skill
            for intent in skill.intents:
                self._intent_map[intent] = skill.name
        logger.info(f"Registered {len(self._skills)} skills, {len(self._intent_map)} intents")

    def register_skill(self, skill: BaseSkill):
        """Dynamically register a new skill"""
        self._skills[skill.name] = skill
        for intent in skill.intents:
            self._intent_map[intent] = skill.name
        logger.info(f"Registered custom skill: {skill.name}")

    async def route(
        self,
        intent: str,
        entities: Dict[str, Any],
        sentiment: Optional[Dict] = None,
        transcript: Optional[str] = None
    ) -> SkillMatch:
        """
        Route an intent to the best matching skill.
        Returns SkillMatch with skill name and confidence.
        """

        # Direct intent lookup
        if intent in self._intent_map:
            skill_name = self._intent_map[intent]
            return SkillMatch(
                name=skill_name,
                confidence=1.0,
                skill_instance=self._skills[skill_name]
            )

        # Fuzzy matching - find best skill by confidence
        best_match = None
        best_confidence = 0.0

        # Sort by priority (descending)
        sorted_skills = sorted(
            self._skills.values(),
            key=lambda s: s.priority,
            reverse=True
        )

        for skill in sorted_skills:
            confidence = skill.can_handle(intent)
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = skill

        if best_match and best_confidence > 0.3:
            return SkillMatch(
                name=best_match.name,
                confidence=best_confidence,
                skill_instance=best_match
            )

        # Sentiment-based routing (e.g., if user is frustrated → prioritize help)
        if sentiment and sentiment.get("tone") == "urgent":
            return SkillMatch(
                name="search",
                confidence=0.5,
                skill_instance=self._skills.get("search")
            )

        # Default to general conversation
        return SkillMatch(
            name="general_conversation",
            confidence=0.3,
            skill_instance=self._skills["general_conversation"]
        )

    def list_skills(self) -> List[Dict[str, Any]]:
        """List all registered skills"""
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "intents": skill.intents,
                "priority": skill.priority
            }
            for skill in self._skills.values()
        ]
