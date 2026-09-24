"""The series nrkarr has already resolved.

Sonarr's RSS sync asks for everything, with no tvdbid to resolve from.
Rather than a hand-maintained mapping, the list builds itself: every
series Sonarr searches for and nrkarr matches to NRK is remembered,
and those are what a bare search enumerates.
"""

import json
from pathlib import Path


class KnownSeries:
    def __init__(self, path):
        self.path = Path(path)
        self.entries = self._read()

    def _read(self):
        if not self.path.exists():
            return {}

        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return {}

    def _write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.entries, ensure_ascii=False, indent=2)
        )

    def remember(self, series):
        """Record a resolved series, replacing any earlier entry for
        the same tvdbid rather than accumulating duplicates."""
        key = str(series.tvdb_id)
        entry = {"slug": series.slug, "title": series.title}

        if self.entries.get(key) == entry:
            return

        self.entries[key] = entry
        self._write()

    def forget(self, tvdb_id):
        if self.entries.pop(str(tvdb_id), None) is not None:
            self._write()

    def all(self):
        """Every remembered series, as (tvdb_id, slug, title)."""
        return [
            (int(tvdb_id), entry["slug"], entry["title"])
            for tvdb_id, entry in self.entries.items()
        ]
