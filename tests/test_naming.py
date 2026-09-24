"""Release names are a contract with Sonarr's parser. Both forms here
were verified against it directly; these lock them in."""

import unittest

from nrkarr.naming import (
    dotted,
    estimated_size,
    release_name,
    strip_episode_number,
)

RELEASE = {
    "group": "Nrkarr",
    "source": "NRK",
    "resolution": "1080p",
    "video_codec": "H.264",
    "audio_codec": "AAC2.0",
    "bitrate_mbps": 5,
}


class ReleaseNameTest(unittest.TestCase):
    def test_uses_the_title_sonarr_holds(self):
        self.assertEqual(
            release_name("Still Breathing", 1, 1, "1. Nattevakt", RELEASE),
            "Still.Breathing.S01E01.Nattevakt.1080p.NRK.WEB-DL"
            ".AAC2.0.H.264-Nrkarr",
        )

    def test_parses_with_the_original_title_too(self):
        self.assertEqual(
            release_name("LIS", 1, 1, "1. Nattevakt", RELEASE),
            "LIS.S01E01.Nattevakt.1080p.NRK.WEB-DL.AAC2.0.H.264-Nrkarr",
        )

    def test_pads_season_and_episode(self):
        name = release_name("LIS", 2, 13, "13. Noe", RELEASE)

        self.assertIn("S02E13", name)


class SanitisingTest(unittest.TestCase):
    def test_strips_the_number_nrk_prefixes_titles_with(self):
        self.assertEqual(strip_episode_number("1. Nattevakt"), "Nattevakt")
        self.assertEqual(strip_episode_number("12.Ulykke"), "Ulykke")

    def test_leaves_a_title_that_merely_starts_with_a_word(self):
        self.assertEqual(strip_episode_number("Nattevakt"), "Nattevakt")

    def test_transliterates_norwegian_characters(self):
        self.assertEqual(dotted("Søsken på Værøy"), "Sosken.pa.Vaeroy")

    def test_collapses_punctuation_into_single_dots(self):
        self.assertEqual(dotted("Hva nå?! - del 2"), "Hva.na.del.2")


class SizeTest(unittest.TestCase):
    def test_derives_size_from_duration_and_bitrate(self):
        self.assertEqual(estimated_size(2411, 5), 1_506_875_000)


if __name__ == "__main__":
    unittest.main()
