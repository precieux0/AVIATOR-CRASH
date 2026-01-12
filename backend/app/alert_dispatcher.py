import asyncio
import logging
from .scraper_state import pop_unsent_alerts, mark_alert_sent
from .config import settings
from .db import AsyncSessionLocal

logger = logging.getLogger(__name__)

async def alert_loop(bot_app):
    """Background task to send unsent alerts to admin via the bot."""
    admin = settings.ADMIN_USERNAME.lstrip('@')
    while True:
        try:
            rows = await pop_unsent_alerts()
            for r in rows:
                try:
                    # bot_app assumed to be the Telegram application from build_and_run_bot
                    await bot_app.bot.send_message(admin, f"[ALERT] {r.message}")
                    await mark_alert_sent(r.id)
                except Exception:
                    logger.exception("Failed to send admin alert for %s", r.id)
        except Exception:
            logger.exception("Error in alert_loop")
        await asyncio.sleep(settings.COLLECTION_INTERVAL)
