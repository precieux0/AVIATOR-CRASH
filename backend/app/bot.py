import logging
from telethon.errors import SessionPasswordNeededError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from .config import settings
from .i18n import t
from .db import AsyncSessionLocal, User, Observation
from .telethon_auth import start_sign_in, complete_sign_in, complete_twofactor
from . import predictor
from sqlalchemy import select
import asyncio
from sqlalchemy import update

# Supported betting sites (initial list; expand over time)
SUPPORTED_SITES = [
    '1xBet', 'Bet365', 'BetWay', 'Betika', 'BetPawa', 'SportyBet', 'MelBet', '1Win', 'MeridianBet', 'SpinCity',
    'Bet9ja', 'Unibet', 'William Hill', 'Betclic', 'Parimatch', 'Betsafe', 'Betfred', 'MozzartBet'
]

logger = logging.getLogger(__name__)

# Simple in-memory state per-user for the step of verification
USER_STATE = {}

def _lang_from_user(obj) -> str:
    if not obj or not getattr(obj, 'language_code', None):
        return settings.DEFAULT_LANG
    return 'fr' if obj.language_code.startswith('fr') else 'en'


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = 'fr' if (update.effective_user and update.effective_user.language_code and update.effective_user.language_code.startswith('fr')) else 'en'
    await update.message.reply_text(t(lang, 'start'))

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    USER_STATE[chat_id] = {'step': 'await_phone'}
    lang = 'fr' if (update.effective_user and update.effective_user.language_code and update.effective_user.language_code.startswith('fr')) else 'en'
    await update.message.reply_text(t(lang, 'ask_phone'))

