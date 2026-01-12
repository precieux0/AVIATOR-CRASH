import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from pathlib import Path
from .config import settings

SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

async def start_sign_in(telegram_user_id: int, phone: str):
    session_path = SESSIONS_DIR / f"{telegram_user_id}"
    client = TelegramClient(str(session_path), settings.API_ID, settings.API_HASH)
    await client.connect()
    try:
        await client.send_code_request(phone)
        await client.disconnect()
        return True
    except Exception as e:
        await client.disconnect()
        raise

async def complete_sign_in(telegram_user_id: int, phone: str, code: str):
    session_path = SESSIONS_DIR / f"{telegram_user_id}"
    client = TelegramClient(str(session_path), settings.API_ID, settings.API_HASH)
    await client.connect()
    try:
        result = await client.sign_in(phone, code)
        await client.disconnect()
        return True
    except SessionPasswordNeededError:
        # 2FA enabled - notify user
        await client.disconnect()
        raise
    except PhoneCodeInvalidError:
        await client.disconnect()
        raise
    except Exception:
        await client.disconnect()
        raise

async def complete_twofactor(telegram_user_id: int, password: str):
    session_path = SESSIONS_DIR / f"{telegram_user_id}"
    client = TelegramClient(str(session_path), settings.API_ID, settings.API_HASH)
    await client.connect()
    try:
        await client.sign_in(password=password)
        await client.disconnect()
        return True
    except Exception:
        await client.disconnect()
        raise
