"""Turning an NRK series into releases Sonarr can grab."""

import base64
import json

from .naming import estimated_size, release_name, strip_episode_number
from .newznab import published
from .nzb import spec_name
from .psapi import is_available

WATCH_URL = "https://tv.nrk.no/se?v={prf_id}"


def encode_token(prf_id, name):
    """The download URL points back at nrkarr and carries only what
    the spec cannot be rebuilt from: the programme and its name.
    Everything else comes from config when the NZB is rendered."""
    payload = json.dumps({"p": prf_id, "n": name}, ensure_ascii=False)

    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_token(token):
    padding = "=" * (-len(token) % 4)
    payload = base64.urlsafe_b64decode(token + padding).decode()
    decoded = json.loads(payload)

    return decoded["p"], decoded["n"]


def build(series_title, tvdb_id, season, episodes, release, download_url):
    """One release per available episode."""
    return [
        _release(
            series_title, tvdb_id, season, episode, release, download_url
        )
        for episode in episodes
        if is_available(episode)
    ]


def _release(series_title, tvdb_id, season, episode, release, download_url):
    number = episode["sequenceNumber"]
    title = strip_episode_number(episode["titles"]["title"])
    token = encode_token(
        episode["prfId"],
        spec_name(series_title, season, number, title),
    )

    return {
        "title": release_name(
            series_title, season, number, episode["titles"]["title"], release
        ),
        "guid": episode["prfId"],
        "link": download_url(token),
        "published": published(episode.get("releaseDateOnDemand")),
        "size": estimated_size(
            episode.get("durationInSeconds", 0), release["bitrate_mbps"]
        ),
        "tvdb_id": tvdb_id,
        "season": season,
        "episode": number,
    }


def watch_url(prf_id):
    """tv.nrk.no/se?v=<prfId> redirects to the canonical episode URL,
    and yt-dlp's NRKTV extractor takes over from there."""
    return WATCH_URL.format(prf_id=prf_id)
