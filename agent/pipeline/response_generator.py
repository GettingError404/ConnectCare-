"""
Response Generator
Converts action results to natural language responses.
Uses templates for structured data and Ollama for conversational responses.
Adapts tone based on sentiment analysis.
"""

import asyncio
import logging
import aiohttp
import json
import random
from typing import Dict, Any, Optional
from config.settings import ResponseSettings

logger = logging.getLogger(__name__)


class ResponseResult:
    def __init__(self, text: str):
        self.text = text
    def __repr__(self):
        return f"ResponseResult(text={self.text[:50]!r})"


class ResponseGenerator:
    TEMPLATES = {
        "weather": {
            "positive": "Great news! In {location}, it's {temperature}{unit} with {condition}. Winds at {wind_speed} {wind_unit}.",
            "neutral":  "Currently in {location}: {temperature}{unit}, {condition}. Wind: {wind_speed} {wind_unit}.",
            "negative": "Here's the weather for {location}: {temperature}{unit} with {condition}.",
        },
        "timer_set":       "Timer set for {duration_text}. I'll let you know when it's done!",
        "timer_cancelled": "All timers have been cancelled.",
        "timer_status":    "You have {count} active timer(s).",
        "time": {
            "get_time": "It's {time} on {day_of_week}.",
            "get_date": "Today is {date}.",
        },
        "joke":         "{joke}",
        "definition":   "{word} ({part_of_speech}): {definition}",
        "music_playing":"Now {action} {song_info}.",
        "smart_home":   "I've {action} the {device}{room_info}.",
        "reminder_set": "Reminder set for '{message}' in {time}.",
    }

    SENTIMENT_PREFIXES = {
        "frustrated": ["I understand that's frustrating. ", "I'm sorry. Let me help. "],
        "positive":   ["Great! ", "Happy to help! "],
        "urgent":     ["Right away! ", "On it! ", ""],
        "neutral":    ["", "Sure, ", ""],
        "inquisitive":["", "Of course! ", "Let me check — "],
    }

    CONVERSATION_SYSTEM_PROMPT = (
        "You are a helpful voice assistant. Give concise spoken responses (1-3 sentences). "
        "No markdown or lists. Be natural and warm."
    )

    def __init__(self, settings: ResponseSettings):
        self.settings = settings
        self._ollama_url = settings.ollama_url
        self._ollama_model = settings.ollama_model
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10.0))
        return self._session

    async def generate(self, action_result, intent, sentiment, skill_name, context) -> ResponseResult:
        if not action_result:
            return ResponseResult("I'm sorry, I couldn't process that request.")

        text = await self._generate_from_template(action_result, intent, sentiment, skill_name)

        if not text or action_result.get("needs_llm_response"):
            text = await self._generate_from_llm(action_result, intent, sentiment, context)

        if not text:
            text = self._rule_based_response(intent, action_result)

        text = self._apply_sentiment_prefix(text, sentiment)
        return ResponseResult(text)

    async def _generate_from_template(self, action_result, intent, sentiment, skill_name):
        rtype = action_result.get("type", "")
        tone  = (sentiment or {}).get("tone", "neutral")
        try:
            if rtype == "weather":
                key = "positive" if tone == "positive" else "negative" if tone == "frustrated" else "neutral"
                return self.TEMPLATES["weather"][key].format(**action_result)
            if rtype == "timer":
                a = action_result.get("action", "")
                if a == "set":       return self.TEMPLATES["timer_set"].format(**action_result)
                if a == "cancelled": return self.TEMPLATES["timer_cancelled"]
                if a == "status":    return self.TEMPLATES["timer_status"].format(count=len(action_result.get("active_timers", [])))
            if rtype == "time":
                key = intent if intent in self.TEMPLATES["time"] else "get_time"
                return self.TEMPLATES["time"][key].format(**action_result)
            if rtype == "joke":
                return self.TEMPLATES["joke"].format(**action_result)
            if rtype == "definition" and action_result.get("definition"):
                return self.TEMPLATES["definition"].format(
                    word=action_result.get("word",""),
                    part_of_speech=action_result.get("part_of_speech",""),
                    definition=action_result.get("definition",""))
            if rtype == "music":
                artist, song = action_result.get("artist",""), action_result.get("song","")
                if song and artist: song_info = f"{song} by {artist}"
                elif song:          song_info = song
                elif artist:        song_info = f"music by {artist}"
                else:               song_info = "your music"
                return self.TEMPLATES["music_playing"].format(action=action_result.get("action","playing"), song_info=song_info)
            if rtype == "smart_home":
                room = action_result.get("room","") or ""
                return self.TEMPLATES["smart_home"].format(
                    action=action_result.get("action","toggled"),
                    device=action_result.get("device","device"),
                    room_info=f" in the {room}" if room else "")
            if rtype == "reminder" and action_result.get("action") == "set":
                return self.TEMPLATES["reminder_set"].format(
                    message=action_result.get("message","reminder"),
                    time=action_result.get("time","later"))
            if rtype == "news":
                headlines = action_result.get("headlines", [])
                if headlines:
                    texts = ". ".join(h["title"] for h in headlines[:3] if h.get("title"))
                    return f"Here are the top {action_result.get('topic','general')} headlines: {texts}."
            if rtype == "search" and action_result.get("answer"):
                return action_result["answer"][:300]
        except (KeyError, ValueError) as e:
            logger.warning(f"Template error: {e}")
        return None

    async def _generate_from_llm(self, action_result, intent, sentiment, context):
        transcript = context.get("transcript", "")
        tone = (sentiment or {}).get("tone", "neutral")
        prompt = (f'User said: "{transcript}"\nIntent: {intent}\n'
                  f'Result: {json.dumps(action_result, default=str)[:300]}\n'
                  f'Tone: {tone}\nGenerate a spoken response (1-3 sentences, no markdown).')
        try:
            session = await self._get_session()
            async with session.post(f"{self._ollama_url}/api/generate", json={
                "model": self._ollama_model, "prompt": prompt,
                "system": self.CONVERSATION_SYSTEM_PROMPT,
                "stream": False, "options": {"temperature": 0.7, "num_predict": 150}
            }) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response","").strip()
        except Exception as e:
            logger.warning(f"Ollama fallback failed: {e}")
        return ""

    def _rule_based_response(self, intent, action_result):
        return {
            "greet": "Hello! How can I help you today?",
            "farewell": "Goodbye! Have a great day!",
            "thanks": "You're welcome! Anything else?",
            "unknown": "I'm not sure I understood that. Could you rephrase?",
            "empty_input": "I didn't catch that. Could you repeat?",
        }.get(intent, "I heard you. Let me look into that.")

    def _apply_sentiment_prefix(self, text, sentiment):
        if not sentiment or not text:
            return text
        tone = sentiment.get("tone", "neutral")
        prefix = random.choice(self.SENTIMENT_PREFIXES.get(tone, [""]))
        if prefix and not text.startswith(prefix.strip()):
            return prefix + text
        return text
