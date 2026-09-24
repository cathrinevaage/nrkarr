import unittest
from copy import deepcopy
from unittest.mock import patch

from nrkarr.config import DEFAULTS
from nrkarr.http import FetchError
from nrkarr.spec import SpecBuilder
from tests.test_hls import MASTER

MANIFEST = {
    "playability": "playable",
    "playable": {
        "assets": [{"url": "https://cdn.example/open/ps/x/y.smil/muxed.m3u8?adap=small&s=0"}],
        "subtitles": [
            {"type": "nor", "language": "nb", "label": "Norsk", "defaultOn": False, "webVtt": "https://u/nor.vtt"},
            {"type": "ttv", "language": "nb", "label": "Norsk – på all tale", "defaultOn": True, "webVtt": "https://u/ttv.vtt"},
        ],
    },
}


class FakePsapi:
    def __init__(self, manifests):
        self.manifests = manifests

    def manifest(self, prf_id):
        return self.manifests.get(prf_id)


def builder(manifests):
    return SpecBuilder(FakePsapi(manifests), deepcopy(DEFAULTS["spec"]))


class SpecTest(unittest.TestCase):
    def test_full_spec_with_hls_subtitles_and_described_audio(self):
        subject = builder({"MDRE1": MANIFEST, "MDRE1SYNS": {**MANIFEST}})

        with patch("nrkarr.hls.fetch", return_value=MASTER):
            spec = subject.build("MDRE1", "Show - S01E01 - Pilot")

        self.assertEqual(spec["url"], "https://tv.nrk.no/se?v=MDRE1")
        self.assertEqual(spec["video"], {"format": "bestvideo[height<=1080]"})
        self.assertEqual([a["title"] for a in spec["audio"]], ["Norsk 5.1", "Norsk", "Synstolking"])
        self.assertEqual([a["format"] for a in spec["audio"]],
                         ["bestaudio[format_id^=aud3]", "bestaudio[format_id^=aud2]", "bestaudio[format_id^=aud2]"])
        self.assertNotIn("channels", spec["audio"][0])
        self.assertEqual(spec["audio"][2]["url"], "https://tv.nrk.no/se?v=MDRE1SYNS")
        self.assertEqual(spec["audio"][2]["flags"], ["visual_impaired"])
        self.assertEqual([s["title"] for s in spec["subtitles"]],
                         ["Norsk", "Norsk – kun ved annet språk", "Norsk – med lydbeskrivelser"])
        self.assertEqual(spec["subtitles"][1]["flags"], ["forced"])

    def test_no_described_version_means_no_described_track(self):
        subject = builder({"MDRE1": MANIFEST})

        with patch("nrkarr.hls.fetch", return_value=MASTER):
            spec = subject.build("MDRE1", "x")

        self.assertEqual([a["title"] for a in spec["audio"]], ["Norsk 5.1", "Norsk"])

    def test_falls_back_to_psapi_subtitles_when_the_master_is_unreadable(self):
        subject = builder({"MDRE1": MANIFEST})

        with patch("nrkarr.hls.fetch", side_effect=FetchError("geo")):
            spec = subject.build("MDRE1", "x")

        self.assertEqual([(s["url"], s["flags"]) for s in spec["subtitles"]],
                         [("https://u/nor.vtt", ["forced"]), ("https://u/ttv.vtt", ["default", "hearing_impaired"])])

    def test_without_a_master_the_optional_surround_track_is_dropped_and_stereo_is_bestaudio(self):
        subject = builder({"MDRE1": MANIFEST})

        with patch("nrkarr.hls.fetch", side_effect=FetchError("geo")):
            spec = subject.build("MDRE1", "x")

        self.assertEqual([(a["title"], a["format"]) for a in spec["audio"]], [("Norsk", "bestaudio")])

    def test_unknown_programme_yields_no_subtitles_but_a_valid_spec(self):
        spec = builder({}).build("NOPE", "x")

        self.assertEqual(spec["subtitles"], [])
        self.assertEqual([a["format"] for a in spec["audio"]], ["bestaudio"])
