# nrkarr

A Newznab indexer for [NRK TV](https://tv.nrk.no). Sonarr searches it
like any usenet indexer; what it hands back are releases whose
"NZB" carries a download spec for [ytdlparr](https://github.com/cathrinevaage/ytdlparr),
which fetches the episode with yt-dlp.

nrkarr knows nothing about downloading. ytdlparr knows nothing about NRK.

## How a search works

```
Sonarr   tvsearch?tvdbid=457520&season=1&ep=1
nrkarr   tvdbid  -> TMDB /find        -> original_name "LIS", original_language "no"
         "LIS"   -> psapi /search     -> serie/lis
         lis, 1  -> psapi /seasons/1  -> episodes with sequenceNumber, prfId
         -> LIS.S01E01.Nattevakt.1080p.NRK.WEB-DL.AAC2.0.H.264-Nrkarr
Sonarr   grabs -> GET /nzb/<token> -> faux NZB with the job spec -> ytdlparr
```

The TMDB hop exists because TVDB (and so Sonarr) holds the English
title - tvdb 457520 is "Still Breathing" - while NRK only knows the
series as "LIS". TMDB's `original_name` is the bridge.

Only NRK series whose title matches `original_name` exactly (ignoring
case) count. psapi's search is fuzzy, and a fuzzy hit for a series NRK
does not carry must never become a release. When several NRK series
share the exact title, the one whose production year matches TMDB's
first-air year wins; if none does, the search returns nothing rather
than guessing.

## RSS

Sonarr's RSS sync calls `tvsearch` with no `tvdbid`. There is no
mapping file: every series nrkarr successfully resolves is remembered
in `state`, and a bare search enumerates those, newest first, capped
at 100. A series becomes visible to RSS the first time Sonarr searches
for it.

## Setup

### Config

Copy [`config.example.yml`](config.example.yml) to `/config/config.yml`.
Only `tmdb.api_key` is required - a free
[TMDB API key](https://www.themoviedb.org/settings/api) (either the v3
key or the v4 read access token). Everything else has defaults.

| key | what |
|---|---|
| `server.api_key` | what Sonarr sends as `apikey` |
| `server.url_base` | prefix when behind a reverse proxy |
| `server.state` | the remembered-series file; keep it on the volume |
| `spec.*` | what goes in the job spec: format, subs, embed, container |
| `release.*` | release-name parts and the bitrate used for the size estimate |
| `cache.ttl` | seconds to cache psapi responses |

Sonarr acts on the advertised size, so `release.bitrate_mbps` should
be roughly right for the format in `spec.format`. NRK's 1080p streams
run 6-9 Mbps; the default of 5 sits under that.

### Environment overrides

Any scalar or list setting can be set from the environment as
`NRKARR_<SECTION>_<KEY>`, which wins over the file:

```
NRKARR_TMDB_API_KEY=...
NRKARR_SERVER_API_KEY=...
NRKARR_SERVER_STATE=/config/known-series.json
NRKARR_SPEC_SUBS=nb-nor,nb-ttv
```

With those two keys in the environment no config file is needed at
all; the defaults cover the rest.

### Compose

```yaml
services:
  nrkarr:
    image: ghcr.io/cathrinevaage/nrkarr:latest
    container_name: nrkarr
    restart: unless-stopped
    ports:
      - "9121:9121"
    volumes:
      - ./nrkarr:/config
```

### Sonarr

Settings → Indexers → Add → Newznab:

| field | value |
|---|---|
| URL | `http://nrkarr:9121` |
| API Path | `/api` |
| API Key | `server.api_key` |
| Categories | 5000 |
| **Download Client** | **ytdlparr** - not "Any" |

**The Download Client field is not optional.** What nrkarr serves as an
"NZB" is a job spec that only ytdlparr understands. Left on "Any",
Sonarr hands grabs to whichever usenet client it picks - and a real
SABnzbd or NZBGet given nrkarr's file fails the download with no
articles to fetch. Pin this indexer to ytdlparr.

The reverse - keeping real NZBs out of ytdlparr - needs no per-indexer
work: give your real usenet client a higher Client Priority than
ytdlparr. See [ytdlparr's README](https://github.com/cathrinevaage/ytdlparr#routing-only-job-specs-must-reach-ytdlparr).

NRK is geo-blocked to Norway. nrkarr's own lookups work from anywhere;
the fetch ytdlparr does must originate in Norway.

## The faux NZB

Newznab's download URL is opaque to Sonarr, so what nrkarr serves at
`/nzb/<token>` is NZB-shaped but carries a job spec:

```xml
<nzb xmlns="http://www.newzbin.com/DTD/2003/nzb">
  <head>
    <meta type="name">LIS - S01E01 - Nattevakt</meta>
    <meta type="ytdlpspec">{"url": "https://tv.nrk.no/se?v=MDRE23000124", ...}</meta>
  </head>
</nzb>
```

The token encodes only the programme id and the name; the rest of the
spec is assembled from `spec.*` when the NZB is rendered, so it is
stateless across restarts. The spec format is documented in
[ytdlparr](https://github.com/cathrinevaage/ytdlparr#the-job-spec).

## Development

```sh
python3 -m venv .venv && .venv/bin/pip install flask pyyaml
.venv/bin/python -m unittest discover -s tests -t .
NRKARR_CONFIG=config.yml .venv/bin/python -m nrkarr
```

The tests do not touch the network. The NRK API (`psapi.nrk.no`) is
public and needs no key, so anything in `psapi.py` can be tried by
hand.
