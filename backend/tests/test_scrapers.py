import asyncio
from app.scrapers import extract_odds_from_html, _parse_1xbet_html


def test_extract_odds_generic():
    html = '<html><body>Upcoming: Odds: 1.23, 2.34 and 3.50 -- other info.</body></html>'
    result = asyncio.run(extract_odds_from_html(html))
    assert 'odds' in result
    assert 3.5 in result['odds']
    assert 2.34 in result['odds']
    assert 1.23 in result['odds']


def test_parse_1xbet_json_snippet():
    html = '''
    <html>
      <head>
        <script>window.__DATA__ = {"market": {"odds": ["1.45", "2.50"]}};</script>
      </head>
      <body>
        <div class="coef">1.75</div>
      </body>
    </html>
    '''
    odds = _parse_1xbet_html(html)
    assert isinstance(odds, list)
    assert 2.5 in odds
    assert 1.75 in odds
    assert 1.45 in odds
