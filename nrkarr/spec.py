"""Builds the tracks-mode job spec for one programme: what to fetch,
from where, and what each stream is called. All the NRK knowledge the
download client must not have lives here."""

import logging
import re

from . import hls
from .http import FetchError

log = logging.getLogger(__name__)

WATCH_URL = "https://tv.nrk.no/se?v={prf_id}"
DESCRIBED_SUFFIX = "SYNS"


class SpecBuilder:
    def __init__(self, psapi, config):
        self.psapi = psapi
        self.config = config          # the "spec" section

    def build(self, prf_id, name):
        manifest, master_text, master = self.master(prf_id)
        groups = hls.audio_groups(master_text) if master_text else []

        spec = {
            "url": WATCH_URL.format(prf_id=prf_id),
            "name": name,
            "container": self.config["container"],
            "video": dict(self.config["video"]),
            "audio": self.audio_entries(self.config["audio"], groups),
            "subtitles": self.subtitles(prf_id, manifest, master_text, master),
            "embed": list(self.config["embed"]),
            "sidecar": list(self.config["sidecar"]),
        }

        described = self.described_audio(prf_id)

        if described:
            spec["audio"].append(described)

        return spec

    def codec_label(self, prf_id):
        """What the release name should say the video codec is, from
        the programme's master and the configured height cap; None
        when the master cannot be read."""
        _, master_text, _ = self.master(prf_id)

        if not master_text:
            return None

        return hls.codec_label(hls.video_variants(master_text), self.max_height())

    def max_height(self):
        found = re.search(r"height<=(\d+)", self.config["video"].get("format", ""))

        return int(found.group(1)) if found else 10**6

    def master(self, prf_id):
        """The playback manifest and the full HLS master it points at.
        Either may be missing; callers fall back."""
        manifest = self.psapi.manifest(prf_id)

        if manifest is None:
            return None, "", ""

        try:
            master = hls.master_url(manifest["playable"]["assets"][0]["url"])
            return manifest, hls.fetch(master), master
        except (KeyError, IndexError, FetchError) as error:
            log.warning("%s: HLS master unreadable (%s)", prf_id, error)
            return manifest, "", ""

    def audio_entries(self, templates, groups):
        """Config names channel counts; the master says which group has
        them. A template with no matching group is dropped when
        optional, and falls back to plain bestaudio when required."""
        entries = []

        for template in templates:
            entry = {key: value for key, value in template.items() if key != "channels"}
            channels = template.get("channels")

            if channels is None:
                entry.setdefault("format", "bestaudio")
            else:
                selector = hls.audio_selector(groups, channels) if groups else None

                if selector is None and template.get("optional"):
                    continue

                entry["format"] = selector or "bestaudio"

            entries.append(entry)

        return entries

    def subtitles(self, prf_id, manifest, master_text, master):
        """From the HLS master when it can be read; from psapi's own
        list otherwise, which lacks the plain track."""
        if manifest is None:
            return []

        renditions = hls.subtitle_renditions(master_text, master) if master_text else []

        if renditions:
            return hls.subtitle_entries(renditions, self.config["forced_title_pattern"])

        return self.psapi_subtitles(manifest)

    def psapi_subtitles(self, manifest):
        """psapi lists two files: type nor is the forced track, type
        ttv the SDH one. Verified against the files themselves."""
        entries = []

        for subtitle in manifest.get("playable", {}).get("subtitles") or []:
            flags = ["default"] if subtitle.get("defaultOn") else []

            if subtitle.get("type") == "nor":
                flags.append("forced")
            elif subtitle.get("type") == "ttv":
                flags.append("hearing_impaired")

            entries.append({
                "url": subtitle["webVtt"],
                "title": subtitle.get("label", ""),
                "language": hls.language_tag(subtitle.get("language")),
                "flags": flags,
            })

        return entries

    def described_audio(self, prf_id):
        """NRK publishes synstolking as a sibling programme, <id>SYNS,
        with the same cut; its audio joins the main file as a track."""
        template = self.config.get("described_audio")

        if not template:
            return None

        described_id = prf_id + DESCRIBED_SUFFIX
        manifest, master_text, _ = self.master(described_id)

        if manifest is None or manifest.get("playability") != "playable":
            return None

        groups = hls.audio_groups(master_text) if master_text else []
        entries = self.audio_entries([template], groups)

        if not entries:
            return None

        return {**entries[0], "url": WATCH_URL.format(prf_id=described_id)}
