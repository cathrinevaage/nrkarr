import unittest

from nrkarr.cache import TtlCache
from nrkarr.resolve import Resolver, Unresolved


class FakeTmdb:
    def __init__(self, series):
        self.series = series

    def find_by_tvdb_id(self, tvdb_id):
        return self.series


class FakePsapi:
    def __init__(self, hits, years=None):
        self.hits = hits
        self.years = years or {}

    def search(self, query):
        return self.hits

    def seasons(self, slug):
        return [{"id": "1"}]

    def episodes(self, slug, season_id):
        return [{"productionYear": self.years.get(slug)}]


NORWEGIAN = {
    "original_name": "LIS",
    "original_language": "no",
    "first_air_date": "2026-04-11",
}


def resolver(tmdb, psapi):
    return Resolver(tmdb, psapi, TtlCache(60))


class ResolverTest(unittest.TestCase):
    def test_takes_a_single_exact_match(self):
        subject = resolver(
            FakeTmdb(NORWEGIAN),
            FakePsapi([
                {"title": "LIS", "url": "serie/lis", "hasRights": True},
            ]),
        )

        self.assertEqual(subject.resolve(457520).slug, "lis")

    def test_never_falls_back_to_a_fuzzy_hit(self):
        """psapi search is fuzzy; a single inexact hit for a title NRK
        does not carry must not become a release."""
        subject = resolver(
            FakeTmdb({**NORWEGIAN, "original_name": "Breaking Bad"}),
            FakePsapi([
                {"title": "Bad", "url": "serie/bad", "hasRights": True},
            ]),
        )

        with self.assertRaises(Unresolved):
            subject.resolve(81189)

    def test_title_match_ignores_case(self):
        subject = resolver(
            FakeTmdb({**NORWEGIAN, "original_name": "Lis"}),
            FakePsapi([
                {"title": "LIS", "url": "serie/lis", "hasRights": True},
            ]),
        )

        self.assertEqual(subject.resolve(457520).slug, "lis")

    def test_ignores_hits_nrk_has_no_rights_to(self):
        subject = resolver(
            FakeTmdb(NORWEGIAN),
            FakePsapi([
                {"title": "LIS", "url": "serie/lis", "hasRights": False},
            ]),
        )

        with self.assertRaises(Unresolved):
            subject.resolve(457520)

    def test_breaks_a_common_word_tie_on_production_year(self):
        subject = resolver(
            FakeTmdb({**NORWEGIAN, "original_name": "Hjem"}),
            FakePsapi(
                [
                    {"title": "Hjem", "url": "serie/hjem-1990",
                     "hasRights": True},
                    {"title": "Hjem", "url": "serie/hjem-2026",
                     "hasRights": True},
                ],
                years={"hjem-1990": 1990, "hjem-2026": 2026},
            ),
        )

        self.assertEqual(subject.resolve(457520).slug, "hjem-2026")

    def test_refuses_a_tie_when_tmdb_has_no_first_air_date(self):
        """TMDB entries can carry an empty first_air_date; with nothing
        to split a tie on, return nothing rather than the first hit."""
        subject = resolver(
            FakeTmdb({**NORWEGIAN, "original_name": "Hjem", "first_air_date": ""}),
            FakePsapi([
                {"title": "Hjem", "url": "serie/a", "hasRights": True},
                {"title": "Hjem", "url": "serie/b", "hasRights": True},
            ]),
        )

        with self.assertRaises(Unresolved):
            subject.resolve(457520)

    def test_refuses_when_no_candidate_matches_the_year(self):
        subject = resolver(
            FakeTmdb({**NORWEGIAN, "original_name": "Hjem"}),
            FakePsapi(
                [
                    {"title": "Hjem", "url": "serie/a", "hasRights": True},
                    {"title": "Hjem", "url": "serie/b", "hasRights": True},
                ],
                years={"a": 1990, "b": 1991},
            ),
        )

        with self.assertRaises(Unresolved):
            subject.resolve(457520)


if __name__ == "__main__":
    unittest.main()
