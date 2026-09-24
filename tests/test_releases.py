import unittest

from nrkarr.releases import build, decode_token, encode_token

RELEASE = {
    "group": "Nrkarr",
    "source": "NRK",
    "resolution": "1080p",
    "video_codec": "H.264",
    "audio_codec": "AAC2.0",
    "bitrate_mbps": 5,
}

EPISODE = {
    "prfId": "MDRE23000124",
    "titles": {"title": "1. Nattevakt"},
    "sequenceNumber": 1,
    "durationInSeconds": 2411,
    "releaseDateOnDemand": "2026-04-11T06:01:00+02:00",
    "availability": {"status": "available"},
}

UNAIRED = {**EPISODE, "prfId": "X", "availability": {"status": "onDemand"}}


class TokenTest(unittest.TestCase):
    def test_round_trips_the_programme_and_its_name(self):
        token = encode_token("MDRE23000124", "LIS - S01E01 - Nattevakt")

        self.assertEqual(
            decode_token(token),
            ("MDRE23000124", "LIS - S01E01 - Nattevakt"),
        )

    def test_survives_norwegian_characters(self):
        token = encode_token("X", "Blodsbånd - S01E01 - Værøy")

        self.assertEqual(decode_token(token)[1], "Blodsbånd - S01E01 - Værøy")

    def test_carries_no_padding_that_would_need_url_escaping(self):
        token = encode_token("MDRE23000124", "LIS - S01E01 - Nattevakt")

        self.assertNotIn("=", token)


class BuildTest(unittest.TestCase):
    def test_offers_one_release_per_available_episode(self):
        built = build(
            "LIS", 457520, 1, [EPISODE], RELEASE, lambda token: token
        )

        self.assertEqual(len(built), 1)
        self.assertEqual(built[0]["episode"], 1)
        self.assertEqual(built[0]["tvdb_id"], 457520)

    def test_skips_anything_not_yet_available(self):
        built = build(
            "LIS", 457520, 1, [EPISODE, UNAIRED], RELEASE,
            lambda token: token,
        )

        self.assertEqual(len(built), 1)


if __name__ == "__main__":
    unittest.main()


class DispositionTest(unittest.TestCase):
    """HTTP headers are latin-1; NRK episode titles are not."""

    def test_carries_the_real_name_and_an_ascii_fallback(self):
        from nrkarr.app import _disposition

        header = _disposition("Blodsbånd - S01E01 - Værøy")

        self.assertIn('filename="Blodsband - S01E01 - Vaeroy.nzb"', header)
        self.assertIn("filename*=UTF-8''", header)

    def test_survives_characters_outside_latin_1(self):
        from nrkarr.app import _disposition

        header = _disposition("Still Breathing - S01E06 - – dash 「")

        header.encode("latin-1")
