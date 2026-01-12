import asyncio
from app.scrapers import _parse_betpawa_html, _parse_sportybet_html


def test_parse_betpawa_simple():
    html = '<div data-price="1.60">1.60</div><span class="odd">2.40</span>'
    odds = _parse_betpawa_html(html)
    assert 2.4 in odds
    assert 1.6 in odds


def test_parse_sportybet_simple():
    html = '<script>var data = {"offers": ["1.90","3.20"]}</script><div class="odds">2.10</div>'
    odds = _parse_sportybet_html(html)
    assert 3.2 in odds
    assert 2.1 in odds
