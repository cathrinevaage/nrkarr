import unittest
from copy import deepcopy

from nrkarr.config import DEFAULTS
from nrkarr.env import apply


class EnvOverrideTest(unittest.TestCase):
    def test_sets_a_string_and_keeps_the_type_of_a_number(self):
        config = apply(deepcopy(DEFAULTS), {
            "NRKARR_TMDB_API_KEY": "abc",
            "NRKARR_SERVER_PORT": "9999",
            "NRKARR_RELEASE_BITRATE_MBPS": "7",
        })

        self.assertEqual(config["tmdb"]["api_key"], "abc")
        self.assertEqual(config["server"]["port"], 9999)
        self.assertEqual(config["release"]["bitrate_mbps"], 7)

    def test_lists_split_on_commas(self):
        config = apply(deepcopy(DEFAULTS), {"NRKARR_SPEC_SUBS": "nb-nor, nb-ttv"})

        self.assertEqual(config["spec"]["subs"], ["nb-nor", "nb-ttv"])

    def test_keys_with_underscores_resolve_past_the_section(self):
        config = apply(deepcopy(DEFAULTS), {"NRKARR_SERVER_URL_BASE": "/nrkarr"})

        self.assertEqual(config["server"]["url_base"], "/nrkarr")

    def test_unknown_names_and_other_prefixes_are_ignored(self):
        before = deepcopy(DEFAULTS)
        config = apply(deepcopy(DEFAULTS), {
            "NRKARR_TMDB_APIKEY": "typo",
            "NRKARR_NOPE_X": "1",
            "YTDLPARR_SERVER_API_KEY": "other app",
            "PATH": "/usr/bin",
        })

        self.assertEqual(config, before)
