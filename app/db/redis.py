import redis.asyncio as redis
from app.config import settings
from app.logger import main_logger
import json

class NexusPubSubMock:
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def subscribe(self, *args, **kwargs): pass
    async def unsubscribe(self, *args, **kwargs): pass
    async def listen(self):
        if False: yield None

class NexusRedisFailsafe:
    def __init__(self):
        self.real_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.fallback_store = {}
        self.is_connected = False
        main_logger.warning("Nexus Redis: Initializing link...")

    async def _test_connection(self):
        try:
            await self.real_client.ping()
            self.is_connected = True
            main_logger.info("Nexus Redis: Primary link ACTIVE.")
        except Exception:
            self.is_connected = False
            main_logger.critical("Nexus Redis: FAILED to connect. Falling back to in-memory persistence.")

    def pubsub(self):
        if self.is_connected:
            return self.real_client.pubsub()
        main_logger.warning("Nexus Redis: Using MOCK PubSub stream.")
        return NexusPubSubMock()

    async def set(self, key, value, **kwargs):
        if not self.is_connected:
            await self._test_connection()
        if self.is_connected:
            try: return await self.real_client.set(key, value, **kwargs)
            except Exception: self.is_connected = False
        self.fallback_store[key] = value
        return True

    async def get(self, key):
        if self.is_connected:
            try: return await self.real_client.get(key)
            except Exception: self.is_connected = False
        return self.fallback_store.get(key)

    async def sadd(self, key, member):
        if self.is_connected:
            try: return await self.real_client.sadd(key, member)
            except Exception: self.is_connected = False
        return True

    async def zrevrange(self, key, start, stop, **kwargs):
        if self.is_connected:
            try: return await self.real_client.zrevrange(key, start, stop, **kwargs)
            except Exception: self.is_connected = False
        return []

# Initialize global proxy
redis_client = NexusRedisFailsafe()
