import asyncio
from app import scrapers

async def run_tests():
    html = '<html><body>Odds: 1.23 2.34 3.50</body></html>'
    res = await scrapers.extract_odds_from_html(html)
    print('generic:', res)
    html2 = '<html><script>var x={"a":["1.45","2.50"]}</script><div class="coef">1.75</div></html>'
    res2 = scrapers._parse_1xbet_html(html2)
    print('1xbet:', res2)

if __name__ == '__main__':
    asyncio.run(run_tests())
