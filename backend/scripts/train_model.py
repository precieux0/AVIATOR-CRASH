import asyncio
import sys
from app import model

async def main():
    X, y = await model.load_dataset()
    if len(X) == 0:
        print("No labeled observations found. Please collect observations with 'multiplier' field populated.")
        return
    res = model.train_and_save(X, y)
    print(res)

if __name__ == '__main__':
    asyncio.run(main())
