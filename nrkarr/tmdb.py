"""Resolves a tvdbid to the title NRK knows the series by.

TVDB and Sonarr hold the English title ("Still Breathing"); NRK only
knows the original ("LIS"). TMDB carries both, and its /find endpoint
takes an external id directly, so this is one call.
"""

from .http import get_json

BASE_URL = "https://api.themoviedb.org/3"


class Tmdb:
    def __init__(self, api_key, base_url=BASE_URL, timeout=20):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def find_by_tvdb_id(self, tvdb_id):
        """The series as TMDB holds it, or None when nothing matches."""
        payload = get_json(
            f"{self.base_url}/find/{tvdb_id}",
            params={"external_source": "tvdb_id", **self._key_param()},
            headers=self._key_header(),
            timeout=self.timeout,
        )

        results = payload.get("tv_results", [])

        return results[0] if results else None


    def _is_v3_key(self):
        """TMDB issues two kinds of credential: a 32-hex v3 key sent as
        a query parameter, and a v4 read access token sent as Bearer."""
        return len(self.api_key) == 32 and all(
            character in "0123456789abcdef" for character in self.api_key
        )

    def _key_param(self):
        return {"api_key": self.api_key} if self._is_v3_key() else {}

    def _key_header(self):
        if self._is_v3_key():
            return {}

        return {"Authorization": f"Bearer {self.api_key}"}


def original_title(series):
    return series.get("original_name") or series.get("name")


def is_norwegian(series):
    """A cheap pre-filter: a series not originally in Norwegian is not
    plausibly an NRK production."""
    return series.get("original_language") in ("no", "nb", "nn")
