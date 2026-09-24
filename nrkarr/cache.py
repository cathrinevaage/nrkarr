"""A tiny time-to-live cache. psapi is fast; this exists so an RSS
sync does not re-walk every mapped series on every poll."""

import time


class TtlCache:
    def __init__(self, ttl):
        self.ttl = ttl
        self.entries = {}

    def get(self, key, produce):
        """Return the cached value, producing and storing it when the
        entry is missing or stale."""
        now = time.monotonic()
        entry = self.entries.get(key)

        if entry is not None and now - entry[0] < self.ttl:
            return entry[1]

        value = produce()
        self.entries[key] = (now, value)

        return value
