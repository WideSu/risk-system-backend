# main.py
from contextlib import asynccontextmanager
from decimal import ROUND_UP, Decimal
from fastapi import FastAPI, HTTPException
from yfinance import Ticker
from tortoise import Tortoise
from datetime import datetime, timezone
from db_config import init_db
from models import Client, Margin, MarketData
import config

# Run the app and initialize the database when the app starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    await Tortoise.init(
        db_url=config.DATABASE_URL,
        modules={'models': ['models']}
    )
    await Tortoise.generate_schemas()
    yield  # Everything inside FastAPI runs here
    await Tortoise.close_connections()

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

async def fetch_latest_price(symbol: str, db_model=MarketData):
    """Fetch the latest stock price closest to the given timestamp."""
    print(repr(init_db))
    market_data = await db_model.filter(symbol=symbol) \
        .order_by('timestamp') \
        .first()
    
    return {
        "symbol": market_data.symbol, 
        "current_price": market_data.current_price, 
        "timestamp": market_data.timestamp
    } if market_data else {"error": "No data found for the given symbol"}

# Function to fetch stock data from Yahoo Finance
async def get_stock_data(symbol: str):
    stock = Ticker(symbol)
    info = stock.history(period="1d", interval="1m").tail(1)
    if info.empty:
        raise HTTPException(status_code=404, detail="Stock data not available")
    # Get the most recent price and timestamp
    timestamp = info.index[0]  # Get the timestamp of the last price
    current_price = Decimal(info['Close'].iloc[0]).quantize(Decimal('0.001'), rounding=ROUND_UP)  # Get the last closing price

    return timestamp, current_price

# API endpoint to fetch stock data and store it in the database
@app.get("/stocks/{symbol}")
async def fetch_stock(symbol: str):
    # Fetch stock data
    timestamp, current_price = await get_stock_data(symbol)
    
    # Save stock data into the database
    await MarketData.create(
        symbol=symbol, timestamp=timestamp, current_price=current_price
    )
    
    return {"symbol": symbol, "timestamp": timestamp, "current_price": current_price}

# API endpoint to get all stock data from the database
@app.get("/stocks")
async def get_stock_data_from_db():
    # Fetch all stock data
    data = await MarketData.all().values()
    return data

@app.get("/positions/{clientId}")
async def get_client_positions(clientId: int):
    client = await Client.get_or_none(id=clientId).prefetch_related("positions")
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    positions = [
        {"symbol":  pos.symbol, "quantity": pos.quantity, "cost_basis": float(pos.cost_basis)}
        for pos in await client.positions.all()
    ]
    return {"clientId": clientId, "positions": positions}

@app.get("/margin/{clientId}")
async def get_margin_status(clientId: int):
    client = await Client.get_or_none(id=clientId)
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Fetch related objects separately
    await client.fetch_related("positions", "margins")

    margin_account = await client.margins.all()
    if not margin_account:
        raise HTTPException(status_code=404, detail="Margin account not found")
    margin_account = margin_account[0]
    total_value = Decimal(0)
    positions = await client.positions.all()
    if not positions:
        raise HTTPException(status_code=404, detail="No positions found for this client")
    for position in await client.positions.all():
        marketData = await fetch_latest_price(position.symbol, MarketData)
        if "error" in marketData:
            raise HTTPException(status_code=404, detail=f"Market data not found for {position.symbol}")
        total_value += Decimal(position.quantity) * Decimal(marketData["current_price"]).quantize(Decimal('0.001'), rounding=ROUND_UP)
    
    net_equity = Decimal(total_value) - Decimal(margin_account.loan).quantize(Decimal('0.001'), rounding=ROUND_UP) 
    margin_account.margin_requirement = (Decimal(total_value) * Decimal(config.MMR)).quantize(Decimal('0.001'), rounding=ROUND_UP)  # Example margin requirement calculation
    margin, created = await Margin.update_or_create(
        client_id=clientId,
        defaults={'margin_requirement': margin_account.margin_requirement, 'loan': margin_account.loan}
    )
    margin_shortfall = max(margin_account.margin_requirement - net_equity, Decimal(0)).quantize(Decimal('0.001'), rounding=ROUND_UP) 
    margin_call_triggered = margin_shortfall > 0
    # await Margin.update_or_create(client_id = clientId, margin_requirement=margin_account.margin_requirement,loan=margin_account.loan)
    return {
        "timestamp": marketData["timestamp"],
        "clientId": clientId,
        "portfolio_value": float(total_value),
        "loan_amount": float(margin_account.loan),  # Fixed field name
        "net_equity": float(net_equity),
        "margin_requirement": float(margin_account.margin_requirement),
        "margin_shortfall": float(margin_shortfall),
        "margin_call_triggered": margin_call_triggered
    }


# Run the FastAPI app using Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
