from contextlib import asynccontextmanager
from decimal import ROUND_UP, Decimal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from tortoise import Tortoise
from yfinance import Ticker

from models import Client, Margin, MarketData
from utils.logging.logging_decorator import log_function
from utils.yfinance.yfinance_stock_utils import fetch_latest_price
import logging
import os

load_dotenv(".env.local")
app = FastAPI()

DB_URL = os.getenv("DATABASE_URL")


@app.on_event("startup")
async def startup_event():
    await Tortoise.init(
        db_url=DB_URL,
        modules={"models": ["models"]}
    )
    await Tortoise.generate_schemas()


@app.on_event("shutdown")
async def shutdown_event():
    await Tortoise.close_connections()


# ---------------------------------------------------------------------------
# Accounts API
# ---------------------------------------------------------------------------

class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1)
    initial_balance: float


class TransactionAmount(BaseModel):
    amount: float


class Transfer(BaseModel):
    sender: str
    recipient: str
    amount: float


@app.get("/accounts")
@app.get("/accounts/")
async def list_accounts():
    clients = await Client.all().values("name", "balance")
    return {"accounts": clients}


@app.post("/accounts/")
async def create_account(data: AccountCreate):
    existing = await Client.get_or_none(name=data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Account already exists")
    if data.initial_balance < 0:
        raise HTTPException(status_code=400, detail="Initial balance must be non-negative")
    await Client.create(name=data.name, balance=float(data.initial_balance))
    return {"message": f"Account '{data.name}' created."}


@app.get("/accounts/{name}")
async def get_balance(name: str):
    client = await Client.get_or_none(name=name)
    if not client:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"name": client.name, "balance": client.balance}


@app.post("/accounts/{name}/deposits")
async def deposit(name: str, data: TransactionAmount):
    client = await Client.get_or_none(name=name)
    if not client:
        raise HTTPException(status_code=404, detail="Account not found")
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    client.balance = float(client.balance) + float(data.amount)
    await client.save()
    return {"message": f"{data.amount:.2f} deposited to {name}"}


@app.post("/accounts/{name}/withdrawals")
async def withdraw(name: str, data: TransactionAmount):
    client = await Client.get_or_none(name=name)
    if not client:
        raise HTTPException(status_code=404, detail="Account not found")
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if float(client.balance) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    client.balance = float(client.balance) - float(data.amount)
    await client.save()
    return {"message": f"{data.amount:.2f} withdrawn from {name}"}


@app.post("/transfers")
async def transfer(data: Transfer):
    sender = await Client.get_or_none(name=data.sender)
    recipient = await Client.get_or_none(name=data.recipient)
    if not sender or not recipient:
        raise HTTPException(status_code=404, detail="Sender or recipient not found")
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if float(sender.balance) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    sender.balance = float(sender.balance) - float(data.amount)
    recipient.balance = float(recipient.balance) + float(data.amount)
    await sender.save()
    await recipient.save()
    return {"message": f"{data.amount:.2f} transferred from {data.sender} to {data.recipient}"}


# ---------------------------------------------------------------------------
# Stocks API
# ---------------------------------------------------------------------------

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

    timestamp = info.index[0]
    current_price = Decimal(info['Close'].iloc[0]).quantize(Decimal('0.001'), rounding=ROUND_UP)
    return timestamp, current_price


@app.get("/stocks/{symbol}")
@log_function
async def fetch_stock(symbol: str):
    try:
        timestamp, current_price = await get_stock_data(symbol)
    except HTTPException as http_exc:
        logging.error(f"HTTPException occurred for symbol {symbol}: {http_exc.detail}")
        raise http_exc

    try:
        await MarketData.create(symbol=symbol, timestamp=timestamp, current_price=current_price)
    except Exception as e:
        logging.error(f"Error storing stock data for symbol {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to store stock data in the database")

    return {"symbol": symbol, "timestamp": timestamp, "current_price": current_price}


@app.get("/stocks")
@log_function
async def get_stock_data_from_db():
    try:
        data = await MarketData.all().values()
    except Exception as e:
        logging.error(f"Error fetching stock data from the database: {e}")
        raise HTTPException(status_code=500, detail="Error fetching stock data from the database")
    return data


# ---------------------------------------------------------------------------
# Positions & Margin API (using account name instead of integer id)
# ---------------------------------------------------------------------------

@app.get("/positions/{name}")
@log_function
async def get_client_positions(name: str):
    try:
        client = await Client.get_or_none(name=name).prefetch_related("positions")
        if not client:
            raise HTTPException(status_code=404, detail="Account not found")
    except Exception as e:
        logging.error(f"Error fetching positions for {name}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching client positions")

    positions = [
        {"symbol": pos.symbol, "quantity": pos.quantity, "cost_basis": float(pos.cost_basis)}
        for pos in await client.positions.all()
    ]
    return {"name": name, "positions": positions}


@app.get("/margin/{name}")
@log_function
async def get_margin_status(name: str):
    try:
        client = await Client.get_or_none(name=name)
        if not client:
            raise HTTPException(status_code=404, detail="Account not found")
    except Exception as e:
        logging.error(f"Error fetching client {name}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching client data")

    try:
        await client.fetch_related("positions", "margins")
        margin_account = await client.margins.all()
        if not margin_account:
            raise HTTPException(status_code=404, detail="Margin account not found")
        margin_account = margin_account[0]
    except Exception as e:
        logging.error(f"Error fetching margin account for {name}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching margin account")

    total_value = Decimal(0)
    positions = await client.positions.all()
    if not positions:
        raise HTTPException(status_code=404, detail="No positions found for this account")

    for position in positions:
        try:
            marketData = await fetch_latest_price(position.symbol, MarketData)
            if "error" in marketData:
                raise HTTPException(status_code=404, detail=f"Market data not found for {position.symbol}")
            total_value += Decimal(position.quantity) * Decimal(marketData["current_price"]).quantize(Decimal('0.001'), rounding=ROUND_UP)
        except HTTPException as e:
            raise e

    net_equity = Decimal(total_value) - Decimal(margin_account.loan).quantize(Decimal('0.001'), rounding=ROUND_UP)
    margin_account.margin_requirement = (Decimal(total_value) * Decimal(config.MMR)).quantize(Decimal('0.001'), rounding=ROUND_UP)

    try:
        if margin_account:
            margin, created = await Margin.update_or_create(
                client_id=client.id,
                defaults={'margin_requirement': margin_account.margin_requirement, 'loan': margin_account.loan}
            )
    except Exception as e:
        logging.error(f"Error updating margin account for {name}: {e}")
        raise HTTPException(status_code=500, detail="Error updating margin account")

    margin_shortfall = (margin_account.margin_requirement - net_equity).quantize(Decimal('0.001'), rounding=ROUND_UP)
    margin_call_triggered = margin_shortfall > 0

    return {
        "timestamp": marketData["timestamp"],
        "name": name,
        "portfolio_value": float(total_value),
        "loan_amount": float(margin_account.loan),
        "net_equity": float(net_equity),
        "margin_requirement": float(margin_account.margin_requirement),
        "margin_shortfall": float(margin_shortfall),
        "margin_call_triggered": margin_call_triggered
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)