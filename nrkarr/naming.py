"""Release name construction, verified against Sonarr's parser."""

import re
import unicodedata

EPISODE_NUMBER_PREFIX = re.compile(r"^\d+\.\s*")
NON_RELEASE_CHARACTERS = re.compile(r"[^A-Za-z0-9]+")

TRANSLITERATIONS = {
    "æ": "ae",
    "ø": "o",
    "å": "a",
    "Æ": "Ae",
    "Ø": "O",
    "Å": "A",
}


def strip_episode_number(title):
    """NRK prefixes episode titles with their number: "1. Nattevakt"."""
    return EPISODE_NUMBER_PREFIX.sub("", title).strip()


def to_ascii(text):
    """Release names are conventionally ASCII."""
    transliterated = "".join(
        TRANSLITERATIONS.get(character, character) for character in text
    )

    return (
        unicodedata.normalize("NFKD", transliterated)
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def dotted(text):
    """Collapse anything that is not alphanumeric into single dots."""
    return NON_RELEASE_CHARACTERS.sub(".", to_ascii(text)).strip(".")


def release_name(series_title, season, episode, episode_title, release):
    """Sonarr parses this back into series, season and episode."""
    parts = [
        dotted(series_title),
        f"S{season:02d}E{episode:02d}",
        dotted(strip_episode_number(episode_title)),
        release["resolution"],
        release["source"],
        "WEB-DL",
        release["audio_codec"],
        dotted(release["video_codec"]),
    ]

    return ".".join(part for part in parts if part) \
        + f"-{release['group']}"


def estimated_size(duration_in_seconds, bitrate_mbps):
    """Sonarr acts on the advertised size, so it has to be a number.
    Derived from duration against a configured bitrate."""
    return int(duration_in_seconds * bitrate_mbps * 1_000_000 / 8)
