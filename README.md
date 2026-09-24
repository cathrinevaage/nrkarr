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
| `spec.*` | what the job spec asks for - see [What gets downloaded](#what-gets-downloaded) |
| `release.*` | release-name parts and the bitrate used for the size estimate; `surround_audio_codec` is used when the first audio entry asks for six channels |
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
    user: ${PUID}:${PGID}
    environment:
      - TZ=${TZ}
      - NRKARR_SERVER_API_KEY=${NRKARR_API_KEY}
      - NRKARR_TMDB_API_KEY=${TMDB_API_KEY}
      - NRKARR_SERVER_STATE=/config/known-series.json
    ports:
      - "9121:9121"
    volumes:
      - ./nrkarr:/config
    restart: unless-stopped
```

The image has no PUID/PGID handling of its own; `user:` is how it runs
as your media user, and the `/config` directory must be writable by
that uid. With the two keys in the environment no config file is
needed.

## Adding it to Sonarr

Two routes. Either way, one setting in Sonarr is mandatory and is
covered after both.

### Directly

Settings → Indexers → Add → Newznab:

| field | value |
|---|---|
| URL | `http://nrkarr:9121` |
| API Path | `/api` |
| API Key | `NRKARR_API_KEY` |
| Categories | 5000 |
| Download Client | **ytdlparr** |

### Through Prowlarr

Indexers → Add → **Generic Newznab**:

| field | value |
|---|---|
| Url | `http://nrkarr:9121` - with the port; without it Prowlarr tries port 80 |
| API Path | `/api` |
| API Key | `NRKARR_API_KEY` |
| **Sync Profile** | one with **RSS and Automatic Search enabled** |
| Download Client | ytdlparr - governs grabs made from Prowlarr's own UI only |

**Check the Sync Profile.** The form pre-selects one, and if that is
an interactive-only profile the indexer syncs into Sonarr with RSS and
Automatic Search off: manual searches work, monitoring does nothing,
and nothing tells you why. What Sonarr ended up with:

```sh
curl -s -H "X-Api-Key: $SONARR_API_KEY" http://sonarr:8989/api/v3/indexer \
  | jq -c '.[] | select(.name | test("nrkarr")) | {enableRss, enableAutomaticSearch, enableInteractiveSearch, downloadClientId}'
```

All three should be `true`. Prowlarr forwards `tvdbid` to nrkarr, and
it preserves the Download Client pin (below) on every sync. Its own
search box sends free text with no `tvdbid`, so searching nrkarr from
Prowlarr returns nothing - search from Sonarr. Prowlarr's test search
reports "no results" until Sonarr's first search has populated the
[RSS](#rss) store; that is a warning, not a failure.

nrkarr advertises only TV categories, so Prowlarr syncs it to Sonarr
and skips Radarr on its own.

### The Download Client pin

In Sonarr, on the nrkarr indexer entry - the one added directly or the
one Prowlarr synced - set **Download Client** to ytdlparr. What nrkarr
serves as an "NZB" is a job spec only ytdlparr understands; left on
"Any", Sonarr hands the grab to whichever usenet client it picks, and
a real SABnzbd fails it with no articles to fetch. The reverse -
keeping real NZBs out of ytdlparr - needs no per-indexer work: give
your real usenet client a higher Client Priority than ytdlparr. See
[ytdlparr's README](https://github.com/cathrinevaage/ytdlparr#routing-only-job-specs-must-reach-ytdlparr).

### Custom format and score

Releases carry the group `Nrkarr`. A custom format matching it, scored
in every quality profile, is what makes Sonarr grab them - and the
score must clear each profile's *minimum custom format score*, or the
release is rejected as below minimum however good it is. Nothing else
in the release name earns points.

Create the format and score it 1000 in every profile, from anywhere
that can reach Sonarr:

```sh
S=http://sonarr:8989/api/v3; K="X-Api-Key: $SONARR_API_KEY"
if ! curl -s -H "$K" $S/customformat | jq -e '.[] | select(.name=="Nrkarr")' >/dev/null; then
  curl -s -H "$K" -H 'Content-Type: application/json' -X POST $S/customformat \
    -d '{"name":"Nrkarr","includeCustomFormatWhenRenaming":false,"specifications":[{"name":"Nrkarr","implementation":"ReleaseTitleSpecification","negate":false,"required":true,"fields":[{"name":"value","value":"-Nrkarr\\b"}]}]}' >/dev/null
fi
for id in $(curl -s -H "$K" $S/qualityprofile | jq '.[].id'); do
  curl -s -H "$K" $S/qualityprofile/$id \
    | jq '.formatItems |= map(if .name=="Nrkarr" then .score=1000 else . end)' \
    | curl -s -H "$K" -H 'Content-Type: application/json' -X PUT $S/qualityprofile/$id -d @- \
    | jq -c '{name, minFormatScore, nrkarr: [.formatItems[] | select(.name=="Nrkarr") | .score]}'
done
```

Sonarr adds a new format to every profile at score 0, which is why
the loop finds it everywhere. If recyclarr manages your profiles with
`reset_unmatched_scores` on, declare the score there instead, or it
is zeroed on the next sync.

### Checking it

Resolve a series by hand, from inside the container - `127.0.0.1`,
not `localhost`, which resolves to IPv6 first on IPv6-enabled compose
networks while the app listens on IPv4:

```sh
docker compose exec nrkarr sh -c 'wget -qO- "http://127.0.0.1:9121/api?t=tvsearch&tvdbid=457520&season=1&ep=1&apikey=$NRKARR_SERVER_API_KEY"'
```

One `<item>` back means the whole chain - TMDB, NRK, release naming -
works. The log says how each search resolved:

```
INFO nrkarr.app: tvdbid 457520 -> lis (LIS)
INFO nrkarr.app: tvdbid 81189: no NRK series titled exactly 'Breaking Bad'
```

NRK is geo-blocked to Norway. nrkarr's own lookups work from anywhere;
the fetch ytdlparr does must originate in Norway.

## What gets downloaded

Per episode nrkarr builds a [tracks-mode spec](https://github.com/cathrinevaage/ytdlparr#tracks-mode)
from what NRK actually publishes for that programme:

- **Video** - `spec.video.format`, default `bestvideo[height<=1080]`.
- **Audio** - `spec.audio` names channel counts, not selectors, because
  yt-dlp exposes neither channels nor bitrate for NRK's audio groups.
  nrkarr reads the programme's HLS master, finds the group with that
  many channels (the high-bitrate one when several have it) and emits
  `bestaudio[format_id^=<group>]`. Defaults: 5.1 as default track
  (optional - dropped when the programme has none), stereo required.
  NRK's 6-channel group is AC-3, hence `DD5.1` in the release name.
- **Synstolking** - NRK publishes audio description as a sibling
  programme, `<id>SYNS`, with the same cut. When it is playable its
  stereo track is added, titled per `spec.described_audio` and flagged
  `visual_impaired`.
- **Subtitles** - all renditions in the HLS master, which is where the
  plain "Norsk" track lives; yt-dlp never lists it because the NRK
  extractor fetches the master with subtitles stripped. Names come from
  NRK, `hearing_impaired` from the master's characteristics, `forced`
  from the name matching `spec.forced_title_pattern`. If the master
  cannot be read, psapi's two files are used (forced and SDH).

For episode 1 of LIS that is: 5.1, stereo, Synstolking; Norsk,
Norsk – kun ved annet språk (forced), Norsk – med lydbeskrivelser (SDH).
Episode 8 has no foreign dialogue and so no forced file; the list
follows the programme.

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
