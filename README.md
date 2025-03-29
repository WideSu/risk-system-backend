# Overview
This FastAPI application provides APIs for fetching stock data, managing client positions, and monitoring margin requirements. It interacts with a PostgreSQL database using Tortoise ORM and retrieves real-time stock prices using Yahoo Finance.
# Setup Instructions
## Step 1. Create virtual env
```{shell}
python -m venv venv
```
## Step 2. Activate then install Dependencies
For macOS/Linux:
```{shell}
source venv/bin/activate
```
For Windows (Command Prompt):
```{shell}
venv\Scripts\Activate.ps1
```
## Step 3. Install Dependencies
```{shell}
pip install -r requirements.txt
```
## Step 4. Setup Database
Modify the `DATABASE_URL` in `config.py` to point to your PostgreSQL instance.

## Step 5. Run main.py in virtual env
```{shell}
python3 main.py
```
## Step 6. Run insert_data.py to create some clients data
```{shell}
python3 insert_data.py
```

# API Endpoints
## Fetch Real-time Stock Data
GET /stocks/{symbol}
- Description: Retrieves the latest stock price from Yahoo Finance and stores it in the database.
- Parameters:
    - symbol (string): Stock ticker symbol (e.g., "AAPL").
- Response:
```{json}
{
  "symbol": "AAPL",
  "timestamp": "2024-03-28T10:30:00Z",
  "current_price": 175.50
}
```
## Retrieve All Stored Stock Data
GET /stocks
- Description: Fetches all stock data stored in the database.
- Response: List of stock records.
## Get Client Positions
GET /positions/{clientId}
- Description: Retrieves all stock positions for a given client.
- Parameters:
    - `clientId` (integer): Unique identifier of the client.
- Response:
```{json}
{
  "clientId": 1,
  "positions": [
    {"symbol": "AAPL", "quantity": 100, "cost_basis": 150.0}
  ]
}
```
## Get Margin Status for a Client
GET /margin/{clientId}
- Description: Computes and retrieves margin status for a client.
- Parameters:
    - `clientId` (integer): Unique identifier of the client.
- Response:
```{json}
{
  "timestamp": "2024-03-28T10:30:00Z",
  "clientId": 1,
  "portfolio_value": 20000.0,
  "loan_amount": 10000.0,
  "net_equity": 10000.0,
  "margin_requirement": 5000.0,
  "margin_shortfall": 0.0,
  "margin_call_triggered": false
}
```
# Database Models
## 1. Client
Stores client details.
```{python}
class Client(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
```
## 2. Position
Stores client stock holdings.
```{python}
class Position(Model):
    id = fields.IntField(pk=True)
    symbol = fields.CharField(max_length=10)
    quantity = fields.IntField(null=True)
    cost_basis = fields.FloatField()
    client = fields.ForeignKeyField("models.Client", related_name="positions")
```
## 3. MarketData
Stores stock prices fetched from real-time market data API.
```{python}
class MarketData(Model):
    id = fields.IntField(pk=True)
    symbol = fields.CharField(max_length=50)
    current_price = fields.FloatField()
    timestamp = fields.DatetimeField()
```
## 4. Margin
Stores margin requirements for clients.
```{python}
class Margin(Model):
    client = fields.ForeignKeyField("models.Client", related_name="margins")
    margin_requirement = fields.FloatField()
    loan = fields.FloatField()
```
# Architecture
- Backend: FastAPI
- Realtime Trading API: Yahoo Finance
- Middleware: Tortoise ORM
- Database: PostgreSQL 14.17
- Dependencies: Python 3.10.9 and requirements.txt
### Comparision of backend framework
| Feature           | FastAPI              | Django                 | Flask                  | Tornado                | Pyramid                |
|------------------|---------------------|------------------------|------------------------|------------------------|------------------------|
| **Type**         | Asynchronous (ASGI)  | Synchronous (WSGI)     | Synchronous (WSGI)     | Asynchronous (ASGI)    | Synchronous (WSGI)     |
| **Performance**  | High                 | Moderate               | Moderate               | High                   | Moderate               |
| **Ease of Use**  | Easy to learn        | Moderate (Full-Stack)  | Very easy (Minimal)    | Moderate (Async-based) | Moderate               |
| **Built-in Features** | Minimal, Pydantic validation | Full-stack (ORM, Admin, Auth) | Minimal | WebSockets, Async I/O | Minimal |
| **Asynchronous Support** | Yes, built-in | Limited (Django 3+) | Limited (via extensions) | Yes, fully async | Limited |
| **Use Case**     | APIs, Microservices  | Full-stack applications | Lightweight applications | Real-time applications | Customizable web apps |
| **ORM Support**  | Tortoise ORM, SQLAlchemy | Django ORM | SQLAlchemy, Flask-SQLAlchemy | Custom | SQLAlchemy, ZODB |
| **WebSockets**   | Yes, built-in        | No (via Channels)      | No (via Flask-SocketIO) | Yes, built-in          | No                     |
| **Documentation**| Excellent            | Extensive              | Good                   | Moderate               | Moderate               |
| **Community Support** | Growing          | Very Large             | Large                  | Small                  | Moderate               |

