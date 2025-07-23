import asyncio
from api.mexc_api import MexcAPI

async def test_price():
    api = MexcAPI()
    price = await api.get_ticker_price('BTCUSDT')
    print(f'BTCUSDT price: {price}')

if __name__ == "__main__":
    asyncio.run(test_price())
