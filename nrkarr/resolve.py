"""The tvdbid -> slug join.

Sonarr queries by tvdbid; NRK knows slugs. The join is derived, not
hand-maintained: tvdbid -> original title -> psapi search -> slug.
"""

from dataclasses import dataclass

from .tmdb import original_title


class Unresolved(Exception):
    """No NRK series could be matched to this tvdbid."""


@dataclass(frozen=True)
class ResolvedSeries:
    tvdb_id: int
    slug: str
    title: str


def first_air_year(series):
    date = series.get("first_air_date") or ""

    return int(date[:4]) if date[:4].isdigit() else None


def exact_matches(hits, title):
    wanted = title.casefold()

    return [hit for hit in hits if hit.get("title", "").casefold() == wanted]


def has_rights(hit):
    return hit.get("hasRights", False)


class Resolver:
    def __init__(self, tmdb, psapi, cache):
        self.tmdb = tmdb
        self.psapi = psapi
        self.cache = cache

    def resolve(self, tvdb_id):
        """The NRK series behind a tvdbid, or raise Unresolved."""
        return self.cache.get(
            f"series:{tvdb_id}",
            lambda: self._resolve(tvdb_id),
        )

    def _resolve(self, tvdb_id):
        series = self.tmdb.find_by_tvdb_id(tvdb_id)

        if series is None:
            raise Unresolved(f"tvdbid {tvdb_id} unknown to TMDB")

        title = original_title(series)
        hits = [hit for hit in self.psapi.search(title) if has_rights(hit)]
        candidates = exact_matches(hits, title)

        if not candidates:
            raise Unresolved(f"no NRK series titled exactly {title!r}")

        slug = self._most_confident(candidates, first_air_year(series))

        return ResolvedSeries(tvdb_id=tvdb_id, slug=slug, title=title)

    def _most_confident(self, candidates, expected_year):
        """One exact title match is taken as read. Several are split
        on production year, because a common-word title can name more
        than one NRK series."""
        if len(candidates) == 1:
            return _slug(candidates[0])

        if expected_year is None:
            return _slug(candidates[0])

        for candidate in candidates:
            if self._production_year(_slug(candidate)) == expected_year:
                return _slug(candidate)

        raise Unresolved(
            f"{len(candidates)} NRK series matched, none from "
            f"{expected_year}"
        )

    def _production_year(self, slug):
        """psapi search hits carry no year; the episodes do."""
        seasons = self.psapi.seasons(slug)

        if not seasons:
            return None

        episodes = self.psapi.episodes(slug, seasons[0]["id"])

        return episodes[0].get("productionYear") if episodes else None


def _slug(hit):
    """psapi returns "serie/lis"; the catalogue wants "lis"."""
    return hit.get("url", "").split("/")[-1] or hit.get("id", "")
