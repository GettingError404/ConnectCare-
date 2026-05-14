#!/usr/bin/env python3
"""
VoiceOS Model Downloader
Downloads Vosk STT models, Rasa dependencies, and sets up the environment.

Usage:
  python scripts/download_models.py --stt en          # Download English Vosk model
  python scripts/download_models.py --stt en fr de    # Multiple languages
  python scripts/download_models.py --all             # Download all required models
"""

import os
import sys
import argparse
import urllib.request
import zipfile
import shutil
from pathlib import Path

# Vosk model URLs
VOSK_MODELS = {
    "en": ("vosk-model-en-us-0.22", "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"),
    "en-small": ("vosk-model-small-en-us-0.15", "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"),
    "fr": ("vosk-model-fr-0.22", "https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip"),
    "de": ("vosk-model-de-0.21", "https://alphacephei.com/vosk/models/vosk-model-de-0.21.zip"),
    "es": ("vosk-model-es-0.42", "https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip"),
    "zh": ("vosk-model-cn-0.22", "https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip"),
    "hi": ("vosk-model-hi-0.22", "https://alphacephei.com/vosk/models/vosk-model-hi-0.22.zip"),
    "ar": ("vosk-model-ar-mgb2-0.4", "https://alphacephei.com/vosk/models/vosk-model-ar-mgb2-0.4.zip"),
    "ru": ("vosk-model-ru-0.42", "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"),
    "ja": ("vosk-model-ja-0.22", "https://alphacephei.com/vosk/models/vosk-model-ja-0.22.zip"),
    "pt": ("vosk-model-pt-fb-v0.1.1-20220516_2113", "https://alphacephei.com/vosk/models/vosk-model-pt-fb-v0.1.1-20220516_2113.zip"),
}

MODELS_DIR = Path("./models/vosk")


def download_with_progress(url: str, dest_path: Path):
    """Download file with progress bar"""
    print(f"  Downloading {url.split('/')[-1]}...")

    def progress(count, block_size, total_size):
        if total_size > 0:
            percent = min(100, count * block_size * 100 // total_size)
            bar = "█" * (percent // 2) + "░" * (50 - percent // 2)
            print(f"\r  [{bar}] {percent}%", end="", flush=True)

    urllib.request.urlretrieve(url, dest_path, progress)
    print()  # newline after progress


def download_vosk_model(lang: str, models_dir: Path):
    """Download and extract a Vosk model"""
    if lang not in VOSK_MODELS:
        print(f"  ✗ Unknown language: {lang}")
        print(f"  Available: {', '.join(VOSK_MODELS.keys())}")
        return False

    model_name, url = VOSK_MODELS[lang]
    model_path = models_dir / model_name

    if model_path.exists():
        print(f"  ✓ {lang} model already downloaded: {model_path}")
        return True

    print(f"\n📥 Downloading Vosk model for '{lang}'...")
    models_dir.mkdir(parents=True, exist_ok=True)

    zip_path = models_dir / f"{model_name}.zip"
    try:
        download_with_progress(url, zip_path)

        print(f"  Extracting...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(models_dir)

        zip_path.unlink()
        print(f"  ✓ Model ready: {model_path}")
        return True

    except Exception as e:
        print(f"  ✗ Failed: {e}")
        if zip_path.exists():
            zip_path.unlink()
        return False


def check_dependencies():
    """Check Python package dependencies"""
    packages = {
        "vosk": "vosk",
        "pyaudio": "pyaudio",
        "pyttsx3": "pyttsx3",
        "gTTS": "gtts",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "aiohttp": "aiohttp",
        "vaderSentiment": "vaderSentiment",
        "lingua": "lingua-language-detector",
        "langdetect": "langdetect",
    }

    print("\n🔍 Checking dependencies...")
    missing = []
    for import_name, pip_name in packages.items():
        try:
            __import__(import_name)
            print(f"  ✓ {pip_name}")
        except ImportError:
            print(f"  ✗ {pip_name} (not installed)")
            missing.append(pip_name)

    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
    else:
        print("\n✅ All dependencies installed!")

    return len(missing) == 0


def check_external_services():
    """Check connectivity to external services"""
    import urllib.request

    services = {
        "Ollama": "http://localhost:11434/api/version",
        "Rasa NLU": "http://localhost:5005/",
        "LibreTranslate": "http://localhost:5000/languages",
    }

    print("\n🔌 Checking external services...")
    for name, url in services.items():
        try:
            req = urllib.request.urlopen(url, timeout=2)
            print(f"  ✓ {name} ({url})")
        except Exception:
            print(f"  ✗ {name} not reachable ({url})")


def create_env_file():
    """Create .env from .env.example if not exists"""
    env_path = Path(".env")
    example_path = Path(".env.example")

    if env_path.exists():
        print(f"  ✓ .env already exists")
        return

    if example_path.exists():
        shutil.copy(example_path, env_path)
        print(f"  ✓ Created .env from .env.example")
    else:
        print(f"  ✗ .env.example not found")


def main():
    parser = argparse.ArgumentParser(description="VoiceOS Model & Dependency Setup")
    parser.add_argument("--stt", nargs="+", metavar="LANG",
                        help="Download Vosk STT models (e.g., --stt en fr de)")
    parser.add_argument("--all", action="store_true",
                        help="Download English STT model + run all checks")
    parser.add_argument("--check", action="store_true",
                        help="Check dependencies and services only")
    parser.add_argument("--models-dir", default="./models/vosk",
                        help="Directory for Vosk models (default: ./models/vosk)")

    args = parser.parse_args()
    models_dir = Path(args.models_dir)

    print("=" * 60)
    print("  VoiceOS Setup")
    print("=" * 60)

    if args.check or args.all:
        create_env_file()
        check_dependencies()
        check_external_services()

    if args.stt:
        print(f"\n📦 Downloading STT models for: {', '.join(args.stt)}")
        for lang in args.stt:
            download_vosk_model(lang, models_dir)

    if args.all:
        print("\n📦 Downloading default English STT model...")
        download_vosk_model("en-small", models_dir)

    if not any([args.stt, args.all, args.check]):
        parser.print_help()
        print("\nQuick start:")
        print("  python scripts/download_models.py --all")


if __name__ == "__main__":
    main()
