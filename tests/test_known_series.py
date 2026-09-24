import json
import tempfile
import unittest
from pathlib import Path

from nrkarr.known_series import KnownSeries
from nrkarr.resolve import ResolvedSeries

LIS = ResolvedSeries(tvdb_id=457520, slug="lis", title="LIS")


class KnownSeriesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "state" / "known.json"

    def tearDown(self):
        self.directory.cleanup()

    def test_starts_empty_when_nothing_is_stored(self):
        self.assertEqual(KnownSeries(self.path).all(), [])

    def test_remembers_across_restarts(self):
        KnownSeries(self.path).remember(LIS)

        self.assertEqual(
            KnownSeries(self.path).all(), [(457520, "lis", "LIS")]
        )

    def test_updates_in_place_rather_than_accumulating(self):
        store = KnownSeries(self.path)
        store.remember(LIS)
        store.remember(ResolvedSeries(457520, "lis-2", "LIS"))

        self.assertEqual(store.all(), [(457520, "lis-2", "LIS")])

    def test_survives_a_corrupt_state_file(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{ not json")

        self.assertEqual(KnownSeries(self.path).all(), [])

    def test_forgets_a_series(self):
        store = KnownSeries(self.path)
        store.remember(LIS)
        store.forget(457520)

        self.assertEqual(store.all(), [])
