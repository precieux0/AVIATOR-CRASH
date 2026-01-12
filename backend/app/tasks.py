import asyncio
import time
import json
import logging
from .scrapers import get_latest_odds, identify_site_from_url
from .db import AsyncSessionLocal, Observation
from .config import settings

logger = logging.getLogger(__name__)

async def collect_observations_for_sites(sites):
    results = []
    async with AsyncSessionLocal() as session:
        for s in sites:
            try:
                # skip blacklisted sites
                from .scraper_state import is_blacklisted, record_failure, reset_failures
                if await is_blacklisted(s):
                    logger.info("Skipping blacklisted site %s", s)
                    results.append({'site': s, 'odds_count': 0, 'skipped': True})
                    continue
                # use configured retries/backoff/proxy
                data = await get_latest_odds(s)
                if data.get('error'):
                    logger.warning("Collection returned error for %s: %s", s, data.get('error'))
                    await record_failure(s)
                else:
                    await reset_failures(s)
                obs = Observation(site=data.get('site') or s, odds=json.dumps(data.get('odds', [])), multiplier=None, ts=int(time.time()))
                session.add(obs)
                results.append({'site': obs.site, 'odds_count': len(data.get('odds', []))})
            except Exception as e:
                logger.exception("Failed to collect for %s: %s", s, e)
        await session.commit()
    return results


async def collect_loop(app):
    """Continuously collect observations for SUPPORTED_SITES"""
    from .bot import SUPPORTED_SITES
    interval = settings.COLLECTION_INTERVAL
    while True:
        try:
            await collect_observations_for_sites(SUPPORTED_SITES)
        except Exception as e:
            logger.exception("Error in collect_loop: %s", e)
        await asyncio.sleep(interval)


async def collect_now(sites=None):
    if not sites:
        from .bot import SUPPORTED_SITES
        sites = SUPPORTED_SITES
    return await collect_observations_for_sites(sites)
