from tortoise import Tortoise
import asyncio

from config import DATABASE_URL
# Database connection URL

async def init_db():
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={'models': ['models']}
    )
    await Tortoise.generate_schemas()