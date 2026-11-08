"""Uvicorn loop factory compatible with psycopg async connections on Windows."""

import asyncio


def selector_loop_factory():
    return asyncio.SelectorEventLoop()
