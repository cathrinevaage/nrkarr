"""The routes through create_app, with the network replaced: the
search must return a feed, and the NZB must carry the built spec."""

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from nrkarr.app import create_app
from nrkarr.config import DEFAULTS, merge
from nrkarr.resolve import ResolvedSeries

EPISODE = {
    "prfId": "MDRE1", "titles": {"title": "1. Pilot"}, "sequenceNumber": 1,
    "durationInSeconds": 2400, "releaseDateOnDemand": "2026-04-11T06:01:00+02:00",
    "productionYear": 2026, "availability": {"status": "available"},
}


class RouteTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        config = merge(DEFAULTS, {
            "server": {"api_key": "k", "state": str(Path(self.directory.name) / "known.json")},
        })
        self.client = create_app(config).test_client()

    def tearDown(self):
        self.directory.cleanup()

    def test_tvsearch_returns_one_release_per_episode(self):
        with patch("nrkarr.app.Resolver.resolve", return_value=ResolvedSeries(1, "show", "Show")), \
             patch("nrkarr.app.Psapi.seasons", return_value=[{"id": "1", "type": "season", "status": "playable"}]), \
             patch("nrkarr.app.Psapi.episodes", return_value=[EPISODE]):
            response = self.client.get("/api?t=tvsearch&tvdbid=1&season=1&ep=1&apikey=k")

        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        titles = [t.text for t in ElementTree.fromstring(response.data).iter("title")][1:]
        self.assertEqual(titles, ["Show.S01E01.Pilot.1080p.NRK.WEB-DL.DD5.1.H.264-Nrkarr"])

    def test_rss_after_a_search_lists_the_remembered_series(self):
        with patch("nrkarr.app.Resolver.resolve", return_value=ResolvedSeries(1, "show", "Show")), \
             patch("nrkarr.app.Psapi.seasons", return_value=[{"id": "1", "type": "season", "status": "playable"}]), \
             patch("nrkarr.app.Psapi.episodes", return_value=[EPISODE]):
            self.client.get("/api?t=tvsearch&tvdbid=1&apikey=k")
            response = self.client.get("/api?t=tvsearch&apikey=k")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<item>", response.data)

    def test_nzb_carries_the_spec_the_builder_made(self):
        from nrkarr.releases import encode_token

        with patch("nrkarr.app.SpecBuilder.build", return_value={"url": "u", "name": "Show - S01E01 - Pilot", "video": {"format": "bestvideo"}}):
            response = self.client.get(f"/nzb/{encode_token('MDRE1', 'Show - S01E01 - Pilot')}")

        self.assertEqual(response.status_code, 200)
        root = ElementTree.fromstring(response.data)
        spec = next(m.text for m in root.iter() if m.get("type") == "ytdlpspec")
        self.assertEqual(json.loads(spec)["video"], {"format": "bestvideo"})

    def test_wrong_key(self):
        self.assertEqual(self.client.get("/api?t=tvsearch&tvdbid=1&apikey=wrong").status_code, 401)
