from contextlib import asynccontextmanager
from decimal import ROUND_UP, Decimal
from fastapi import FastAPI, HTTPException
from yfinance import Ticker
from tortoise import Tortoise
from models import Client, Margin, MarketData
from utils.logging.logging_decorator import log_function
from utils.yfinance.yfinance_stock_utils import fetch_latest_price
import logging
import config

# Run the app and initialize the database when the app starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await Tortoise.init(
            db_url=config.DATABASE_URL,
            modules={'models': ['models']}
        )
        await Tortoise.generate_schemas()
        yield  # Everything inside FastAPI runs here
    except Exception as e:
        logging.error(f"Error during database initialization: {e}")
        raise HTTPException(status_code=500, detail="Database initialization failed")
    finally:
        await Tortoise.close_connections()

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Function to fetch stock data from Yahoo Finance
@log_function
async def get_stock_data(symbol: str):
    try:
        stock = Ticker(symbol)
        info = stock.history(period="1d", interval="1m").tail(1)
        if info.empty:
            raise HTTPException(status_code=404, detail="Stock data not available")
    except Exception as e:
        logging.error(f"Error fetching data for stock {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock data")
    
    # Get the most recent price and timestamp
    timestamp = info.index[0]  # Get the timestamp of the last price
    current_price = Decimal(info['Close'].iloc[0]).quantize(Decimal('0.001'), rounding=ROUND_UP)  # Get the last closing price

    return timestamp, current_price

# API endpoint to fetch stock data and store it in the database
@app.get("/stocks/{symbol}")
@log_function
async def fetch_stock(symbol: str):
    try:
        timestamp, current_price = await get_stock_data(symbol)
    except HTTPException as http_exc:
        logging.error(f"HTTPException occurred for symbol {symbol}: {http_exc.detail}")
        raise http_exc  # Pass through the HTTPException if it occurs
    
    try:
        await MarketData.create(
            symbol=symbol, timestamp=timestamp, current_price=current_price
        )
    except Exception as e:
        logging.error(f"Error storing stock data for symbol {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to store stock data in the database")
    
    return {"symbol": symbol, "timestamp": timestamp, "current_price": current_price}

# API endpoint to get all stock data from the database
@app.get("/stocks")
@log_function
async def get_stock_data_from_db():
    try:
        data = await MarketData.all().values()
    except Exception as e:
        logging.error(f"Error fetching stock data from the database: {e}")
        raise HTTPException(status_code=500, detail="Error fetching stock data from the database")
    
    return data

@app.get("/positions/{clientId}")
@log_function
async def get_client_positions(clientId: int):
    try:
        client = await Client.get_or_none(id=clientId).prefetch_related("positions")
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    except Exception as e:
        logging.error(f"Error fetching client positions for clientId {clientId}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching client positions")
    
    positions = [
        {"symbol": pos.symbol, "quantity": pos.quantity, "cost_basis": float(pos.cost_basis)}
        for pos in await client.positions.all()
    ]
    return {"clientId": clientId, "positions": positions}

@app.get("/margin/{clientId}")
@log_function
async def get_margin_status(clientId: int):
    try:
        client = await Client.get_or_none(id=clientId)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    except Exception as e:
        logging.error(f"Error fetching client {clientId} margin data: {e}")
        raise HTTPException(status_code=500, detail="Error fetching client margin data")
    
    # Fetch related objects separately
    try:
        await client.fetch_related("positions", "margins")
        margin_account = await client.margins.all()
        if not margin_account:
            raise HTTPException(status_code=404, detail="Margin account not found")
        margin_account = margin_account[0]
    except Exception as e:
        logging.error(f"Error fetching margin account for client {clientId}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching margin account")
    
    total_value = Decimal(0)
    positions = await client.positions.all()
    if not positions:
        raise HTTPException(status_code=404, detail="No positions found for this client")
    
    for position in positions:
        try:
            marketData = await fetch_latest_price(position.symbol, MarketData)
            if "error" in marketData:
                raise HTTPException(status_code=404, detail=f"Market data not found for {position.symbol}")
            total_value += Decimal(position.quantity) * Decimal(marketData["current_price"]).quantize(Decimal('0.001'), rounding=ROUND_UP)
        except HTTPException as e:
            raise e  # Pass through HTTPException for failed market data fetch
    
    net_equity = Decimal(total_value) - Decimal(margin_account.loan).quantize(Decimal('0.001'), rounding=ROUND_UP) 
    margin_account.margin_requirement = (Decimal(total_value) * Decimal(config.MMR)).quantize(Decimal('0.001'), rounding=ROUND_UP)
    
    try:
        if margin_account:
            margin, created = await Margin.update_or_create(
                client_id=clientId,  # <-- This ensures we are updating a specific record
                defaults={'margin_requirement': margin_account.margin_requirement, 'loan': margin_account.loan}
            )
        else:
            logging.warning(f"No margin account found for clientId {clientId}")
    except Exception as e:
        logging.error(f"Error updating margin account for clientId {clientId}: {e}")
        raise HTTPException(status_code=500, detail="Error updating margin account")
    
    margin_shortfall = (margin_account.margin_requirement - net_equity).quantize(Decimal('0.001'), rounding=ROUND_UP) 
    margin_call_triggered = margin_shortfall > 0

    return {
        "timestamp": marketData["timestamp"],
        "clientId": clientId,
        "portfolio_value": float(total_value),
        "loan_amount": float(margin_account.loan),
        "net_equity": float(net_equity),
        "margin_requirement": float(margin_account.margin_requirement),
        "margin_shortfall": float(margin_shortfall),
        "margin_call_triggered": margin_call_triggered
    }

# Run the FastAPI app using Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
