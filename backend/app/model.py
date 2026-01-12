import json
import time
from typing import Tuple, List, Dict
from sqlalchemy import select
from .db import Observation, AsyncSessionLocal
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'model.pkl')


def _extract_features_from_odds(odds: List[float]) -> Dict[str, float]:
    if not odds:
        return {'mean': 0.0, 'std': 0.0, 'min': 0.0, 'max': 0.0, 'count': 0}
    arr = np.array(odds, dtype=float)
    return {
        'mean': float(np.mean(arr)),
        'std': float(np.std(arr)),
        'min': float(np.min(arr)),
        'max': float(np.max(arr)),
        'count': int(len(arr))
    }


async def load_dataset(limit: int = 10000) -> Tuple[List[List[float]], List[float]]:
    """Load observations that have a 'multiplier' label (non-null) and return X, y."""
    X = []
    y = []
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(Observation).limit(limit))
        rows = q.scalars().all()
        for r in rows:
            try:
                odds = json.loads(r.odds) if r.odds else []
                if not r.multiplier:
                    continue
                features = _extract_features_from_odds(odds)
                X.append([features['mean'], features['std'], features['min'], features['max'], features['count']])
                y.append(float(r.multiplier))
            except Exception:
                continue
    return X, y


def train_and_save(X, y, n_estimators: int = 100) -> Dict[str, float]:
    if len(X) < 20:
        return {'ok': False, 'msg': 'Not enough labeled data to train. Need at least 20 samples.'}
    X = np.array(X)
    y = np.array(y)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestRegressor(n_estimators=n_estimators, random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    mse = float(mean_squared_error(y_test, preds))
    # ensure models folder exists
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    return {'ok': True, 'mse': mse, 'n_train': len(y_train), 'n_test': len(y_test)}


def load_model() -> RandomForestRegressor:
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None


def predict_from_model(model, odds: List[float]) -> float:
    features = _extract_features_from_odds(odds)
    X = [[features['mean'], features['std'], features['min'], features['max'], features['count']]]
    return float(model.predict(X)[0])
