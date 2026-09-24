"""The Newznab endpoint, plus the faux NZB the client fetches."""

import logging
from urllib.parse import quote

from flask import Flask, Response, request

from . import nzb, releases
from .cache import TtlCache
from .http import FetchError
from .known_series import KnownSeries
from .naming import to_ascii
from .newznab import CAPS, feed
from .psapi import Psapi
from .resolve import Resolver, Unresolved
from .spec import SpecBuilder
from .tmdb import Tmdb

log = logging.getLogger(__name__)

XML = "application/xml; charset=utf-8"
NZB = "application/x-nzb; charset=utf-8"
RSS_LIMIT = 100


def create_app(config):
    app = Flask(__name__)

    cache = TtlCache(config["cache"]["ttl"])
    psapi = Psapi(config["nrk"]["base_url"], config["nrk"]["timeout"])
    tmdb = Tmdb(config["tmdb"]["api_key"])
    resolver = Resolver(tmdb, psapi, cache)
    known = KnownSeries(config["server"]["state"])
    specs = SpecBuilder(psapi, config["spec"])
    labels = release_labels(config)

    def labels_for(episode):
        """The codec in the name follows the programme, cached per id."""
        prf_id = episode["prfId"]
        codec = cache.get(f"codec:{prf_id}", lambda: specs.codec_label(prf_id))

        return {**labels, "video_codec": codec} if codec else labels

    def authorised():
        expected = config["server"]["api_key"]

        return not expected or request.args.get("apikey") == expected

    def download_url(token):
        base = config["server"]["url_base"].rstrip("/")

        return f"{request.host_url.rstrip('/')}{base}/nzb/{token}"

    def releases_for(series, wanted_season=None, wanted_episode=None):
        """Every available episode of a series, optionally narrowed to
        one season or one episode."""
        return [
            release
            for season in psapi.seasons(series.slug)
            if _season_wanted(season, wanted_season)
            for release in releases.build(
                series.title,
                series.tvdb_id,
                int(season["id"]),
                psapi.episodes(series.slug, season["id"]),
                labels_for,
                download_url,
            )
            if wanted_episode is None
            or release["episode"] == wanted_episode
        ]

    def targeted_search(tvdb_id):
        try:
            series = resolver.resolve(tvdb_id)
        except Unresolved as reason:
            log.info("tvdbid %s: %s", tvdb_id, reason)
            return []
        except FetchError as error:
            log.error("tvdbid %s: upstream failure: %s", tvdb_id, error)
            return []

        log.info("tvdbid %s -> %s (%s)", tvdb_id, series.slug, series.title)
        known.remember(series)

        return releases_for(
            series,
            request.args.get("season", type=int),
            request.args.get("ep", type=int),
        )

    def rss():
        """A bare search carries no tvdbid, so it enumerates the
        series Sonarr has already had resolved, newest first."""
        found = [
            release
            for tvdb_id, slug, title in known.all()
            for release in cache.get(
                f"rss:{slug}",
                lambda slug=slug, title=title, tvdb_id=tvdb_id: releases_for(
                    _series(tvdb_id, slug, title)
                ),
            )
        ]

        return sorted(
            found, key=lambda release: release["published"], reverse=True
        )[:RSS_LIMIT]

    @app.get("/api")
    def api():
        mode = request.args.get("t", "caps")

        if mode == "caps":
            return Response(CAPS, mimetype=XML)

        if not authorised():
            return Response("unauthorised", status=401)

        if mode not in ("tvsearch", "search"):
            return Response(f"unsupported mode {mode!r}", status=400)

        tvdb_id = request.args.get("tvdbid", type=int)

        try:
            found = rss() if tvdb_id is None else targeted_search(tvdb_id)
        except FetchError as error:
            log.error("search failed upstream: %s", error)
            found = []

        return Response(feed(found), mimetype=XML)

    @app.get("/nzb/<token>")
    def download(token):
        prf_id, name = releases.decode_token(token)
        spec = specs.build(prf_id, name)

        return Response(
            nzb.render(spec),
            mimetype=NZB,
            headers={"Content-Disposition": _disposition(name)},
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "known_series": len(known.all())}

    return app


def release_labels(config):
    """The release name says what the first audio track asks for."""
    audio = config["spec"].get("audio") or []
    labels = dict(config["release"])

    if audio and audio[0].get("channels") == 6:
        labels["audio_codec"] = labels.get("surround_audio_codec", "DD5.1")

    return labels


def _disposition(name):
    """HTTP headers are latin-1, and NRK titles are not. RFC 6266's
    filename* carries the real name; the plain filename is an ASCII
    fallback for anything that ignores it."""
    return (
        f'attachment; filename="{to_ascii(name)}.nzb"; '
        f"filename*=UTF-8''{quote(name)}.nzb"
    )


def _series(tvdb_id, slug, title):
    from .resolve import ResolvedSeries

    return ResolvedSeries(tvdb_id=tvdb_id, slug=slug, title=title)


def _season_wanted(season, wanted):
    """Season ids are numeric for real seasons; extra material was
    already filtered out by type."""
    if not season["id"].isdigit():
        return False

    return wanted is None or int(season["id"]) == wanted
