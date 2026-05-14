# VoiceOS 🎙️

> **Production-grade, modular voice assistant pipeline** — offline-first, multilingual, extensible.

```
Microphone → Wake Word → STT (Vosk) → Language Detection → Translation (English pivot)
         → Hybrid NLP (Rasa + Ollama) → Sentiment Analysis → Skill Manager
         → Action Handler → Response Generator → Translate Back → TTS
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        VoiceOS Pipeline                          │
│                                                                   │
│  🎤 Audio    ──►  Wake Word  ──►  Vosk STT  ──►  Lang Detect    │
│                   (Porcupine/      (offline)      (Lingua/        │
│                    Energy VAD)                     langdetect)    │
│                                                         │         │
│                                                    Translation    │
│                                                  (LibreTranslate) │
│                                                         │         │
│                 ┌───────────────────────────────────────┘         │
│                 ▼                                                 │
│            Hybrid NLP                                             │
│         ┌──────────────┐                                         │
│         │  Rasa NLU    │ ──► confidence ≥ 0.7?                  │
│         │  (primary)   │         │         │                     │
│         └──────────────┘        YES        NO                    │
│                                  │          │                     │
│                         ┌────────┘    ┌─────▼──────┐            │
│                         │             │  Ollama LLM │            │
│                         │             │  (fallback) │            │
│                         │             └─────────────┘            │
│                         ▼                                         │
│                  Sentiment Analysis  ──►  Skill Router            │
│                  (VADER + emotions)       (12 built-in skills)    │
│                                                │                  │
│                                         Action Handler            │
│                                    (weather, timer, news...)      │
│                                                │                  │
│                                        Response Generator         │
│                                     (templates + Ollama LLM)      │
│                                                │                  │
│                                    Translate Back (if needed)     │
│                                                │                  │
│                                    🔊  TTS Output                 │
│                                 (Coqui/pyttsx3/gTTS/espeak)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download Vosk STT Model

```bash
python scripts/download_models.py --stt en
# For multiple languages:
python scripts/download_models.py --stt en fr de es hi
```

### 3. Start External Services

**Option A: Docker Compose (recommended)**
```bash
docker compose up -d
# Starts: Rasa NLU, Ollama, LibreTranslate
```

**Option B: Manual**
```bash
# Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2

# Rasa NLU
cd rasa && rasa train && rasa run --enable-api

# LibreTranslate (optional)
docker run -p 5000:5000 libretranslate/libretranslate
```

### 4. Configure

```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Run

```bash
# Interactive text mode (no microphone needed — great for testing)
python main.py text

# Full voice mode (requires microphone)
python main.py voice

# REST API server
python main.py api

# Demo mode (runs sample utterances automatically)
python main.py demo
```

---

## Project Structure

```
voice_assistant/
├── main.py                    # Entry point (voice/api/text/demo modes)
├── api.py                     # FastAPI REST + WebSocket API
│
├── pipeline/
│   ├── orchestrator.py        # ★ Main pipeline orchestrator
│   ├── wake_word.py           # Wake word detection (Porcupine/VAD)
│   ├── stt.py                 # Speech-to-Text (Vosk + Whisper fallback)
│   ├── language.py            # Language detection + Translation
│   ├── translator.py          # Translation re-export
│   ├── nlp_hybrid.py          # ★ Hybrid NLP (Rasa + Ollama)
│   ├── sentiment.py           # Sentiment + emotion analysis
│   ├── skill_manager.py       # ★ Skill registry + intent router
│   ├── action_handler.py      # ★ Real-world action execution
│   ├── response_generator.py  # NL response generation
│   └── tts.py                 # Text-to-Speech (multi-backend)
│
├── config/
│   └── settings.py            # Typed config with env var support
│
├── utils/
│   ├── event_bus.py           # Pub/sub for pipeline events
│   └── metrics.py             # Latency + success rate tracking
│
├── skills/
│   └── custom/
│       └── crypto_skill.py    # Example custom skill plugin
│
├── rasa/
│   ├── config.yml             # Rasa NLU pipeline config
│   ├── domain.yml             # Intents, entities, slots
│   └── data/nlu.yml           # Training data (200+ examples)
│
├── scripts/
│   └── download_models.py     # Model download + setup helper
│
├── tests/
│   └── test_pipeline.py       # Comprehensive test suite
│
├── docker-compose.yml         # Full stack: VoiceOS + Rasa + Ollama + LibreTranslate
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Built-in Skills (12)

| Skill | Intents | External API |
|-------|---------|-------------|
| 🌤️ Weather | `get_weather`, `weather_forecast` | Open-Meteo (free) |
| ⏱️ Timer | `set_timer`, `cancel_timer`, `check_timer` | Built-in async |
| 🎵 Music | `play_music`, `pause_music`, `next_song` | Spotify (optional) |
| 📰 News | `get_news`, `news_headlines` | NewsAPI (optional) |
| 🏠 Smart Home | `turn_on`, `turn_off`, `set_temperature` | Home Assistant |
| 🔔 Reminder | `set_reminder`, `get_reminders` | Built-in async |
| 🔍 Search | `search_web`, `lookup` | DuckDuckGo (free) |
| 🕐 Time/Date | `get_time`, `get_date` | System clock |
| 😄 Jokes | `tell_joke`, `fun_fact` | Built-in |
| 📖 Dictionary | `get_definition`, `define_word` | Free Dictionary API |
| 🔊 System | `volume_control`, `mute`, `brightness` | System calls |
| 💬 Conversation | `greet`, `farewell`, `general_question` | Ollama LLM |

---

## REST API

Start with `python main.py api`, then:

```bash
# Process text
curl -X POST http://localhost:8000/process/text \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the weather in Mumbai?", "language": "auto"}'

