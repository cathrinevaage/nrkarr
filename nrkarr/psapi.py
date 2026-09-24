"""Client for NRK's public programme API. No key, no auth."""

from .http import FetchError, get_json


class Psapi:
    def __init__(self, base_url, timeout=20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path, params=None):
        return get_json(
            f"{self.base_url}{path}",
            params=params,
            timeout=self.timeout,
        )

    def search(self, query):
        """Series hits for a free-text query, best match first."""
        payload = self._get("/search", {"q": query})

        return [
            hit["hit"]
            for hit in payload.get("hits", [])
            if hit.get("type") == "serie"
        ]

    def seasons(self, slug):
        """Playable numbered seasons. Extra material is type 'fixed'."""
        payload = self._get(f"/tv/catalog/series/{slug}")
        sections = payload.get("navigation", {}).get("sections", [])

        return [
            section
            for section in sections
            if section.get("type") == "season"
            and section.get("status") == "playable"
        ]

    def manifest(self, prf_id):
        """The playback manifest, or None when the id is unknown -
        psapi answers 400/404 for a programme that does not exist."""
        try:
            return self._get(f"/playback/manifest/program/{prf_id}")
        except FetchError as error:
            if "returned 40" in str(error):
                return None

            raise

    def episodes(self, slug, season_id):
        """Episodes in one season, in sequence order."""
        payload = self._get(
            f"/tv/catalog/series/{slug}/seasons/{season_id}"
        )

        return sorted(
            _collect_episodes(payload),
            key=lambda episode: episode.get("sequenceNumber", 0),
        )


def _collect_episodes(payload):
    """Walk the season payload for anything carrying a prfId."""
    if isinstance(payload, dict):
        if "prfId" in payload:
            yield payload
            return

        for value in payload.values():
            yield from _collect_episodes(value)

    if isinstance(payload, list):
        for value in payload:
            yield from _collect_episodes(value)


def is_available(episode):
    """Skip anything unaired or expired rather than offering a
    release that fails on fetch."""
    status = episode.get("availability", {}).get("status")

    return status == "available"
