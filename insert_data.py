import asyncio
import httpx
from db_config import init_db
from models import Client, Margin, Position
from tortoise import Tortoise

BASE_URL = "http://localhost:8000"

ALL_SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "SPY", "QQQ", "RIVN"]


async def fetch_market_data(symbols: list[str]):
    """Call GET /stocks/{symbol} for each symbol to pull live prices into MarketData."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        for symbol in symbols:
            r = await client.get(f"/stocks/{symbol}")
            if r.status_code == 200:
                data = r.json()
                print(f"  ✓ {symbol}: ${data['current_price']}")
            else:
                print(f"  ✗ {symbol}: {r.status_code} {r.text}")


async def insert_data():
    await init_db()

    # ---------------------------------------------------------------------------
    # Fetch live market data via stocks API (writes into MarketData table)
    # ---------------------------------------------------------------------------
    print("=== Fetching live market data ===")
    await fetch_market_data(ALL_SYMBOLS)

    # ---------------------------------------------------------------------------
    # Clients
    # ---------------------------------------------------------------------------
    print("\n=== Creating clients ===")
    client1, _ = await Client.get_or_create(name="U84729163", defaults={"balance": 50000.00})
    client2, _ = await Client.get_or_create(name="U31956742", defaults={"balance": 120000.00})
    client3, _ = await Client.get_or_create(name="U67043821", defaults={"balance": 75000.00})
    client4, _ = await Client.get_or_create(name="U29384710", defaults={"balance": 200000.00})
    client5, _ = await Client.get_or_create(name="U95162038", defaults={"balance": 30000.00})
    print(f"  ✓ Clients ready: {[c.name for c in [client1, client2, client3, client4, client5]]}")

    # ---------------------------------------------------------------------------
    # Positions
    # ---------------------------------------------------------------------------
    print("\n=== Creating positions ===")
    # U84729163 — healthy portfolio
    p1  = await Position.create(symbol="AAPL", quantity=50,  cost_basis=172.50, client=client1)
    p2  = await Position.create(symbol="MSFT", quantity=30,  cost_basis=415.00, client=client1)

    # U31956742 — diversified, large loan but ok
    p3  = await Position.create(symbol="NVDA", quantity=100, cost_basis=880.00, client=client2)
    p4  = await Position.create(symbol="TSLA", quantity=80,  cost_basis=245.00, client=client2)
    p5  = await Position.create(symbol="AMZN", quantity=40,  cost_basis=185.00, client=client2)

    # U67043821 — healthy, moderate loan
    p6  = await Position.create(symbol="GOOGL", quantity=25, cost_basis=175.00, client=client3)
    p7  = await Position.create(symbol="META",  quantity=60, cost_basis=530.00, client=client3)

    # U29384710 — overleveraged → likely margin call
    p8  = await Position.create(symbol="SPY",  quantity=200, cost_basis=510.00, client=client4)
    p9  = await Position.create(symbol="QQQ",  quantity=150, cost_basis=440.00, client=client4)
    p10 = await Position.create(symbol="AAPL", quantity=100, cost_basis=168.00, client=client4)

    # U95162038 — high loan relative to portfolio → likely margin call
    p11 = await Position.create(symbol="TSLA", quantity=20,  cost_basis=290.00, client=client5)
    p12 = await Position.create(symbol="RIVN", quantity=200, cost_basis=18.50,  client=client5)

    for p in [p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12]:
        print(f"  ✓ {p.client_id} {p.symbol} x{p.quantity} @ {p.cost_basis}")

    # ---------------------------------------------------------------------------
    # Margin accounts (margin_requirement=0, computed dynamically by /margin API)
    # ---------------------------------------------------------------------------
    print("\n=== Creating margin accounts ===")
    m1 = await Margin.create(client_id=client1.id, margin_requirement=0, loan=5000.00)
    m2 = await Margin.create(client_id=client2.id, margin_requirement=0, loan=80000.00)
    m3 = await Margin.create(client_id=client3.id, margin_requirement=0, loan=10000.00)
    m4 = await Margin.create(client_id=client4.id, margin_requirement=0, loan=180000.00)
    m5 = await Margin.create(client_id=client5.id, margin_requirement=0, loan=28000.00)

    for m in [m1, m2, m3, m4, m5]:
        print(f"  ✓ client_id={m.client_id} loan={m.loan}")

    await Tortoise.close_connections()  # close before API calls — API has its own DB connection

    # ---------------------------------------------------------------------------
    # Verify margin status via API
    # ---------------------------------------------------------------------------
    print("\n=== Margin status (live) ===")
    accounts = ["U84729163", "U31956742", "U67043821", "U29384710", "U95162038"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        for name in accounts:
            r = await client.get(f"/margin/{name}")
            if r.status_code == 200:
                d = r.json()
                status = "⚠️  MARGIN CALL" if d["margin_call_triggered"] else "✅ healthy"
                print(f"  {name} | equity={d['net_equity']:,.2f} | req={d['margin_requirement']:,.2f} | {status}")
            else:
                print(f"  {name}: {r.status_code} {r.text}")


if __name__ == "__main__":
    asyncio.run(insert_data())