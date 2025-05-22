# create_tables.py
import asyncio

from src.db import models
from src.db.session import engine


async def run():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


asyncio.run(run())
