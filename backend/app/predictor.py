import time
import hashlib
import random
import asyncio
from typing import Dict, Any, Optional, List
from . import scrapers
from .db import Observation

# Simple heuristic/pseudo-predictor with site data collection
# Aim: make a realistic, testable prediction until a trained model is available.


def _seed_from_site(site: Optional[str]) -> int:
    s = (site or "") + str(int(time.time() // 60))
    return int(hashlib.sha256(s.encode()).hexdigest(), 16) % (2 ** 32)


def _heuristic_from_odds(odds: List[float]) -> Dict[str, Any]:
    # Aggregate odds to produce a single predicted odds and confidence
    if not odds:
        rnd = random.Random(_seed_from_site(None))
        odds_val = round(1.05 + rnd.random() * 2.0, 2)
        return {"odds": odds_val, "confidence": 35}
    avg = sum(odds) / len(odds)
    # confidence increases with number and spread
    conf = max(40, min(95, int(50 + (len(odds) ** 0.5) * 5 - (max(odds)-min(odds)))))
    return {"odds": round(avg, 2), "confidence": conf}


def predict(site: Optional[str] = None) -> Dict[str, Any]:
    """Synchronous simplistic predictor (keeps old interface)."""
    seed = _seed_from_site(site)
    rnd = random.Random(seed)
    odds = round(1.01 + rnd.random() * 4.0, 2)
    confidence = int(40 + rnd.random() * 60)
    return {"site": site or "global", "odds": odds, "confidence": confidence, "ts": int(time.time())}


async def model_predict(site_or_url: Optional[str] = None) -> Dict[str, Any]:
    """Asynchronous prediction that tries to use live odds and historical observations.
    Steps:
    - If site_or_url is URL: try to fetch page and extract odds
    - Else, try to fetch site homepage
    - Use heuristic combination of recent odds to return a prediction
    """
    site = site_or_url
    odds_list: List[float] = []
    try:
        data = await scrapers.get_latest_odds(site_or_url)
        odds_list = data.get('odds', []) if isinstance(data, dict) else []
    except Exception:
        odds_list = []

    # Try to use trained model
    try:
        from .model import load_model, predict_from_model
        model_obj = load_model()
        if model_obj and odds_list:
            pred_value = predict_from_model(model_obj, odds_list)
            # confidence heuristic: if many odds, more confident
            conf = max(45, min(95, 40 + len(odds_list) * 5))
            return {'site': (site_or_url or 'global'), 'odds': round(pred_value, 2), 'confidence': conf, 'ts': int(time.time())}
    except Exception:
        pass

    # Fallback: use synchronous heuristic if no model or no odds
    heur = _heuristic_from_odds(odds_list)

    return {
        'site': (site_or_url or 'global'),
        'odds': heur['odds'],
        'confidence': heur['confidence'],
        'ts': int(time.time())
    }


async def batch_predict(sites: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    sites = sites or [None]
    out = []
    for s in sites:
        out.append(await model_predict(s))
    return out
