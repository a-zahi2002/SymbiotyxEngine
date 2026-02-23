import asyncio
from backend.server.websocket_server import inference_worker_sync

loop = asyncio.get_event_loop()
inference_worker_sync(loop)