# Process audio file
curl -X POST http://localhost:8000/process/audio-upload \
  -F "file=@my_audio.wav"

# Health check
curl http://localhost:8000/health

# Pipeline metrics
curl http://localhost:8000/metrics

# List all skills
curl http://localhost:8000/skills
```

### WebSocket Streaming

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/stream");
ws.send(JSON.stringify({ type: "text", text: "Tell me a joke" }));
// Receives real-time stage updates:
// { stage: "language_detection", data: { language: "en" } }
// { stage: "nlp", data: { intent: "tell_joke" } }
// { stage: "complete", response_text: "Why don't scientists trust atoms?..." }
```

---

## Writing Custom Skills

Drop a Python file in `skills/custom/`:

```python
from pipeline.skill_manager import BaseSkill

class StockPriceSkill(BaseSkill):
    name = "stock_price"
    description = "Get real-time stock prices"
    intents = ["get_stock_price", "check_stock", "ticker_price"]
    priority = 7

    async def execute(self, intent, entities, context):
        ticker = entities.get("ticker", "AAPL")
        # ... fetch price from API ...
        return {
            "type": "stock",
            "ticker": ticker,
            "price": 185.32,
            "change": "+1.2%"
        }
```

---

## Supported Languages

| STT (Vosk) | Translation | TTS |
|-----------|-------------|-----|
| English, French, German, Spanish, Portuguese | 50+ via LibreTranslate | 30+ via Coqui/gTTS |
| Chinese, Japanese, Korean | including Arabic, Hindi, Russian | pyttsx3 uses system voices |
| Arabic, Hindi, Russian, Italian, Dutch | Auto-detected pivot via English | espeak: 100+ languages |

---

## NLP Hybrid Strategy

```
User input
    │
    ▼
[Rasa NLU] ──► confidence ≥ 0.7 ──► Use Rasa result
    │
    └── confidence < 0.7 or unavailable
              │
              ▼
         [Ollama LLM]  ──► Structured JSON intent extraction
              │
              └── unavailable
                        │
                        ▼
                [Keyword Fallback]  ──► Rule-based matching
```

---

## Configuration Reference

All settings via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `WAKE_WORD_KEYWORD` | `hey assistant` | Wake phrase |
| `WAKE_WORD_ENGINE` | `energy` | `energy` \| `porcupine` |
| `VOSK_MODEL_DIR` | `./models/vosk` | Vosk models path |
| `RASA_URL` | `http://localhost:5005` | Rasa NLU server |
| `RASA_CONFIDENCE_THRESHOLD` | `0.70` | Min confidence for Rasa |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_MODEL` | `llama3.2` | LLM model for fallback |
| `LIBRETRANSLATE_URL` | `http://localhost:5000` | Translation server |
| `TTS_BACKEND` | `auto` | `auto` \| `pyttsx3` \| `gtts` \| `coqui` |
| `NEWSAPI_KEY` | — | For live news headlines |
| `HOME_ASSISTANT_URL` | — | Smart home integration |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Performance Targets

| Stage | Target Latency |
|-------|---------------|
| Wake Word | < 50ms |
| STT (Vosk) | < 500ms |
| Language Detection | < 20ms |
| Rasa NLU | < 100ms |
| Ollama fallback | < 3s |
| Sentiment | < 10ms |
| Action (local) | < 50ms |
| Action (API) | < 2s |
| Response Gen | < 200ms |
| TTS | < 500ms |
| **Total (local skills)** | **< 1.5s** |

---

## License

MIT
