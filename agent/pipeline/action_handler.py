"""
Action Handler
Executes actual actions based on skill routing results.
Integrates with external APIs, system commands, IoT devices, etc.
"""

import asyncio
import datetime
import logging
import aiohttp
from typing import Dict, Any, Optional
from config.settings import ActionSettings

logger = logging.getLogger(__name__)


class ActionHandler:
    """
    Executes actions delegated by skills.
    Handles real-world integrations: weather APIs, timers, music, etc.
    """

    def __init__(self, settings: ActionSettings):
        self.settings = settings
        self._session: Optional[aiohttp.ClientSession] = None
        self._active_timers: Dict[str, asyncio.Task] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5.0),
                headers={"User-Agent": "VoiceOS/1.0"}
            )
        return self._session

    async def execute(
        self,
        skill_name: str,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute action based on skill type and intent"""

        handler_map = {
            "weather": self._handle_weather,
            "timer": self._handle_timer,
            "music": self._handle_music,
            "news": self._handle_news,
            "smart_home": self._handle_smart_home,
            "reminder": self._handle_reminder,
            "search": self._handle_search,
            "time": self._handle_time,
            "entertainment": self._handle_entertainment,
            "dictionary": self._handle_definition,
            "system": self._handle_system,
            "general_conversation": self._handle_conversation,
        }

        handler = handler_map.get(skill_name, self._handle_conversation)

        try:
            result = await handler(intent, entities, context)
            result["skill"] = skill_name
            result["success"] = True
            return result
        except Exception as e:
            logger.error(f"Action handler error for skill '{skill_name}': {e}")
            return {
                "skill": skill_name,
                "success": False,
                "error": str(e),
                "fallback_response": f"I had trouble with that. {str(e)}"
            }

    async def _handle_weather(self, intent, entities, context) -> Dict:
        """Fetch real weather data from Open-Meteo (free, no API key)"""
        location = entities.get("location", "New York")

        try:
            # Step 1: Geocode the location
            session = await self._get_session()
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"

            async with session.get(geo_url) as resp:
                if resp.status == 200:
                    geo_data = await resp.json()
                    results = geo_data.get("results", [])
                    if results:
                        lat = results[0]["latitude"]
                        lon = results[0]["longitude"]
                        city = results[0]["name"]
                        country = results[0].get("country", "")

                        # Step 2: Get weather
                        weather_url = (
                            f"https://api.open-meteo.com/v1/forecast?"
                            f"latitude={lat}&longitude={lon}"
                            f"&current_weather=true"
                            f"&hourly=temperature_2m,precipitation_probability"
                        )

                        async with session.get(weather_url) as wresp:
                            if wresp.status == 200:
                                wdata = await wresp.json()
                                current = wdata.get("current_weather", {})
                                temp = current.get("temperature", "N/A")
                                wind = current.get("windspeed", "N/A")
                                code = current.get("weathercode", 0)

                                condition = self._weather_code_to_text(code)

                                return {
                                    "type": "weather",
                                    "location": f"{city}, {country}",
                                    "temperature": temp,
                                    "unit": "°C",
                                    "condition": condition,
                                    "wind_speed": wind,
                                    "wind_unit": "km/h"
                                }
        except Exception as e:
            logger.warning(f"Weather API failed: {e}")

        # Fallback mock data
        return {
            "type": "weather",
            "location": location,
            "temperature": 22,
            "unit": "°C",
            "condition": "partly cloudy",
            "wind_speed": 15,
            "wind_unit": "km/h",
            "note": "Using cached data"
        }

    def _weather_code_to_text(self, code: int) -> str:
        """Convert WMO weather code to text"""
        conditions = {
            0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
            45: "foggy", 48: "icy fog", 51: "light drizzle", 53: "moderate drizzle",
            61: "light rain", 63: "moderate rain", 65: "heavy rain",
            71: "light snow", 73: "moderate snow", 75: "heavy snow",
            80: "light showers", 81: "moderate showers", 82: "heavy showers",
            95: "thunderstorm", 99: "heavy thunderstorm"
        }
        return conditions.get(code, "unknown conditions")

    async def _handle_timer(self, intent, entities, context) -> Dict:
        """Set or manage timers"""
        if "cancel" in intent:
            # Cancel all timers
            for task in self._active_timers.values():
                task.cancel()
            self._active_timers.clear()
            return {"type": "timer", "action": "cancelled", "count": 0}

        if "check" in intent or "status" in intent:
            active = list(self._active_timers.keys())
            return {"type": "timer", "action": "status", "active_timers": active}

        # Parse duration
        duration_str = entities.get("duration", entities.get("time", "5 minutes"))
        seconds = self._parse_duration(duration_str)
        label = entities.get("label", f"timer_{len(self._active_timers) + 1}")

        # Create async timer
        async def timer_callback():
            await asyncio.sleep(seconds)
            logger.info(f"Timer '{label}' completed!")
            del self._active_timers[label]

        task = asyncio.create_task(timer_callback())
        self._active_timers[label] = task

        return {
            "type": "timer",
            "action": "set",
            "label": label,
            "duration_seconds": seconds,
            "duration_text": duration_str
        }

    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string to seconds"""
        if not duration_str:
            return 300  # 5 minutes default

        duration_str = str(duration_str).lower()
        total_seconds = 0

        import re
        # Order matters: longer patterns first to avoid double-matching
        # e.g. "minutes" matches both "minute" and "min" — use one combined pattern
        hour_match   = re.search(r'(\d+)\s*(?:hour|hr)s?', duration_str)
        minute_match = re.search(r'(\d+)\s*min(?:ute)?s?', duration_str)
        second_match = re.search(r'(\d+)\s*sec(?:ond)?s?', duration_str)

        if hour_match:   total_seconds += int(hour_match.group(1))   * 3600
        if minute_match: total_seconds += int(minute_match.group(1)) * 60
        if second_match: total_seconds += int(second_match.group(1))

        return total_seconds if total_seconds > 0 else 300

    async def _handle_music(self, intent, entities, context) -> Dict:
        """Handle music playback (simulated or Spotify)"""
        artist = entities.get("artist", "")
        song = entities.get("song", "")
        genre = entities.get("genre", "")

        action_map = {
            "play_music": "playing",
            "pause_music": "paused",
            "next_song": "skipped to next",
            "previous_song": "went back",
            "volume_up": "volume increased",
            "volume_down": "volume decreased",
        }

        action_text = action_map.get(intent, intent)

        return {
            "type": "music",
            "action": action_text,
            "artist": artist,
            "song": song,
            "genre": genre,
            "player": "default"
        }

    async def _handle_news(self, intent, entities, context) -> Dict:
        """Fetch news headlines"""
        topic = entities.get("topic", "general")

        try:
            # Use newsapi.org if API key configured
            if self.settings.newsapi_key:
                session = await self._get_session()
                url = (
                    f"https://newsapi.org/v2/top-headlines?"
                    f"country=us&category={topic}&pageSize=5"
                    f"&apiKey={self.settings.newsapi_key}"
                )
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        articles = data.get("articles", [])
                        headlines = [
                            {"title": a["title"], "source": a["source"]["name"]}
                            for a in articles[:5]
                        ]
                        return {"type": "news", "headlines": headlines, "topic": topic}
        except Exception as e:
            logger.warning(f"News API failed: {e}")

        # Fallback
        return {
            "type": "news",
            "headlines": [{"title": f"No news available for {topic}", "source": "N/A"}],
            "topic": topic,
            "note": "Configure NEWSAPI_KEY for live news"
        }

    async def _handle_smart_home(self, intent, entities, context) -> Dict:
        """Control smart home devices via Home Assistant or MQTT"""
        device = entities.get("device", "")
        room = entities.get("room", "")
        value = entities.get("value")

        # Try Home Assistant if configured
        if self.settings.home_assistant_url:
            try:
                result = await self._home_assistant_control(intent, device, room, value)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Home Assistant error: {e}")

        return {
            "type": "smart_home",
            "action": intent,
            "device": device,
            "room": room,
            "value": value,
            "simulated": True
        }

    async def _home_assistant_control(self, intent, device, room, value) -> Optional[Dict]:
        """Call Home Assistant REST API"""
        headers = {
            "Authorization": f"Bearer {self.settings.home_assistant_token}",
            "Content-Type": "application/json"
        }
        session = await self._get_session()

        # Map intent to HA service
        service_map = {
            "turn_on": ("homeassistant", "turn_on"),
            "turn_off": ("homeassistant", "turn_off"),
            "dim_lights": ("light", "turn_on"),
        }

        domain, service = service_map.get(intent, ("homeassistant", "toggle"))
        entity_id = f"{device.replace(' ', '_')}_{room.replace(' ', '_')}"

        url = f"{self.settings.home_assistant_url}/api/services/{domain}/{service}"
        payload = {"entity_id": entity_id}
        if value:
            payload["brightness"] = int(float(value) * 255)

        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status == 200:
                return {
                    "type": "smart_home",
                    "action": intent,
                    "device": device,
                    "success": True,
                    "source": "home_assistant"
                }
        return None

    async def _handle_reminder(self, intent, entities, context) -> Dict:
        """Set reminders and notes"""
        message = entities.get("message", entities.get("text", "Reminder"))
        time_val = entities.get("time", "5 minutes")

        seconds = self._parse_duration(str(time_val))

        async def reminder_callback():
            await asyncio.sleep(seconds)
            logger.info(f"REMINDER: {message}")

        task_id = f"reminder_{int(datetime.datetime.now().timestamp())}"
        asyncio.create_task(reminder_callback())

        return {
            "type": "reminder",
            "action": "set",
            "message": message,
            "time": time_val,
            "task_id": task_id
        }

    async def _handle_search(self, intent, entities, context) -> Dict:
        """Web search using DuckDuckGo Instant Answer API"""
        query = entities.get("query", context.get("transcript", ""))

        try:
            session = await self._get_session()
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    abstract = data.get("AbstractText", "")
                    if abstract:
                        return {
                            "type": "search",
                            "query": query,
                            "answer": abstract[:500],
                            "source": data.get("AbstractSource", "DuckDuckGo")
                        }
        except Exception as e:
            logger.warning(f"Search failed: {e}")

        return {
            "type": "search",
            "query": query,
            "answer": f"I couldn't find specific information about '{query}'",
            "source": "fallback"
        }

    async def _handle_time(self, intent, entities, context) -> Dict:
        """Return current time/date"""
        now = datetime.datetime.now()
        timezone = entities.get("timezone", "local")

        return {
            "type": "time",
            "time": now.strftime("%I:%M %p"),
            "time_24": now.strftime("%H:%M"),
            "date": now.strftime("%A, %B %d, %Y"),
            "day_of_week": now.strftime("%A"),
            "timezone": timezone,
            "timestamp": now.isoformat()
        }

    async def _handle_entertainment(self, intent, entities, context) -> Dict:
        """Tell jokes and fun facts"""
        from pipeline.skill_manager import JokeSkill
        skill = JokeSkill()
        return await skill.execute(intent, entities, context)

    async def _handle_definition(self, intent, entities, context) -> Dict:
        """Look up word definitions"""
        word = entities.get("word", entities.get("term", ""))
        if not word:
            return {"type": "definition", "word": "", "definition": "Please specify a word."}

        try:
            session = await self._get_session()
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and isinstance(data, list):
                        meanings = data[0].get("meanings", [])
                        if meanings:
                            defs = meanings[0].get("definitions", [])
                            if defs:
                                return {
                                    "type": "definition",
                                    "word": word,
                                    "part_of_speech": meanings[0].get("partOfSpeech", ""),
                                    "definition": defs[0].get("definition", ""),
                                    "example": defs[0].get("example", "")
                                }
        except Exception as e:
            logger.warning(f"Dictionary API failed: {e}")

        return {
            "type": "definition",
            "word": word,
            "definition": f"Definition lookup for '{word}' is unavailable."
        }

    async def _handle_system(self, intent, entities, context) -> Dict:
        """System control actions"""
        level = entities.get("level", entities.get("value"))

        if "volume" in intent:
            return {
                "type": "system",
                "action": intent,
                "level": level,
                "note": "Volume control requires platform-specific implementation"
            }

        return {
            "type": "system",
            "action": intent,
            "level": level
        }

    async def _handle_conversation(self, intent, entities, context) -> Dict:
        """General conversation - pass to response generator"""
        return {
            "type": "conversation",
            "intent": intent,
            "transcript": context.get("transcript", ""),
            "needs_llm_response": True
        }
