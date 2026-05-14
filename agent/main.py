"""
VoiceOS - Main Entry Point (VOICE-ONLY VERSION)
Default: Pure voice mode. No text interface.
"""

import asyncio
import argparse
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import load_settings, configure_clean_logging


# -------------------------
# VOICE MODE (DEFAULT)
# -------------------------
def run_voice_mode(settings):
    from pipeline.orchestrator import VoiceAssistantPipeline

    print("=" * 50)
    print("🎙️  VoiceOS - Voice Assistant")
    print("=" * 50)
    print(f"   Wake word : '{settings.wake_word.keyword}'")
    print(f"   STT       : Vosk (offline)")
    print(f"   TTS       : {settings.tts.backend or 'auto'}")
    print("-" * 50)
    print("   Press Ctrl+C to stop\n")

    async def _run():
        pipeline = VoiceAssistantPipeline(settings)
        await pipeline.run()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\n👋 VoiceOS stopped.")


# -------------------------
# API MODE (OPTIONAL)
# -------------------------
def run_api_mode(settings):
    import uvicorn

    print(f"🌐 API running at http://{settings.api_host}:{settings.api_port}")
    print(f"   Docs: http://localhost:{settings.api_port}/docs")

    uvicorn.run(
        "api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


# -------------------------
# MAIN - VOICE BY DEFAULT
# -------------------------
def main():
    parser = argparse.ArgumentParser(
        description="VoiceOS - Pure Voice Assistant (default: voice)"
    )

    parser.add_argument(
        "mode",
        choices=["voice", "api"],
        default="voice",
        nargs="?",
        help="voice (default) | api"
    )

    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--quiet", action="store_true", help="Suppress startup messages")
    parser.add_argument("--log-level", default="INFO")

    args = parser.parse_args()

    # Logging setup
    if args.debug:
        os.environ["DEBUG"] = "true"
        os.environ["LOG_LEVEL"] = "DEBUG"
        log_level = "DEBUG"
    else:
        os.environ["LOG_LEVEL"] = args.log_level.upper()
        log_level = args.log_level.upper()

    configure_clean_logging(log_level=log_level)
    settings = load_settings()

    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    modes = {
        "voice": run_voice_mode,
        "api": run_api_mode,
    }

    modes[args.mode](settings)


if __name__ == "__main__":
    main()

