"""Minimal JSON-over-HTTP helper, stdlib only."""

import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class FetchError(Exception):
    """A request failed, or returned something that is not JSON."""


def get_json(url, params=None, headers=None, timeout=20):
    """GET a URL and parse the response as JSON."""
    query = urlencode(params or {})
    target = f"{url}?{query}" if query else url

    request = Request(target, headers=headers or {})

    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except HTTPError as error:
        raise FetchError(f"{target} returned {error.code}") from error
    except (OSError, ValueError) as error:
        raise FetchError(f"{target} failed: {error}") from error
