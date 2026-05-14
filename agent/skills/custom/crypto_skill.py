"""
Custom Skill Example: Cryptocurrency Price Tracker
Demonstrates how to write and register a custom skill plugin for VoiceOS.

Place custom skills in skills/custom/ directory.
VoiceOS will auto-discover and register them on startup.
"""

import aiohttp
import asyncio
from pipeline.skill_manager import BaseSkill


class CryptoPriceSkill(BaseSkill):
    """
    Custom skill: Get cryptocurrency prices using CoinGecko API (free, no key needed).

    Handles intents: get_crypto_price, check_bitcoin, crypto_info
    Example: "What is the price of Bitcoin?"
    """

    name = "crypto_price"
    description = "Get real-time cryptocurrency prices"
    intents = ["get_crypto_price", "check_bitcoin", "check_ethereum", "crypto_info"]
    priority = 7

    # CoinGecko ID mapping
    COIN_IDS = {
        "bitcoin": "bitcoin", "btc": "bitcoin",
        "ethereum": "ethereum", "eth": "ethereum",
        "solana": "solana", "sol": "solana",
        "dogecoin": "dogecoin", "doge": "dogecoin",
        "cardano": "cardano", "ada": "cardano",
        "xrp": "ripple", "ripple": "ripple",
    }

    async def execute(self, intent, entities, context):
        coin_name = entities.get("coin", entities.get("currency", "bitcoin")).lower()
        coin_id = self.COIN_IDS.get(coin_name, coin_name)

        try:
            async with aiohttp.ClientSession() as session:
                url = (
                    f"https://api.coingecko.com/api/v3/simple/price"
                    f"?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
                )
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if coin_id in data:
                            price = data[coin_id]["usd"]
                            change = data[coin_id].get("usd_24h_change", 0)
                            return {
                                "type": "crypto_price",
                                "coin": coin_name.title(),
                                "price_usd": price,
                                "change_24h": round(change, 2),
                                "trend": "up" if change > 0 else "down"
                            }
        except Exception as e:
            pass

        return {
            "type": "crypto_price",
            "coin": coin_name.title(),
            "error": "Price unavailable"
        }
