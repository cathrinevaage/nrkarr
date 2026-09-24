"""Configuration loading, with defaults for everything optional."""

from copy import deepcopy
from pathlib import Path

import yaml

DEFAULTS = {
    "server": {
        "host": "0.0.0.0",
        "port": 9121,
        "api_key": "changeme",
        "url_base": "",
        "state": "known-series.json",
    },
    "tmdb": {
        "api_key": "",
    },
    "nrk": {
        "base_url": "https://psapi.nrk.no",
        "timeout": 20,
    },
    "spec": {
        "format": "bestvideo[height<=1080]+bestaudio/best",
        "subs": ["nb-nor"],
        "embed": ["subs", "chapters", "thumbnail", "metadata"],
        "container": "mkv",
    },
    "release": {
        "group": "Nrkarr",
        "source": "NRK",
        "resolution": "1080p",
        "video_codec": "H.264",
        "audio_codec": "AAC2.0",
        "bitrate_mbps": 5,
    },
    "cache": {
        "ttl": 300,
    },
}


def merge(base, override):
    """Deep-merge two mappings, preferring values from override."""
    merged = deepcopy(base)

    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge(merged[key], value)
        else:
            merged[key] = value

    return merged


def load(path):
    """Read a YAML config, filling anything absent from DEFAULTS."""
    source = Path(path)

    if not source.exists():
        return deepcopy(DEFAULTS)

    return merge(DEFAULTS, yaml.safe_load(source.read_text()))
