import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        # First login (the default password in auth.py is probably something simple. Let's check auth.py)
        pass

asyncio.run(test())
