import asyncio
import unittest

from uvicorn import Config


class EventLoopTests(unittest.TestCase):
    def test_uvicorn_custom_factory_creates_usable_loop(self):
        config = Config("app.main:app", loop="app.core.event_loop:selector_loop_factory")
        factory = config.get_loop_factory()
        loop = factory()
        try:
            self.assertIsInstance(loop, asyncio.SelectorEventLoop)

            async def value():
                return 42

            self.assertEqual(loop.run_until_complete(value()), 42)
        finally:
            loop.close()
