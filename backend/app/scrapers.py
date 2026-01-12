import logging
import re
import httpx
import asyncio
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from .config import settings

logger = logging.getLogger(__name__)

# A small, extensible set of site patterns. In practice, many sites block scraping; prefer official APIs when possible.
SITE_PATTERNS = {
    '1xBet': ['1xbet.com', '1xbet.kz'],
    'Bet365': ['bet365.com'],
    'BetWay': ['betway.com'],
    'Betika': ['betika.com'],
    'BetPawa': ['betpawa.com'],
    'SportyBet': ['sportybet.com'],
    'MelBet': ['melbet.com'],
    '1Win': ['1win.com'],
    'MeridianBet': ['meridianbet.com'],
    'SpinCity': ['spincity.bet'],
    'Bet9ja': ['bet9ja.com'],
    'Unibet': ['unibet.com'],
    'William Hill': ['williamhill.com'],
    'Betclic': ['betclic.com'],
    'Parimatch': ['parimatch.com'],
    'Betsafe': ['betsafe.com'],
    'Betfred': ['betfred.com'],
    'MozzartBet': ['mozzartbet.com']
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36'
}


async def fetch_html(url: str, timeout: int = 10, retries: int = 3, backoff_base: float = 1.0, proxy: Optional[str] = None) -> Optional[str]:
    attempt = 0
    while attempt <= retries:
        try:
            transport = None
            async with httpx.AsyncClient(headers=HEADERS, timeout=timeout, proxies=proxy) as c:
                r = await c.get(url)
                r.raise_for_status()
                return r.text
        except Exception as e:
            attempt += 1
            wait_time = backoff_base * (2 ** (attempt - 1))
            logger.warning("Fetch failed (attempt %s/%s) for %s: %s — retrying in %ss", attempt, retries, url, e, wait_time)
            if attempt > retries:
                logger.exception("Failed to fetch %s after %s attempts: %s", url, retries, e)
                return None
            await asyncio.sleep(wait_time)


def _extract_numbers_from_text(text: str) -> list:
    """Find decimal numbers in text, normalize commas, and return sorted unique odds."""
    # capture both 1.23 and 1,23 formats
    matches = re.findall(r"\d+[\.,]\d{1,3}", text)
    odds = set()
    for m in matches:
        m_clean = m.replace(',', '.')
        try:
            val = float(m_clean)
            if 1.01 <= val <= 1000:
                odds.add(round(val, 2))
        except Exception:
            continue
    return sorted(odds, reverse=True)


def _parse_json_like_for_odds(html: str) -> list:
    """Try to find JSON-like structures in <script> tags that contain odds/coeffs."""
    results = set()
    # look for quoted decimals in script tags
    for m in re.findall(r'"\d+[\.,]\d{1,3}"', html):
        try:
            val = float(m.strip('"').replace(',', '.'))
            if 1.01 <= val <= 1000:
                results.add(round(val, 2))
        except Exception:
            continue
    return sorted(results, reverse=True)


def _parse_1xbet_html(html: str) -> list:
    """Heuristic parser for 1xBet pages: look into JSON-like blocks and common class names."""
    odds = set()
    # Heuristic 1: JSON-like numeric literals in scripts
    odds.update(_parse_json_like_for_odds(html))

    # Heuristic 2: look for classes or data attributes referencing coefficient/odds
    soup = BeautifulSoup(html, 'html.parser')
    # common attribute/class name patterns seen across betting sites
    selectors = [
        '[data-coef]',
        '[data-odds]',
        '[class*="coef" i]',
        '[class*="odds" i]',
        '[class*="price" i]'
    ]
    for sel in selectors:
        for el in soup.select(sel):
            text = el.get('data-coef') or el.get('data-odds') or el.get_text()
            for n in _extract_numbers_from_text(text):
                odds.add(n)

    # Heuristic 3: fallback to scanning visible text
    if not odds:
        text = soup.get_text(separator=' ', strip=True)
        for n in _extract_numbers_from_text(text):
            odds.add(n)

    return sorted(odds, reverse=True)


