"""Caché TTL en memoria (aislada para poder migrar a Redis sin tocar motores)."""
from __future__ import annotations

import functools
import time


def ttl_cache(ttl: int = 300, maxsize: int = 256):
    def deco(fn):
        store: dict = {}

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            hit = store.get(key)
            if hit is not None and now - hit[0] < ttl:
                return hit[1]
            value = fn(*args, **kwargs)
            store[key] = (now, value)
            if len(store) > maxsize:
                store.pop(next(iter(store)))
            return value

        wrapper.cache_clear = store.clear
        return wrapper

    return deco
