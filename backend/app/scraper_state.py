import time
import logging
from .db import AsyncSessionLocal, SiteBlacklist, AdminAlert
from .config import settings

logger = logging.getLogger(__name__)

async def record_failure(site: str):
    now = int(time.time())
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            "SELECT id, fail_count FROM site_blacklist WHERE site = :site",
            {'site': site}
        )).first()
        # Use ORM-style upsert for portability
        from sqlalchemy import select
        q = await session.execute(select(SiteBlacklist).filter_by(site=site))
        r = q.scalars().first()
        if not r:
            r = SiteBlacklist(site=site, fail_count=1, last_failure_ts=now)
            session.add(r)
        else:
            r.fail_count = (r.fail_count or 0) + 1
            r.last_failure_ts = now
        # if threshold reached, blacklist
        if r.fail_count >= settings.SCRAPE_FAILURE_THRESHOLD:
            r.blacklisted_until = now + settings.BLACKLIST_DURATION
            # create admin alert
            msg = f"Site {site} added to blacklist after {r.fail_count} failures (until {r.blacklisted_until})."
            alert = AdminAlert(message=msg, ts=now, sent=False)
            session.add(alert)
        await session.commit()

async def reset_failures(site: str):
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        q = await session.execute(select(SiteBlacklist).filter_by(site=site))
        r = q.scalars().first()
        if r:
            r.fail_count = 0
            r.blacklisted_until = None
            r.last_failure_ts = None
            await session.commit()

async def is_blacklisted(site: str) -> bool:
    now = int(time.time())
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        q = await session.execute(select(SiteBlacklist).filter_by(site=site))
        r = q.scalars().first()
        if not r:
            return False
        if r.blacklisted_until and r.blacklisted_until > now:
            return True
        # expired
        if r.blacklisted_until and r.blacklisted_until <= now:
            r.blacklisted_until = None
            r.fail_count = 0
            await session.commit()
            return False
        return False

async def pop_unsent_alerts(limit: int = 10):
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        q = await session.execute(select(AdminAlert).filter_by(sent=False).limit(limit))
        rows = q.scalars().all()
        return rows

async def mark_alert_sent(alert_id: int):
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        q = await session.execute(select(AdminAlert).filter_by(id=alert_id))
        r = q.scalars().first()
        if r:
            r.sent = True
            await session.commit()
