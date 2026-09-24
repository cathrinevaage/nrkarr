"""Configuration loading, with defaults for everything optional."""

from copy import deepcopy
from pathlib import Path

import yaml

from . import env

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
        "container": "mkv",
        "video": {"format": "bestvideo[height<=1080]"},
        "audio": [
            {"channels": 6, "title": "Norsk 5.1", "language": "nob",
             "flags": ["default"], "optional": True},
            {"channels": 2, "title": "Norsk", "language": "nob"},
        ],
        "described_audio": {
            "channels": 2, "title": "Synstolking", "language": "nob",
            "flags": ["visual_impaired"], "optional": True,
        },
        "forced_title_pattern": "kun ved annet spr\u00e5k",
        "embed": ["chapters", "thumbnail", "metadata"],
        "sidecar": [],
    },
    "release": {
        "group": "Nrkarr",
        "source": "NRK",
        "resolution": "1080p",
        "video_codec": "H.264",
        "audio_codec": "AAC2.0",
        "surround_audio_codec": "DD5.1",   # NRK's 6-channel group is AC-3
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
    """Defaults, then the YAML file, then environment overrides."""
    source = Path(path)
    from_file = yaml.safe_load(source.read_text()) if source.exists() else {}

    return env.apply(merge(DEFAULTS, from_file))