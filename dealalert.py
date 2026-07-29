import logging
import requests

logger = logging.getLogger(__name__)

TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_deal_alert(bot_token: str, chat_id: str, deals: list[dict]) -> bool:
    """
    Send a batch Telegram alert summarising the best deals found.
    Returns True if delivered successfully.
    """
    if not bot_token or not chat_id or not deals:
        return False

    # Only send the top 5 deals
    top_deals = deals[:5]

    lines = [f"🛒 *CreatorMoneyManager — Top {len(top_deals)} Creator Deals*\n"]

    for i, deal in enumerate(top_deals, 1):
        lowest_tag = " 🔥 *LOWEST EVER PRICE*" if deal.get("is_lowest_ever") else ""
        lines.append(
            f"{i}. {deal['ai_verdict']} *{deal['name']}*\n"
            f"   💰 `${deal['current_price']:.2f}` ({deal['discount_pct']:.0f}% off){lowest_tag}\n"
            f"   📊 {deal['ai_reason']}\n"
            f"   🛍️ [Buy on Amazon]({deal['affiliate_url']}) | "
            f"[Price History]({deal['camel_url']})\n"
        )

    lines.append("\n_Affiliate links support CreatorMoneyManager_ 🙏")

    try:
        resp = requests.post(
            TELEGRAM_URL.format(token=bot_token),
            json={
                "chat_id":    chat_id,
                "text":       "\n".join(lines),
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as exc:
        logger.error("Telegram deal alert failed: %s", exc)
        return False
