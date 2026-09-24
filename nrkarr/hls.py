"""NRK's HLS master carries subtitle renditions yt-dlp never lists,
because the NRK extractor asks for the master with ?s=0 - subtitles
stripped - and takes subtitles from psapi's shorter list instead.
Reading the full master is how the plain "Norsk" track is found."""

import re
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .http import FetchError

ATTRIBUTE = re.compile(r'([A-Z0-9-]+)=("(?:[^"\\]|\\.)*"|[^,]*)')

# HLS/ISO 639-1 codes NRK uses -> the 639-2 tag written into the file.
# NRK tags subtitles "no"; they are Bokmål, and the audio is tagged nob.
LANGUAGE_TAGS = {
    "no": "nob", "nb": "nob", "nn": "nno", "se": "sme", "en": "eng",
    "sv": "swe", "da": "dan", "fi": "fin", "de": "ger", "fr": "fre",
    "es": "spa", "it": "ita",
}

SOUND_DESCRIPTIONS = "public.accessibility.describes-music-and-sound"


def master_url(asset_url):
    """psapi hands out .../<x>.smil/muxed.m3u8?adap=small&s=0; the
    full master the player uses sits beside it as cmaf.m3u8."""
    parts = urlsplit(asset_url)
    path = parts.path.rsplit("/", 1)[0] + "/cmaf.m3u8"

    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def fetch(url, timeout=20):
    try:
        with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=timeout) as response:
            return response.read().decode("utf-8", "replace")
    except OSError as error:
        raise FetchError(f"{url} failed: {error}") from error


def attributes(line):
    return {
        key: value[1:-1] if value.startswith('"') else value
        for key, value in ATTRIBUTE.findall(line.split(":", 1)[1])
    }


def subtitle_renditions(master_text, master_url):
    """Every #EXT-X-MEDIA:TYPE=SUBTITLES line, with its URI absolute."""
    renditions = []

    for line in master_text.splitlines():
        if not line.startswith("#EXT-X-MEDIA:"):
            continue

        found = attributes(line)

        if found.get("TYPE") != "SUBTITLES" or "URI" not in found:
            continue

        renditions.append({
            "url": urljoin(master_url, found["URI"]),
            "name": found.get("NAME", ""),
            "language": found.get("LANGUAGE", ""),
            "default": found.get("DEFAULT") == "YES",
            "characteristics": found.get("CHARACTERISTICS", ""),
        })

    return renditions


def language_tag(code):
    code = (code or "").lower()

    return LANGUAGE_TAGS.get(code, code if len(code) == 3 else "und")


def subtitle_entries(renditions, forced_pattern):
    """Spec subtitle tracks from renditions. Flags come from what the
    master says; only "forced" needs NRK's naming, since HLS has no
    attribute for it and NRK sets none."""
    forced = re.compile(forced_pattern, re.I) if forced_pattern else None
    entries = []

    for rendition in renditions:
        flags = []

        if rendition["default"]:
            flags.append("default")

        if SOUND_DESCRIPTIONS in rendition["characteristics"]:
            flags.append("hearing_impaired")

        if forced and forced.search(rendition["name"]):
            flags.append("forced")

        entries.append({
            "url": rendition["url"],
            "title": rendition["name"],
            "language": language_tag(rendition["language"]),
            "flags": flags,
        })

    return entries


def audio_groups(master_text):
    """Audio renditions by GROUP-ID with their channel count, plus the
    highest variant bandwidth that references each group - which is
    how the high-bitrate stereo group is told from the low one, since
    EXT-X-MEDIA carries no bitrate of its own."""
    groups = {}
    referenced = {}

    for line in master_text.splitlines():
        if line.startswith("#EXT-X-MEDIA:"):
            found = attributes(line)

            if found.get("TYPE") == "AUDIO" and found.get("GROUP-ID"):
                groups[found["GROUP-ID"]] = int(found.get("CHANNELS", "2") or 2)

        elif line.startswith("#EXT-X-STREAM-INF:"):
            found = attributes(line)
            group = found.get("AUDIO")

            if group:
                bandwidth = int(found.get("BANDWIDTH", "0") or 0)
                referenced[group] = max(referenced.get(group, 0), bandwidth)

    return [
        {"group": group, "channels": channels, "bandwidth": referenced.get(group, 0)}
        for group, channels in groups.items()
    ]


def audio_selector(groups, channels):
    """A yt-dlp selector for the best group with this many channels,
    or None when there is none. yt-dlp names NRK's audio formats after
    the group id, and exposes neither channels nor bitrate itself."""
    matching = sorted(
        (g for g in groups if g["channels"] == channels),
        key=lambda g: g["bandwidth"], reverse=True,
    )

    if not matching:
        return None

    return f"bestaudio[format_id^={matching[0]['group']}]"


# yt-dlp's own codec preference, best first; the release name says
# what it will pick.
CODEC_PREFERENCE = (("av01", "AV1"), ("hvc1", "HEVC"), ("hev1", "HEVC"), ("avc1", "H.264"), ("avc3", "H.264"))


def video_variants(master_text):
    """(codec, height) for every variant stream in the master."""
    variants = []

    for line in master_text.splitlines():
        if not line.startswith("#EXT-X-STREAM-INF:"):
            continue

        found = attributes(line)
        codecs = found.get("CODECS", "")
        resolution = found.get("RESOLUTION", "0x0")
        height = int(resolution.split("x")[-1] or 0) if "x" in resolution else 0
        video = next((c for c in codecs.split(",") if not c.startswith("mp4a") and not c.startswith("ac-3") and not c.startswith("ec-3")), "")
        variants.append({"codec": video, "height": height})

    return variants


def codec_label(variants, max_height):
    """The label for the codec yt-dlp will choose within max_height,
    or None when the master says nothing usable."""
    eligible = [v for v in variants if v["height"] and v["height"] <= max_height]

    for prefix, label in CODEC_PREFERENCE:
        if any(v["codec"].startswith(prefix) for v in eligible):
            return label

    return None
