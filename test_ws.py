import asyncio
import websockets

async def test():
    async with websockets.connect("ws://localhost:8001/ws") as ws:
        print("Connected!")
        await asyncio.sleep(8)
        print("Done")

asyncio.run(test())
