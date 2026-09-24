"""TMDB issues two credential forms and accepts each in a different
place; sending one where the other belongs is a silent 401."""

import unittest

from nrkarr.tmdb import Tmdb

V3_KEY = "e" * 32
V4_TOKEN = "eyJhbGciOiJIUzI1NiJ9.payload.signature"


class CredentialPlacementTest(unittest.TestCase):
    def test_v3_key_goes_in_the_query_string(self):
        client = Tmdb(V3_KEY)

        self.assertEqual(client._key_param(), {"api_key": V3_KEY})
        self.assertEqual(client._key_header(), {})

    def test_v4_token_goes_in_the_bearer_header(self):
        client = Tmdb(V4_TOKEN)

        self.assertEqual(client._key_param(), {})
        self.assertEqual(
            client._key_header(), {"Authorization": f"Bearer {V4_TOKEN}"}
        )
