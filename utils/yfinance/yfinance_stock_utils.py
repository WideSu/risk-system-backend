# Function to check if the stock symbol exists using Yahoo Finance API
from fastapi import HTTPException
from yfinance import Ticker

from models import MarketData
from utils.logging.logging_decorator import log_function

@log_function
async def fetch_latest_price(symbol: str, db_model=MarketData):
    """Fetch the latest stock price closest to the given timestamp."""
    try:
        market_data = await db_model.filter(symbol=symbol) \
            .order_by('timestamp') \
            .first()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching market data from the database")
    
    if market_data:
        return {
            "symbol": market_data.symbol,
            "current_price": market_data.current_price,
            "timestamp": market_data.timestamp
        }
    else:
        raise HTTPException(status_code=404, detail="No data found for the given symbol")