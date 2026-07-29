import json
import logging
import time

import requests

from config import OPENROUTER_API_KEY, MIN_DISCOUNT_PCT

logger = logging.getLogger(__name__)

AI_URL       = "https://openrouter.ai/api/v1/chat/completions"
MODEL        = "google/gemini-2.0-flash-001"
MAX_RETRIES  = 3
BACKOFF_BASE = 1.0


def analyse_deal(deal: dict, api_key: str = None) -> dict:
    """
    Use AI to analyse whether a deal is genuinely worth buying.
    Searches for product reviews, typical prices, and creator relevance.

    Returns the deal dict enriched with:
        ai_verdict, ai_score (0-10), ai_reason, ai_buy_rating
    """
    key = api_key or OPENROUTER_API_KEY
    if not key:
        return {**deal, "ai_verdict": "⚠️ No AI key", "ai_score": 5, "ai_reason": "API key missing", "ai_buy_rating": "Unknown"}

    lowest_msg = "At or near lowest ever price! 🔥" if deal["is_lowest_ever"] else f"{deal['drop_from_low']:+.1f}% vs lowest ever"
    prompt = (
        f"You are an expert deal analyst for content creators.\n\n"
        f"PRODUCT: {deal['name']}\n"
        f"CATEGORY: {deal['category']}\n"
        f"CURRENT PRICE: ${deal['current_price']:.2f}\n"
        f"HIGHEST PRICE: ${deal['highest_price']:.2f}\n"
        f"DISCOUNT: {deal['discount_pct']:.1f}% off highest price\n"
        f"VS LOWEST EVER: {lowest_msg}\n\n"
        f"Search the web for:\n"
        f"1. Current reviews and ratings for '{deal['name']}'\n"
        f"2. Whether this is genuinely a good price right now\n"
        f"3. How useful this product is for YouTubers, TikTokers and Instagram creators\n\n"
        f"Then respond ONLY with JSON:\n"
        f'{{"ai_score": 8, "ai_verdict": "🔥 Exceptional Deal", "ai_reason": "One sentence explanation", "ai_buy_rating": "Buy Now"}}\n\n'
        f"ai_score: 1-10 (10 = incredible deal, 1 = avoid)\n"
        f"ai_verdict: one of: '🔥 Exceptional Deal', '✅ Great Deal', '👍 Good Deal', '⚠️ Decent Deal', '❌ Skip'\n"
        f"ai_buy_rating: one of: 'Buy Now', 'Buy if Needed', 'Wait for Better Price', 'Skip'"
    )

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a deal analysis expert specialising in creator equipment. "
                    "Search the web for current product information before analysing. "
                    "Respond ONLY with the requested JSON object."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "tools":           [{"type": "web_search"}],
        "response_format": {"type": "json_object"},
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(AI_URL, headers=headers, json=payload, timeout=60)

            if resp.status_code == 429:
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning("Rate limited — retrying in %.0fs", wait)
                time.sleep(wait)
                continue

            resp.raise_for_status()

            content = None
            for choice in resp.json().get("choices", []):
                msg = choice.get("message", {})
                if msg.get("content"):
                    content = msg["content"]
                    break

            if not content:
                return _default_analysis(deal)

            clean = content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data  = json.loads(clean)

            return {
                **deal,
                "ai_score":      int(data.get("ai_score", 5)),
                "ai_verdict":    str(data.get("ai_verdict", "👍 Good Deal")),
                "ai_reason":     str(data.get("ai_reason", "")),
                "ai_buy_rating": str(data.get("ai_buy_rating", "Buy if Needed")),
            }

        except Exception as exc:
            wait = BACKOFF_BASE * (2 ** attempt)
            logger.error("AI analysis failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES - 1:
                time.sleep(wait)

    return _default_analysis(deal)


def _default_analysis(deal: dict) -> dict:
    """Fallback analysis based on discount % alone when AI is unavailable."""
    pct = deal["discount_pct"]
    if pct >= 50:
        verdict, score, rating = "🔥 Exceptional Deal", 9, "Buy Now"
    elif pct >= 35:
        verdict, score, rating = "✅ Great Deal", 7, "Buy Now"
    elif pct >= 25:
        verdict, score, rating = "👍 Good Deal", 6, "Buy if Needed"
    else:
        verdict, score, rating = "⚠️ Decent Deal", 4, "Wait for Better Price"

    return {
        **deal,
        "ai_score":      score,
        "ai_verdict":    verdict,
        "ai_reason":     f"{pct:.0f}% off highest recorded price.",
        "ai_buy_rating": rating,
    }
