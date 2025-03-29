from datetime import datetime 
import pytz
from tortoise import Tortoise
import asyncio
from config import DATABASE_URL
from db_config import init_db
from models import Client, Margin, MarketData, Position
# Insert sample data
async def insert_data():
    await init_db()

    # Creating Clients
    client1 = await Client.create(name="John Doe")
    client2 = await Client.create(name="Jane Smith")

    # Creating Positions for each Client
    position1 = await Position.create(symbol="AAPL", quantity=100, cost_basis=150.00, client=client1)
    position2 = await Position.create(symbol="TSLA", quantity=50, cost_basis=700.00, client=client1)
    position3 = await Position.create(symbol="GOOG", quantity=200, cost_basis=2800.00, client=client2)

    # # Creating Market Data
    # market_data1 = await MarketData.create(symbol="AAPL", current_price=160.00, timestamp=datetime.now(pytz.utc))
    # market_data2 = await MarketData.create(symbol="TSLA", current_price=750.00, timestamp=datetime.now(pytz.utc))
    # market_data3 = await MarketData.create(symbol="GOOG", current_price=2900.00, timestamp=datetime.now(pytz.utc))

    # Creating Margin for Clients
    margin1 = await Margin.create(client=client1, margin_requirement=0.25, loan=10000.00)
    margin2 = await Margin.create(client=client2, margin_requirement=0.3, loan=15000.00)

    # Print out the data
    print(repr(client1))
    print(repr(client2))
    print(repr(position1))
    print(repr(position2))
    print(repr(position3))
    # print(market_data1)
    # print(market_data2)
    # print(market_data3)
    print(repr(margin1))
    print(repr(margin2))
    await Tortoise.close_connections()

# Running the asynchronous function
if __name__ == "__main__":
    asyncio.run(insert_data())