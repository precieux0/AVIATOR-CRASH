import asyncio
from app import model

async def test_load_dataset_empty():
    X, y = await model.load_dataset(limit=10)
    # no labeled data in default test environment; expect lists
    assert isinstance(X, list)
    assert isinstance(y, list)


def test_train_not_enough():
    res = model.train_and_save([[1,0,1,1,1]]*5, [2.0]*5)
    assert res['ok'] is False
