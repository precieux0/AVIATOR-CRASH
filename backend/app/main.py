import asyncio
import logging
from fastapi import FastAPI, Request, HTTPException
from .bot import build_and_run_bot, stop_bot
from .db import init_db
from .config import settings

logger = logging.getLogger(__name__)
app = FastAPI()
bot_app = None

@app.on_event("startup")
async def on_startup():
    await init_db()
    global bot_app
    bot_app = await build_and_run_bot()
    logger.info("Bot started")

    # if WEBHOOK_BASE_URL is set, register webhook with Telegram
    if settings.WEBHOOK_BASE_URL:
        webhook_url = f"{settings.WEBHOOK_BASE_URL.rstrip('/')}/webhook/{settings.BOT_TOKEN}"
        try:
            await bot_app.bot.set_webhook(webhook_url)
            logger.info("Webhook set to %s", webhook_url)
        except Exception:
            logger.exception("Failed to set webhook to %s", webhook_url)

@app.on_event("shutdown")
async def on_shutdown():
    if bot_app:
        # remove webhook if set
        if settings.WEBHOOK_BASE_URL:
            try:
                await bot_app.bot.delete_webhook()
                logger.info("Webhook deleted")
            except Exception:
                logger.exception("Failed to delete webhook")
        await stop_bot(bot_app)

@app.post('/webhook/{token}')
async def telegram_webhook(token: str, request: Request):
    if token != settings.BOT_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
    body = await request.json()
    try:
        from telegram import Update
        update = Update.de_json(body, bot_app.bot)
        # enqueue update for processing
        await bot_app.update_queue.put(update)
    except Exception:
        logger.exception("Failed to process incoming webhook update")
        raise HTTPException(status_code=500, detail="Failed to process update")
    return {"ok": True}

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# quick root page
@app.get("/")
async def root():
    return {"message": "Unified Telegram Bot API"}

# endpoint for alert status (admin can check)
@app.get("/alerts")
async def alerts():
    from .scraper_state import pop_unsent_alerts
    rows = await pop_unsent_alerts(50)
    return {"pending_alerts": [ {"id": r.id, "msg": r.message, "ts": r.ts} for r in rows ]}