def _parse_betpawa_html(html: str) -> list:
    """Simple parser for BetPawa pages: looks for odds in data-attributes and decimal text."""
    odds = set()
    soup = BeautifulSoup(html, 'html.parser')

    # data-attributes often used for odds
    for el in soup.select('[data-price], [data-odd], [data-odds]'):
        txt = el.get('data-price') or el.get('data-odd') or el.get('data-odds') or el.get_text()
        for n in _extract_numbers_from_text(txt):
            odds.add(n)

    # look for elements with common betting classes
    for el in soup.select('[class*="odd" i], [class*="price" i], [class*="coef" i]'):
        for n in _extract_numbers_from_text(el.get_text() or ''):
            odds.add(n)

    # fallback to JSON-like extraction
    odds.update(_parse_json_like_for_odds(html))

    return sorted(odds, reverse=True)


def _parse_sportybet_html(html: str) -> list:
    """Heuristic parser for SportyBet: JSON payloads in scripts and visible odds."""
    odds = set()
    # JSON-like first
    odds.update(_parse_json_like_for_odds(html))

    # visible text
    soup = BeautifulSoup(html, 'html.parser')
    for el in soup.select('[data-price], [class*="odds" i], [class*="coefficient" i]'):
        for n in _extract_numbers_from_text(el.get('data-price') or el.get_text() or ''):
            odds.add(n)

    # fallback
    if not odds:
        text = soup.get_text(separator=' ', strip=True)
        for n in _extract_numbers_from_text(text):
            odds.add(n)

    return sorted(odds, reverse=True)


async def extract_odds_from_html(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)

    # Prefer specialized parsers when detected
    lhtml = html.lower()
    if '1xbet' in lhtml or '1xbet' in text.lower():
        odds = _parse_1xbet_html(html)
        return {'odds': odds, 'raw_text_sample': text[:500]}
    if 'betpawa' in lhtml or 'betpawa' in text.lower():
        odds = _parse_betpawa_html(html)
        return {'odds': odds, 'raw_text_sample': text[:500]}
    if 'sportybet' in lhtml or 'sportybet' in text.lower():
        odds = _parse_sportybet_html(html)
        return {'odds': odds, 'raw_text_sample': text[:500]}

    # Generic extraction
    odds = _extract_numbers_from_text(text)

    # also look for JSON-like snippets
    odds_json = _parse_json_like_for_odds(html)
    for o in odds_json:
        if o not in odds:
            odds.insert(0, o)

    return {'odds': odds, 'raw_text_sample': text[:500]}


async def get_site_odds_by_url(url: str) -> Dict[str, Any]:
    html = await fetch_html(url, retries=settings.COLLECTION_RETRIES, backoff_base=settings.REQUEST_BACKOFF_BASE, proxy=(settings.PROXY_URL or None))
    if not html:
        return {'odds': [], 'error': 'failed_fetch'}
    data = await extract_odds_from_html(html)
    return data


def identify_site_from_url(url: str) -> Optional[str]:
    for site, patterns in SITE_PATTERNS.items():
        for p in patterns:
            if p in url:
                return site
    return None


async def get_latest_odds(site_or_url: Optional[str]) -> Dict[str, Any]:
    """Try to fetch latest odds for a site name or URL. Returns {'site':..., 'odds': [...]}"""
    if not site_or_url:
        return {'site': None, 'odds': []}
    # If input looks like URL
    if site_or_url.startswith('http'):
        site = identify_site_from_url(site_or_url) or site_or_url
        data = await get_site_odds_by_url(site_or_url)
        return {'site': site, 'odds': data.get('odds', []), 'raw': data.get('raw_text_sample')}
    else:
        # Try to produce a common home page for the site name
        patterns = SITE_PATTERNS.get(site_or_url)
        if patterns:
            url = 'https://' + patterns[0]
            data = await get_site_odds_by_url(url)
            return {'site': site_or_url, 'odds': data.get('odds', []), 'raw': data.get('raw_text_sample')}
        return {'site': site_or_url, 'odds': []}