async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = settings.ADMIN_USERNAME
    msg_text = ' '.join(context.args) if context.args else 'User requests contact'
    # Try to forward or send message to admin
    try:
        admin_chat = await context.bot.get_chat(admin)
        await context.bot.send_message(admin_chat.id, f"From @{update.effective_user.username or update.effective_user.id}: {msg_text}")
        lang = 'fr' if (update.effective_user and update.effective_user.language_code and update.effective_user.language_code.startswith('fr')) else 'en'
        await update.message.reply_text(t(lang, 'contact_sent'))
    except Exception as e:
        await update.message.reply_text(f"Could not contact admin: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = 'fr' if (update.effective_user and update.effective_user.language_code and update.effective_user.language_code.startswith('fr')) else 'en'
    await update.message.reply_text(t(lang, 'help'))

async def sites_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = 'fr' if (update.effective_user and update.effective_user.language_code and update.effective_user.language_code.startswith('fr')) else 'en'
    keyboard = []
    row = []
    for i, site in enumerate(SUPPORTED_SITES, 1):
        row.append(InlineKeyboardButton(site, callback_data=f"site:{site}"))
        if i % 3 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(t(lang, 'choose_site'), reply_markup=reply_markup)

async def site_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data or not data.startswith('site:'):
        return
    site = data.split(':', 1)[1]
    lang = 'fr' if (query.from_user and query.from_user.language_code and query.from_user.language_code.startswith('fr')) else 'en'
    # Call predictor for selected site
    try:
        p = predictor.predict(site)
        await query.edit_message_text(t(lang, 'predict_result', site=p['site'], odds=p['odds'], confidence=p['confidence']))
    except Exception as e:
        await query.edit_message_text(t(lang, 'error', msg=str(e)))

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/predict [site] - return one prediction"""
    lang = 'fr' if (update.effective_user and update.effective_user.language_code and update.effective_user.language_code.startswith('fr')) else 'en'
    site = ' '.join(context.args) if context.args else None
    try:
        p = predictor.predict(site)
        await update.message.reply_text(t(lang, 'predict_result', site=p['site'], odds=p['odds'], confidence=p['confidence']))
    except Exception as e:
        await update.message.reply_text(t(lang, 'error', msg=str(e)))

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = 'fr' if (update.effective_user and update.effective_user.language_code and update.effective_user.language_code.startswith('fr')) else 'en'
    user_id = update.effective_user.id
    preferred_sites = ' '.join(context.args) if context.args else None
    async with AsyncSessionLocal() as session:
        result = (await session.execute(select(User).filter_by(telegram_id=user_id))).scalars().first()
        if not result:
            user = User(telegram_id=user_id, subscribed=True, language=lang, preferred_sites=preferred_sites)
            session.add(user)
            await session.commit()
            await update.message.reply_text(t(lang, 'subscribed'))
            return
        if result.subscribed:
            await update.message.reply_text(t(lang, 'already_subscribed'))
            return
        result.subscribed = True
        if preferred_sites:
            result.preferred_sites = preferred_sites
        result.language = lang
        await session.commit()
        await update.message.reply_text(t(lang, 'subscribed'))

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = 'fr' if (update.effective_user and update.effective_user.language_code and update.effective_user.language_code.startswith('fr')) else 'en'
    user_id = update.effective_user.id
    async with AsyncSessionLocal() as session:
        result = (await session.execute(select(User).filter_by(telegram_id=user_id))).scalars().first()
        if not result or not result.subscribed:
            await update.message.reply_text(t(lang, 'not_subscribed'))
            return
        result.subscribed = False
        await session.commit()
        await update.message.reply_text(t(lang, 'unsubscribed'))

async def _send_prediction_to_user(bot, user: User, prediction: dict):
    try:
        msg = t(user.language or settings.DEFAULT_LANG, 'signal_alert', site=prediction['site'], odds=prediction['odds'], confidence=prediction['confidence'])
        await bot.send_message(user.telegram_id, msg)
    except Exception as e:
        logger.exception("Failed to send signal to %s: %s", user.telegram_id, e)

async def signal_dispatcher(app):
    """Background task that periodically computes predictions and sends to subscribed users."""
    bot = app.bot
    interval = settings.PREDICTION_INTERVAL
    while True:
        try:
            # Compute some predictions (global or for specific sites)
            preds = await predictor.batch_predict() if hasattr(predictor, 'batch_predict') else [predictor.predict(None)]
            async with AsyncSessionLocal() as session:
                rows = (await session.execute(select(User).filter_by(subscribed=True))).scalars().all()
                for user in rows:
                    if user.preferred_sites:
                        sites = [s.strip() for s in user.preferred_sites.split(',') if s.strip()]
                        for s in sites:
                            try:
                                p = await predictor.model_predict(s) if hasattr(predictor, 'model_predict') else predictor.predict(s)
                                await _send_prediction_to_user(bot, user, p)
                            except Exception:
                                logger.exception("Failed to compute/send prediction for %s to %s", s, user.telegram_id)
                    else:
                        for p in preds:
                            await _send_prediction_to_user(bot, user, p)
        except Exception as e:
            logger.exception("Error in signal_dispatcher: %s", e)
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break

async def collect_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usr = update.effective_user
    admin = settings.ADMIN_USERNAME.lstrip('@')
    if (usr.username or '') != admin and str(usr.id) != admin:
        await update.message.reply_text("Not authorized")
        return
    sites = [s.strip() for s in ' '.join(context.args).split(',')] if context.args else None
    from .tasks import collect_now
    try:
        res = await collect_now(sites)
        await update.message.reply_text(t(_lang_from_user(usr), 'collected', count=len(res)))
    except Exception as e:
        logger.exception("collect_now_command failed: %s", e)
        await update.message.reply_text(t(_lang_from_user(usr), 'error', msg=str(e)))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _lang_from_user(update.effective_user)
    async with AsyncSessionLocal() as session:
        import time
        cutoff = int(time.time()) - 24 * 3600
        q = await session.execute(select(Observation).filter(Observation.ts >= cutoff))
        rows = q.scalars().all()
        by_site = {}
        for r in rows:
            by_site.setdefault(r.site or 'unknown', 0)
            by_site[r.site or 'unknown'] += 1
        if not by_site:
            await update.message.reply_text(t(lang, 'stats_empty'))
            return
        msg = '\n'.join([f"{k}: {v}" for k, v in by_site.items()])
        await update.message.reply_text(t(lang, 'stats_result') + '\n' + msg)


async def build_and_run_bot():
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('verify', verify))
    app.add_handler(CommandHandler('contact_admin', contact_admin))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('predict', predict_command))
    app.add_handler(CommandHandler('subscribe', subscribe_command))
    app.add_handler(CommandHandler('unsubscribe', unsubscribe_command))
    app.add_handler(CommandHandler('sites', sites_command))
    app.add_handler(CommandHandler('collect_now', collect_now_command))
    app.add_handler(CommandHandler('stats', stats_command))
    app.add_handler(CallbackQueryHandler(site_callback, pattern='^site:'))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    await app.initialize()
    await app.start()
    # start background dispatcher
    app.signal_task = asyncio.create_task(signal_dispatcher(app))
    # start collection loop
    from .tasks import collect_loop
    app.collect_task = asyncio.create_task(collect_loop(app))
    # start alert dispatcher
    from .alert_dispatcher import alert_loop
    app.alert_task = asyncio.create_task(alert_loop(app))
    logger.info("Started signal dispatcher with interval %s seconds", settings.PREDICTION_INTERVAL)
    logger.info("Started collect loop with interval %s seconds", settings.COLLECTION_INTERVAL)
    logger.info("Started alert loop")
    return app


async def stop_bot(app):
    try:
        if hasattr(app, 'signal_task') and not app.signal_task.done():
            app.signal_task.cancel()
            await app.signal_task
    except Exception:
        logger.exception("Error cancelling signal task")
    await app.stop()
    await app.shutdown()
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    state = USER_STATE.get(chat_id, {})
    lang = 'fr' if (update.effective_user and update.effective_user.language_code and update.effective_user.language_code.startswith('fr')) else 'en'

    if state.get('step') == 'await_phone':
        # store phone and send code
        phone = text
        USER_STATE[chat_id]['phone'] = phone
        try:
            await start_sign_in(chat_id, phone)
            USER_STATE[chat_id]['step'] = 'await_code'
            await update.message.reply_text(t(lang, 'ask_code', phone=phone))
        except Exception as e:
            await update.message.reply_text(t(lang, 'error', msg=str(e)))
    elif state.get('step') == 'await_code':
        code = text
        phone = state.get('phone')
        try:
            await complete_sign_in(chat_id, phone, code)
            # mark user verified in DB
            async with AsyncSessionLocal() as session:
                existing = (await session.execute(select(User).filter_by(telegram_id=update.effective_user.id))).scalars().first()
                if not existing:
                    user = User(telegram_id=update.effective_user.id, phone=phone, verified=True, session_file=str(chat_id))
                    session.add(user)
                else:
                    existing.phone = phone
                    existing.verified = True
                    existing.session_file = str(chat_id)
                await session.commit()
            USER_STATE.pop(chat_id, None)
            await update.message.reply_text(t(lang, 'verified'))
        except SessionPasswordNeededError:
            USER_STATE[chat_id]['step'] = 'await_2fa'
            await update.message.reply_text(t(lang, 'ask_2fa'))
        except Exception as e:
            await update.message.reply_text(t(lang, 'error', msg=str(e)))
    elif state.get('step') == 'await_2fa':
        password = text
        phone = state.get('phone')
        try:
            await complete_twofactor(chat_id, password)
            # mark user verified in DB
            async with AsyncSessionLocal() as session:
                existing = (await session.execute(select(User).filter_by(telegram_id=update.effective_user.id))).scalars().first()
                if not existing:
                    user = User(telegram_id=update.effective_user.id, phone=phone, verified=True, session_file=str(chat_id))
                    session.add(user)
                else:
                    existing.phone = phone
                    existing.verified = True
                    existing.session_file = str(chat_id)
                await session.commit()
            USER_STATE.pop(chat_id, None)
            await update.message.reply_text(t(lang, 'verified'))
        except Exception as e:
            await update.message.reply_text(t(lang, 'error', msg=str(e)))
    else:
        await update.message.reply_text("I didn't understand. Use /verify to start authentication.")