### Comparision of database
| Feature                         | Oracle Database       | Microsoft SQL Server  | PostgreSQL          | MySQL               | MongoDB            | Redis              |
|---------------------------------|-----------------------|-----------------------|---------------------|---------------------|--------------------|--------------------|
| **Primary Use Case**            | Enterprise-level transactions and analytics | Enterprise-level transactions | Data warehousing, financial analysis | Transactional systems, analytics | NoSQL document-based storage | Caching, high-speed transactions |
| **Data Model**                  | Relational            | Relational            | Relational          | Relational          | Document-oriented  | Key-value store    |
| **ACID Compliance**             | Yes                   | Yes                   | Yes                 | Yes                 | No                 | No                 |
| **SQL Support**                 | Full SQL support      | Full SQL support      | Full SQL support    | Full SQL support    | Limited SQL support | No                 |
| **Transactions (ACID)**         | Yes                   | Yes                   | Yes                 | Yes                 | No                 | No                 |
| **Horizontal Scaling**          | Yes (with Oracle RAC) | Yes (with Always On Availability Groups) | Yes (with Citus extension) | Yes (with Galera Cluster) | Yes (with sharding) | Yes (with clustering) |
| **Vertical Scaling**            | Yes                   | Yes                   | Yes                 | Yes                 | No (sharding)      | Yes (in-memory)    |
| **Query Performance**           | High (optimized for large-scale enterprise queries) | High (optimized for transactional workloads) | High (supports complex queries) | High (well-suited for web apps) | Low to moderate (document search) | Extremely fast for small, simple queries |
| **Data Integrity**              | High (strong consistency) | High (strong consistency) | High (strong consistency) | High (strong consistency) | Low (eventual consistency) | Low (eventual consistency) |
| **Data Replication**            | Yes (advanced replication options) | Yes (Always On)       | Yes (synchronous and asynchronous) | Yes (master-slave replication) | Yes (replica sets) | Yes (master-slave replication) |
| **Concurrency Control**         | Multi-version concurrency control (MVCC) | Lock-based concurrency | MVCC                | Lock-based concurrency | Eventual consistency | Single-threaded |
| **Licensing Model**             | Paid (Enterprise licenses) | Paid (Enterprise licenses) | Open-source, Paid options | Open-source, Paid options | Open-source, Paid options | Open-source, Paid options |
| **Cost**                         | High                  | High                  | Free                | Free                | Free               | Free (paid for enterprise versions) |
| **Cloud Deployment**            | Yes (Oracle Cloud, AWS, Azure, GCP) | Yes (Azure)           | Yes (AWS, Azure, GCP) | Yes (AWS, Azure, GCP) | Yes (AWS, Azure, GCP) | Yes (AWS, Azure, GCP) |
| **Industry Adoption**           | Widely adopted in banking, investment firms, insurance | Widely adopted in banking, corporate finance | Widely used in analytics, fintech, startups | Widely used in fintech, startups, web applications | Increasing in fintech for unstructured data | Popular for caching in high-performance environments |

### Comparision of real-time market data API 
The pros and cons of popular market data APIs including Twelve Data, IEX Cloud, Alpha Vantage with a real-time plan, Yahoo Finance, Moomoo and IBKR

|<p>Feature/</p><p>Provider</p>|<p>Twelve</p><p>Data</p>|IEX Cloud|<p>Alpha</p><p>Vantage</p>|<p>Yahoo</p><p>Finance</p>|Moomoo|<p>Interactive</p><p>Brokers</p>|
| :- | :- | :- | :- | :- | :- | :- |
|<p>Real-time</p><p>Data</p>|Yes|<p>Yes</p><p>(delayed)</p>|Yes|<p>Yes</p><p>(delayed)</p>|Yes|Yes|
|Granularity|1-minute|1-minute|1-minute|<p>15-min</p><p>delay</p>|1-minute|1-minute|
|<p>Data</p><p>Coverage</p>|Global|US only|Global|US only|US only|Global|
|API Rate Limit|<p>5/min</p><p>(free)</p>|<p>50,000/</p><p>month</p>|5/min (free)|N/A|N/A|Varies|
|<p>Historical</p><p>Data</p>|Yes|Yes (limited)|Yes|Yes|Yes|Yes|
|<p>Premium Plan</p><p>Cost</p>|<p>$29/</p><p>month</p>|$9/month|<p>$29.99/</p><p>month</p>|Free|Free|Depends on equity and subsctiption fee|
|<p>Additional</p><p>Features</p>|<p>Crypto,</p><p>Forex</p>|<p>Financials,</p><p>News</p>|<p>Technical</p><p>Indicators</p>|Basic Data|<p>Charting,</p><p>Trading</p>|<p>Advanced</p><p>Trading Tools</p>|

